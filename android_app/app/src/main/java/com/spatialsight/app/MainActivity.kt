package com.spatialsight.app

import android.Manifest
import android.content.Intent
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
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * MainActivity - Landscape Camera Streamer with MJPEG HTTP Server & Sensor Bridge.
 *
 * Design Specifications:
 * - Forced horizontal/landscape mode
 * - Rear camera (CameraSelector.DEFAULT_BACK_CAMERA)
 * - Matching Forest Green & Brass Gold styling (#15370D, #E5CD82, #FFF2B4)
 * - Clean UI: Top "SpatialSight" title, status "• Streaming", central [Start/Stop Streaming] button
 * - Zero emojis
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

    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            startCamera()
        } else {
            Toast.makeText(this, "Camera permission is required for streaming", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()

        // Initialize sensor service & stream server
        sensorService = SensorService(this)
        streamServer = MjpegStreamServer(STREAM_PORT)

        sensorService.onSensorUpdate = { data ->
            streamServer.pushSensorData(data)
        }

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

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder()
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .build()
                .also {
                    it.surfaceProvider = binding.previewView.surfaceProvider
                }

            val imageAnalysis = ImageAnalysis.Builder()
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()
                .also { analysis ->
                    analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        processFrame(imageProxy)
                    }
                }

            // Forced Rear / Back Camera as specified
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalysis
                )
                Log.i(TAG, "Rear camera started successfully in landscape mode")
                if (intent?.getBooleanExtra("auto_stream", false) == true) {
                    startStreaming()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Camera bind failed: ${e.message}", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }

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
            Log.e(TAG, "Frame processing error: ${e.message}", e)
        } finally {
            imageProxy.close()
        }
    }

    private fun imageProxyToBitmap(imageProxy: ImageProxy): Bitmap? {
        val yBuffer = imageProxy.planes[0].buffer
        val uBuffer = imageProxy.planes[1].buffer
        val vBuffer = imageProxy.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
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

        val rotation = imageProxy.imageInfo.rotationDegrees
        var finalBitmap: Bitmap? = bitmap
        if (rotation != 0 && bitmap != null) {
            val matrix = Matrix()
            matrix.postRotate(rotation.toFloat())
            finalBitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
            bitmap.recycle()
        }

        // Guarantee horizontal / landscape feed: if height > width, rotate 90 degrees to landscape
        if (finalBitmap != null && finalBitmap.height > finalBitmap.width) {
            val matrix = Matrix()
            matrix.postRotate(90f)
            val landscapeBitmap = Bitmap.createBitmap(
                finalBitmap, 0, 0, finalBitmap.width, finalBitmap.height, matrix, true
            )
            finalBitmap.recycle()
            finalBitmap = landscapeBitmap
        }

        return finalBitmap
    }

    private fun startStreaming() {
        if (isStreaming) return
        try {
            if (!streamServer.isAlive) {
                streamServer.start()
            }
            sensorService.start()
            isStreaming = true

            binding.btnToggleStream.text = "Stop Streaming"
            binding.btnToggleStream.setBackgroundResource(R.drawable.button_border_red)
            binding.streamingIndicatorLayout.visibility = View.VISIBLE
            binding.txtFps.visibility = View.VISIBLE

            Log.i(TAG, "Stream server started on port $STREAM_PORT")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start stream server: ${e.message}", e)
            Toast.makeText(this, "Failed to start server: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun stopStreaming() {
        try {
            streamServer.stop()
            sensorService.stop()
            isStreaming = false

            binding.btnToggleStream.text = "Start Streaming"
            binding.btnToggleStream.setBackgroundResource(R.drawable.button_border_gold)
            binding.streamingIndicatorLayout.visibility = View.GONE
            binding.txtFps.visibility = View.GONE

            Log.i(TAG, "Stream server stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping stream server: ${e.message}", e)
        }
    }

    private fun updateFpsDisplay() {
        binding.txtFps.text = "%.0f FPS".format(displayFps)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent?.getBooleanExtra("auto_stream", false) == true && !isStreaming) {
            startStreaming()
        }
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
