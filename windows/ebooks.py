"""Local, reflowable EPUB and plain-text reading (GPL-3.0-only)."""

from dataclasses import dataclass
from pathlib import Path
import posixpath
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

from PySide6.QtCore import QByteArray, QPoint, QUrl
from PySide6.QtGui import QFont, QTextDocument
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
                              QComboBox, QPushButton, QLabel, QSpinBox)


def member_path(base, href):
    url = urlsplit(href)
    if url.scheme or url.netloc:
        raise ValueError('External EPUB content is not supported.')
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(url.path)))
    if path.startswith(('/', '../')) or path == '..' or '\\' in path:
        raise ValueError('Invalid EPUB content path.')
    return path


@dataclass
class Chapter:
    path: str
    title: str
    text: str


class Book:
    def __init__(self, path):
        self.path = Path(path)
        self.title = self.path.stem
        self.chapters = []
        self.resources = {}
        self.plain = self.path.suffix.lower() == '.txt'
        if self.plain:
            if self.path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError('This text file exceeds the 32 MB reading limit.')
            data = self.path.read_bytes()
            encodings = (['utf-32'] if data.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff'))
                         else ['utf-16'] if data.startswith((b'\xff\xfe', b'\xfe\xff'))
                         else ['utf-8-sig', 'gb18030', 'cp1252'])
            for encoding in encodings:
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeError:
                    continue
            else:
                raise ValueError('Could not decode this text file. Save it as UTF-8 and retry.')
            # Bound layout work for long novels while preserving every character.
            while text:
                end = min(len(text), 40000)
                if end < len(text):
                    newline = text.rfind('\n', 0, end)
                    if newline > 20000:
                        end = newline + 1
                self.chapters.append(Chapter(str(len(self.chapters)), f'Section {len(self.chapters) + 1}', text[:end]))
                text = text[end:]
        else:
            self._epub()
        if not self.chapters:
            raise ValueError('This book contains no readable text chapters.')

    def _epub(self):
        try:
            with ZipFile(self.path) as archive:
                infos = archive.infolist()
                if len(infos) > 10000 or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
                    raise ValueError('This EPUB exceeds the 256 MB unpacked reading limit.')
                for info in infos:
                    if info.file_size > 32 * 1024 * 1024:
                        raise ValueError('An EPUB resource exceeds the 32 MB reading limit.')
                    if not info.is_dir():
                        self.resources[info.filename] = archive.read(info)
            container = ET.fromstring(self.resources['META-INF/container.xml'])
            rootfile = container.find('.//{*}rootfile')
            if rootfile is None:
                raise ValueError('EPUB package location is missing.')
            package_path = member_path('', rootfile.attrib['full-path'])
            package = ET.fromstring(self.resources[package_path])
            title = package.find('.//{*}metadata/{*}title')
            if title is not None and title.text:
                self.title = title.text
            manifest = {item.attrib['id']: item for item in package.findall('.//{*}manifest/{*}item')}
            for reference in package.findall('.//{*}spine/{*}itemref'):
                item = manifest[reference.attrib['idref']]
                if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
                    raise ValueError('This EPUB uses unsupported chapter content; text-based EPUBs are supported.')
                path = member_path(package_path, item.attrib['href'])
                data = self.resources[path]
                root = ET.fromstring(data)
                heading = next((el for el in root.iter() if el.tag.split('}')[-1] in ('h1', 'h2')
                                and ''.join(el.itertext()).strip()), None)
                if heading is None:
                    heading = root.find('.//{*}title')
                label = ''.join(heading.itertext()).strip() if heading is not None else Path(path).stem
                self.chapters.append(Chapter(path, label or Path(path).stem, data.decode('utf-8-sig')
                                             if not data.startswith((b'\xff\xfe', b'\xfe\xff')) else data.decode('utf-16')))
        except (BadZipFile, KeyError, ET.ParseError, UnicodeError, RuntimeError) as error:
            raise ValueError('Cannot read this EPUB. It may be damaged, encrypted, or unsupported.') from error


class BookBrowser(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.book = None
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)

    def loadResource(self, resource_type, url):
        # Never resolve book resources against the filesystem or the network.
        if self.book and url.scheme() == 'book' and not url.host():
            data = self.book.resources.get(url.path().lstrip('/'))
            if data is not None:
                if resource_type == QTextDocument.ResourceType.StyleSheetResource:
                    return data.decode('utf-8', errors='replace')
                return QByteArray(data)
        return QByteArray()


class EbookReader(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.book = None
        self.index = 0
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.previous = QPushButton('Previous')
        self.previous.setToolTip('Previous chapter or text section')
        self.next = QPushButton('Next')
        self.next.setToolTip('Next chapter or text section')
        self.chapters = QComboBox()
        self.chapters.setMinimumWidth(140)
        self.chapters.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 36)
        self.font_size.setValue(settings.value('ebook_font_size', 16, type=int))
        for widget in (self.previous, self.chapters, self.next, QLabel('Font size'), self.font_size):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.browser = BookBrowser()
        self.browser.setStyleSheet('QTextBrowser { padding: 24px; }')
        layout.addWidget(self.browser)
        self.previous.clicked.connect(lambda: self.show_chapter(self.index - 1))
        self.next.clicked.connect(lambda: self.show_chapter(self.index + 1))
        self.chapters.activated.connect(self.show_chapter)
        self.font_size.valueChanged.connect(self.change_font)
        self.browser.anchorClicked.connect(self.follow_link)

    def open_book(self, book, position):
        self.book = book
        self.browser.book = book
        self.chapters.clear()
        self.chapters.addItems([chapter.title for chapter in book.chapters])
        self.show_chapter(max(0, min(position.get('chapter', 0), len(book.chapters) - 1)))
        self.restore_offset(position.get('offset', 0))

    def show_chapter(self, index):
        if not self.book or not 0 <= index < len(self.book.chapters):
            return
        self.index = index
        chapter = self.book.chapters[index]
        self.browser.clear()
        self.browser.document().setBaseUrl(QUrl('book:/' + chapter.path))
        self.browser.document().setDefaultFont(QFont('Segoe UI', self.font_size.value()))
        if self.book.plain:
            self.browser.setPlainText(chapter.text)
        else:
            self.browser.setHtml(chapter.text)
        self.chapters.setCurrentIndex(index)
        self.previous.setEnabled(index > 0)
        self.next.setEnabled(index < len(self.book.chapters) - 1)
        self.browser.verticalScrollBar().setValue(0)

    def position(self):
        return {'chapter': self.index, 'offset': self.browser.cursorForPosition(QPoint(0, 0)).position()}

    def restore_offset(self, offset):
        cursor = self.browser.textCursor()
        cursor.setPosition(max(0, min(offset, self.browser.document().characterCount() - 1)))
        self.browser.setTextCursor(cursor)
        self.browser.ensureCursorVisible()
        bar = self.browser.verticalScrollBar()
        bar.setValue(bar.value() + self.browser.cursorRect(cursor).top())

    def change_font(self, size):
        position = self.position()
        self.settings.setValue('ebook_font_size', size)
        if self.book:
            self.show_chapter(self.index)
            self.restore_offset(position['offset'])

    def follow_link(self, url):
        if not self.book:
            return
        resolved = self.browser.document().baseUrl().resolved(url)
        if resolved.scheme() != 'book' or resolved.host():
            return
        path = resolved.path().lstrip('/')
        for index, chapter in enumerate(self.book.chapters):
            if chapter.path == path:
                if index != self.index:
                    self.show_chapter(index)
                if resolved.fragment():
                    self.browser.scrollToAnchor(resolved.fragment())
                break
