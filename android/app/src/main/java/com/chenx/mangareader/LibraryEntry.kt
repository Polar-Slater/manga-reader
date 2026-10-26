package com.chenx.mangareader

import org.json.JSONArray
import org.json.JSONObject

data class LibraryEntry(val source: String, val tree: Boolean, val title: String,
    val page: Int, val total: Int, val chapter: String, val lastRead: Long)

internal fun encodeLibrary(entries: List<LibraryEntry>): String = JSONArray().apply {
    entries.forEach { entry -> put(JSONObject().put("source", entry.source).put("tree", entry.tree)
        .put("title", entry.title).put("page", entry.page).put("total", entry.total)
        .put("chapter", entry.chapter).put("lastRead", entry.lastRead)) }
}.toString()

internal fun decodeLibrary(json: String): List<LibraryEntry> = try {
    val array = JSONArray(json)
    (0 until array.length()).mapNotNull { index ->
        try {
            val item = array.getJSONObject(index)
            LibraryEntry(item.getString("source"), item.getBoolean("tree"), item.getString("title"),
                item.getInt("page"), item.getInt("total"), item.getString("chapter"), item.getLong("lastRead"))
        } catch (_: Exception) { null }
    }.distinctBy { it.source }.sortedByDescending { it.lastRead }
} catch (_: Exception) { emptyList() }
