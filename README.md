# Manga Reader

Local manga readers for Windows and Android, supporting image folders and PDFs.
The Windows app also has an Ebook library for EPUB, TXT, and PDF books.

- **Windows:** [Setup and reading guide](windows/README.md). Requires Python 3.12
  or newer. Double-click `windows/run.bat` to start.
- **Android:** [Setup and reading guide](android/README.md).

## License

The original code in this repository, including the Windows and Android apps,
is licensed under the [GNU General Public License version 3](LICENSE)
(`GPL-3.0-only`).

You may use, study, modify, and redistribute it, including commercially. If you
distribute modified versions or other covered works, you must provide the
corresponding source code to recipients under GPLv3 and comply with its notice
and other requirements. Private modifications do not have to be published.
The software is provided without warranty, as described in the license.

Third-party dependencies retain their own licenses. This license does not apply
to manga, ebooks, or other reading content loaded into the apps.

## Project layout

- `windows/` — Python desktop app, launcher, requirements, and smoke tests.
- `android/` — Native Android app and its build files and tests.
- `Manga/` — Local manga files (excluded from Git). The Windows reader opens here
  by default; existing file paths, bookmarks, and reading progress are preserved.
- `books/` — Local EPUB, TXT, and PDF books for the Windows Ebook library.
  Reading content is excluded from Git; the empty folder is included.
- `VERSION` and `CHANGELOG.md` — Shared version and release history.

The Windows launcher can reuse an existing `.venv` at the project root. New
installations create their environment inside `windows/`.

## Validation

From the project root, using the existing environment:

```powershell
.\.venv\Scripts\python.exe windows\smoke_test.py
.\.venv\Scripts\python.exe windows\ebook_test.py
```

If the environment was created inside `windows/`, use
`windows\.venv\Scripts\python.exe` instead. Android checks are documented in the
[Android guide](android/README.md#checks).

## Version tracking

[`VERSION`](VERSION) is the source of truth for both apps.
[`CHANGELOG.md`](CHANGELOG.md) records changes in each version.
Use `MAJOR.MINOR.PATCH`: PATCH for fixes, MINOR for compatible features, and MAJOR
for incompatible changes. Versions starting with `0` indicate early development.

For each release:

1. Record changes under **Unreleased** in `CHANGELOG.md`.
2. Update `VERSION`, move the notes into a matching version/date heading, and
   leave a fresh **Unreleased** section.
3. Run the Windows smoke tests and relevant Android checks.
4. Commit changes and create an annotated tag, for example
   `git tag -a v0.1.0 -m "Release 0.1.0"` using the actual release version.
5. Push the commit and tag.
