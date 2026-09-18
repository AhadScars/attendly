package com.attendly.parent.ui

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.ImageView
import android.widget.TextView
import com.attendly.parent.R
import com.attendly.parent.data.Child

class ChildAdapter(
    context: Context,
    private val items: List<Child>,
) : ArrayAdapter<Child>(context, 0, items) {

    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
        val view = convertView ?: LayoutInflater.from(context).inflate(R.layout.item_child_selected, parent, false)
        bind(view, items[position], selected = true)
        return view
    }

    override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View {
        val view = convertView ?: LayoutInflater.from(context).inflate(R.layout.item_child_dropdown, parent, false)
        bind(view, items[position], selected = false)
        return view
    }

    private fun bind(view: View, child: Child, selected: Boolean) {
        view.findViewById<TextView>(R.id.childName).text = child.name
        view.findViewById<TextView>(R.id.childMeta).text = Ui.classLabel(child.className)
        view.findViewById<ImageView>(R.id.chevron)?.visibility =
            if (selected && items.size > 1) View.VISIBLE else if (selected) View.GONE else View.GONE
    }
}
