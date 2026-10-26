package com.chenx.mangareader

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
internal fun LibraryScreen(vm: ReaderViewModel, onOpen: () -> Unit) {
    val entries = vm.libraryEntries
    LazyVerticalGrid(columns = GridCells.Adaptive(144.dp), modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp), horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item(span = { GridItemSpan(maxLineSpan) }) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Your library", style = MaterialTheme.typography.headlineLarge)
                Text("Pick up where you left off.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = onOpen) { Text("Open manga") }
            }
        }
        if (entries.isEmpty()) item(span = { GridItemSpan(maxLineSpan) }) {
            Text("Open a title’s folder or PDF to add it here. Covers and reading progress are saved on your Pixel Fold.",
                Modifier.padding(vertical = 32.dp))
        }
        entries.firstOrNull()?.let { recent ->
            item(span = { GridItemSpan(maxLineSpan) }) {
                Card(onClick = { vm.resume(recent) }, modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Cover(vm, recent, Modifier.width(84.dp).height(120.dp))
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Continue reading", style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.primary)
                            Text(recent.title, maxLines = 2, overflow = TextOverflow.Ellipsis,
                                style = MaterialTheme.typography.titleLarge)
                            Text("Page ${recent.page} of ${recent.total}", style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
            item(span = { GridItemSpan(maxLineSpan) }) {
                Text("Saved titles · ${entries.size}", style = MaterialTheme.typography.titleMedium)
            }
        }
        items(entries, key = { it.source }) { entry ->
            Card(onClick = { vm.resume(entry) }, modifier = Modifier.fillMaxWidth()) {
                Cover(vm, entry, Modifier.fillMaxWidth().aspectRatio(0.7f))
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(entry.title, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleMedium)
                    Text("Page ${entry.page} / ${entry.total}", style = MaterialTheme.typography.bodySmall)
                    Text(entry.chapter.substringAfterLast(" / "), maxLines = 1, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    TextButton(onClick = { vm.removeFromLibrary(entry) }) { Text("Remove from library") }
                }
            }
        }
    }
}

@Composable
private fun Cover(vm: ReaderViewModel, entry: LibraryEntry, modifier: Modifier) {
    val bitmap by produceState<Bitmap?>(null, entry.source, vm.coverRevision) {
        value = withContext(Dispatchers.IO) { BitmapFactory.decodeFile(vm.coverFile(entry.source).absolutePath) }
    }
    Box(modifier.background(MaterialTheme.colorScheme.surfaceVariant), contentAlignment = Alignment.Center) {
        bitmap?.let {
            Image(it.asImageBitmap(), contentDescription = "Cover of ${entry.title}",
                modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
        } ?: Text(if (entry.tree) "MANGA" else "PDF", style = MaterialTheme.typography.labelLarge)
    }
}
