# build_agent.ps1 — gradle-free IMMORTAL build. Light, like the agent.
# Prereqs: Android cmdline-tools installed (see README_BUILD.md), JDK 21.
# Output: agent\build\immortal.apk  (~<100KB expected)
param(
    [string]$Sdk = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME }
                    else { "$env:LOCALAPPDATA\Android\Sdk" })
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path   # agent\
$src  = Join-Path $root "src"
$res  = Join-Path $root "res"
$man  = Join-Path $root "AndroidManifest.xml"
$out  = Join-Path $root "build"
New-Item -ItemType Directory -Force -Path $out | Out-Null

# --- locate newest platform + build-tools -------------------------------
$platform   = Get-ChildItem (Join-Path $Sdk "platforms") -Directory |
              Sort-Object Name | Select-Object -Last 1
$buildTools = Get-ChildItem (Join-Path $Sdk "build-tools") -Directory |
              Sort-Object Name | Select-Object -Last 1
if (-not $platform -or -not $buildTools) {
    throw "SDK incomplete. Run: sdkmanager 'platforms;android-34' 'build-tools;34.0.0'"
}
$androidJar = Join-Path $platform.FullName "android.jar"
Write-Host "[*] platform : $($platform.Name)"
Write-Host "[*] bt       : $($buildTools.Name)"

$aapt2     = Join-Path $buildTools.FullName "aapt2.exe"
$d8        = Join-Path $buildTools.FullName "d8.bat"
$zipalign  = Join-Path $buildTools.FullName "zipalign.exe"
$apksigner = Join-Path $buildTools.FullName "apksigner.bat"

# --- 1. resources -> flat + linked base apk (with R.java) ---------------
& $aapt2 compile --dir $res -o (Join-Path $out "res.zip")
& $aapt2 link -o (Join-Path $out "base.apk") `
    -I $androidJar `
    --manifest $man `
    --java (Join-Path $out "gen") `
    (Join-Path $out "res.zip")
if ($LASTEXITCODE -ne 0) { throw "aapt2 link failed" }

# --- 2. javac (JDK 21, language level 8) --------------------------------
$classes = Join-Path $out "classes"
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$javaFiles = Get-ChildItem $src -Recurse -Filter *.java |
             ForEach-Object { $_.FullName }
& javac --release 8 -nowarn `
    -classpath $androidJar `
    -d $classes `
    (Join-Path $out "gen\com\lo\syskit\R.java") `
    $javaFiles
if ($LASTEXITCODE -ne 0) { throw "javac failed" }

# --- 3. d8 -> classes.dex -----------------------------------------------
$classFiles = Get-ChildItem $classes -Recurse -Filter *.class |
              ForEach-Object { $_.FullName }
& $d8 --release --min-api 21 --lib $androidJar `
      --output $out $classFiles
if ($LASTEXITCODE -ne 0) { throw "d8 failed" }

# --- 4. dex into the apk (jar = JDK tool, keeps entries right) ----------
Copy-Item (Join-Path $out "base.apk") (Join-Path $out "unsigned.apk") -Force
Push-Location $out
& jar uf unsigned.apk classes.dex
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "dex merge failed" }

# --- 5. align + sign with debug key -------------------------------------
$aligned   = Join-Path $out "aligned.apk"
$finalApk  = Join-Path $out "immortal.apk"
& $zipalign -f 4 (Join-Path $out "unsigned.apk") $aligned
$keystore = Join-Path $out "immortal.keystore"
if (-not (Test-Path $keystore)) {
    & keytool -genkeypair -keystore $keystore -storepass immortal `
      -keypass immortal -alias immortal -keyalg RSA -keysize 2048 `
      -validity 10000 -dname "CN=WebView System"
}
& $apksigner sign --ks $keystore --ks-pass pass:immortal `
    --key-pass pass:immortal --out $finalApk $aligned
if ($LASTEXITCODE -ne 0) { throw "signing failed" }

$size = (Get-Item $finalApk).Length
Write-Host "[+] BUILT: $finalApk ($size bytes = $([math]::Round($size/1KB,1)) KB)"
Write-Host "[*] install: adb install -r -g $finalApk"
