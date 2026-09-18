package com.attendly.parent

import android.app.Application
import com.attendly.parent.data.SessionStore
import com.attendly.parent.notify.Fcm
import com.attendly.parent.notify.Notify

class AttendlyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        SessionStore.init(this)
        Notify.ensureChannel(this)
        Fcm.ready(this)
    }
}
