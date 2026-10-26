# Pixel Fold release 0.2.0

## Build and sign future updates

From this Android directory, using Android Studio's JDK as `JAVA_HOME`:

```powershell
.\gradlew.bat :app:testQaUnitTest :app:connectedQaAndroidTest :app:assembleRelease :app:lintRelease
..\.venv\Scripts\python.exe .\sign-release.py
```

Connect the Pixel Fold for the device tests. They install a separate `.qa` app
with synthetic images/PDFs and do not use the everyday reader's data. Development
builds now use `.dev`; the everyday release retains `com.chenx.mangareader`.

Increment `versionCode` in `app/build.gradle.kts` for every later release and update
the repository's `VERSION` and `CHANGELOG.md`. The release version name reads VERSION.
Gradle produces an unsigned optimized APK. The signing script produces the final
`releases/MangaReader-<version>-pixel-fold.apk` plus its SHA-256 checksum and verifies
the APK signature. Only distribute that final APK.

## Signing backup — required for future updates

Back up the entire **android/signing** directory to private encrypted storage
outside this computer. It contains:

- `manga-reader-release.p12`: the private release signing key.
- `store-password.txt`: the randomly generated key password. Keep it private.
- `signing-lineage.bin`: the signed transition from the original development key.
- `original-debug.keystore`: the original key used to establish that transition.
- `pre-release-data.tar`: a precautionary backup of the original app's settings,
  saved library, bookmarks, and cached covers (not the manga files).
- `pre-release-debug.apk`: the original installed APK for reference.

The directory is excluded from Git and restricted to this Windows account and
SYSTEM. Do not share it, commit it, or include it in an APK. Do not regenerate the
key for subsequent releases. The `--init` option is for first-time setup only.

The app supports Android 13+; releases use APK Signature Scheme v3 and a signing
lineage to upgrade the original debug install in place. The release key is now the
key for future everyday updates. Ordinary debug APKs cannot replace this release;
use the separate `.dev` app for development. Do not uninstall the everyday app to
resolve a signing error, as uninstalling would discard its data and folder grants.

## Validation scope

- Release 0.2.0 passed 13 unit tests and 4 instrumented tests on the connected
  Pixel Fold. The optimized APK is approximately 2.46 MiB and is not debuggable.
- The debug-to-release signing transition was verified first with a private data
  marker in the isolated QA app, then installed over the everyday reader without
  uninstalling it. Its saved library/position remained visible and its folder
  access still worked. The original settings/APK were backed up before updating.
- The installed release passed a device smoke check: Continue reading rendered
  manga, Next/Previous returned to the starting page, fullscreen/Back worked,
  and Menu → Library returned to the main screen.
- Unit tests cover natural ordering and spread navigation with odd/even chapter
  lengths, single-page chapters, focused-page preservation and separate covers.
- Device regression tests cover mixed folder ordering, nested chapters, PDF/image
  rendering, corrupt files, persistent progress/bookmarks/preferences, library
  removal/re-addition, and library state after ViewModel recreation.
- Release lint completes with no errors; advisory dependency/style warnings remain.
- Physical pinch/swipe feel and repeated fold/unfold transitions still need normal
  hands-on use. Automated tests do not prove every physical gesture or posture.
