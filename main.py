import os
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.utils import platform

import shared

if platform not in ("android", "ios"):
    Window.size = (400, 780)  # masaüstünde telefon oranı

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_SUFFIX = ".ServiceOverlay"  # buildozer.spec -> services = Overlay:...


class MainScreen(BoxLayout):
    pass


class SettingsDialog(ModalView):
    pass


class MicToggleApp(App):
    title = "Mic Toggle"

    status_text = StringProperty("Hazır.")
    service_running = BooleanProperty(False)
    mic_open = BooleanProperty(False)
    level = NumericProperty(0.0)
    size_name = StringProperty("ORTA")
    gear_text = StringProperty("AYAR")
    gear_font = StringProperty("Roboto")

    def build(self):
        self._was_running = False
        self._waiting_overlay_perm = False

        self.size_name = shared.read_json(
            "settings.json", shared.DEFAULT_SETTINGS)["size"]
        if self.size_name not in shared.SIZES:
            self.size_name = "ORTA"

        font = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")
        if os.path.exists(font):
            self.gear_font = font
            self.gear_text = "\u2699"  # ⚙

        Clock.schedule_interval(self.refresh, 0.5)
        return MainScreen()

    # ---------- Android yaşam döngüsü ----------
    def on_pause(self):
        return True  # uygulama arka plana geçince kapanmasın

    def on_resume(self):
        if self._waiting_overlay_perm:
            self._waiting_overlay_perm = False
            self._continue_start()

    # ---------- Ayarlar ----------
    def open_settings(self):
        SettingsDialog().open()

    def set_size(self, name):
        if name not in shared.SIZES:
            return
        self.size_name = name
        shared.write_json("settings.json", {"size": name, "quit": False})

    # ---------- Servis kontrolü ----------
    def toggle_service(self):
        if self.service_running:
            self.stop_overlay()
        else:
            self.start_overlay()

    def start_overlay(self):
        if platform != "android":
            self.status_text = ("Masaüstü önizleme: overlay ve servis "
                                "yalnızca Android'de çalışır.")
            return
        from android.permissions import request_permissions, Permission
        request_permissions(
            [Permission.RECORD_AUDIO, "android.permission.POST_NOTIFICATIONS"],
            self._on_permissions,
        )

    def _on_permissions(self, permissions, grants):
        Clock.schedule_once(lambda dt: self._after_permissions(grants), 0)

    def _after_permissions(self, grants):
        if not grants or not grants[0]:
            self.status_text = ("Mikrofon izni verilmedi. Servis, yalnızca siz "
                                "izin verirseniz başlatılır.")
            return
        self._continue_start()

    def _continue_start(self):
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        Settings = autoclass("android.provider.Settings")

        if not Settings.canDrawOverlays(activity):
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + activity.getPackageName()),
            )
            self._waiting_overlay_perm = True
            self.status_text = ("Açılan ekranda Mic Toggle için "
                                "'Diğer uygulamaların üzerinde göster' iznini "
                                "açıp geri dönün.")
            activity.startActivity(intent)
            return

        shared.write_json("settings.json",
                          {"size": self.size_name, "quit": False})
        status = shared.read_json("status.json", shared.DEFAULT_STATUS)
        status.update(state="KAPALI", level=0.0, alive=0.0, error="")
        shared.write_json("status.json", status)

        service_cls = autoclass(activity.getPackageName() + SERVICE_SUFFIX)
        service_cls.start(activity, "")
        self.status_text = "Overlay başlatılıyor..."

    def stop_overlay(self):
        shared.write_json("settings.json",
                          {"size": self.size_name, "quit": True})
        self.status_text = "Durduruluyor..."
        Clock.schedule_once(self._stop_service_final, 1.0)

    def _stop_service_final(self, dt):
        if platform != "android":
            return
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        service_cls = autoclass(activity.getPackageName() + SERVICE_SUFFIX)
        service_cls.stop(activity)

    # ---------- Durum ----------
    def refresh(self, dt):
        st = shared.read_json("status.json", shared.DEFAULT_STATUS)
        running = (time.time() - float(st["alive"])) < 3.0

        self.service_running = running
        self.mic_open = running and st["state"] == "AÇIK"
        self.level = float(st["level"]) if self.mic_open else 0.0

        if running:
            self.status_text = "Overlay çalışıyor.\nMikrofon: " + st["state"]
        elif self._was_running:
            self.status_text = "Overlay durduruldu."
        if st.get("error"):
            self.status_text = "Hata: " + str(st["error"])
        self._was_running = running


if __name__ == "__main__":
    MicToggleApp().run()
