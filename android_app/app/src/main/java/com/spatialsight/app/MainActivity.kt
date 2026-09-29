package com.spatialsight.app

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.YuvImage
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.spatialsight.app.databinding.ActivityMainBinding
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Main Activity — Camera preview with MJPEG streaming and sensor data.
 *
 * Architecture:
 *   1. CameraX captures 720p frames at 30 FPS.
 *   2. ImageAnalysis callback compresses frames to JPEG.
 *   3. MjpegStreamServer serves frames over HTTP on localhost:8080.
 *   4. SensorService provides rotation vector orientation data.
 *   5. Mac connects via ADB: `adb forward tcp:8080 tcp:8080`
 *      then opens http://127.0.0.1:8080/video with OpenCV.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "SpatialSight"
        private const val STREAM_PORT = 8080
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var streamServer: MjpegStreamServer
    private lateinit var sensorService: SensorService

    private var isStreaming = false
    private var frameCount = 0L
    private var lastFpsTime = System.currentTimeMillis()
    private var displayFps = 0f

    // Camera permission request
    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startCamera()
        } else {
            Toast.makeText(this, "Camera permission is required", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()

        // Initialize sensor service
        sensorService = SensorService(this)

        // Initialize MJPEG stream server
        streamServer = MjpegStreamServer(STREAM_PORT)

        // Wire sensor data to stream server
        sensorService.onSensorUpdate = { data ->
            streamServer.pushSensorData(data)
            // Update UI on main thread
            runOnUiThread { updateSensorDisplay(data) }
        }

        // Set up UI buttons
        setupUI()

        // Check camera permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startCamera()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun setupUI() {
        binding.btnToggleStream.setOnClickListener {
            if (isStreaming) {
                stopStreaming()
            } else {
                startStreaming()
            }
        }
    }

    /**
     * Start the CameraX preview and image analysis pipeline.
     */
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // Preview use case — shows camera feed on screen
            val preview = Preview.Builder()
                .setTargetResolution(android.util.Size(1280, 720))
                .build()
                .also {
                    it.surfaceProvider = binding.previewView.surfaceProvider
                }

            // ImageAnalysis use case — captures frames for MJPEG streaming
            val imageAnalysis = ImageAnalysis.Builder()
                .setTargetResolution(android.util.Size(1280, 720))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()
                .also { analysis ->
                    analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        processFrame(imageProxy)
                    }
                }

            // Use back camera
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalysis
                )
                Log.i(TAG, "Camera started successfully")
                updateStatus("Camera ready — tap Start to stream")
            } catch (e: Exception) {
                Log.e(TAG, "Camera bind failed", e)
                updateStatus("Camera error: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    /**
     * Process each camera frame — compress to JPEG and push to the stream server.
     */
    private fun processFrame(imageProxy: ImageProxy) {
        if (!isStreaming) {
            imageProxy.close()
            return
        }

        try {
            val bitmap = imageProxyToBitmap(imageProxy)
            if (bitmap != null) {
                streamServer.pushFrame(bitmap)
                bitmap.recycle()

                // FPS counter
                frameCount++
                val now = System.currentTimeMillis()
                val elapsed = now - lastFpsTime
                if (elapsed >= 1000) {
                    displayFps = (frameCount * 1000f) / elapsed
                    frameCount = 0
                    lastFpsTime = now
                    runOnUiThread { updateFpsDisplay() }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Frame processing error", e)
        } finally {
            imageProxy.close()
        }
    }

    /**
     * Convert CameraX ImageProxy (YUV_420_888) to a Bitmap.
     */
    private fun imageProxyToBitmap(imageProxy: ImageProxy): Bitmap? {
        val yBuffer = imageProxy.planes[0].buffer
        val uBuffer = imageProxy.planes[1].buffer
        val vBuffer = imageProxy.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)

        // YUV_420_888 → NV21
        yBuffer.get(nv21, 0, ySize)
        vBuffer.get(nv21, ySize, vSize)
        uBuffer.get(nv21, ySize + vSize, uSize)

        val yuvImage = YuvImage(
            nv21, ImageFormat.NV21,
            imageProxy.width, imageProxy.height, null
        )

        val out = ByteArrayOutputStream()
        yuvImage.compressToJpeg(
            android.graphics.Rect(0, 0, imageProxy.width, imageProxy.height),
            80, out
        )

        val jpegBytes = out.toByteArray()
        val bitmap = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)

        // Handle rotation if needed
        val rotation = imageProxy.imageInfo.rotationDegrees
        if (rotation != 0 && bitmap != null) {
            val matrix = Matrix()
            matrix.postRotate(rotation.toFloat())
            val rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
            bitmap.recycle()
            return rotated
        }

        return bitmap
    }

    /**
     * Start the MJPEG stream server and sensor service.
     */
    private fun startStreaming() {
        try {
            streamServer.start()
            sensorService.start()
            isStreaming = true

            binding.btnToggleStream.text = "Stop Streaming"
            binding.btnToggleStream.setBackgroundColor(
                ContextCompat.getColor(this, android.R.color.holo_red_dark)
            )
            updateStatus("Streaming on port $STREAM_PORT — Connect Mac via USB")
            binding.connectionIndicator.visibility = View.VISIBLE

            Log.i(TAG, "Stream server started on port $STREAM_PORT")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start stream server", e)
            updateStatus("Error: ${e.message}")
        }
    }

    /**
     * Stop the MJPEG stream server and sensor service.
     */
    private fun stopStreaming() {
        streamServer.stop()
        sensorService.stop()
        isStreaming = false

        binding.btnToggleStream.text = "Start Streaming"
        binding.btnToggleStream.setBackgroundColor(
            ContextCompat.getColor(this, android.R.color.holo_green_dark)
        )
        updateStatus("Streaming stopped")
        binding.connectionIndicator.visibility = View.GONE
        binding.txtFps.text = ""

        Log.i(TAG, "Stream server stopped")
    }

    private fun updateStatus(message: String) {
        binding.txtStatus.text = message
    }

    private fun updateFpsDisplay() {
        binding.txtFps.text = "%.0f FPS | Clients: %d".format(
            displayFps, streamServer.activeClients
        )
    }

    private fun updateSensorDisplay(data: SensorData) {
        binding.txtSensor.text = "Yaw: %.1f° | Pitch: %.1f° | Roll: %.1f°".format(
            data.yaw, data.pitch, data.roll
        )
    }

    override fun onResume() {
        super.onResume()
        if (isStreaming) {
            sensorService.start()
        }
    }

    override fun onPause() {
        super.onPause()
        sensorService.stop()
    }

    override fun onDestroy() {
        super.onDestroy()
        stopStreaming()
        cameraExecutor.shutdown()
    }
}
