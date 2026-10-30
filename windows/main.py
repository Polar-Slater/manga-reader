"""A small local manga reader. Run with: python main.py"""

import hashlib
import json
from pathlib import Path
import sys

if sys.version_info < (3, 12):
    sys.exit('Manga Reader requires Python 3.12 or newer. Recreate .venv with a supported Python version.')

from PySide6.QtCore import Qt, QSettings, QTimer, QEvent
from PySide6.QtGui import QAction, QImageReader, QKeySequence, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QMessageBox,
    QScrollArea, QToolBar, QComboBox, QDockWidget, QListWidget,
    QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QInputDialog,
)

from library import image_files, library_sources, ebook_sources
from ebooks import Book, EbookReader

DEFAULT_MANGA_FOLDER = Path(__file__).resolve().parent.parent / 'Manga'
DEFAULT_BOOKS_FOLDER = Path(__file__).resolve().parent.parent / 'books'


class MangaReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(QSettings.defaultFormat(), QSettings.Scope.UserScope,
                                  'LearningCode', 'MangaReader')
        self.pages = []
        self.pdf_pages = []
        self.pdf = QPdfDocument(self)
        self.pdf_path = None
        self.folder = None
        self.index = 0
        self.chapter_starts = []
        self.pixmap = QPixmap()
        self.zoom = 1.0
        self.source_kind = 'manga'
        self.ebook_source = None
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render)
        self.setWindowTitle('Manga Reader')
        self.resize(1000, 800)

        self.label = QLabel('Choose a title from your library to read.')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet('QLabel { color: #dddddd; background: #202124; padding: 0; }')
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.label)
        self.scroll.setWidgetResizable(True)
        self.scroll.viewport().installEventFilter(self)
        self.scroll.setStyleSheet('QScrollArea { border: none; background: #202124; }')
        self.stack = QStackedWidget()
        self.library_panel = QWidget()
        library_layout = QVBoxLayout(self.library_panel)
        library_layout.setContentsMargins(24, 24, 24, 24)
        heading = QLabel('Your library')
        heading.setStyleSheet('font-size: 26px; font-weight: bold;')
        library_layout.addWidget(heading)
        self.library_kind = QComboBox()
        self.library_kind.addItem('Manga', 'manga')
        self.library_kind.addItem('Ebook', 'ebook')
        library_layout.addWidget(self.library_kind)
        self.introduction = QLabel()
        self.introduction.setWordWrap(True)
        library_layout.addWidget(self.introduction)
        self.library_list = QListWidget()
        self.library_list.setSpacing(6)
        self.library_list.setStyleSheet('QListWidget::item { padding: 14px; }')
        self.library_list.itemDoubleClicked.connect(lambda item: self.open_library_entry())
        library_layout.addWidget(self.library_list)
        self.library_empty = QLabel('Add title folders or PDFs to Manga, then click Refresh. You can also open a folder or PDF from elsewhere.')
        self.library_empty.setWordWrap(True)
        library_layout.addWidget(self.library_empty)
        buttons = QHBoxLayout()
        self.library_open = QPushButton('Read selected')
        self.library_open.clicked.connect(self.open_library_entry)
        self.library_remove = QPushButton('Remove from library')
        self.library_remove.clicked.connect(self.remove_library_entry)
        for button in (self.library_open, self.library_remove):
            buttons.addWidget(button)
        buttons.addStretch()
        self.library_restore = QPushButton('Restore hidden titles')
        self.library_restore.clicked.connect(self.restore_hidden_titles)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh_library)
        buttons.addWidget(refresh)
        library_layout.addLayout(buttons)
        library_layout.addWidget(self.library_restore, 0, Qt.AlignmentFlag.AlignLeft)
        self.library_list.itemSelectionChanged.connect(self.update_library_selection)
        self.stack.addWidget(self.library_panel)
        self.stack.addWidget(self.scroll)
        self.ebook_reader = EbookReader(self.settings)
        self.stack.addWidget(self.ebook_reader)
        self.setCentralWidget(self.stack)

        toolbar = QToolBar('Reader controls')
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        def action(text, callback, shortcuts=(), checkable=False):
            item = QAction(text, self)
            item.setCheckable(checkable)
            item.setShortcuts([QKeySequence(key) for key in shortcuts])
            item.triggered.connect(callback)
            toolbar.addAction(item)
            return item

        action('Library', self.show_library, ['Ctrl+L'])
        common_toolbar = toolbar
        self.addToolBarBreak()
        toolbar = QToolBar('Page controls')
        self.reader_toolbar = toolbar
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.previous = action('Previous', lambda: self.move(-1), ['PageUp'])
        self.next = action('Next', lambda: self.move(1), ['PageDown', 'Space'])
        action('←', lambda: self.move(1 if self.rtl.isChecked() else -1), ['Left'])
        action('→', lambda: self.move(-1 if self.rtl.isChecked() else 1), ['Right'])
        toolbar.addSeparator()
        self.fit = action('Fit page', self.render, ['F'], True)
        self.fit.setChecked(True)
        action('Zoom −', lambda: self.change_zoom(1 / 1.25), ['-', 'Ctrl+-'])
        action('Zoom +', lambda: self.change_zoom(1.25), ['+', '=', 'Ctrl+='])
        self.rtl = action('Right to left', self.save_preferences, [], True)
        self.rtl.setChecked(self.settings.value('rtl', False, type=bool))
        action('Fullscreen', self.toggle_fullscreen, ['F11'])
        escape = QAction(self)
        escape.setShortcut(QKeySequence('Escape'))
        escape.triggered.connect(self.showNormal)
        self.addAction(escape)
        self.addToolBarBreak()
        chapters = QToolBar('Chapters')
        self.chapters_toolbar = chapters
        chapters.setMovable(False)
        self.addToolBar(chapters)
        self.previous_chapter = QAction('Previous chapter', self)
        self.previous_chapter.setShortcut(QKeySequence('Ctrl+PageUp'))
        self.previous_chapter.triggered.connect(lambda: self.jump_chapter(self.chapter_picker.currentIndex() - 1))
        chapters.addAction(self.previous_chapter)
        self.chapter_picker = QComboBox()
        self.chapter_picker.setMinimumWidth(240)
        self.chapter_picker.setToolTip('Choose a folder / chapter')
        self.chapter_picker.activated.connect(self.jump_chapter)
        chapters.addWidget(self.chapter_picker)
        self.next_chapter = QAction('Next chapter', self)
        self.next_chapter.setShortcut(QKeySequence('Ctrl+PageDown'))
        self.next_chapter.triggered.connect(lambda: self.jump_chapter(self.chapter_picker.currentIndex() + 1))
        chapters.addAction(self.next_chapter)
        self.previous_chapter.setEnabled(False)
        self.next_chapter.setEnabled(False)
        self.previous.setEnabled(False)
        self.next.setEnabled(False)
        self.bookmarks_dock = QDockWidget('Bookmarks', self)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemDoubleClicked.connect(lambda item: self.open_bookmark())
        layout.addWidget(self.bookmark_list)
        for title, callback in [('Add / rename current page', self.add_bookmark),
                                ('Go to bookmark', self.open_bookmark),
                                ('Remove selected', self.remove_bookmark)]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            layout.addWidget(button)
        self.bookmarks_dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.bookmarks_dock)
        self.bookmarks_dock.hide()
        toggle = self.bookmarks_dock.toggleViewAction()
        toggle.setShortcut(QKeySequence('Ctrl+B'))
        common_toolbar.addAction(toggle)
        add = QAction('Bookmark page', self)
        add.setShortcut(QKeySequence('Ctrl+D'))
        add.triggered.connect(self.add_bookmark)
        common_toolbar.addAction(add)
        self.refresh_bookmarks()
        self.statusBar().showMessage('PageUp / PageDown: previous / next • F: fit page • F11: fullscreen')
        # Import the old last-opened source once, without opening or scanning it.
        if not self.settings.contains('library'):
            last_folder = self.settings.value('last_folder', '')
            self.write_library([{'source': last_folder}] if last_folder else [])
        self.library_kind.currentIndexChanged.connect(self.refresh_library)
        self.show_library()

    def read_library(self):
        try:
            records = json.loads(self.settings.value('library', '[]'))
            if not isinstance(records, list):
                return []
            valid, seen = [], set()
            for record in records:
                if not isinstance(record, dict):
                    continue
                source = record.get('source')
                if isinstance(source, str) and source and source not in seen:
                    valid.append(record)
                    seen.add(source)
            return valid
        except (ValueError, TypeError):
            return []

    def write_library(self, records):
        self.settings.setValue('library', json.dumps(records, ensure_ascii=False))
        self.settings.sync()

    def hidden_library_sources(self):
        try:
            sources = json.loads(self.settings.value('hidden_library_sources', '[]'))
            return {Path(s) for s in sources if isinstance(s, str) and s} if isinstance(sources, list) else set()
        except (ValueError, TypeError):
            return set()

    def set_hidden_library_sources(self, sources):
        self.settings.setValue('hidden_library_sources', json.dumps(sorted(str(s) for s in sources)))

    def discover_library(self):
        records = self.read_library()
        known = {Path(r['source']) for r in records} | self.hidden_library_sources()
        try:
            sources = [(source, 'manga') for source in library_sources(DEFAULT_MANGA_FOLDER)]
            sources += [(source, 'ebook') for source in ebook_sources(DEFAULT_BOOKS_FOLDER)]
        except OSError:
            self.statusBar().showMessage('Could not scan the library folders. Check access and click Refresh to retry.')
            return
        additions = [{'source': str(source), 'kind': kind} for source, kind in sources if source not in known]
        if additions:
            self.write_library(records + additions)

    def refresh_library(self):
        kind = self.library_kind.currentData()
        self.introduction.setText('Folders and PDFs in Manga appear here automatically.' if kind == 'manga'
                                  else 'EPUB, TXT, and PDF files in books appear here automatically.')
        self.library_empty.setText('Add title folders or PDFs to Manga, then click Refresh.' if kind == 'manga'
                                   else 'Add EPUB, TXT, or PDF files to books, then click Refresh.')
        self.library_restore.setEnabled(bool(self.hidden_library_sources()))
        selected = self.library_list.currentItem()
        selected_source = selected.data(Qt.ItemDataRole.UserRole) if selected else None
        self.discover_library()
        self.library_list.clear()
        for record in self.read_library():
            if record.get('kind', 'manga') != kind:
                continue
            source = Path(record['source'])
            progress = (f"Page {record['position']} of {record['total']}"
                        if isinstance(record.get('position'), int)
                        and isinstance(record.get('total'), int) else 'Ready to read')
            if record.get('format') == 'text' and isinstance(record.get('position'), int):
                progress = f"Chapter / section {record['position']} of {record['total']}"
            item = QListWidgetItem(f'{source.name}\n{progress}\n{source}')
            item.setData(Qt.ItemDataRole.UserRole, record['source'])
            self.library_list.addItem(item)
        self.library_empty.setVisible(self.library_list.count() == 0)
        if self.library_list.count():
            self.library_list.setCurrentRow(0)
            for row in range(self.library_list.count()):
                if self.library_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_source:
                    self.library_list.setCurrentRow(row)
                    break
        self.update_library_selection()

    def update_library_selection(self):
        selected = self.library_list.currentItem() is not None
        self.library_open.setEnabled(selected)
        self.library_remove.setEnabled(selected)

    def show_library(self):
        self.save_progress()
        self.ebook_source = None
        self.ebook_reader.book = None
        self.ebook_reader.browser.book = None
        self.ebook_reader.browser.clear()
        self.pdf.close()
        self.pdf_path = None
        self.folder = None
        self.pages = []
        self.pdf_pages = []
        self.chapter_starts = []
        self.index = 0
        self.pixmap = QPixmap()
        self.label.clear()
        self.reader_toolbar.setEnabled(False)
        self.reader_toolbar.hide()
        self.chapters_toolbar.setEnabled(False)
        self.chapters_toolbar.hide()
        self.bookmarks_dock.hide()
        self.stack.setCurrentWidget(self.library_panel)
        self.setWindowTitle('Library — Manga Reader')
        self.statusBar().showMessage('Choose Manga or Ebook • Double-click a title to read')
        self.refresh_library()

    def open_library_entry(self):
        item = self.library_list.currentItem()
        if item is not None:
            source = Path(item.data(Qt.ItemDataRole.UserRole))
            if self.library_kind.currentData() == 'ebook':
                self.load_ebook(source)
            else:
                self.load_folder(source)

    def ebook_progress_key(self, source):
        return 'ebook_progress/' + hashlib.sha256(str(source).encode('utf-8')).hexdigest()

    def load_ebook(self, source):
        source = source.resolve()
        if source.suffix.lower() == '.pdf':
            return self.load_folder(source, kind='ebook')
        if source.suffix.lower() not in ('.epub', '.txt'):
            QMessageBox.warning(self, 'Cannot open ebook', 'Choose an EPUB, TXT, or PDF file.')
            return False
        try:
            book = Book(source)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Cannot open ebook', str(error))
            return False
        self.show_library()
        self.ebook_source = source
        self.source_kind = 'ebook'
        self.library_kind.setCurrentIndex(1)
        try:
            position = json.loads(self.settings.value(self.ebook_progress_key(source), '{}'))
            if not isinstance(position, dict) or not all(isinstance(position.get(k, 0), int) for k in ('chapter', 'offset')):
                position = {}
        except (ValueError, TypeError):
            position = {}
        self.stack.setCurrentWidget(self.ebook_reader)
        self.ebook_reader.open_book(book, position)
        self.set_hidden_library_sources(self.hidden_library_sources() - {source})
        self.setWindowTitle(f'{book.title} — Ebook — Manga Reader')
        self.statusBar().showMessage('Scroll to read • Choose a chapter or section • Adjust the font size above')
        self.save_progress()
        return True

    def remove_library_entry(self):
        item = self.library_list.currentItem()
        if item is not None:
            source = item.data(Qt.ItemDataRole.UserRole)
            self.set_hidden_library_sources(self.hidden_library_sources() | {Path(source)})
            self.write_library([r for r in self.read_library() if r['source'] != source])
            self.refresh_library()

    def restore_hidden_titles(self):
        self.set_hidden_library_sources(set())
        self.refresh_library()

    def read_bookmarks(self):
        try:
            records = json.loads(self.settings.value('bookmarks', '[]'))
            if not isinstance(records, list):
                return []
            return [record for record in records if isinstance(record, dict)
                    and all(isinstance(record.get(key), str)
                            for key in ('name', 'source', 'page'))]
        except (ValueError, TypeError):
            return []

    def refresh_bookmarks(self):
        self.bookmark_list.clear()
        for record in self.read_bookmarks():
            item = QListWidgetItem(record['name'])
            item.setToolTip(f"{record['source']}\n{record['page']}")
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.bookmark_list.addItem(item)

    def write_bookmarks(self, records):
        self.settings.setValue('bookmarks', json.dumps(records, ensure_ascii=False))
        self.settings.sync()
        self.refresh_bookmarks()

    def add_bookmark(self):
        if not self.pages and not self.ebook_source:
            QMessageBox.information(self, 'Bookmarks', 'Open a book or manga first.')
            return
        if self.ebook_source:
            position = self.ebook_reader.position()
            source = str(self.ebook_source)
            page = f"ebook:{position['chapter']}:{position['offset']}"
        else:
            source, page = str(self.folder), self.page_key(self.index)
        records = self.read_bookmarks()
        existing = next((r for r in records if r['source'] == source and r['page'] == page), None)
        default = existing['name'] if existing else f'{Path(source).name} — {page}'
        name, accepted = QInputDialog.getText(self, 'Bookmark page', 'Bookmark name:', text=default)
        if not accepted or not name.strip():
            return
        if existing is not None:
            existing['name'] = name.strip()
        else:
            records.append({'name': name.strip(), 'source': source, 'page': page, 'kind': self.source_kind})
        self.write_bookmarks(records)
        self.bookmarks_dock.show()

    def open_bookmark(self):
        item = self.bookmark_list.currentItem()
        if item is None:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        source = Path(record['source'])
        if not source.exists():
            QMessageBox.warning(self, 'Bookmark unavailable', 'The bookmarked folder or PDF was moved or deleted.')
            return
        if record['page'].startswith('ebook:'):
            try:
                _, chapter, offset = record['page'].split(':')
                chapter, offset = int(chapter), int(offset)
            except ValueError:
                QMessageBox.warning(self, 'Bookmark unavailable', 'This bookmark has an invalid text position.')
                return
            if self.load_ebook(source):
                self.ebook_reader.show_chapter(chapter)
                self.ebook_reader.restore_offset(offset)
            return
        if not self.load_folder(source, kind=record.get('kind', 'manga')):
            return
        target = next((i for i in range(len(self.pages)) if self.page_key(i) == record['page']), None)
        if target is None:
            QMessageBox.warning(self, 'Bookmark unavailable', 'The bookmarked page no longer exists in this manga.')
            return
        self.index = target
        self.show_page()

    def remove_bookmark(self):
        item = self.bookmark_list.currentItem()
        if item is not None:
            record = item.data(Qt.ItemDataRole.UserRole)
            self.write_bookmarks([r for r in self.read_bookmarks() if r != record])

    def progress_key(self):
        return 'progress/' + hashlib.sha256(str(self.folder).encode('utf-8')).hexdigest()

    def page_key(self, index):
        path = self.pages[index]
        base = self.folder.parent if self.folder.is_file() else self.folder
        key = path.relative_to(base).as_posix()
        number = self.pdf_pages[index]
        return f'{key}#page={number + 1}' if number is not None else key

    def chapter_key(self, index):
        path = self.pages[index]
        return path if self.pdf_pages[index] is not None else path.parent

    def load_folder(self, folder, quiet_empty=False, kind='manga'):
        folder = folder.resolve()
        try:
            files = [folder] if folder.is_file() else image_files(folder, include_pdf=True)
        except OSError as error:
            QMessageBox.warning(self, 'Cannot open folder', str(error))
            return
        pages, pdf_pages, failures = [], [], []
        probe = QPdfDocument(self)
        for path in files:
            if path.suffix.lower() == '.pdf':
                error = probe.load(str(path))
                if error != QPdfDocument.Error.None_ or probe.pageCount() == 0:
                    failures.append(f'{path.name}: {error.name}')
                else:
                    pages.extend([path] * probe.pageCount())
                    pdf_pages.extend(range(probe.pageCount()))
                probe.close()
            else:
                pages.append(path)
                pdf_pages.append(None)
        probe.deleteLater()
        if failures:
            QMessageBox.warning(self, 'Unreadable PDFs',
                                'These PDFs could not be opened (damaged or password-protected):\n'
                                + '\n'.join(failures[:10]))
        if not pages:
            if not quiet_empty:
                if not failures:
                    QMessageBox.information(self, 'No pages', 'No supported images or PDFs were found.')
            return
        self.save_progress()
        self.folder = folder.resolve()
        self.ebook_source = None
        self.ebook_reader.book = None
        self.ebook_reader.browser.book = None
        self.ebook_reader.browser.clear()
        self.source_kind = kind
        self.library_kind.setCurrentIndex(1 if kind == 'ebook' else 0)
        self.pages = pages
        self.pdf_pages = pdf_pages
        self.pdf.close()
        self.pdf_path = None
        saved_name = self.settings.value(self.progress_key(), '')
        self.index = next((i for i, page in enumerate(pages)
                           if self.page_key(i) == saved_name), 0)
        self.chapter_starts = []
        self.chapter_picker.clear()
        for i, page in enumerate(pages):
            if i == 0 or self.chapter_key(i) != self.chapter_key(i - 1):
                self.chapter_starts.append(i)
                base = self.folder.parent if self.folder.is_file() else self.folder
                relative = self.chapter_key(i).relative_to(base)
                self.chapter_picker.addItem(str(relative) if relative.parts else self.folder.name)
        self.settings.setValue('last_folder', str(self.folder))
        self.set_hidden_library_sources(self.hidden_library_sources() - {self.folder})
        self.stack.setCurrentWidget(self.scroll)
        self.reader_toolbar.setEnabled(True)
        self.reader_toolbar.show()
        self.chapters_toolbar.setEnabled(True)
        self.chapters_toolbar.show()
        self.show_page()
        return True

    def move(self, delta):
        if self.pages:
            index = max(0, min(self.index + delta, len(self.pages) - 1))
            if index != self.index:
                self.index = index
                self.show_page()

    def jump_chapter(self, chapter):
        if 0 <= chapter < len(self.chapter_starts):
            self.index = self.chapter_starts[chapter]
            self.show_page()

    def show_page(self):
        path = self.pages[self.index]
        number = self.pdf_pages[self.index]
        error_text = ''
        if number is not None:
            if self.pdf_path != path:
                self.pdf.close()
                self.pdf.load(str(path))
                self.pdf_path = path
            size = self.pdf.pagePointSize(number)
            # Render only the current page, bounded to avoid huge allocations.
            scale = min(2.0, 2400 / max(size.width(), size.height(), 1))
            image = self.pdf.render(number, (size * scale).toSize())
            error_text = 'PDF page could not be rendered.'
        else:
            self.pdf.close()
            self.pdf_path = None
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            image = reader.read()
            error_text = reader.errorString()
        self.pixmap = QPixmap.fromImage(image)
        self.label.clear()
        if self.pixmap.isNull():
            self.label.setText(f'Could not read {path.name}\n{error_text}\n\nUse Next to skip this page.')
        self.previous.setEnabled(self.index > 0)
        self.next.setEnabled(self.index < len(self.pages) - 1)
        self.setWindowTitle(f'{self.folder.name} — {self.index + 1}/{len(self.pages)} — Manga Reader')
        chapter = max(i for i, start in enumerate(self.chapter_starts) if start <= self.index)
        self.chapter_picker.setCurrentIndex(chapter)
        self.previous_chapter.setEnabled(chapter > 0)
        self.next_chapter.setEnabled(chapter < len(self.chapter_starts) - 1)
        end = self.chapter_starts[chapter + 1] if chapter + 1 < len(self.chapter_starts) else len(self.pages)
        page_number = self.index - self.chapter_starts[chapter] + 1
        chapter_size = end - self.chapter_starts[chapter]
        self.statusBar().showMessage(
            f'{self.chapter_picker.currentText()} • Page {page_number}/{chapter_size}'
            f' • Total {self.index + 1}/{len(self.pages)} • {path.name}'
        )
        self.render()
        self.scroll.verticalScrollBar().setValue(0)
        self.scroll.horizontalScrollBar().setValue(0)
        self.save_progress()

    def render(self):
        if self.pixmap.isNull():
            self.scroll.setWidgetResizable(True)
            self.label.setMinimumSize(1, 1)
            self.label.setMaximumSize(16777215, 16777215)
            return
        self.scroll.setWidgetResizable(False)
        if self.fit.isChecked():
            size = self.scroll.viewport().size()
            size.setWidth(max(1, size.width() - 4))
            size.setHeight(max(1, size.height() - 4))
        else:
            size = self.pixmap.size() * self.zoom
        displayed = self.pixmap.scaled(
            size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(displayed)
        self.label.setFixedSize(displayed.size())

    def change_zoom(self, factor):
        if self.pixmap.isNull():
            return
        if self.fit.isChecked():
            self.zoom = self.label.width() / self.pixmap.width()
        self.zoom = max(0.05, min(4.0, self.zoom * factor))
        self.fit.setChecked(False)
        self.render()

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def save_preferences(self):
        self.settings.setValue('rtl', self.rtl.isChecked())

    def save_progress(self):
        if self.ebook_source and self.ebook_reader.book:
            position = self.ebook_reader.position()
            self.settings.setValue(self.ebook_progress_key(self.ebook_source), json.dumps(position))
            record = {'source': str(self.ebook_source), 'kind': 'ebook', 'format': 'text',
                      'position': position['chapter'] + 1, 'total': len(self.ebook_reader.book.chapters)}
            self.write_library([record] + [r for r in self.read_library() if r['source'] != record['source']])
        if self.folder and self.pages:
            self.settings.setValue(self.progress_key(), self.page_key(self.index))
            record = {'source': str(self.folder), 'kind': self.source_kind, 'position': self.index + 1, 'total': len(self.pages)}
            self.write_library([record] + [r for r in self.read_library() if r['source'] != record['source']])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fit'):
            self.render_timer.start(0)

    def eventFilter(self, watched, event):
        if (watched is self.scroll.viewport()
                and event.type() == QEvent.Type.Resize
                and hasattr(self, 'fit') and self.fit.isChecked()):
            self.render_timer.start(0)
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        self.render_timer.stop()
        self.save_progress()
        self.save_preferences()
        self.settings.sync()
        self.pdf.close()
        self.pdf_path = None
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MangaReader()
    window.show()
    sys.exit(app.exec())
