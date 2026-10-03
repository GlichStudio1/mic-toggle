[app]
title = Mic Toggle
package.name = mictoggle
package.domain = org.mictoggle
version = 0.1.0

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_dirs = .github,.buildozer,bin,.venv,venv,__pycache__,dejavu_tmp

requirements = python3,kivy,pyjnius,android
orientation = portrait
fullscreen = 0

# Arka plan servisi (foreground + mikrofon tipi)
services = Overlay:service/main.py:foreground:sticky:foregroundServiceType=microphone

# İzinler
android.permissions = SYSTEM_ALERT_WINDOW,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,RECORD_AUDIO,POST_NOTIFICATIONS,WAKE_LOCK

android.api = 34
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
