package com.attendly.parent.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.attendly.parent.R
import com.attendly.parent.data.Api
import com.attendly.parent.data.PushItem
import com.attendly.parent.data.SessionStore
import com.attendly.parent.databinding.FragmentHomeBinding
import com.attendly.parent.notify.Notify
import kotlin.concurrent.thread

class HomeFragment : Fragment() {
    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        binding.refresh.setOnRefreshListener { load() }
        binding.signOut.setOnClickListener {
            thread {
                Api.logout()
                activity?.runOnUiThread {
                    startActivity(Intent(requireContext(), LoginActivity::class.java))
                    activity?.finish()
                }
            }
        }
        load()
    }

    private fun load() {
        binding.refresh.isRefreshing = true
        thread {
            val today = runCatching { Api.today() }.getOrNull()
            val feed = runCatching { Notify.poll(requireContext()) }.getOrDefault(emptyList())
            activity?.runOnUiThread {
                if (!isAdded) return@runOnUiThread
                binding.refresh.isRefreshing = false
                val present = today?.present == true
                binding.todayLabel.text = today?.date?.ifBlank { "Today" } ?: "Today"
                binding.status.text = if (present) "At school" else "Not marked present"
                binding.status.setTextColor(requireContext().getColor(if (present) R.color.present else R.color.absent))
                binding.statusCard.setBackgroundResource(
                    if (present) R.drawable.bg_status_present else R.drawable.bg_status_absent
                )
                binding.statusHint.text = if (present) {
                    "Marked present for ${SessionStore.selected()?.name ?: "your child"}."
                } else {
                    "No gate tap yet today."
                }
                binding.timeIn.text = today?.timeIn.orEmpty().ifBlank { "—" }
                binding.timeOut.text = today?.timeOut.orEmpty().ifBlank { "—" }
                renderFeed(feed)
            }
        }
    }

    private fun renderFeed(items: List<PushItem>) {
        binding.feed.removeAllViews()
        if (items.isEmpty()) {
            val empty = layoutInflater.inflate(R.layout.item_update, binding.feed, false)
            empty.findViewById<TextView>(R.id.title).text = "No updates yet"
            empty.findViewById<TextView>(R.id.whenText).text = "Pull down to refresh."
            empty.isClickable = false
            binding.feed.addView(empty)
            return
        }
        items.take(8).forEach { item ->
            val row = layoutInflater.inflate(R.layout.item_update, binding.feed, false)
            row.findViewById<TextView>(R.id.title).text = item.title
            row.findViewById<TextView>(R.id.whenText).text = Ui.niceWhen(item.createdAt)
            row.setOnClickListener {
                Ui.showMessage(requireContext(), item.title, item.body, Ui.niceWhen(item.createdAt))
            }
            binding.feed.addView(row)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
