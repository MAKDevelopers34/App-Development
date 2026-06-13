package com.example.mobile

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

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

                try {
                    val request = DownloadManager.Request(Uri.parse(url))
                        .setTitle(fileName)
                        .setDescription("Downloading Electric Bus Tracker report")
                        .setMimeType("application/pdf")
                        .setAllowedOverMetered(true)
                        .setAllowedOverRoaming(true)
                        .setNotificationVisibility(
                            DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
                        )
                        .setDestinationInExternalPublicDir(
                            Environment.DIRECTORY_DOWNLOADS,
                            fileName
                        )

                    if (!token.isNullOrBlank()) {
                        request.addRequestHeader("Authorization", "Bearer $token")
                    }

                    val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
                    val downloadId = manager.enqueue(request)
                    result.success(downloadId)
                } catch (error: Exception) {
                    result.error("DOWNLOAD_FAILED", error.message, null)
                }
            }
    }
}
