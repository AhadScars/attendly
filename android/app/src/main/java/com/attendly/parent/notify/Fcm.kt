package com.attendly.parent.notify

import android.content.Context
import com.attendly.parent.data.Api
import com.attendly.parent.data.SessionStore
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging

object Fcm {
    fun ready(context: Context): Boolean {
        return runCatching {
            if (FirebaseApp.getApps(context).isEmpty()) {
                FirebaseApp.initializeApp(context) != null
            } else {
                true
            }
        }.getOrDefault(false)
    }

    fun registerIfPossible(context: Context) {
        if (!ready(context) || !SessionStore.signedIn()) return
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            val token = if (task.isSuccessful) task.result else null
            if (token.isNullOrBlank()) return@addOnCompleteListener
            SessionStore.fcmToken = token
            Thread { runCatching { Api.registerFcm(token) } }.start()
        }
    }
}
