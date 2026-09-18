package com.attendly.parent.ui

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.AdapterView
import androidx.appcompat.app.AppCompatActivity
import com.attendly.parent.R
import com.attendly.parent.data.Api
import com.attendly.parent.data.SessionStore
import com.attendly.parent.databinding.ActivityMainBinding
import com.attendly.parent.notify.Fcm
import com.attendly.parent.notify.Notify
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private val handler = Handler(Looper.getMainLooper())
    private var suppressSwitch = false
    private val poll = object : Runnable {
        override fun run() {
            thread {
                Notify.poll(this@MainActivity)
                handler.postDelayed(this, 15_000)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.schoolName.text = SessionStore.schoolName.ifBlank { "School" }
        Fcm.registerIfPossible(this)
        bindChildren()
        binding.bottom.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> show(HomeFragment())
                R.id.nav_calendar -> show(CalendarFragment())
                R.id.nav_alerts -> show(AlertsFragment())
            }
            true
        }
        if (savedInstanceState == null) {
            binding.bottom.selectedItemId = R.id.nav_home
            show(HomeFragment())
        }
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(poll)
        handler.post(poll)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(poll)
    }

    private fun bindChildren() {
        val kids = SessionStore.children()
        binding.childSwitch.adapter = ChildAdapter(this, kids)
        val selected = kids.indexOfFirst { it.id == SessionStore.selectedId }.coerceAtLeast(0)
        suppressSwitch = true
        binding.childSwitch.setSelection(selected)
        binding.childSwitch.isEnabled = kids.size > 1
        binding.childSwitch.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (suppressSwitch) {
                    suppressSwitch = false
                    return
                }
                val child = kids.getOrNull(position) ?: return
                if (child.id == SessionStore.selectedId) return
                thread {
                    runCatching { Api.switchChild(child.id) }
                    runOnUiThread { recreate() }
                }
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        suppressSwitch = false
    }

    private fun show(fragment: androidx.fragment.app.Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.container, fragment)
            .commit()
    }
}
