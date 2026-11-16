package com.spatialsight.app

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log
import kotlin.math.abs

/**
 * Manages the phone's orientation sensors (rotation vector).
 *
 * Uses TYPE_ROTATION_VECTOR which fuses gyroscope + accelerometer + magnetometer
 * for drift-free yaw/pitch/roll readings. This is critical for the Room Map mode
 * where we need accurate camera orientation to trigger keyframes and deduplicate objects.
 *
 * Raw accelerometer double-integration drifts catastrophically (meters in seconds).
 * Rotation vector has NO drift because it's gravity + magnetic-field referenced.
 */
class SensorService(context: Context) : SensorEventListener {

    companion object {
        private const val TAG = "SensorService"
        private const val SENSOR_DELAY = SensorManager.SENSOR_DELAY_UI // ~60Hz
    }

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val rotationSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
    private val rotationMatrix = FloatArray(9)
    private val orientationAngles = FloatArray(3)

    // Callback to push sensor data to the MJPEG server
    var onSensorUpdate: ((SensorData) -> Unit)? = null

    // Latest readings
    @Volatile
    var currentData: SensorData = SensorData()
        private set

    // Sensor availability
    val isAvailable: Boolean
        get() = rotationSensor != null

    /**
     * Start listening for orientation sensor updates.
     */
    fun start() {
        if (rotationSensor == null) {
            Log.w(TAG, "Rotation vector sensor NOT available on this device")
            return
        }

        sensorManager.registerListener(this, rotationSensor, SENSOR_DELAY)
        Log.i(TAG, "Sensor listener started (TYPE_ROTATION_VECTOR)")
    }

    /**
     * Stop listening for sensor updates. Call in onPause/onDestroy.
     */
    fun stop() {
        sensorManager.unregisterListener(this)
        Log.i(TAG, "Sensor listener stopped")
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_ROTATION_VECTOR) return

        // Convert rotation vector to rotation matrix
        SensorManager.getRotationMatrixFromVector(rotationMatrix, event.values)

        // Extract orientation angles (in radians)
        SensorManager.getOrientation(rotationMatrix, orientationAngles)

        // Convert to degrees
        // orientationAngles[0] = azimuth (yaw): -pi to pi -> 0 deg to 360 deg
        // orientationAngles[1] = pitch: -pi/2 to pi/2 -> -90 deg to 90 deg
        // orientationAngles[2] = roll: -pi to pi -> -180 deg to 180 deg
        val yawDeg = ((Math.toDegrees(orientationAngles[0].toDouble()) + 360) % 360).toFloat()
        val pitchDeg = Math.toDegrees(orientationAngles[1].toDouble()).toFloat()
        val rollDeg = Math.toDegrees(orientationAngles[2].toDouble()).toFloat()

        val data = SensorData(
            yaw = yawDeg,
            pitch = pitchDeg,
            roll = rollDeg,
            timestamp = System.currentTimeMillis(),
            accuracy = event.accuracy
        )

        currentData = data
        onSensorUpdate?.invoke(data)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        val level = when (accuracy) {
            SensorManager.SENSOR_STATUS_ACCURACY_HIGH -> "HIGH"
            SensorManager.SENSOR_STATUS_ACCURACY_MEDIUM -> "MEDIUM"
            SensorManager.SENSOR_STATUS_ACCURACY_LOW -> "LOW"
            SensorManager.SENSOR_STATUS_UNRELIABLE -> "UNRELIABLE"
            else -> "UNKNOWN"
        }
        Log.d(TAG, "Sensor accuracy changed: $level")
    }

    /**
     * Check if the phone has moved significantly since last reading.
     * Useful for the UI to show movement indicators.
     */
    fun hasSignificantMovement(previousData: SensorData, yawThreshold: Float = 5f): Boolean {
        val deltaYaw = abs(angleDiff(currentData.yaw, previousData.yaw))
        return deltaYaw >= yawThreshold
    }

    /**
     * Shortest angular difference handling wraparound (350 deg -> 10 deg = 20 deg).
     */
    private fun angleDiff(a: Float, b: Float): Float {
        return ((a - b + 180f) % 360f) - 180f
    }
}
