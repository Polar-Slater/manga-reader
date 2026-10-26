"""Sign a locally built release; keep the private signing/ directory backed up.

Uses an Android signing lineage to update this project's original debug install
without uninstalling it. Requires Python 3 and Android Studio's JDK/SDK.
"""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import subprocess

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--init', action='store_true', help='Create the release key and debug-to-release signing lineage once')
parser.add_argument('--input', type=Path, help='Optional APK to sign for isolated upgrade verification')
parser.add_argument('--output', type=Path, help='Output for that verification APK')
args = parser.parse_args()
jdk = Path(os.environ.get('JAVA_HOME', r'C:\Program Files\Android\Android Studio\jbr'))
sdk = Path(os.environ.get('ANDROID_HOME', str(Path.home() / 'AppData/Local/Android/Sdk')))
build_tools = sorted((sdk / 'build-tools').glob('[0-9]*'), key=lambda p: tuple(int(n) for n in p.name.split('.') if n.isdigit()))[-1]
java = str(jdk / 'bin/java.exe')
signer = [java, '-jar', str(build_tools / 'lib/apksigner.jar')]
private = root / 'signing'
key = private / 'manga-reader-release.p12'
password = private / 'store-password.txt'
lineage = private / 'signing-lineage.bin'
old_key = private / 'original-debug.keystore'
def run(command):
    subprocess.run([str(part) for part in command], check=True)

if args.init:
    private.mkdir(exist_ok=True)
    if not key.exists():
        if password.exists():
            raise SystemExit('Password file exists without a key. Inspect signing/ before initializing again.')
        password.write_text(secrets.token_urlsafe(48), encoding='utf-8')
        run([jdk / 'bin/keytool.exe', '-genkeypair', '-keystore', key, '-storetype', 'PKCS12',
             '-alias', 'manga-reader', '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
             '-dname', 'CN=Manga Reader, OU=Personal Android App',
             '-storepass:file', password, '-keypass:file', password])
    if not lineage.exists():
        if not old_key.exists():
            shutil.copy2(Path.home() / '.android/debug.keystore', old_key)
        run(signer + ['rotate', '--out', lineage, '--old-signer', '--ks', old_key,
            '--ks-key-alias', 'androiddebugkey', '--ks-pass', 'pass:android',
            '--set-installed-data', 'true', '--set-rollback', 'false',
            '--new-signer', '--ks', key, '--ks-key-alias', 'manga-reader', '--ks-pass', f'file:{password}'])

if not all(p.is_file() for p in (key, password, lineage)):
    raise SystemExit('Missing signing material. Run with --init for the first release only.')
version = (root.parent / 'VERSION').read_text().strip()
unsigned = args.input or root / 'app/build/outputs/apk/release/app-release-unsigned.apk'
output_dir = root / 'releases'
output_dir.mkdir(exist_ok=True)
output = args.output or output_dir / f'MangaReader-{version}-pixel-fold.apk'
run(signer + ['sign', '--ks', key, '--ks-key-alias', 'manga-reader', '--ks-pass', f'file:{password}',
    '--lineage', lineage, '--min-sdk-version', '33', '--rotation-min-sdk-version', '33',
    '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'false',
    '--v3-signing-enabled', 'true', '--v4-signing-enabled', 'false',
    '--out', output, unsigned])
run(signer + ['verify', '--verbose', '--print-certs', output])
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix('.apk.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
print(f'Verified release: {output}')
