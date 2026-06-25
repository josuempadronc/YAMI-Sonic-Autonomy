[app]

# ── IDENTIDAD ─────────────────────────────────────────────────────────────
title           = YAMI Sonic Autonomy
package.name    = yamisonicautonomy
package.domain  = com.cristmedicals
version         = 1.0

# ── ARCHIVOS ──────────────────────────────────────────────────────────────
source.dir      = .
source.include_exts = py,kv,png,jpg,ttf,mp3,ogg,wav,flac

# Archivo principal (sin .py)
entrypoint      = yami_main

# ── REQUISITOS (dependencias Python) ─────────────────────────────────────
# Separar con comas, sin espacios
requirements    = python3,kivy==2.3.0,pyjnius,android

# ── ORIENTACIÓN Y PANTALLA ───────────────────────────────────────────────
orientation     = portrait
fullscreen      = 1

# ── ICONO Y SPLASH (opcional, colocar archivos en el proyecto) ────────────
# icon.filename   = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/splash.png

# ── ANDROID ──────────────────────────────────────────────────────────────
[android]

# API mínima y objetivo
android.minapi          = 21
android.api             = 33
android.ndk             = 25b

# Permisos necesarios para YAMI
android.permissions     = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,RECORD_AUDIO

# Arquitecturas (incluye 64-bit para Play Store)
android.archs           = arm64-v8a, armeabi-v7a

# Aceptar licencias automáticamente (CI/CD)
android.accept_sdk_license = True

# Formato de salida en debug
android.debug_artifact  = apk

# Formato de salida en release (Play Store requiere aab)
android.release_artifact = aab

# ── BUILDOZER ─────────────────────────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1
