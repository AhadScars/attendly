package com.attendly.parent.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.attendly.parent.R
import com.attendly.parent.data.Api
import com.attendly.parent.databinding.FragmentAlertsBinding
import kotlin.concurrent.thread

class AlertsFragment : Fragment() {
    private var _binding: FragmentAlertsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAlertsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        thread {
            val alerts = runCatching { Api.alerts() }.getOrDefault(emptyList())
            activity?.runOnUiThread {
                if (!isAdded) return@runOnUiThread
                binding.list.removeAllViews()
                if (alerts.isEmpty()) {
                    val empty = layoutInflater.inflate(R.layout.item_alert, binding.list, false)
                    empty.findViewById<TextView>(R.id.title).text = "No alerts yet"
                    empty.findViewById<TextView>(R.id.whenText).text = "School messages will appear here."
                    empty.isClickable = false
                    binding.list.addView(empty)
                    return@runOnUiThread
                }
                alerts.forEach { item ->
                    val row = layoutInflater.inflate(R.layout.item_alert, binding.list, false)
                    row.findViewById<TextView>(R.id.title).text = item.title
                    row.findViewById<TextView>(R.id.whenText).text = Ui.niceWhen(item.createdAt)
                    row.setOnClickListener {
                        Ui.showMessage(requireContext(), item.title, item.body, Ui.niceWhen(item.createdAt))
                    }
                    binding.list.addView(row)
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
