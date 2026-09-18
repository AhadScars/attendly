package com.attendly.parent.notify

import com.attendly.parent.data.Api
import com.attendly.parent.data.PushItem
import com.attendly.parent.data.SessionStore
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlin.concurrent.thread

class AttendlyFirebaseService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        SessionStore.fcmToken = token
        if (SessionStore.signedIn()) {
            thread { runCatching { Api.registerFcm(token) } }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        Notify.ensureChannel(this)
        val title = message.notification?.title
            ?: message.data["title"]
            ?: "Attendly"
        val body = message.notification?.body
            ?: message.data["body"]
            ?: ""
        val type = message.data["ntype"] ?: "alert"
        if (body.isBlank()) return
        Notify.show(
            this,
            PushItem(
                id = (System.currentTimeMillis() % Int.MAX_VALUE).toInt(),
                type = type,
                title = title,
                body = body,
                createdAt = "",
            ),
        )
    }
}
