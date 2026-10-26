package com.chenx.mangareader

// Pair from each chapter's first page. Never pair across a chapter boundary.
// The focused index stays unchanged on fold/unfold, even when it is the second page.
internal fun visiblePages(chapters: List<String>, index: Int, twoPage: Boolean, separateCover: Boolean = false): List<Int> {
    if (index !in chapters.indices) return emptyList()
    if (!twoPage) return listOf(index)
    var chapterStart = index
    while (chapterStart > 0 && chapters[chapterStart - 1] == chapters[index]) chapterStart--
    if (separateCover && index == chapterStart) return listOf(index)
    val pairingStart = chapterStart + if (separateCover) 1 else 0
    val start = pairingStart + (index - pairingStart) / 2 * 2
    return if (start + 1 < chapters.size && chapters[start + 1] == chapters[start])
        listOf(start, start + 1) else listOf(start)
}

internal fun turnPage(chapters: List<String>, index: Int, twoPage: Boolean, delta: Int, separateCover: Boolean = false): Int {
    val visible = visiblePages(chapters, index, twoPage, separateCover)
    if (visible.isEmpty() || delta == 0) return index
    val target = if (delta > 0) visible.last() + 1 else visible.first() - 1
    return if (target in chapters.indices) target else index
}
