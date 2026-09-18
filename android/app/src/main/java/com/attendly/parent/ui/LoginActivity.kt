package com.attendly.parent.ui

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.attendly.parent.data.Api
import com.attendly.parent.data.SessionStore
import com.attendly.parent.databinding.ActivityLoginBinding
import com.attendly.parent.notify.Fcm
import kotlin.concurrent.thread

class LoginActivity : AppCompatActivity() {
    private lateinit var binding: ActivityLoginBinding

    private val notifyPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (SessionStore.signedIn()) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        if (Build.VERSION.SDK_INT >= 33) {
            notifyPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        binding.signIn.setOnClickListener { signIn() }
    }

    private fun signIn() {
        val school = binding.school.text?.toString().orEmpty().trim()
        val phone = binding.phone.text?.toString().orEmpty().trim()
        val dob = binding.dob.text?.toString().orEmpty().trim()
        if (school.isEmpty() || phone.isEmpty() || dob.isEmpty()) {
            showError("Fill school name, phone and date of birth.")
            return
        }
        binding.signIn.isEnabled = false
        binding.error.visibility = View.GONE
        thread {
            try {
                Api.login(school, phone, dob)
                val existing = runCatching { Api.notifications(0) }.getOrDefault(emptyList())
                if (existing.isNotEmpty()) {
                    SessionStore.lastNotifId = existing.maxOf { it.id }
                }
                Fcm.registerIfPossible(this)
                runOnUiThread {
                    startActivity(Intent(this, MainActivity::class.java))
                    finish()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    binding.signIn.isEnabled = true
                    showError(e.message ?: "Could not sign in")
                }
            }
        }
    }

    private fun showError(message: String) {
        binding.error.visibility = View.VISIBLE
        binding.error.text = message
    }
}
