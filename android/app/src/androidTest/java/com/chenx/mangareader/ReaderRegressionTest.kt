package com.chenx.mangareader

import android.app.Application
import android.net.Uri
import android.provider.DocumentsContract
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

class ReaderRegressionTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val app get() = instrumentation.targetContext.applicationContext as Application
    private val authority = "com.chenx.mangareader.qa.fixtures"
    private val tree get() = DocumentsContract.buildTreeDocumentUri(authority, "root")
    private fun main(block: () -> Unit) = instrumentation.runOnMainSync(block)
    private fun waitFor(vm: ReaderViewModel) {
        val end = System.currentTimeMillis() + 15000
        while (System.currentTimeMillis() < end) {
            var done = false
            main { done = !vm.busy && !vm.rendering }
            if (done) return
            Thread.sleep(40)
        }
        fail("Reader did not finish within 15 seconds")
    }
    @Test fun mixedFolderOrderingPdfRenderingAndDamageHandling() = runBlocking {
        val library = Library(app.contentResolver)
        val result = library.scan(tree, true)
        assertEquals(listOf("01.png", "03.png", "corrupt.png", "02.pdf · 1", "02.pdf · 2", "02.pdf · 3",
            "page2.png", "page10.png", "page1.png", "page1.png"), result.pages.map { it.name })
        assertEquals(1, result.warnings.size)
        assertTrue(result.warnings.single().contains("broken.pdf"))
        for (page in listOf(result.pages.first(), result.pages[3])) {
            val bitmap = library.render(page, 96)
            assertTrue(maxOf(bitmap.width, bitmap.height) <= 96)
            assertTrue(bitmap.width > 0)
            bitmap.recycle()
        }
        try { library.render(result.pages[2]); fail("Corrupt image should fail") } catch (_: java.io.IOException) { }
    }
    @Test fun progressBookmarksCoverPreferenceAndRemovalSurviveRecreation() {
        check(app.packageName.endsWith(".qa")) // Never touch the everyday app's data.
        app.getSharedPreferences("reader", 0).edit().clear().commit()
        var store = ViewModelStore()
        lateinit var vm: ReaderViewModel
        fun create() { vm = ViewModelProvider(store, ViewModelProvider.AndroidViewModelFactory(app))[ReaderViewModel::class.java] }
        try {
            main { create(); vm.open(tree, true) }
            waitFor(vm)
            main {
                assertEquals(10, vm.pages.size)
                assertEquals(1, vm.libraryEntries.size)
                vm.goTo(7)
                vm.toggleSeparateCover()
                vm.saveBookmark("QA bookmark")
                vm.toggleRtl()
            }
            waitFor(vm)
            main {
                vm.showLibrary()
                val readTime = vm.libraryEntries.single().lastRead
                vm.updateTwoPageMode(true)
                assertEquals(readTime, vm.libraryEntries.single().lastRead)
                assertTrue(vm.renderedPages.isEmpty())
                store.clear()
                store = ViewModelStore()
                create()
                assertTrue(vm.libraryVisible)
                assertEquals(8, vm.libraryEntries.single().page)
                assertTrue(vm.rtl)
                assertEquals("QA bookmark", vm.bookmarks.single().name)
                vm.resume(vm.libraryEntries.single())
            }
            waitFor(vm)
            main {
                assertEquals(7, vm.index)
                assertTrue(vm.separateCover)
                vm.goTo(0)
                vm.openBookmark(vm.bookmarks.single())
            }
            waitFor(vm)
            main {
                assertEquals(7, vm.index)
                vm.showLibrary()
                vm.removeFromLibrary(vm.libraryEntries.single())
                assertTrue(vm.libraryEntries.isEmpty())
                assertEquals(1, vm.bookmarks.size)
                store.clear(); store = ViewModelStore(); create()
                assertTrue(vm.libraryEntries.isEmpty())
                vm.open(tree, true)
            }
            waitFor(vm)
            main { assertEquals(7, vm.index); assertTrue(vm.separateCover) }
        } finally {
            main { store.clear() }
            app.getSharedPreferences("reader", 0).edit().clear().commit()
        }
    }
    @Test fun savedLibraryJsonRoundTripsAndSkipsDamagedRecords() {
        val entry = LibraryEntry("content://example/漫画", true, "漫画", 12, 30, "第2章", 123L)
        assertEquals(listOf(entry), decodeLibrary(encodeLibrary(listOf(entry))))
        assertEquals(emptyList<LibraryEntry>(), decodeLibrary("broken json"))
        assertEquals(listOf(entry), decodeLibrary("[{}," + encodeLibrary(listOf(entry)).removePrefix("[")))
    }
}
