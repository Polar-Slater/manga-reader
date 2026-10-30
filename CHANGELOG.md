# Changelog

This file records user-visible changes. The current version is stored in `VERSION`.

## Unreleased

No changes yet.

## 0.3.0 - 2026-10-30

- Ebook text now uses the app theme's default background and text colors.
- Removed standalone Open folder/PDF/ebook controls and shortcuts from Windows;
  titles open through the library. Added restoration of hidden folder titles.
- Added Manga and Ebook categories to the Windows library and a sibling `books`
  folder for EPUB, TXT, and PDF discovery. EPUB/TXT support includes chapter or
  section navigation, font sizing, saved text positions, and bookmarks; ebook
  PDFs reuse the existing PDF viewer.
- Automatically discover title folders and PDFs inside `Manga` in the Windows
  library, with refresh and persistent hiding of removed titles.
- Added a Windows startup library with saved folder/PDF titles, reading progress,
  explicit resume, and removal without deleting files or bookmarks. The previous
  source migrates into the library instead of opening automatically.

## 0.2.1 - 2026-10-30

- Moved the Windows app, launcher, tests, and documentation into `windows/`.
  Existing manga paths and the root Python environment remain usable.
- Fixed Android zoom and pan gestures after toggling Show cover separately.
- Raised the Windows minimum Python version to 3.12, with startup checks and
  guidance for updating existing virtual environments.

## 0.2.0 - 2026-10-25

- Stabilized library/reader transitions: returning to the library stops page
  rendering, and folding on the library screen no longer changes reading history.
- Fixed folders ending in `.pdf` being treated as PDF files.
- Added isolated device regression tests and repeatable release signing.
- Signed and installed the optimized Pixel Fold release with an in-place signing-key
  transition, preserving existing reading data and folder access.
- Added a Pixel Fold library with cached cover thumbnails, saved titles and reading
  progress, Continue reading, and removal from the library without deleting manga.
- Added a per-title Show cover separately setting, pairing chapter pages as cover,
  2–3, 4–5 while keeping the focused page when switching modes.
- Pixel Fold automatically switches to two-page spreads on its unfolded display,
  with right-to-left ordering, chapter-aware page turns, and focused-page continuity.
- Combined Android folder and PDF opening under one **Open manga** entry.
- Added a native Android reader for Pixel 10a and Pixel Fold: local image folders,
  nested chapters, PDFs, touch navigation, zoom, fullscreen, right-to-left mode,
  automatic progress, and named bookmarks. Regression checks run on Pixel Fold.

## 0.1.0 - 2026-10-25

### Added

- Local image-folder reading with natural page ordering and nested chapters.
- PDF reading, including folders containing both images and PDFs.
- Page and chapter navigation, zoom, fit-to-window, right-to-left controls,
  and fullscreen mode.
- Saved reading progress and named bookmarks for images and PDF pages.
- Windows launcher and headless smoke tests.

### Fixed

- Fit-to-window updates when the bookmarks panel opens or closes.
- Images in mixed image/PDF folders remain together as one chapter.
