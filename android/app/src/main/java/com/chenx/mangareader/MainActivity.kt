package com.chenx.mangareader

import android.os.Bundle
import android.os.Build
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.ViewModelProvider
import androidx.window.layout.FoldingFeature
import androidx.window.layout.WindowInfoTracker
import kotlinx.coroutines.flow.map
import com.chenx.mangareader.ui.theme.MangaReaderTheme
import kotlin.math.abs

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val reader = ViewModelProvider(this)[ReaderViewModel::class.java]
        setContent {
            val configuration = LocalConfiguration.current
            val windowInfo = remember {
                WindowInfoTracker.getOrCreate(this).windowLayoutInfo(this)
                    .map { info -> info.displayFeatures.any { it is FoldingFeature } }
            }
            val hasFold by windowInfo.collectAsState(initial = false)
            // WindowManager reports the fold on the inner display. The size fallback
            // handles its initial asynchronous emission on the user's Pixel Fold.
            val innerDisplay = hasFold ||
                (Build.MODEL == "Pixel Fold" && configuration.smallestScreenWidthDp >= 600)
            val twoPage = innerDisplay && configuration.screenWidthDp >= 600
            LaunchedEffect(twoPage) { reader.updateTwoPageMode(twoPage) }
            MangaReaderTheme(darkTheme = true) {
                ReaderScreen(reader) { fullscreen ->
                    WindowCompat.getInsetsController(window, window.decorView).apply {
                        systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                        if (fullscreen) hide(WindowInsetsCompat.Type.systemBars())
                        else show(WindowInsetsCompat.Type.systemBars())
                    }
                }
            }
        }
    }
}

@Composable
private fun ReaderScreen(vm: ReaderViewModel, setFullscreen: (Boolean) -> Unit) {
    var controls by rememberSaveable { mutableStateOf(true) }
    var menu by remember { mutableStateOf(false) }
    var dialog by rememberSaveable { mutableStateOf("") }
    var bookmarkName by rememberSaveable { mutableStateOf("") }
    val folderPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) {
        it?.let { uri -> vm.pick(uri, true) }
    }
    val pdfPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        it?.let { uri -> vm.pick(uri, false) }
    }
    LaunchedEffect(controls, vm.libraryVisible) { setFullscreen(!controls && !vm.libraryVisible) }
    BackHandler(!vm.libraryVisible) {
        if (!controls) controls = true else vm.showLibrary()
    }
    val page = vm.current
    val chapterPages = remember(vm.pages, page?.chapter) {
        vm.pages.indices.filter { vm.pages[it].chapter == page?.chapter }
    }
    Scaffold(containerColor = Color(0xFF101114), contentColor = MaterialTheme.colorScheme.onSurface, topBar = {
        if (controls || vm.libraryVisible) Surface {
            Row(Modifier.fillMaxWidth().statusBarsPadding().padding(start = 16.dp, end = 4.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f).padding(vertical = 12.dp)) {
                    Text("Manga Reader", style = MaterialTheme.typography.titleMedium)
                    Text(if (vm.libraryVisible) "Made for your Pixel Fold" else page?.chapter ?: "Your offline reading space", maxLines = 1,
                        overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                }
                Box {
                    TextButton(onClick = { menu = true }) { Text("Menu") }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text("Library") }, onClick = { menu = false; controls = true; vm.showLibrary() })
                        DropdownMenuItem(text = { Text("Open manga") }, onClick = { menu = false; dialog = "open" })
                        DropdownMenuItem(text = { Text("Chapters") }, enabled = page != null && !vm.libraryVisible,
                            onClick = { menu = false; dialog = "chapters" })
                        DropdownMenuItem(text = { Text("Bookmarks") }, onClick = { menu = false; dialog = "bookmarks" })
                        DropdownMenuItem(text = { Text(if (vm.rtl) "Direction: right to left" else "Direction: left to right") },
                            onClick = { vm.toggleRtl(); menu = false })
                        if (!vm.libraryVisible && page != null) DropdownMenuItem(
                            text = { Text("Show cover separately: ${if (vm.separateCover) "On" else "Off"}") },
                            onClick = { vm.toggleSeparateCover(); menu = false })
                        DropdownMenuItem(text = { Text("Hide controls") }, enabled = page != null && !vm.libraryVisible,
                            onClick = { controls = false; menu = false })
                    }
                }
            }
        }
    }, bottomBar = {
        if (controls && page != null && !vm.libraryVisible) Surface {
            Column(Modifier.navigationBarsPadding().padding(horizontal = 12.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = { vm.move(-1) }, enabled = vm.canGoPrevious) { Text("Previous") }
                    val numbers = vm.visibleIndices.map { chapterPages.indexOf(it) + 1 }
                    val range = if (numbers.size == 2) "${numbers.first()}–${numbers.last()}" else "${numbers.firstOrNull() ?: 1}"
                    Text("$range / ${chapterPages.size}",
                        Modifier.weight(1f), textAlign = TextAlign.Center)
                    TextButton(onClick = { vm.move(1) }, enabled = vm.canGoNext) { Text("Next") }
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    TextButton(onClick = { dialog = "chapters" }) { Text("Chapters") }
                    TextButton(onClick = {
                        bookmarkName = "${page.chapter.substringAfterLast(" / ")} · ${chapterPages.indexOf(vm.index) + 1}"
                        dialog = "add"
                    }) { Text("Bookmark") }
                    TextButton(onClick = { controls = false }) { Text("Full screen") }
                }
            }
        }
    }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
            when {
                vm.busy -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator()
                    Spacer(Modifier.height(16.dp))
                    Text("Finding chapters…")
                }
                vm.libraryVisible -> LibraryScreen(vm, onOpen = { dialog = "open" })
                page == null -> Column(Modifier.widthIn(max = 420.dp).padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("A little space for\nyour next chapter.", style = MaterialTheme.typography.headlineMedium,
                        textAlign = TextAlign.Center)
                    Text("Open a manga folder or PDF on your phone. Your place is saved automatically.", textAlign = TextAlign.Center)
                    Button(onClick = { dialog = "open" }, modifier = Modifier.fillMaxWidth()) { Text("Open manga") }
                    Text("JPG · PNG · WebP · BMP · GIF · PDF\nNested chapter folders supported",
                        style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
                }
                else -> {
                    PageCanvas(vm, onToggleControls = { controls = !controls })
                    if (vm.rendering) CircularProgressIndicator()
                }
            }
        }
    }
    vm.message?.let { message ->
        AlertDialog(onDismissRequest = vm::dismissMessage, title = { Text("Library") },
            text = { Text(message) }, confirmButton = { TextButton(onClick = vm::dismissMessage) { Text("OK") } })
    }
    when (dialog) {
        "open" -> AlertDialog(onDismissRequest = { dialog = "" }, title = { Text("Open manga") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Choose a folder of chapters or a PDF file.")
                    Button(onClick = { dialog = ""; folderPicker.launch(null) }, modifier = Modifier.fillMaxWidth()) {
                        Text("Choose folder")
                    }
                    OutlinedButton(onClick = { dialog = ""; pdfPicker.launch(arrayOf("application/pdf")) }, modifier = Modifier.fillMaxWidth()) {
                        Text("Choose PDF")
                    }
                }
            }, confirmButton = { TextButton(onClick = { dialog = "" }) { Text("Cancel") } })
        "add" -> AlertDialog(onDismissRequest = { dialog = "" }, title = { Text("Name this bookmark") },
            text = { OutlinedTextField(value = bookmarkName, onValueChange = { bookmarkName = it }, singleLine = true, label = { Text("Name") }) },
            confirmButton = { TextButton(enabled = bookmarkName.isNotBlank(), onClick = { vm.saveBookmark(bookmarkName); dialog = "" }) { Text("Save") } },
            dismissButton = { TextButton(onClick = { dialog = "" }) { Text("Cancel") } })
        "chapters" -> {
            val chapters = remember(vm.pages) { vm.pages.indices.filter { it == 0 || vm.pages[it].chapter != vm.pages[it - 1].chapter } }
            AlertDialog(onDismissRequest = { dialog = "" }, title = { Text("Chapters") }, text = {
                LazyColumn(Modifier.heightIn(max = 420.dp)) {
                    items(chapters) { start ->
                        Text(vm.pages[start].chapter, Modifier.fillMaxWidth().clickable { vm.goTo(start); dialog = "" }.padding(vertical = 16.dp),
                            color = if (vm.pages[start].chapter == page?.chapter) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface)
                    }
                }
            }, confirmButton = { TextButton(onClick = { dialog = "" }) { Text("Close") } })
        }
        "bookmarks" -> AlertDialog(onDismissRequest = { dialog = "" }, title = { Text("Bookmarks") }, text = {
            if (vm.bookmarks.isEmpty()) Text("Save a bookmark from the reader to find it here.")
            else LazyColumn(Modifier.heightIn(max = 420.dp)) {
                items(vm.bookmarks) { mark ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(mark.name, Modifier.weight(1f).clickable { vm.openBookmark(mark); dialog = "" }.padding(vertical = 16.dp))
                        TextButton(onClick = { vm.removeBookmark(mark) }) { Text("Remove") }
                    }
                }
            }
        }, confirmButton = { TextButton(onClick = { dialog = "" }) { Text("Close") } })
    }
}

@Composable
private fun PageCanvas(vm: ReaderViewModel, onToggleControls: () -> Unit) {
    val page = vm.current ?: return
    var zoom by rememberSaveable(page.key, vm.twoPage, vm.separateCover) { mutableFloatStateOf(1f) }
    var panX by rememberSaveable(page.key, vm.twoPage, vm.separateCover) { mutableFloatStateOf(0f) }
    var panY by rememberSaveable(page.key, vm.twoPage, vm.separateCover) { mutableFloatStateOf(0f) }
    val toggle by rememberUpdatedState(onToggleControls)
    BoxWithConstraints(Modifier.fillMaxSize().clipToBounds().background(Color(0xFF101114))) {
        val width = constraints.maxWidth.toFloat()
        val height = constraints.maxHeight.toFloat()
        LaunchedEffect(width, height, vm.twoPage) {
            panX = panX.coerceIn(-width * (zoom - 1) / 2, width * (zoom - 1) / 2)
            panY = panY.coerceIn(-height * (zoom - 1) / 2, height * (zoom - 1) / 2)
        }
        Box(Modifier.fillMaxSize()
            .pointerInput(page.key, vm.rtl, vm.twoPage) {
                detectTapGestures(
                    onDoubleTap = { zoom = if (zoom > 1f) 1f else 2f; panX = 0f; panY = 0f },
                    onTap = {
                        if (zoom > 1f || it.x in size.width * 0.3f..size.width * 0.7f) toggle()
                        else vm.move(if ((it.x > size.width / 2) != vm.rtl) 1 else -1)
                    })
            }
            .pointerInput(page.key, vm.rtl, vm.twoPage) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    var travel = Offset.Zero
                    var transformed = zoom > 1f
                    var dragging = false
                    do {
                        val event = awaitPointerEvent()
                        val change = event.calculatePan()
                        val factor = event.calculateZoom()
                        travel += change
                        if (event.changes.count { it.pressed } > 1) transformed = true
                        if (travel.getDistance() > viewConfiguration.touchSlop || factor != 1f) dragging = true
                        if (dragging) {
                            if (transformed) {
                                zoom = (zoom * factor).coerceIn(1f, 5f)
                                panX = (panX + change.x).coerceIn(-size.width * (zoom - 1) / 2, size.width * (zoom - 1) / 2)
                                panY = (panY + change.y).coerceIn(-size.height * (zoom - 1) / 2, size.height * (zoom - 1) / 2)
                            }
                            event.changes.forEach { it.consume() }
                        }
                    } while (event.changes.any { it.pressed })
                    if (!transformed && abs(travel.x) > 64.dp.toPx() && abs(travel.x) > abs(travel.y)) {
                        vm.move(if ((travel.x < 0) != vm.rtl) 1 else -1)
                    }
                }
            }) {
            val visible = vm.visibleIndices
            val isCover = vm.separateCover && (vm.index == 0 || vm.pages[vm.index - 1].chapter != page.chapter)
            val slots: List<Int?> = if (vm.twoPage && visible.size == 1 && !isCover) visible + listOf(null) else visible
            val ordered = if (vm.rtl) slots.reversed() else slots
            // Set physical left/right explicitly; the manga preference controls order,
            // independently of the phone's system language.
            CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
                Row(Modifier.fillMaxSize().graphicsLayer {
                        scaleX = zoom; scaleY = zoom; translationX = panX; translationY = panY
                    }, horizontalArrangement = Arrangement.spacedBy(if (vm.twoPage) 8.dp else 0.dp)) {
                    ordered.forEach { pageIndex ->
                        Box(Modifier.weight(1f).fillMaxHeight(), contentAlignment = Alignment.Center) {
                            val rendered = vm.renderedPages.firstOrNull { it.index == pageIndex }
                            rendered?.bitmap?.let { bitmap ->
                                Image(bitmap.asImageBitmap(), contentDescription = vm.pages[rendered.index].name,
                                    modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                            }
                            rendered?.error?.let { error ->
                                Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text(error, textAlign = TextAlign.Center)
                                    TextButton(onClick = vm::retry) { Text("Retry") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
