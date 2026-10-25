"""A small local manga reader. Run with: python main.py"""

import hashlib
import json
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QSettings, QTimer, QEvent
from PySide6.QtGui import QAction, QImageReader, QKeySequence, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox,
    QScrollArea, QToolBar, QComboBox, QDockWidget, QListWidget,
    QListWidgetItem, QWidget, QVBoxLayout, QPushButton, QInputDialog,
)

from library import image_files

DEFAULT_MANGA_FOLDER = Path(__file__).resolve().parent / 'Manga'


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
        self.setWindowTitle('Manga Reader')
        self.resize(1000, 800)

        self.label = QLabel('Put your manga in the Manga folder beside this app.\n\nCtrl+O — Open folder')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet('QLabel { color: #dddddd; background: #202124; padding: 0; }')
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.label)
        self.scroll.setWidgetResizable(True)
        self.scroll.viewport().installEventFilter(self)
        self.scroll.setStyleSheet('QScrollArea { border: none; background: #202124; }')
        self.setCentralWidget(self.scroll)

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

        action('Open folder', self.choose_folder, ['Ctrl+O'])
        action('Open PDF', self.choose_pdf, ['Ctrl+Shift+O'])
        toolbar.addSeparator()
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
        chapters.addAction(toggle)
        add = QAction('Bookmark page', self)
        add.setShortcut(QKeySequence('Ctrl+D'))
        add.triggered.connect(self.add_bookmark)
        chapters.addAction(add)
        self.refresh_bookmarks()
        self.statusBar().showMessage('PageUp / PageDown: previous / next • F: fit page • F11: fullscreen')
        last_folder = self.settings.value('last_folder', '')
        if last_folder and Path(last_folder).exists():
            QTimer.singleShot(0, lambda: self.load_folder(Path(last_folder)))
        elif DEFAULT_MANGA_FOLDER.is_dir():
            QTimer.singleShot(0, lambda: self.load_folder(DEFAULT_MANGA_FOLDER, quiet_empty=True))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Open manga folder', str(DEFAULT_MANGA_FOLDER)
        )
        if folder:
            self.load_folder(Path(folder))

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
        if not self.pages:
            QMessageBox.information(self, 'Bookmarks', 'Open a manga page first.')
            return
        source, page = str(self.folder), self.page_key(self.index)
        records = self.read_bookmarks()
        existing = next((r for r in records if r['source'] == source and r['page'] == page), None)
        default = existing['name'] if existing else f'{self.folder.name} — {page}'
        name, accepted = QInputDialog.getText(self, 'Bookmark page', 'Bookmark name:', text=default)
        if not accepted or not name.strip():
            return
        if existing is not None:
            existing['name'] = name.strip()
        else:
            records.append({'name': name.strip(), 'source': source, 'page': page})
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
        if not self.load_folder(source):
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

    def choose_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open manga PDF', str(DEFAULT_MANGA_FOLDER), 'PDF files (*.pdf)'
        )
        if filename:
            self.load_folder(Path(filename))

    def page_key(self, index):
        path = self.pages[index]
        base = self.folder.parent if self.folder.is_file() else self.folder
        key = path.relative_to(base).as_posix()
        number = self.pdf_pages[index]
        return f'{key}#page={number + 1}' if number is not None else key

    def chapter_key(self, index):
        path = self.pages[index]
        return path if self.pdf_pages[index] is not None else path.parent

    def load_folder(self, folder, quiet_empty=False):
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
        if self.folder and self.pages:
            self.settings.setValue(self.progress_key(), self.page_key(self.index))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'fit'):
            QTimer.singleShot(0, self.render)

    def eventFilter(self, watched, event):
        if (watched is self.scroll.viewport()
                and event.type() == QEvent.Type.Resize
                and hasattr(self, 'fit') and self.fit.isChecked()):
            QTimer.singleShot(0, self.render)
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
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
