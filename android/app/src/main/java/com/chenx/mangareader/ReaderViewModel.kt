package com.chenx.mangareader

import android.app.Application
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

data class Bookmark(val name: String, val source: String, val tree: Boolean, val page: String)
data class RenderedPage(val index: Int, val bitmap: Bitmap? = null, val error: String? = null)

class ReaderViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("reader", 0)
    private val library = Library(app.contentResolver)
    private val renderLock = Mutex()
    var pages by mutableStateOf<List<MangaPage>>(emptyList()); private set
    var index by mutableStateOf(0); private set
    var renderedPages by mutableStateOf<List<RenderedPage>>(emptyList()); private set
    var twoPage by mutableStateOf(false); private set
    var separateCover by mutableStateOf(false); private set
    var libraryVisible by mutableStateOf(true); private set
    var libraryEntries by mutableStateOf(decodeLibrary(prefs.getString("library", "[]") ?: "[]")); private set
    var coverRevision by mutableStateOf(0); private set
    private var chapters: List<String> = emptyList()
    val visibleIndices get() = visiblePages(chapters, index, twoPage, separateCover)
    val canGoPrevious get() = visibleIndices.firstOrNull()?.let { it > 0 } ?: false
    val canGoNext get() = visibleIndices.lastOrNull()?.let { it < pages.lastIndex } ?: false
    var busy by mutableStateOf(false); private set
    var rendering by mutableStateOf(false); private set
    var message by mutableStateOf<String?>(null); private set
    var rtl by mutableStateOf(prefs.getBoolean("rtl", false)); private set
    var bookmarks by mutableStateOf(readBookmarks()); private set
    private var source = ""
    private var tree = true
    private var scanJob: Job? = null
    private var renderJob: Job? = null
    val current get() = pages.getOrNull(index)

    init {
        if (libraryEntries.isEmpty()) prefs.getString("lastSource", null)?.let {
            open(Uri.parse(it), prefs.getBoolean("lastTree", true), showReader = false)
        }
    }

    fun pick(uri: Uri, isTree: Boolean) {
        try {
            getApplication<Application>().contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            open(uri, isTree)
        } catch (e: Exception) {
            message = "Access could not be saved. Choose a local folder or PDF using the system picker."
        }
    }

    fun open(uri: Uri, isTree: Boolean, targetPage: String? = null, showReader: Boolean = true) {
        scanJob?.cancel()
        renderJob?.cancel()
        rendering = false
        busy = true
        message = null
        renderedPages = emptyList()
        pages = emptyList()
        chapters = emptyList()
        scanJob = viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) { library.scan(uri, isTree) }
                source = uri.toString()
                tree = isTree
                separateCover = prefs.getBoolean("cover:$source", false)
                pages = result.pages
                chapters = pages.map { it.chapter }
                val saved = targetPage ?: prefs.getString("position:$source", null)
                index = pages.indexOfFirst { it.key == saved }.coerceAtLeast(0)
                if (pages.isNotEmpty()) {
                    val title = if (tree) pages.first().chapter.substringBefore(" / ") else pages.first().chapter
                    val entry = LibraryEntry(source, tree, title, index + 1, pages.size,
                        pages[index].chapter, System.currentTimeMillis())
                    libraryEntries = listOf(entry) + libraryEntries.filterNot { it.source == source }
                    persistLibrary()
                    libraryVisible = !showReader
                    val firstPage = pages.first()
                    val coverFile = coverFile(source)
                    // Thumbnail creation is independent of reading; failure leaves a placeholder.
                    viewModelScope.launch {
                        withContext(Dispatchers.IO) {
                            try {
                                if (!coverFile.exists()) renderLock.withLock {
                                    val cover = library.render(firstPage, 480)
                                    try {
                                        coverFile.parentFile?.mkdirs()
                                        coverFile.outputStream().use { cover.compress(Bitmap.CompressFormat.JPEG, 85, it) }
                                    } finally { cover.recycle() }
                                }
                            } catch (e: CancellationException) { throw e }
                            catch (_: Exception) { coverFile.delete() }
                        }
                        coverRevision++
                    }
                }
                prefs.edit().putString("lastSource", source).putBoolean("lastTree", tree).apply()
                message = when {
                    pages.isEmpty() -> "No readable images or PDFs found. Choose a folder containing manga pages."
                    targetPage != null && pages.none { it.key == targetPage } -> "The bookmarked page was moved or removed. Opened the first page."
                    result.warnings.isNotEmpty() -> result.warnings.joinToString("\n")
                    else -> null
                }
                showPage()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                message = "Cannot open this source. It may have moved or access was lost. Please select it again."
            } finally { if (currentCoroutineContext().isActive) busy = false }
        }
    }

    fun goTo(page: Int) {
        if (page !in pages.indices || page == index) return
        index = page
        showPage()
    }
    fun move(delta: Int) = goTo(turnPage(chapters, index, twoPage, delta, separateCover))
    fun toggleSeparateCover() {
        separateCover = !separateCover
        prefs.edit().putBoolean("cover:$source", separateCover).apply()
        showPage()
    }
    fun showLibrary() {
        scanJob?.cancel()
        renderJob?.cancel()
        rendering = false
        renderedPages = emptyList()
        busy = false
        libraryVisible = true
    }
    fun resume(entry: LibraryEntry) {
        if (source == entry.source && pages.isNotEmpty()) {
            libraryVisible = false
            showPage()
        }
        else open(Uri.parse(entry.source), entry.tree)
    }
    fun removeFromLibrary(entry: LibraryEntry) {
        libraryEntries = libraryEntries.filterNot { it.source == entry.source }
        persistLibrary()
        if (prefs.getString("lastSource", null) == entry.source) prefs.edit().remove("lastSource").apply()
    }
    fun coverFile(source: String): File {
        val hash = MessageDigest.getInstance("SHA-256").digest(source.toByteArray()).joinToString("") { "%02x".format(it) }
        return File(getApplication<Application>().filesDir, "covers/$hash.jpg")
    }
    private fun persistLibrary() { prefs.edit().putString("library", encodeLibrary(libraryEntries)).apply() }
    fun updateTwoPageMode(enabled: Boolean) {
        if (twoPage == enabled) return
        twoPage = enabled
        if (!libraryVisible) showPage(recordProgress = false)
    }
    fun retry() = showPage()
    fun dismissMessage() { message = null }
    fun toggleRtl() {
        rtl = !rtl
        prefs.edit().putBoolean("rtl", rtl).apply()
    }
    private fun showPage(recordProgress: Boolean = true) {
        renderJob?.cancel()
        rendering = false
        renderedPages = emptyList()
        val page = current ?: return
        if (libraryVisible) return
        val targets = visibleIndices.map { it to pages[it] }
        if (recordProgress) {
            prefs.edit().putString("position:$source", page.key).apply()
            libraryEntries = libraryEntries.map {
                if (it.source == source) it.copy(page = index + 1, chapter = page.chapter, lastRead = System.currentTimeMillis()) else it
            }.sortedByDescending { it.lastRead }
            persistLibrary()
        }
        rendering = true
        renderJob = viewModelScope.launch {
            try {
                for ((pageIndex, target) in targets) {
                    val rendered = try {
                        val bitmap = withContext(Dispatchers.IO) { renderLock.withLock { library.render(target) } }
                        RenderedPage(pageIndex, bitmap)
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        RenderedPage(pageIndex, error = "Could not read this page. Retry or continue to the next page.")
                    }
                    renderedPages = renderedPages + rendered
                }
            } catch (e: CancellationException) {
                throw e
            } finally { if (currentCoroutineContext().isActive) rendering = false }
        }
    }
    fun saveBookmark(name: String) {
        val page = current ?: return
        if (name.isBlank()) return
        bookmarks = bookmarks.filterNot { it.source == source && it.page == page.key } +
            Bookmark(name.trim(), source, tree, page.key)
        writeBookmarks()
    }
    fun removeBookmark(mark: Bookmark) {
        bookmarks = bookmarks - mark
        writeBookmarks()
    }
    fun openBookmark(mark: Bookmark) = open(Uri.parse(mark.source), mark.tree, mark.page)
    private fun readBookmarks(): List<Bookmark> = try {
        val array = JSONArray(prefs.getString("bookmarks", "[]"))
        (0 until array.length()).map {
            val item = array.getJSONObject(it)
            Bookmark(item.getString("name"), item.getString("source"), item.getBoolean("tree"), item.getString("page"))
        }
    } catch (_: Exception) { emptyList() }
    private fun writeBookmarks() {
        val array = JSONArray()
        bookmarks.forEach { array.put(JSONObject().put("name", it.name).put("source", it.source)
            .put("tree", it.tree).put("page", it.page)) }
        prefs.edit().putString("bookmarks", array.toString()).apply()
    }
}
