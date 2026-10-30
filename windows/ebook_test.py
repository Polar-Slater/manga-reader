"""Headless integration checks for ebook loading and library separation."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from zipfile import ZipFile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import QSettings, QUrl, QCoreApplication, QEvent
from PySide6.QtGui import QPdfWriter, QPainter, QColor, QTextDocument, QImage
from PySide6.QtWidgets import QApplication
from ebooks import Book, member_path
from main import MangaReader


app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    books = root / 'books'
    books.mkdir()
    manga = root / 'Manga'
    manga.mkdir()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(root / 'settings'))
    txt = books / 'Novel.txt'
    txt.write_text(('中文 reading line\n' * 6000), encoding='utf-8')
    encoded = root / 'Chinese.txt'
    encoded.write_bytes('中文小说'.encode('gb18030'))
    assert Book(encoded).chapters[0].text == '中文小说'
    encoded.write_bytes('Unicode book'.encode('utf-16'))
    assert Book(encoded).chapters[0].text == 'Unicode book'
    assert ''.join(c.text for c in Book(txt).chapters) == txt.read_bytes().decode('utf-8')
    epub = books / 'Example.epub'
    cover = QImage(100, 100, QImage.Format.Format_RGB32)
    cover.fill(QColor('blue'))
    assert cover.save(str(root / 'cover.png'))
    with ZipFile(epub, 'w') as archive:
        archive.writestr('mimetype', 'application/epub+zip')
        archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OPS/package.opf"/></rootfiles></container>')
        archive.writestr('OPS/package.opf', '''<package xmlns="http://www.idpf.org/2007/opf">
          <metadata><title>Sample book</title></metadata><manifest>
          <item id="a" href="text/one.xhtml" media-type="application/xhtml+xml"/>
          <item id="b" href="text/two.xhtml" media-type="application/xhtml+xml"/>
          </manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>''')
        archive.writestr('OPS/text/one.xhtml', '<html><body><h1>First</h1><p id="target">Hello reader</p></body></html>')
        archive.writestr('OPS/text/two.xhtml', '<html><body><h1>Second</h1><img src="../cover.png"/><a href="one.xhtml#target">Next link</a></body></html>')
        archive.writestr('OPS/cover.png', (root / 'cover.png').read_bytes())
        archive.writestr('OPS/test.bin', b'book resource')
    assert [c.title for c in Book(epub).chapters] == ['Second', 'First']
    for path in ('../../outside', 'file:///secret', 'https://example.com/book'):
        try:
            member_path('OPS/package.opf', path)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsafe resource path accepted')
    pdf = books / 'Reference.pdf'
    writer = QPdfWriter(str(pdf))
    painter = QPainter(writer)
    painter.fillRect(0, 0, writer.width(), writer.height(), QColor('white'))
    painter.end()
    del painter, writer
    (manga / 'Comic.pdf').write_bytes(pdf.read_bytes())
    (books / 'ignored.png').write_bytes(b'not a book')
    with patch('main.DEFAULT_MANGA_FOLDER', manga), patch('main.DEFAULT_BOOKS_FOLDER', books):
        window = MangaReader()
        window.show()
        app.processEvents()
        assert window.library_list.count() == 1
        window.library_kind.setCurrentIndex(1)
        assert window.library_list.count() == 3
        assert window.load_ebook(epub)
        assert window.stack.currentWidget() is window.ebook_reader
        reader = window.ebook_reader
        assert 'Second' in reader.browser.toPlainText()
        loaded_image = reader.browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl('book:/OPS/cover.png'))
        assert not QImage.fromData(loaded_image).isNull()
        reader.browser.anchorClicked.emit(QUrl('one.xhtml#target'))
        assert reader.index == 1 and 'Hello reader' in reader.browser.toPlainText()
        assert not reader.browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl.fromLocalFile(str(txt)))
        assert bytes(reader.browser.loadResource(QTextDocument.ResourceType.ImageResource, QUrl('book:/OPS/test.bin'))) == b'book resource'
        window.show_library()
        assert window.load_ebook(epub) and reader.index == 1
        assert window.load_ebook(txt)
        reader.show_chapter(1)
        app.processEvents()
        reader.browser.verticalScrollBar().setValue(1000)
        offset = reader.position()['offset']
        assert offset > 0
        reader.font_size.setValue(20)
        app.processEvents()
        assert abs(reader.position()['offset'] - offset) < 100
        with patch('main.QInputDialog.getText', return_value=('Text bookmark', True)):
            window.add_bookmark()
        assert window.read_bookmarks()[-1]['page'].startswith('ebook:1:')
        window.bookmarks_dock.hide()
        window.show_library()
        saved = json.loads(window.settings.value(window.ebook_progress_key(txt)))
        window.close()
        restored = MangaReader()
        restored.show()
        app.processEvents()
        assert restored.load_ebook(txt)
        app.processEvents()
        assert restored.ebook_reader.index == 1
        assert abs(restored.ebook_reader.position()['offset'] - saved['offset']) < 100
        restored.show_library()
        restored.bookmark_list.setCurrentRow(0)
        restored.open_bookmark()
        assert restored.ebook_reader.index == 1
        assert restored.load_ebook(pdf) and not restored.pixmap.isNull()
        restored.show_library()
        record = next(r for r in restored.read_library() if r['source'] == str(pdf))
        assert record['kind'] == 'ebook'
        assert restored.library_list.count() == 3
        restored.library_list.setCurrentRow(0)
        removed = Path(restored.library_list.currentItem().data(256))
        restored.remove_library_entry()
        restored.refresh_library()
        assert restored.library_list.count() == 2 and removed.exists()
        assert restored.load_ebook(removed)
        restored.show_library()
        assert restored.library_list.count() == 3
        broken = root / 'broken.epub'
        broken.write_bytes(b'not a zip')
        with patch('main.QMessageBox.warning') as warning:
            assert not restored.load_ebook(broken) and warning.called
            assert restored.stack.currentWidget() is restored.library_panel
        restored.close()
        for widget in (window, restored):
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
print('PASS: EPUB spine order, internal links, resource isolation, damaged books, TXT encodings and lossless sections')
print('PASS: library categories, ebook PDF, font resizing, text resume across restart, bookmarks, removal and reopening')
