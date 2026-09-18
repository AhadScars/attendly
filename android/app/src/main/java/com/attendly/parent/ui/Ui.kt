package com.attendly.parent.ui

import android.content.Context
import com.google.android.material.dialog.MaterialAlertDialogBuilder

object Ui {
    fun classLabel(raw: String?): String {
        val value = raw.orEmpty().trim()
        if (value.isEmpty()) return ""
        return if (value.startsWith("Class", ignoreCase = true)) value else "Class $value"
    }

    fun niceWhen(raw: String?): String {
        val value = raw.orEmpty().trim()
        if (value.isEmpty()) return ""
        return value.replace('T', ' ').take(16)
    }

    fun showMessage(context: Context, title: String, body: String, whenText: String = "") {
        val message = if (whenText.isBlank()) body else "$body\n\n$whenText"
        MaterialAlertDialogBuilder(context)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("Close", null)
            .show()
    }
}
