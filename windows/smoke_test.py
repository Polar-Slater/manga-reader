"""Run headlessly: python smoke_test.py."""

import os
from pathlib import Path
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import QSettings, QCoreApplication, QEvent
from PySide6.QtGui import QImage, QColor, QPdfWriter, QPainter
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from library import image_files, library_sources
from main import MangaReader


app = QApplication([])
with (tempfile.TemporaryDirectory() as directory,
      patch('main.DEFAULT_MANGA_FOLDER', Path(directory) / 'auto_library'),
      patch('main.DEFAULT_BOOKS_FOLDER', Path(directory) / 'books')):
    root = Path(directory)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(root / 'settings'))
    for name in ['10.png', '2.png', '1.png']:
        image = QImage(600, 900, QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        assert image.save(str(root / name))
    (root / '11.png').write_text('corrupt image')
    (root / 'notes.txt').write_text('Not an image')
    assert [p.name for p in image_files(root)] == ['1.png', '2.png', '10.png', '11.png']
    window = MangaReader()
    window.library_kind.setCurrentIndex(0)
    window.show()
    app.processEvents()
    window.load_folder(root)
    app.processEvents()
    assert not window.pixmap.isNull()
    assert window.index == 0 and not window.previous.isEnabled()
    window.move(-1)
    assert window.index == 0
    window.move(1)
    window.change_zoom(1.25)
    assert not window.fit.isChecked()
    window.fit.setChecked(True)
    window.render()
    window.move(100)
    assert window.index == 3 and window.pixmap.isNull()
    assert not window.next.isEnabled()
    window.move(-1)
    assert not window.pixmap.isNull()
    window.close()
    restored = MangaReader()
    restored.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert not restored.pages and restored.stack.currentWidget() is restored.library_panel
    restored.open_library_entry()
    assert restored.index == 2
    assert restored.pages[restored.index].name == '10.png'
    restored.close()
    manga = root / 'manga'
    for chapter in ['10 folder', '02 folder', '01 folder']:
        directory = manga / chapter
        directory.mkdir(parents=True)
        for name in ['manga 10.png', 'manga 02.png', 'manga 01.png']:
            assert image.save(str(directory / name))
    (manga / 'empty').mkdir()
    nested = manga / '10 folder' / 'extra'
    nested.mkdir()
    assert image.save(str(nested / '1.png'))
    expected = [f'{chapter}/manga {page}.png'
                for chapter in ['01 folder', '02 folder', '10 folder']
                for page in ['01', '02', '10']]
    expected.append('10 folder/extra/1.png')
    assert [p.relative_to(manga).as_posix() for p in image_files(manga)] == expected
    restored.load_folder(manga)
    assert restored.chapter_picker.count() == 4
    restored.move(2)
    restored.move(1)
    assert restored.index == 3 and restored.chapter_picker.currentIndex() == 1
    restored.move(-1)
    assert restored.chapter_picker.currentIndex() == 0
    restored.next_chapter.trigger()
    assert restored.index == 3
    restored.previous_chapter.trigger()
    assert restored.index == 0
    restored.chapter_picker.activated.emit(2)
    assert restored.index == 6
    restored.move(1)
    restored.close()
    resumed = MangaReader()
    resumed.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert not resumed.pages
    resumed.open_library_entry()
    assert resumed.index == 7
    assert resumed.pages[7].relative_to(manga).as_posix() == '10 folder/manga 02.png'
    resumed.close()
    pdf_folder = root / 'pdf_chapters'
    pdf_folder.mkdir()
    pdf_file = pdf_folder / '01.pdf'
    writer = QPdfWriter(str(pdf_file))
    painter = QPainter(writer)
    painter.fillRect(0, 0, writer.width(), writer.height(), QColor('red'))
    assert writer.newPage()
    painter.fillRect(0, 0, writer.width(), writer.height(), QColor('blue'))
    painter.end()
    del painter
    del writer
    assert image.save(str(pdf_folder / '02.png'))
    resumed.load_folder(pdf_folder)
    assert len(resumed.pages) == 3 and resumed.chapter_picker.count() == 2
    assert resumed.pixmap.toImage().pixelColor(100, 100).red() > 200
    resumed.move(1)
    assert resumed.pdf_pages[resumed.index] == 1
    assert resumed.pixmap.toImage().pixelColor(100, 100).blue() > 200
    resumed.change_zoom(1.25)
    assert not resumed.label.pixmap().isNull()
    resumed.move(1)
    assert resumed.pdf_pages[resumed.index] is None
    resumed.move(-1)
    resumed.close()
    pdf_resume = MangaReader()
    pdf_resume.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert not pdf_resume.pages
    pdf_resume.open_library_entry()
    assert pdf_resume.index == 1 and pdf_resume.pdf_pages[1] == 1
    pdf_resume.load_folder(pdf_file)
    assert len(pdf_resume.pages) == 2
    pdf_resume.move(1)
    pdf_resume.close()
    direct_resume = MangaReader()
    direct_resume.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert not direct_resume.pages
    direct_resume.open_library_entry()
    assert direct_resume.folder == pdf_file and direct_resume.index == 1
    with patch('main.QInputDialog.getText', return_value=('Favorite PDF page', True)):
        direct_resume.add_bookmark()
    direct_resume.load_folder(manga)
    direct_resume.index = 7
    direct_resume.show_page()
    with patch('main.QInputDialog.getText', return_value=('Favorite image', True)):
        direct_resume.add_bookmark()
    with patch('main.QInputDialog.getText', return_value=('Renamed image', True)):
        direct_resume.add_bookmark()
    assert len(direct_resume.read_bookmarks()) == 2
    with patch('main.QInputDialog.getText', return_value=('Cancelled', False)):
        direct_resume.add_bookmark()
    assert len(direct_resume.read_bookmarks()) == 2
    direct_resume.close()
    bookmark_reader = MangaReader()
    bookmark_reader.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert bookmark_reader.bookmark_list.count() == 2
    bookmark_reader.bookmark_list.setCurrentRow(0)
    bookmark_reader.open_bookmark()
    assert bookmark_reader.folder == pdf_file and bookmark_reader.index == 1
    bookmark_reader.bookmark_list.setCurrentRow(1)
    bookmark_reader.open_bookmark()
    assert bookmark_reader.folder == manga and bookmark_reader.index == 7
    assert bookmark_reader.bookmark_list.currentItem().text() == 'Renamed image'
    with patch('main.Path.exists', return_value=False), patch('main.QMessageBox.warning') as warning:
        bookmark_reader.open_bookmark()
        assert warning.called
    bookmark_reader.remove_bookmark()
    assert len(bookmark_reader.read_bookmarks()) == 1
    bookmark_reader.close()
    direct_resume.refresh_bookmarks()
    assert direct_resume.bookmark_list.count() == 1
    mixed = root / 'mixed_chapters'
    mixed.mkdir()
    wide = QImage(1200, 600, QImage.Format.Format_RGB32)
    wide.fill(QColor('white'))
    assert wide.save(str(mixed / '01.png'))
    assert wide.save(str(mixed / '03.png'))
    (mixed / '02.pdf').write_bytes(pdf_file.read_bytes())
    direct_resume.load_folder(mixed)
    assert [p.name for p in direct_resume.pages] == ['01.png', '03.png', '02.pdf', '02.pdf']
    assert direct_resume.chapter_picker.count() == 2
    direct_resume.move(1)
    assert direct_resume.chapter_picker.currentIndex() == 0
    direct_resume.next_chapter.trigger()
    assert direct_resume.index == 2 and direct_resume.pdf_pages[2] == 0
    direct_resume.previous_chapter.trigger()
    assert direct_resume.index == 0
    direct_resume.fit.setChecked(True)
    direct_resume.bookmarks_dock.hide()
    direct_resume.show()
    for _ in range(5):
        app.processEvents()
    full_width = direct_resume.label.width()
    direct_resume.bookmarks_dock.show()
    for _ in range(5):
        app.processEvents()
    assert direct_resume.label.width() < full_width
    assert direct_resume.label.width() <= direct_resume.scroll.viewport().width()
    assert direct_resume.scroll.horizontalScrollBar().maximum() == 0
    direct_resume.bookmarks_dock.hide()
    for _ in range(5):
        app.processEvents()
    assert direct_resume.label.width() == full_width
    (pdf_folder / '03.pdf').write_bytes(b'broken pdf')
    with patch('main.QMessageBox.warning') as warning:
        direct_resume.load_folder(pdf_folder)
        assert warning.called and len(direct_resume.pages) == 3
    # Returning home releases the reader and disables page navigation.
    direct_resume.load_folder(manga)
    direct_resume.move(1)
    saved_index = direct_resume.index
    progress_key = direct_resume.progress_key()
    saved_position = direct_resume.settings.value(progress_key)
    bookmarks = direct_resume.read_bookmarks()
    direct_resume.show_library()
    assert direct_resume.stack.currentWidget() is direct_resume.library_panel
    assert not direct_resume.pages and not direct_resume.reader_toolbar.isEnabled()
    direct_resume.move(1)
    assert not direct_resume.pages
    assert direct_resume.read_library()[0]['position'] == saved_index + 1
    assert direct_resume.library_list.count() == len(direct_resume.read_library())
    # Removal affects membership only, including after restarting with an empty library.
    while direct_resume.library_list.count():
        direct_resume.remove_library_entry()
    assert manga.exists() and direct_resume.read_bookmarks() == bookmarks
    assert direct_resume.settings.value(progress_key) == saved_position
    direct_resume.close()
    home = MangaReader()
    home.library_kind.setCurrentIndex(0)
    app.processEvents()
    assert home.library_list.count() == 0 and not home.pages
    home.load_folder(manga)
    assert home.index == saved_index
    home.show_library()
    # Refresh prunes missing sources without changing saved progress or bookmarks.
    home.write_library([{'source': str(root / 'missing')}])
    home.refresh_library()
    with patch('main.QMessageBox.warning') as warning:
        home.open_library_entry()
        assert not warning.called and not home.pages
        assert home.library_list.count() == 0 and home.read_library() == []
        assert home.settings.value(progress_key) == saved_position
        assert home.read_bookmarks() == bookmarks
        assert home.stack.currentWidget() is home.library_panel
    home.close()
    # Legacy settings migrate once without scanning a manga at startup.
    home.settings.remove('library')
    home.settings.setValue('last_folder', str(manga))
    with patch('main.image_files', side_effect=AssertionError('Startup must not scan manga')):
        migrated = MangaReader()
        migrated.library_kind.setCurrentIndex(0)
        app.processEvents()
        assert not migrated.pages and migrated.library_list.count() == 1
    migrated.open_library_entry()
    assert migrated.index == saved_index
    migrated.show_library()
    migrated.settings.setValue('library', '{invalid')
    migrated.refresh_library()
    assert migrated.library_list.count() == 0
    migrated.close()
    # Discover immediate title folders/PDFs, without treating chapters as titles.
    auto_root = root / 'auto_library'
    for title in ['Title 10', 'Title 2']:
        chapter = auto_root / title / 'Chapter 1'
        chapter.mkdir(parents=True)
        assert image.save(str(chapter / '1.png'))
        assert image.save(str(chapter / '2.png'))
    (auto_root / 'notes.txt').write_text('not a title')
    (auto_root / 'Book.PDF').write_bytes(pdf_file.read_bytes())
    assert [p.name for p in library_sources(auto_root)] == ['Book.PDF', 'Title 2', 'Title 10']
    auto = MangaReader()
    auto.library_kind.setCurrentIndex(0)
    assert not auto.pages and auto.library_list.count() == 3
    auto.library_list.setCurrentRow(1)
    auto.open_library_entry()
    auto.move(1)
    auto.show_library()
    assert auto.read_library()[0]['position'] == 2
    auto.refresh_library()
    assert auto.library_list.count() == 3
    # Removed automatic titles stay hidden across refresh/restart; explicit open restores them.
    auto.library_list.setCurrentRow(0)
    auto.remove_library_entry()
    auto.refresh_library()
    assert auto.library_list.count() == 2
    auto.close()
    rediscovered = MangaReader()
    rediscovered.library_kind.setCurrentIndex(0)
    assert rediscovered.library_list.count() == 2 and not rediscovered.pages
    rediscovered.load_folder(auto_root / 'Title 2')
    assert rediscovered.index == 1
    (auto_root / 'Title 3').mkdir()
    rediscovered.show_library()
    assert rediscovered.library_list.count() == 4
    rediscovered.refresh_library()
    assert rediscovered.library_list.count() == 4
    with patch('main.library_sources', side_effect=PermissionError('unavailable')):
        rediscovered.refresh_library()
        assert rediscovered.library_list.count() == 4
    (auto_root / 'Title 3').rmdir()
    rediscovered.refresh_library()
    assert rediscovered.library_list.count() == 3
    (auto_root / 'Book.PDF').unlink()
    rediscovered.refresh_library()
    assert rediscovered.library_list.count() == 2
    assert all(Path(record['source']).exists() for record in rediscovered.read_library())
    rediscovered.close()
    for reader_window in [window, restored, resumed, pdf_resume, direct_resume, bookmark_reader, home, migrated, auto, rediscovered]:
        reader_window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
print('PASS: image ordering, loading, navigation bounds, zoom, corrupt images, and saved progress')
print('PASS: nested chapters, chapter controls, cross-chapter paging, and duplicate-name bookmarks')
print('PASS: PDF rendering, mixed image/PDF chapters, zoom, folder/direct PDF resume, and damaged PDFs')
print('PASS: named image/PDF bookmarks, rename, cancellation, restart persistence, missing source, and deletion')
print('PASS: contiguous mixed-file chapters and fit-page resizing when bookmarks open and close')
print('PASS: library startup, explicit resume, progress, removal, missing sources, and legacy migration')
print('PASS: automatic title discovery, natural ordering, refresh, deduplication, and persistent hiding')
