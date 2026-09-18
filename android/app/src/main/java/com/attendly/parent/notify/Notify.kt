package com.attendly.parent.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.attendly.parent.R
import com.attendly.parent.data.Api
import com.attendly.parent.data.PushItem
import com.attendly.parent.data.SessionStore

object Notify {
    private const val CHANNEL = "attendly_parent"

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val mgr = context.getSystemService(NotificationManager::class.java)
            mgr.createNotificationChannel(
                NotificationChannel(CHANNEL, "School updates", NotificationManager.IMPORTANCE_HIGH)
            )
        }
    }

    fun poll(context: Context): List<PushItem> {
        if (!SessionStore.signedIn()) return emptyList()
        val items = runCatching { Api.notifications(SessionStore.lastNotifId) }.getOrDefault(emptyList())
        val fresh = items.filter { it.id > SessionStore.lastNotifId }.sortedBy { it.id }
        val useFcm = SessionStore.serverFcm && Fcm.ready(context)
        if (!useFcm) {
            fresh.forEach { show(context, it) }
        }
        if (fresh.isNotEmpty()) SessionStore.lastNotifId = fresh.maxOf { it.id }
        return items
    }

    fun show(context: Context, item: PushItem) {
        val note = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_alerts)
            .setContentTitle(item.title)
            .setContentText(item.body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(item.body))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        runCatching { NotificationManagerCompat.from(context).notify(item.id, note) }
    }
}
