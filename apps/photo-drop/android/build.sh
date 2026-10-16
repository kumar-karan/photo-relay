#!/bin/bash
# Offline APK build for the Photo Drop launcher. No Gradle, no network.
# Reuses the Android SDK already vendored under apps/t3-server-android.
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../../.. && pwd)"

SDK="$ROOT/apps/t3-server-android/android-sdk"
BT="$SDK/build-tools/34.0.0"
AJAR="$SDK/platforms/android-34/android.jar"
KS="$ROOT/apps/t3-server-android/debug.keystore"
ZX="$PWD/lib/zxing-core-3.5.3.jar"

for f in "$BT/aapt2" "$AJAR" "$ZX"; do
  [ -e "$f" ] || { echo "missing $f" >&2; exit 1; }
done

rm -rf out && mkdir -p out/gen out/classes out/dex

echo "--- aapt2 compile/link"
"$BT/aapt2" compile --dir res -o out/compiled.zip
"$BT/aapt2" link -o out/base.apk -I "$AJAR" \
  --manifest AndroidManifest.xml \
  --min-sdk-version 26 --target-sdk-version 34 \
  --java out/gen out/compiled.zip

echo "--- javac"
find src out/gen -name '*.java' > out/sources.txt
javac --release 8 -cp "$AJAR:$ZX" -d out/classes @out/sources.txt

echo "--- d8"
# The ZXing jar goes in as program input, not just --lib, so its classes are
# actually present in classes.dex. It is pure Java with no Android dependency,
# which is why it is the one library worth shipping here.
"$BT/d8" --lib "$AJAR" --min-api 26 --output out/dex \
  $(find out/classes -name '*.class') "$ZX"

echo "--- zip/align/sign"
cp out/base.apk out/unsigned.apk
zip -j -q out/unsigned.apk out/dex/classes.dex
"$BT/zipalign" -f 4 out/unsigned.apk out/aligned.apk
[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -alias androiddebugkey \
  -storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Android Debug" -noprompt
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --out photodrop.apk out/aligned.apk
"$BT/apksigner" verify --print-certs photodrop.apk | head -2
ls -la photodrop.apk
echo BUILD_OK