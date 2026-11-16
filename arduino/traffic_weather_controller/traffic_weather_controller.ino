/*
 * SpatialSight — Universal Traffic Signal & Weather Controller
 * Supports all Arduino Uno digital pinouts (Pins 2-13):
 *   RED    -> Pins 13, 10, 7, 4
 *   YELLOW -> Pins 12,  9, 6, 3
 *   GREEN  -> Pins 11,  8, 5, 2
 *   RAIN   -> Analog Pin A0
 *
 * Firmware Behavior (aligned with Page 1 & Page 2 specification):
 * - Idle / Waiting for PC app / No camera connected:
 *     Sequentially cycles Red -> Yellow -> Green one at a time (S_WAITING).
 * - Streaming:
 *     Clear path:       Green LED ON
 *     Caution hazard:   Yellow LED ON
 *     Imminent hazard:  Red LED ON (0ms instant latency)
 * - Rain sensor ADC telemetry sent at 10Hz: "RAIN:<value>"
 * - Zero emojis in logs/serial.
 */

// Multi-pin definitions covering standard digital pin groupings
const int RED_PINS[]    = {13, 10, 7, 4};
const int YELLOW_PINS[] = {12,  9, 6, 3};
const int GREEN_PINS[]  = {11,  8, 5, 2};
const int NUM_PINS = 4;

#define PIN_RAIN A0

enum State {
  S_WAITING,   // Sequential Red -> Yellow -> Green cycle ("waiting for camera")
  S_GREEN,     // Clear path
  S_YELLOW,    // Caution hazard
  S_RED,       // Imminent hazard (0ms latency)
  S_BLINK_RED, // Flashing red
  S_ALL_ON,
  S_ALL_OFF,
  S_DEMO
};

State currentState = S_WAITING;

bool activeLow = false; // Normal (active high): HIGH=ON, LOW=OFF
unsigned long lastHeartbeat  = 0;
unsigned long lastSensorRead = 0;
unsigned long lastBlinkTime  = 0;
unsigned long lastCmdTime    = 0;
unsigned long waitStepTime   = 0;
int waitStep = 0; // 0=RED, 1=YELLOW, 2=GREEN

bool blinkState = false;
bool appActive  = false;
const unsigned long IDLE_TIMEOUT_MS = 5000;

void writePinGroup(const int pins[], int count, bool turnOn) {
  int level = activeLow ? (turnOn ? LOW : HIGH) : (turnOn ? HIGH : LOW);
  for (int i = 0; i < count; i++) {
    digitalWrite(pins[i], level);
  }
}

void setSignalOutputs(bool r, bool y, bool g) {
  writePinGroup(RED_PINS,    NUM_PINS, r);
  writePinGroup(YELLOW_PINS, NUM_PINS, y);
  writePinGroup(GREEN_PINS,  NUM_PINS, g);
}

void setup() {
  Serial.begin(115200);

  // Initialize all digital pins 2-13 as OUTPUT
  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(RED_PINS[i],    OUTPUT);
    pinMode(YELLOW_PINS[i], OUTPUT);
    pinMode(GREEN_PINS[i],  OUTPUT);
  }

  // Initial state: Start in S_WAITING (sequential Red -> Yellow -> Green)
  currentState = S_WAITING;
  waitStep = 0;
  waitStepTime = millis();
  setSignalOutputs(true, false, false); // Start with Red

  Serial.println("STATUS:READY");
}

int getRainReading() {
  long sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(PIN_RAIN);
    delay(1);
  }
  return sum / 5;
}

const int WATER_THRESHOLD = 30;

bool isWaterPresent() {
  return getRainReading() >= WATER_THRESHOLD;
}

void transitionTo(State target) {
  if (currentState == target) return;

  currentState = target;
  switch (target) {
    case S_WAITING:
      waitStep = 0;
      waitStepTime = millis();
      setSignalOutputs(true, false, false);
      break;
    case S_GREEN:
      setSignalOutputs(false, false, true);
      break;
    case S_YELLOW:
      setSignalOutputs(false, true, false);
      break;
    case S_RED:
      // 0ms latency for imminent collision safety
      setSignalOutputs(true, false, false);
      break;
    case S_BLINK_RED:
      setSignalOutputs(true, false, false);
      blinkState = true;
      lastBlinkTime = millis();
      break;
    case S_ALL_ON:
      setSignalOutputs(true, true, true);
      break;
    case S_ALL_OFF:
      setSignalOutputs(false, false, false);
      break;
    case S_DEMO:
      waitStep = 0;
      waitStepTime = millis();
      setSignalOutputs(false, false, true);
      break;
  }
}

void loop() {
  unsigned long now = millis();

  // Heartbeat every 2s
  if (now - lastHeartbeat >= 2000) {
    lastHeartbeat = now;
    Serial.println("STATUS:OK");
  }

  // Rain sensor reading at 10Hz
  if (now - lastSensorRead >= 100) {
    lastSensorRead = now;
    Serial.print("RAIN:");
    Serial.println(getRainReading());
  }

  // Process serial commands from PC app
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      lastCmdTime = now;
      appActive = true;

      if      (cmd == "WAITING" || cmd == "CYCLE" || cmd == "NO_CAMERA") transitionTo(S_WAITING);
      else if (cmd == "GREEN") {
        if (isWaterPresent()) {
          // Rule 1: Water detected -> keep light in YELLOW, DO NOT GO TO GREEN!
          transitionTo(S_YELLOW);
          Serial.println("GUARD:WATER_HOLD_YELLOW");
        } else {
          transitionTo(S_GREEN);
        }
      }
      else if (cmd == "YELLOW")    transitionTo(S_YELLOW);
      else if (cmd == "RED")       transitionTo(S_RED);
      else if (cmd == "BLINK_RED") transitionTo(S_BLINK_RED);
      else if (cmd == "ALL_ON")    transitionTo(S_ALL_ON);
      else if (cmd == "ALL_OFF")   transitionTo(S_ALL_OFF);
      else if (cmd == "DEMO")      transitionTo(S_DEMO);
      else if (cmd == "INVERT_ON") {
        activeLow = true;
        transitionTo(currentState);
      }
      else if (cmd == "INVERT_OFF") {
        activeLow = false;
        transitionTo(currentState);
      }
      else if (cmd == "PING") {
        // Keep-alive
      }
      else if (cmd == "RAIN") {
        Serial.print("RAIN:");
        Serial.println(getRainReading());
      }
    }
  }

  // Rule 1 Active Guard: If Green is currently ON but water touches the sensor, immediately promote to Yellow!
  if (currentState == S_GREEN && isWaterPresent()) {
    transitionTo(S_YELLOW);
    Serial.println("GUARD:WATER_DETECTED_YELLOW");
  }

  // Idle Watchdog: Return to S_WAITING if app closes or stops communicating for 5s
  if (appActive && (now - lastCmdTime >= IDLE_TIMEOUT_MS)) {
    appActive = false;
    transitionTo(S_WAITING);
  }

  // Sequential cycle for S_WAITING: Red (350ms) -> Yellow (350ms) -> Green (350ms) -> repeat
  if (currentState == S_WAITING && (now - waitStepTime >= 350)) {
    waitStepTime = now;
    waitStep = (waitStep + 1) % 3;
    if (waitStep == 0) {
      setSignalOutputs(true, false, false);   // Red
    } else if (waitStep == 1) {
      setSignalOutputs(false, true, false);  // Yellow
    } else {
      setSignalOutputs(false, false, true);  // Green
    }
  }

  // Blink red handler
  if (currentState == S_BLINK_RED && (now - lastBlinkTime >= 500)) {
    lastBlinkTime = now;
    blinkState = !blinkState;
    writePinGroup(RED_PINS, NUM_PINS, blinkState);
  }

  // Demo cycle handler
  if (currentState == S_DEMO && (now - waitStepTime >= 1000)) {
    waitStepTime = now;
    waitStep = (waitStep + 1) % 3;
    setSignalOutputs(waitStep == 2, waitStep == 1, waitStep == 0);
  }
}
