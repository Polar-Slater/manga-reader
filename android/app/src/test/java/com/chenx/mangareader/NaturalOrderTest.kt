package com.chenx.mangareader

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NaturalOrderTest {
    @Test fun numberedPagesSortNumerically() {
        assertEquals(listOf("page1.jpg", "page2.jpg", "page10.jpg"),
            listOf("page10.jpg", "page2.jpg", "page1.jpg").sortedWith(naturalOrder))
    }
    @Test fun handlesHugeNumbersAndLeadingZeroes() {
        val names = listOf("9999999999999999999999999999.png", "10.png", "002.png", "2.png")
        assertEquals(listOf("002.png", "2.png", "10.png", "9999999999999999999999999999.png"), names.sortedWith(naturalOrder))
    }
    @Test fun comparesEveryNumericRunAndIgnoresCase() {
        assertTrue(naturalOrder.compare("Chapter2-page9.PNG", "chapter2-page10.png") < 0)
        assertTrue(naturalOrder.compare("Chapter2-page99.png", "chapter10-page1.png") < 0)
    }
    @Test fun comparisonIsConsistentForMixedNames() {
        val names = listOf("", "2", "02", "A", "a", "chapter1", "chapter001", "chapter10", "cover", "漫画2", "漫画10")
        for (a in names) for (b in names) {
            assertEquals(-naturalOrder.compare(b, a).compareTo(0), naturalOrder.compare(a, b).compareTo(0))
            for (c in names) if (naturalOrder.compare(a, b) <= 0 && naturalOrder.compare(b, c) <= 0) {
                assertTrue(naturalOrder.compare(a, c) <= 0)
            }
        }
    }
}
