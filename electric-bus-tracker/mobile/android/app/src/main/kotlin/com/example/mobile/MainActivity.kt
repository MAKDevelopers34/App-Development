package com.example.mobile

import android.content.ContentValues
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : FlutterActivity() {
    private val channelName = "electric_bus_tracker/downloads"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                if (call.method != "downloadPdf") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }

                val url = call.argument<String>("url")
                val fileName = call.argument<String>("fileName") ?: "report.pdf"
                val token = call.argument<String>("token")

                if (url.isNullOrBlank()) {
                    result.error("INVALID_URL", "Download URL is required", null)
                    return@setMethodCallHandler
                }

                Thread {
                    try {
                        val savedUri = downloadPdf(url, fileName, token)
                        runOnUiThread { result.success(savedUri.toString()) }
                    } catch (error: Exception) {
                        runOnUiThread {
                            result.error("DOWNLOAD_FAILED", error.message, null)
                        }
                    }
                }.start()
            }
    }

    private fun downloadPdf(url: String, fileName: String, token: String?): Uri {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 20000
            readTimeout = 30000
            setRequestProperty("Accept", "application/pdf")
            if (!token.isNullOrBlank()) {
                setRequestProperty("Authorization", "Bearer $token")
            }
        }

        connection.connect()
        val responseCode = connection.responseCode
        if (responseCode !in 200..299) {
            val message = connection.errorStream?.bufferedReader()?.use { it.readText() }
            connection.disconnect()
            throw IllegalStateException("Server returned $responseCode${message?.let { ": $it" } ?: ""}")
        }

        val safeFileName = if (fileName.lowercase().endsWith(".pdf")) fileName else "$fileName.pdf"

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val resolver = applicationContext.contentResolver
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, safeFileName)
                put(MediaStore.Downloads.MIME_TYPE, "application/pdf")
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                put(MediaStore.Downloads.IS_PENDING, 1)
            }

            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: throw IllegalStateException("Could not create Downloads file")

            try {
                resolver.openOutputStream(uri)?.use { output ->
                    connection.inputStream.use { input -> input.copyTo(output) }
                } ?: throw IllegalStateException("Could not open Downloads file")

                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
                uri
            } catch (error: Exception) {
                resolver.delete(uri, null, null)
                throw error
            } finally {
                connection.disconnect()
            }
        } else {
            try {
                val downloadsDir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS
                )
                if (!downloadsDir.exists()) {
                    downloadsDir.mkdirs()
                }
                val file = File(downloadsDir, safeFileName)
                FileOutputStream(file).use { output ->
                    connection.inputStream.use { input -> input.copyTo(output) }
                }
                Uri.fromFile(file)
            } finally {
                connection.disconnect()
            }
        }
    }
}
