package com.chenx.mangareader

import android.database.Cursor
import android.database.MatrixCursor
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfDocument
import android.os.ParcelFileDescriptor
import android.provider.DocumentsContract.Document
import android.content.ContentProvider
import android.content.ContentValues
import android.net.Uri
import android.provider.DocumentsContract
import java.io.File

/** QA build only: synthetic pages in its own private cache, never user manga. */
class FixtureProvider : ContentProvider() {
    private val fixtureRoot get() = File(requireNotNull(context).cacheDir, "fixture").canonicalFile
    override fun onCreate(): Boolean {
        val root = fixtureRoot
        root.mkdirs()
        fun image(path: String) {
            val file = File(root, path)
            file.parentFile!!.mkdirs()
            val bitmap = Bitmap.createBitmap(240, 360, Bitmap.Config.ARGB_8888)
            bitmap.eraseColor(Color.BLUE)
            file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            bitmap.recycle()
        }
        image("01.png"); image("03.png")
        image("chapter2/page10.png"); image("chapter2/page2.png")
        image("chapter10/page1.png"); image("folder.pdf/page1.png")
        File(root, "corrupt.png").writeText("not an image")
        File(root, "broken.pdf").writeText("not a PDF")
        val pdf = PdfDocument()
        try {
            repeat(3) { number ->
                val page = pdf.startPage(PdfDocument.PageInfo.Builder(240, 360, number + 1).create())
                page.canvas.drawColor(Color.WHITE)
                pdf.finishPage(page)
            }
            File(root, "02.pdf").outputStream().use { pdf.writeTo(it) }
        } finally { pdf.close() }
        return true
    }
    private fun file(id: String): File {
        val root = fixtureRoot.canonicalFile
        val file = if (id == "root") root else File(root, id.removePrefix("root/")).canonicalFile
        require(file == root || file.path.startsWith(root.path + File.separator))
        return file
    }
    private fun result(files: List<File>, projection: Array<out String>?): Cursor {
        val columns = projection ?: arrayOf(Document.COLUMN_DOCUMENT_ID, Document.COLUMN_DISPLAY_NAME, Document.COLUMN_MIME_TYPE)
        return MatrixCursor(columns).apply {
            files.forEach { f ->
                val relative = f.relativeTo(fixtureRoot).invariantSeparatorsPath
                val id = if (relative.isEmpty()) "root" else "root/$relative"
                addRow(columns.map<String, Any?> { column -> when (column) {
                    Document.COLUMN_DOCUMENT_ID -> id
                    Document.COLUMN_DISPLAY_NAME -> f.name
                    Document.COLUMN_MIME_TYPE -> if (f.isDirectory) Document.MIME_TYPE_DIR else if (f.extension == "pdf") "application/pdf" else "image/png"
                    Document.COLUMN_SIZE -> f.length()
                    Document.COLUMN_FLAGS -> 0
                    else -> null
                } }.toTypedArray())
            }
        }
    }
    override fun query(uri: Uri, projection: Array<out String>?, selection: String?, selectionArgs: Array<out String>?, sortOrder: String?): Cursor {
        val file = file(DocumentsContract.getDocumentId(uri))
        return result(if (uri.lastPathSegment == "children") file.listFiles()?.toList() ?: emptyList() else listOf(file), projection)
    }
    override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor =
        ParcelFileDescriptor.open(file(DocumentsContract.getDocumentId(uri)), ParcelFileDescriptor.MODE_READ_ONLY)
    override fun getType(uri: Uri): String = "application/octet-stream"
    override fun insert(uri: Uri, values: ContentValues?): Uri? = throw UnsupportedOperationException()
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = throw UnsupportedOperationException()
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?): Int = throw UnsupportedOperationException()
}
