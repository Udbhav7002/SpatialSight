package com.spatialsight.app

import android.graphics.Bitmap
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import java.io.ByteArrayOutputStream
import java.io.PipedInputStream
import java.io.PipedOutputStream
import java.util.concurrent.atomic.AtomicReference

/**
 * Lightweight embedded HTTP server that streams the camera feed as MJPEG.
 *
 * Endpoints:
 *   GET /video   - MJPEG video stream (consumed by OpenCV on the Mac)
 *   GET /sensors - JSON with current rotation vector sensor data
 *   GET /status  - JSON health check
 *
 * The Mac connects to this server via ADB port forwarding:
 *   adb forward tcp:8080 tcp:8080
 *   Then: http://127.0.0.1:8080/video
 */
class MjpegStreamServer(
    port: Int = 8080
) : NanoHTTPD(port) {

    companion object {
        private const val TAG = "MjpegStreamServer"
        private const val BOUNDARY = "--spatialsight_boundary"
        private const val JPEG_QUALITY = 80
    }

    // Latest JPEG frame (thread-safe atomic reference)
    private val latestFrame = AtomicReference<ByteArray?>(null)

    // Latest sensor data (thread-safe atomic reference)
    private val latestSensorData = AtomicReference<SensorData>(SensorData())

    // Track number of active stream clients
    @Volatile
    var activeClients: Int = 0
        private set

    /**
     * Called by the camera callback to push a new frame.
     * Compresses the frame to JPEG and stores it for streaming.
     */
    fun pushFrame(bitmap: Bitmap) {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, stream)
        latestFrame.set(stream.toByteArray())
    }

    /**
     * Called by the camera callback to push a raw YUV frame.
     * More efficient than Bitmap conversion for CameraX ImageAnalysis.
     */
    fun pushYuvFrame(yuvData: ByteArray, width: Int, height: Int) {
        try {
            val yuvImage = YuvImage(yuvData, ImageFormat.NV21, width, height, null)
            val stream = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, width, height), JPEG_QUALITY, stream)
            latestFrame.set(stream.toByteArray())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to compress YUV frame", e)
        }
    }

    /**
     * Called by the sensor listener to push updated orientation data.
     */
    fun pushSensorData(data: SensorData) {
        latestSensorData.set(data)
    }

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri

        return when {
            uri == "/video" || uri == "/video/" -> serveMjpegStream()
            uri == "/sensors" || uri == "/sensors/" -> serveSensorData()
            uri == "/status" || uri == "/status/" -> serveStatus()
            uri == "/frame" || uri == "/frame/" -> serveSingleFrame()
            else -> newFixedLengthResponse(
                Response.Status.NOT_FOUND,
                "text/plain",
                "SpatialSight Camera Server\n\nEndpoints:\n" +
                    "  /video   - MJPEG stream\n" +
                    "  /frame   - Single JPEG frame\n" +
                    "  /sensors - Orientation sensor data (JSON)\n" +
                    "  /status  - Server health check\n"
            )
        }
    }

    /**
     * Serves a continuous MJPEG stream.
     * Each frame is sent as a multipart chunk with Content-Type: image/jpeg.
     * OpenCV's VideoCapture can read this directly.
     */
    private fun serveMjpegStream(): Response {
        val pipedOutput = PipedOutputStream()
        val pipedInput = PipedInputStream(pipedOutput, 1024 * 1024) // 1MB buffer

        activeClients++
        Log.i(TAG, "MJPEG client connected (active: $activeClients)")

        // Background thread to push frames into the pipe
        Thread({
            try {
                while (!Thread.interrupted()) {
                    val jpegData = latestFrame.get()
                    if (jpegData != null) {
                        val header = (
                            "$BOUNDARY\r\n" +
                            "Content-Type: image/jpeg\r\n" +
                            "Content-Length: ${jpegData.size}\r\n" +
                            "\r\n"
                        ).toByteArray()

                        pipedOutput.write(header)
                        pipedOutput.write(jpegData)
                        pipedOutput.write("\r\n".toByteArray())
                        pipedOutput.flush()
                    }
                    // Target ~30 FPS streaming rate
                    Thread.sleep(33)
                }
            } catch (e: Exception) {
                Log.d(TAG, "MJPEG stream ended: ${e.message}")
            } finally {
                activeClients--
                Log.i(TAG, "MJPEG client disconnected (active: $activeClients)")
                try { pipedOutput.close() } catch (_: Exception) {}
            }
        }, "MjpegStreamer").start()

        val response = newChunkedResponse(
            Response.Status.OK,
            "multipart/x-mixed-replace; boundary=$BOUNDARY",
            pipedInput
        )
        response.addHeader("Cache-Control", "no-cache, no-store, must-revalidate")
        response.addHeader("Pragma", "no-cache")
        response.addHeader("Access-Control-Allow-Origin", "*")
        return response
    }

    /**
     * Serves the latest sensor data as JSON.
     */
    private fun serveSensorData(): Response {
        val data = latestSensorData.get()
        val json = """
            {
                "yaw": ${data.yaw},
                "pitch": ${data.pitch},
                "roll": ${data.roll},
                "timestamp": ${data.timestamp},
                "accuracy": ${data.accuracy}
            }
        """.trimIndent()

        return newFixedLengthResponse(
            Response.Status.OK,
            "application/json",
            json
        ).apply {
            addHeader("Access-Control-Allow-Origin", "*")
        }
    }

    /**
     * Serves a single JPEG snapshot of the current frame.
     */
    private fun serveSingleFrame(): Response {
        val jpegData = latestFrame.get()
            ?: return newFixedLengthResponse(
                Response.Status.SERVICE_UNAVAILABLE,
                "text/plain",
                "No frame available yet"
            )

        return newFixedLengthResponse(
            Response.Status.OK,
            "image/jpeg",
            jpegData.inputStream(),
            jpegData.size.toLong()
        )
    }

    /**
     * Health check endpoint.
     */
    private fun serveStatus(): Response {
        val hasFrame = latestFrame.get() != null
        val sensor = latestSensorData.get()
        val json = """
            {
                "server": "SpatialSight Camera Server",
                "version": "1.0.0",
                "streaming": $hasFrame,
                "active_clients": $activeClients,
                "sensor_active": ${sensor.timestamp > 0},
                "yaw": ${sensor.yaw},
                "pitch": ${sensor.pitch}
            }
        """.trimIndent()

        return newFixedLengthResponse(Response.Status.OK, "application/json", json)
    }
}

/**
 * Data class holding the phone's orientation sensor readings.
 */
data class SensorData(
    val yaw: Float = 0f,      // Azimuth / horizontal rotation (0-360 deg)
    val pitch: Float = 0f,    // Vertical tilt (-90 deg to +90 deg)
    val roll: Float = 0f,     // Side tilt (-180 deg to +180 deg)
    val timestamp: Long = 0L, // System timestamp in milliseconds
    val accuracy: Int = 0     // Sensor accuracy (0=unreliable, 3=high)
)
