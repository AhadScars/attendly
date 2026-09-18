package com.attendly.parent.ui

import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.attendly.parent.R
import com.attendly.parent.data.Api
import com.attendly.parent.data.DayMark
import com.attendly.parent.databinding.FragmentCalendarBinding
import java.util.Calendar
import kotlin.concurrent.thread

class CalendarFragment : Fragment() {
    private var _binding: FragmentCalendarBinding? = null
    private val binding get() = _binding!!
    private var year = Calendar.getInstance().get(Calendar.YEAR)
    private var month = Calendar.getInstance().get(Calendar.MONTH) + 1

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentCalendarBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        binding.prev.setOnClickListener {
            month -= 1
            if (month < 1) { month = 12; year -= 1 }
            load()
        }
        binding.next.setOnClickListener {
            month += 1
            if (month > 12) { month = 1; year += 1 }
            load()
        }
        load()
    }

    private fun load() {
        thread {
            val chart = runCatching { Api.month(year, month) }.getOrNull()
            activity?.runOnUiThread {
                if (!isAdded) return@runOnUiThread
                binding.monthTitle.text = chart?.let { "${it.monthName} ${it.year}" } ?: "$month / $year"
                binding.summary.text = if (chart == null) {
                    "Could not load this month."
                } else {
                    "Present ${chart.present}   ·   Absent ${chart.absent}"
                }
                draw(chart?.days.orEmpty())
            }
        }
    }

    private fun draw(days: List<DayMark>) {
        binding.grid.removeAllViews()
        listOf("M", "T", "W", "T", "F", "S", "S").forEach { label ->
            binding.grid.addView(cell(label, Color.TRANSPARENT, ContextCompat.getColor(requireContext(), R.color.muted)))
        }
        val firstWeekday = days.firstOrNull()?.weekday ?: 0
        repeat(firstWeekday) {
            binding.grid.addView(cell("", Color.TRANSPARENT, Color.TRANSPARENT))
        }
        days.forEach { day ->
            val bg = when (day.status) {
                "present" -> ContextCompat.getColor(requireContext(), R.color.present_bg)
                "absent" -> ContextCompat.getColor(requireContext(), R.color.absent_bg)
                else -> Color.TRANSPARENT
            }
            val fg = when (day.status) {
                "present" -> ContextCompat.getColor(requireContext(), R.color.present)
                "absent" -> ContextCompat.getColor(requireContext(), R.color.absent)
                else -> ContextCompat.getColor(requireContext(), R.color.muted)
            }
            binding.grid.addView(cell(day.day.toString(), bg, fg))
        }
    }

    private fun cell(text: String, bg: Int, fg: Int): TextView {
        val size = ((resources.displayMetrics.widthPixels - 48 * resources.displayMetrics.density) / 7).toInt()
        return TextView(requireContext()).apply {
            this.text = text
            gravity = Gravity.CENTER
            setTextColor(fg)
            setBackgroundColor(bg)
            textSize = 13f
            layoutParams = android.widget.GridLayout.LayoutParams().apply {
                width = size
                height = size
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
