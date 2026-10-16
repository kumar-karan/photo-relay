#!/bin/bash
# Manual offline build of the T3 Code controller app (no Gradle/network).
set -e
cd "$(dirname "$0")"
SDK="$(pwd)/android-sdk"
BT=$SDK/build-tools/34.0.0
AJAR=$SDK/platforms/android-34/android.jar
rm -rf out && mkdir -p out/gen out/classes out/dex
echo "--- aapt2 compile/link"
$BT/aapt2 compile --dir t3app/res -o out/compiled.zip
$BT/aapt2 link -o out/base.apk -I "$AJAR" \
  --manifest t3app/AndroidManifest.xml \
  --min-sdk-version 26 --target-sdk-version 34 \
  --java out/gen out/compiled.zip
echo "--- javac"
find t3app/src out/gen -name '*.java' > out/sources.txt
javac --release 8 -cp "$AJAR" -d out/classes @out/sources.txt
echo "--- d8"
$BT/d8 --lib "$AJAR" --min-api 26 --output out/dex $(find out/classes -name '*.class')
echo "--- zip/align/sign"
cp out/base.apk out/unsigned.apk
zip -j -q out/unsigned.apk out/dex/classes.dex
$BT/zipalign -f 4 out/unsigned.apk out/aligned.apk
[ -f debug.keystore ] || keytool -genkeypair -keystore debug.keystore -alias androiddebugkey \
  -storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Android Debug" -noprompt
$BT/apksigner sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
  --out t3code.apk out/aligned.apk
$BT/apksigner verify --print-certs t3code.apk | head -2
ls -la t3code.apk
echo BUILD_OK
