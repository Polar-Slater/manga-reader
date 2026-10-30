# Manga Reader for Windows

A Python / PySide6 desktop reader for local manga and ebooks.

## Manga and Ebook libraries

Choose **Manga** or **Ebook** in the library. Manga discovers title folders and
PDFs inside `Manga`; Ebook discovers EPUB, TXT, and PDF files directly inside
`books`, alongside `Manga` at the project root. Click **Refresh** after adding
files, then double-click a title. All titles are opened through the library.
Removing a library entry hides it without deleting the file. **Restore hidden
titles** makes removed titles in `Manga` and `books` discoverable again.

EPUB and TXT use a scrollable text reader with chapter/section navigation,
selectable text, adjustable font size, saved reading position, and bookmarks
(`Ctrl+D` to add, `Ctrl+B` to show). Long TXT files are split into sections for
responsive layout. UTF-8, BOM-marked UTF-16/32, and common GB18030 Chinese text
are supported, with a Windows-1252 fallback. If text looks incorrect, save the
file as UTF-8. PDFs use the existing fixed-page viewer, zoom, and page bookmarks.

EPUB support targets DRM-free text-based EPUB 2/3 books, with spine chapter
order, basic formatting, embedded images, and links between chapters. Advanced
CSS, fixed layouts, embedded fonts, scripts, audio, and video are not fully
supported. External links/resources are not opened. Text files and individual
EPUB resources are limited to 32 MB; EPUBs are limited to 256 MB unpacked.

Run the ebook regression checks with `python windows/ebook_test.py` from the
project root, in addition to `python windows/smoke_test.py`.

## Version tracking

[`VERSION`](../VERSION) is the source of truth for the current version.
[`CHANGELOG.md`](../CHANGELOG.md) records changes in each version.

Use `MAJOR.MINOR.PATCH` version numbers: increase PATCH for bug fixes, MINOR
for new compatible features, and MAJOR for incompatible changes. Versions
starting with `0` indicate early development.

For each release:

1. Record changes under **Unreleased** in `CHANGELOG.md` as you make them.
2. Update `VERSION`, then move the unreleased notes into a heading with the
   matching version and release date. Leave a fresh **Unreleased** section.
3. Run `python smoke_test.py` using the project's virtual environment.
4. Commit the changes and create an annotated Git tag such as
   `git tag -a v0.1.0 -m "Release 0.1.0"` (replace the version for later releases).
5. Push the commit and tag with `git push origin main` and
   `git push origin v0.1.0` (using the matching tag).

Git tracks individual edits; the version file, changelog, and release tags
identify named versions of the app.

## Start on Windows

Install Python 3.12 or newer from https://www.python.org/downloads/ with the
Python launcher enabled. Double-click `run.bat`. On first launch it creates a
local `.venv` and installs PySide6 (internet access required). If the project root
already has a `.venv`, the launcher reuses it instead.

If an existing `.venv` uses Python 3.11 or older, recreate it with Python 3.12
or newer before starting the reader.

Or, from PowerShell in this folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Store your manga in the **Manga** folder at the project root (`../Manga`).
The app opens to **Your library** on every startup.
Titles retain their reading position.
Folders directly inside `Manga` are also detected automatically as separate titles;
nested chapter folders stay within their parent title. PDFs directly inside `Manga`
appear as individual titles too. Detection runs at startup, when returning to the
library, and when you click **Refresh**. Empty folders appear as titles but cannot
be read until you add supported pages.
Double-click a title or select it and click **Read selected** to resume.
Use **Library** (Ctrl+L) to return to the library while reading.
**Remove from library** only removes the saved title; files, progress, and bookmarks
are kept. Removed automatic titles stay hidden during discovery. Click
**Restore hidden titles** to rediscover removed titles in `Manga` and `books`.
When upgrading, the previously opened source is added to the library automatically
without opening it. Put each manga in its own folder directly inside `Manga`.

Choose a title from the library. Images are sorted
naturally: page 2 comes before page 10. Supported files: JPG, JPEG, PNG, WebP,
BMP, and GIF (first frame). A title folder can contain numbered
chapter folders: the reader searches all subfolders, sorts folders and pages
naturally, and moves into the next chapter when you advance past its last page.
Images directly in a folder are read before its subfolders. Directory links
and junctions are skipped.

Use the chapter dropdown or **Previous chapter / Next chapter** to jump between
folders. Each folder containing images is treated as a chapter. Bookmarks
include the chapter path, so repeated image names in different chapters work.

| Shortcut | Action |
| --- | --- |
| Ctrl+L | Return to library |
| Ctrl+D | Add or rename a bookmark for the current page |
| Ctrl+B | Show / hide bookmarks |
| Ctrl+PageUp / Ctrl+PageDown | Previous / next chapter |
| Left / Right | Previous / next; reversed in right-to-left mode |
| PageUp / PageDown or Space | Previous / next (Space advances) |
| + / − | Zoom in / out |
| F | Toggle fit-to-window |
| F11 / Escape | Toggle fullscreen / leave fullscreen |

When zoomed in, use the scrollbars or mouse wheel to move around the page.
The last folder and each folder's reading position are saved automatically
using Qt's user settings (on Windows, under HKCU\Software\LearningCode\MangaReader).
Only one original image is held in memory at a time.

## Named bookmarks

Click **Bookmark page** (Ctrl+D), enter a name, and save. You can save multiple
pages across image folders and PDFs. **Bookmarks** (Ctrl+B) opens the saved list;
double-click an entry or select it and click **Go to bookmark**. Use
**Remove selected** to delete an entry. Bookmark the same page again to rename
it. Bookmarks persist across restarts, separately from automatic reading progress.
They reference the original file locations; moving or deleting manga can make
bookmarks unavailable.

This first version reads extracted image folders; CBZ/CBR archives and
two-page spreads are not supported yet.

## PDF manga

Put PDF files directly in **Manga** for individual library entries, or inside
a title's chapter folders. Select the title in the library. Each PDF appears as a
chapter, with its pages in document order. PDFs and image files can be mixed.
Images within each folder stay together as one chapter. That image chapter and
the folder's PDF chapters are ordered naturally by their first file name.
Navigation, zoom, fullscreen, and exact-page bookmarks also work for PDFs.
Only the current PDF page is rendered, at up to 2400 pixels on its longest side;
high zoom levels can therefore look soft. Damaged and password-protected PDFs
are reported and skipped. Password entry is not supported yet.
