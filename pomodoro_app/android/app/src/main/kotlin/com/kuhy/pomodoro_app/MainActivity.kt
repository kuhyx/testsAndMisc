package com.kuhy.pomodoro_app

import android.content.Context
import android.net.wifi.WifiManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var multicastLock: WifiManager.MulticastLock? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "pomodoro_multicast_lock"
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "acquire" -> {
                    val wifi = applicationContext
                        .getSystemService(Context.WIFI_SERVICE) as WifiManager
                    multicastLock = wifi.createMulticastLock("pomodoro_sync")
                    multicastLock?.setReferenceCounted(true)
                    multicastLock?.acquire()
                    result.success(true)
                }
                "release" -> {
                    multicastLock?.release()
                    multicastLock = null
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onDestroy() {
        multicastLock?.release()
        multicastLock = null
        super.onDestroy()
    }
}
