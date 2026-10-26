# Manga Reader for Android

Native Kotlin / Jetpack Compose companion to the Windows reader. Targets Android
13 or later. Development and device testing currently focus on Pixel Fold.

## Run on your phone

1. Open this `android` directory in Android Studio and let Gradle sync finish.
2. On the Pixel, open Settings → About phone and tap Build number seven times.
   Then open Settings → System → Developer options and enable USB debugging.
3. Connect the phone by USB and accept its debugging authorization prompt.
4. Select the phone in Android Studio's device selector and click Run.
5. Copy your manga to a folder on the phone, such as `Documents/Manga`.
   In the app, choose **Open manga → Choose folder** and grant access to that folder.
   To read a single PDF, use **Open manga → Choose PDF**.

The phone reads its own files. It does not automatically access the Windows
`Manga` folder or sync progress with the desktop app or your other phone.

## Reading

- The home screen is your library. Each title folder or PDF opened through
  **Open manga** is saved as a card, with its first page as a cached cover.
  Open individual title folders to give each manga its own card; selecting a parent
  collection folder creates one card for that whole folder.
- Tap **Continue reading** for the most recently read title, or any saved title
  to resume its position. **Menu → Library** (or Back with controls visible)
  returns to the library. **Remove from library** removes the card only: manga
  files, progress and bookmarks remain intact.
- While reading, **Menu → Show cover separately** saves the preference for that
  folder/PDF. In two-page mode the first page of each chapter appears alone,
  followed by 2–3, 4–5, etc. Turning it off restores 1–2, 3–4. Your focused page
  stays unchanged. One-page mode is unaffected.
- Supports JPG, JPEG, PNG, WebP, BMP, GIF (first frame), and PDF.
- Scans nested folders, orders page numbers naturally, and advances across chapters.
- Tap the left/right edges or swipe horizontally to turn pages. In **Menu**, change
  the reading direction for manga. Previous/Next buttons always mean reading order.
- Pinch to zoom and drag to pan. Double-tap toggles 2× zoom / fit page.
- Tap the center to hide/show controls. Android Back restores hidden controls.
- Use **Chapters** to jump, **Bookmark** to save/rename the current page, and
  **Menu → Bookmarks** to open or remove saved entries.
- Reading position is saved per source. The library appears at startup.
- A retained ViewModel preserves the library/page during rotation and folding;
  the page fits the available display. Zoom/pan use saved UI state.
- Unfolding the Pixel Fold automatically shows two pages side by side when the
  app window is at least 600 dp wide. The outer screen and Pixel 10a use one page.
  Narrow split-screen windows also use one page. Page turns advance by a spread.
- Pairs start at each chapter's first page (1–2, 3–4, etc.). An odd final page has
  an empty facing slot; chapters are never mixed in a spread. Right-to-left mode
  places the earlier page on the right. Folding returns to the focused page,
  including when it was the second page of the pair before unfolding.
  Bookmarks refer to that focused page. Zoom resets when switching reading modes.

## Limits

CBZ/CBR, custom pairing offsets beyond the separate-cover option, password entry, network browsing,
and cross-device synchronization are not implemented. Images are decoded at up
to 3000 pixels on the longest side; PDFs are rendered at up to 2400 pixels.
Very high zoom may look soft. PDFs require a seekable file descriptor (local files
are recommended). Moved/deleted files or revoked folder access require reselection.

## Checks

From this directory, with Android Studio's JDK available as `JAVA_HOME`:

```powershell
.\gradlew.bat :app:assembleDebug :app:testQaUnitTest :app:connectedQaAndroidTest :app:lintRelease
```

The debug APK is `app/build/outputs/apk/debug/app-debug.apk`.
It now installs as a separate `.dev` application. For everyday use and future
updates, follow [RELEASE.md](RELEASE.md) and install the signed release APK from
`releases/`. Keep the private signing material backed up as described there.

Before relying on the app, test on Pixel Fold: folder/PDF selection, nested
chapters, page 2 before page 10, bookmarks, relaunch/resume, RTL, pinch/double-tap,
and folding/unfolding at the same page, two-page RTL order, and odd chapter endings.
Also try a damaged image, missing folder,
and a protected PDF. The two-page update was built, unit-tested, lint-checked,
installed, and launched on a connected Pixel Fold. Physical fold/unfold transitions
and touch behavior still need hands-on verification.
