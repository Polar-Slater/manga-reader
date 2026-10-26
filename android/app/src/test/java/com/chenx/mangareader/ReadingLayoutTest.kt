package com.chenx.mangareader

import org.junit.Assert.assertEquals
import org.junit.Test

class ReadingLayoutTest {
    @Test fun separateCoverPairsFollowingPagesAndResetsPerChapter() {
        val chapters = listOf("A", "A", "A", "A", "B", "B", "B")
        assertEquals(listOf(0), visiblePages(chapters, 0, true, true))
        assertEquals(listOf(1, 2), visiblePages(chapters, 2, true, true))
        assertEquals(listOf(3), visiblePages(chapters, 3, true, true))
        assertEquals(listOf(4), visiblePages(chapters, 4, true, true))
        assertEquals(listOf(5, 6), visiblePages(chapters, 6, true, true))
        assertEquals(listOf(2), visiblePages(chapters, 2, false, true))
    }

    @Test fun coverPairingNeverSkipsPagesForOddEvenAndSinglePageChapters() {
        for (size in 1..8) {
            val chapters = List(size) { "A" } + List(size + 1) { "B" }
            var index = 0
            val visited = mutableListOf<Int>()
            val spreads = mutableListOf<List<Int>>()
            do {
                val visible = visiblePages(chapters, index, true, true)
                visited += visible
                spreads += visible
                val next = turnPage(chapters, index, true, 1, true)
                if (next == index) break
                index = next
            } while (true)
            assertEquals(chapters.indices.toList(), visited)
            for (expected in spreads.dropLast(1).reversed()) {
                index = turnPage(chapters, index, true, -1, true)
                assertEquals(expected, visiblePages(chapters, index, true, true))
            }
        }
    }

    private val chapters = listOf("A", "A", "A", "A", "A", "B", "B", "B")

    @Test fun singlePageModeShowsExactlyTheFocusedPage() {
        for (index in chapters.indices) assertEquals(listOf(index), visiblePages(chapters, index, false))
    }

    @Test fun unfoldingContainsTheFocusedPageAndFoldingReturnsToIt() {
        assertEquals(listOf(2, 3), visiblePages(chapters, 3, true))
        assertEquals(listOf(3), visiblePages(chapters, 3, false))
    }

    @Test fun pairingRestartsAtEachChapterAndLeavesOddFinalPagesAlone() {
        assertEquals(listOf(4), visiblePages(chapters, 4, true))
        assertEquals(listOf(5, 6), visiblePages(chapters, 5, true))
        assertEquals(listOf(7), visiblePages(chapters, 7, true))
    }

    @Test fun forwardTurnsNeverSkipPagesOrCrossPairBoundaries() {
        var index = 0
        val visited = mutableListOf<Int>()
        do {
            visited += visiblePages(chapters, index, true)
            val next = turnPage(chapters, index, true, 1)
            if (next == index) break
            index = next
        } while (true)
        assertEquals(chapters.indices.toList(), visited)
    }

    @Test fun previousReturnsToPriorSpreadAcrossOddChapterBoundary() {
        assertEquals(listOf(4), visiblePages(chapters, turnPage(chapters, 5, true, -1), true))
        assertEquals(listOf(2, 3), visiblePages(chapters, turnPage(chapters, 4, true, -1), true))
        assertEquals(0, turnPage(chapters, 0, true, -1))
        assertEquals(7, turnPage(chapters, 7, true, 1))
    }

    @Test fun singlePageTurnsAndEmptyLibrariesAreSafe() {
        assertEquals(4, turnPage(chapters, 3, false, 1))
        assertEquals(2, turnPage(chapters, 3, false, -1))
        assertEquals(emptyList<Int>(), visiblePages(emptyList(), 0, true))
        assertEquals(0, turnPage(emptyList(), 0, true, 1))
        assertEquals(listOf(0), visiblePages(listOf("One"), 0, true))
    }
}
