package com.chenx.mangareader

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.provider.DocumentsContract
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import java.util.Locale

// Compare digit runs without converting to Int, including very long page numbers.
internal val naturalOrder = Comparator<String> { a, b ->
    val parts = Regex("[0-9]+|[^0-9]+")
    val left = parts.findAll(a.lowercase(Locale.ROOT)).map { it.value }.toList()
    val right = parts.findAll(b.lowercase(Locale.ROOT)).map { it.value }.toList()
    var result = 0
    for (i in 0 until minOf(left.size, right.size)) {
        val x = left[i]; val y = right[i]
        result = if (x[0].isDigit() && y[0].isDigit()) {
            val nx = x.trimStart('0').ifEmpty { "0" }
            val ny = y.trimStart('0').ifEmpty { "0" }
            nx.length.compareTo(ny.length).takeIf { it != 0 } ?: nx.compareTo(ny)
        } else x.compareTo(y)
        if (result != 0) break
    }
    if (result != 0) result else left.size.compareTo(right.size).takeIf { it != 0 } ?: a.compareTo(b)
}

data class MangaPage(val uri: Uri, val name: String, val chapter: String, val pdfPage: Int = -1) {
    val key: String get() = "$uri#$pdfPage"
}
data class ScanResult(val pages: List<MangaPage>, val warnings: List<String>)
private data class Entry(val uri: Uri, val id: String, val name: String, val mime: String)

class Library(private val resolver: ContentResolver) {
    private val extensions = setOf("jpg", "jpeg", "png", "webp", "bmp", "gif")

    suspend fun scan(source: Uri, isTree: Boolean): ScanResult {
        val pages = mutableListOf<MangaPage>()
        val warnings = mutableListOf<String>()
        val visited = mutableSetOf<String>()
        fun addPdf(uri: Uri, name: String, chapter: String) {
            try {
                resolver.openFileDescriptor(uri, "r")!!.use { fd ->
                    PdfRenderer(fd).use { pdf ->
                        repeat(pdf.pageCount) { pages += MangaPage(uri, "$name · ${it + 1}", chapter, it) }
                    }
                }
            } catch (e: Exception) {
                warnings += "Could not open $name (damaged, protected, or unavailable)."
            }
        }
        suspend fun walk(id: String, path: String) {
            currentCoroutineContext().ensureActive()
            if (!visited.add(id)) return
            val children = DocumentsContract.buildChildDocumentsUriUsingTree(source, id)
            val entries = mutableListOf<Entry>()
            val columns = arrayOf(DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                DocumentsContract.Document.COLUMN_DISPLAY_NAME, DocumentsContract.Document.COLUMN_MIME_TYPE)
            val cursor = resolver.query(children, columns, null, null, null)
                ?: error("Unable to read this folder. Please select it again.")
            cursor.use {
                while (it.moveToNext()) {
                    val childId = it.getString(0)
                    entries += Entry(DocumentsContract.buildDocumentUriUsingTree(source, childId),
                        childId, it.getString(1) ?: childId, it.getString(2) ?: "")
                }
            }
            entries.sortWith { a, b -> naturalOrder.compare(a.name, b.name) }
            val images = entries.filter { it.mime != DocumentsContract.Document.MIME_TYPE_DIR &&
                it.name.substringAfterLast('.', "").lowercase(Locale.ROOT) in extensions }
            val pdfs = entries.filter { it.mime != DocumentsContract.Document.MIME_TYPE_DIR &&
                (it.mime == "application/pdf" || it.name.endsWith(".pdf", true)) }
            // Keep a folder's images together, even when PDFs appear between them.
            val groups = pdfs.map { listOf(it) }.toMutableList()
            if (images.isNotEmpty()) groups += images
            groups.sortWith { a, b -> naturalOrder.compare(a.first().name, b.first().name) }
            for (group in groups) {
                currentCoroutineContext().ensureActive()
                if (group.first() in pdfs) {
                    val file = group.first()
                    addPdf(file.uri, file.name, "$path / ${file.name}")
                } else group.forEach { pages += MangaPage(it.uri, it.name, path) }
            }
            for (entry in entries.filter { it.mime == DocumentsContract.Document.MIME_TYPE_DIR }) {
                walk(entry.id, "$path / ${entry.name}")
            }
        }
        if (isTree) {
            val id = DocumentsContract.getTreeDocumentId(source)
            walk(id, id.substringAfterLast('/').substringAfterLast(':').ifBlank { "Manga" })
        } else {
            var name = "PDF"
            resolver.query(source, arrayOf("_display_name"), null, null, null)?.use {
                if (it.moveToFirst()) name = it.getString(0) ?: name
            }
            addPdf(source, name, name)
        }
        return ScanResult(pages, warnings)
    }

    fun render(page: MangaPage, maxEdge: Int = if (page.pdfPage >= 0) 2400 else 3000): Bitmap {
        if (page.pdfPage >= 0) {
            return resolver.openFileDescriptor(page.uri, "r")!!.use { fd ->
                PdfRenderer(fd).use { pdf ->
                    pdf.openPage(page.pdfPage).use { p ->
                        val ratio = maxEdge.toFloat() / maxOf(p.width, p.height)
                        Bitmap.createBitmap((p.width * ratio).toInt().coerceAtLeast(1),
                            (p.height * ratio).toInt().coerceAtLeast(1), Bitmap.Config.ARGB_8888).also {
                            it.eraseColor(Color.WHITE)
                            p.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                        }
                    }
                }
            }
        }
        return ImageDecoder.decodeBitmap(ImageDecoder.createSource(resolver, page.uri)) { decoder, info, _ ->
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            val ratio = minOf(1f, maxEdge.toFloat() / maxOf(info.size.width, info.size.height))
            decoder.setTargetSize((info.size.width * ratio).toInt().coerceAtLeast(1),
                (info.size.height * ratio).toInt().coerceAtLeast(1))
        }
    }
}
