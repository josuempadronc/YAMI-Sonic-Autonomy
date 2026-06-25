[app]

title           = YAMI Sonic Autonomy
package.name    = yamisonicautonomy
package.domain  = com.cristmedicals
version         = 1.0

source.dir      = .
source.include_exts = py,kv,png,jpg,ttf,mp3,ogg,wav,flac

entrypoint      = yami_main

requirements    = python3,kivy==2.3.0,pyjnius,android

orientation     = portrait
fullscreen      = 1

android.minapi          = 21
android.api             = 33
android.ndk             = 23b

android.sdk_path        = /usr/local/lib/android/sdk
android.ndk_path        = /usr/local/lib/android/sdk/ndk/23.2.8568313

android.permissions     = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,RECORD_AUDIO
android.archs           = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

android.debug_artifact  = apk
android.release_artifact = aab

[buildozer]
log_level = 2
warn_on_root = 1
