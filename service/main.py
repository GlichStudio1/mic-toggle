"""Mic Toggle arka plan servisi (foreground service).

- Yüzen daire: WindowManager + TYPE_APPLICATION_OVERLAY
- Mikrofon: yalnızca AÇIK iken AudioRecord ile açılır; sadece ses seviyesi
  ölçülür. Hiçbir ses dosyaya yazılmaz, saklanmaz veya gönderilmez.
"""
import math
import os
import sys
import threading
import time
import traceback

try:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    _ROOT = os.getcwd()
for _p in (_ROOT, os.getcwd()):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import shared  # noqa: E402
from jnius import PythonJavaClass, autoclass, cast, java_method  # noqa: E402

svc = autoclass("org.kivy.android.PythonService").mService

Context = autoclass("android.content.Context")
Handler = autoclass("android.os.Handler")
Looper = autoclass("android.os.Looper")
Settings = autoclass("android.provider.Settings")
TextView = autoclass("android.widget.TextView")
Typeface = autoclass("android.graphics.Typeface")
Color = autoclass("android.graphics.Color")
PixelFormat = autoclass("android.graphics.PixelFormat")
GradientDrawable = autoclass("android.graphics.drawable.GradientDrawable")
Gravity = autoclass("android.view.Gravity")
TypedValue = autoclass("android.util.TypedValue")
LP = autoclass("android.view.WindowManager$LayoutParams")
AudioRecord = autoclass("android.media.AudioRecord")
AudioFormat = autoclass("android.media.AudioFormat")
AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
ByteBuffer = autoclass("java.nio.ByteBuffer")
ByteOrder = autoclass("java.nio.ByteOrder")

_pending = set()  # Python nesnelerinin çöp toplanmasını engeller


class Runner(PythonJavaClass):
    __javainterfaces__ = ["java/lang/Runnable"]
    __javacontext__ = "app"

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    @java_method("()V")
    def run(self):
        try:
            self.fn()
        except Exception:
            traceback.print_exc()
        finally:
            _pending.discard(self)


_main_handler = Handler(Looper.getMainLooper())


def post_ui(fn):
    r = Runner(fn)
    _pending.add(r)
    _main_handler.post(r)


class TouchListener(PythonJavaClass):
    __javainterfaces__ = ["android/view/View$OnTouchListener"]
    __javacontext__ = "app"

    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay

    @java_method("(Landroid/view/View;Landroid/view/MotionEvent;)Z")
    def onTouch(self, view, event):
        try:
            return self.overlay.on_touch(event)
        except Exception:
            traceback.print_exc()
            return False


class Overlay:
    def __init__(self, size_name, x, y):
        self.size_name = size_name if size_name in shared.SIZES else "ORTA"
        self.state = "KAPALI"
        self.x, self.y = int(x), int(y)
        self.error = ""
        self.view = None
        self.params = None
        self.bg = None
        self.listener = None
        self.wm = cast("android.view.WindowManager",
                       svc.getSystemService(Context.WINDOW_SERVICE))
        self.density = svc.getResources().getDisplayMetrics().density
        self.slop = 8 * self.density
        self._down = None
        self._start = None
        self._moved = False

    def px(self, dp):
        return int(dp * self.density + 0.5)

    # ----- dışarıdan (herhangi bir thread) çağrılanlar -----
    def create(self):
        post_ui(self._create)

    def destroy(self):
        post_ui(self._destroy)

    def set_size(self, name):
        self.size_name = name
        post_ui(self._apply)

    def set_state(self, state):
        self.state = state
        post_ui(self._apply)

    # ----- yalnızca ana (UI) thread'inde çalışanlar -----
    def _create(self):
        try:
            tv = TextView(svc)
            tv.setGravity(Gravity.CENTER)
            tv.setTypeface(Typeface.DEFAULT_BOLD)
            tv.setTextColor(Color.WHITE)
            tv.setIncludeFontPadding(False)
            tv.setMaxLines(1)

            self.bg = GradientDrawable()
            self.bg.setShape(GradientDrawable.OVAL)
            tv.setBackground(self.bg)

            self.listener = TouchListener(self)
            tv.setOnTouchListener(self.listener)
            self.view = tv

            flags = LP.FLAG_NOT_FOCUSABLE | LP.FLAG_LAYOUT_IN_SCREEN
            size = self.px(shared.SIZES[self.size_name][0])
            self.params = LP(size, size, LP.TYPE_APPLICATION_OVERLAY,
                             flags, PixelFormat.TRANSLUCENT)
            self.params.gravity = Gravity.TOP | Gravity.START
            self._apply(add=True)
        except Exception as e:
            traceback.print_exc()
            self.error = "Overlay oluşturulamadı: " + str(e)

    def _apply(self, add=False):
        if self.view is None:
            return
        dp_size, sp_size = shared.SIZES[self.size_name]
        s = self.px(dp_size)
        dm = svc.getResources().getDisplayMetrics()
        w, h = int(dm.widthPixels), int(dm.heightPixels)

        if self.x < 0 or self.y < 0:  # ilk açılış: sağ kenar, ekranın üst yarısı
            self.x = w - s - self.px(16)
            self.y = int(h * 0.35)
        # ekran sınırları içinde tut
        self.x = max(0, min(self.x, w - s))
        self.y = max(0, min(self.y, h - s))

        p = self.params
        p.width = s
        p.height = s
        p.x = self.x
        p.y = self.y

        on = self.state == "AÇIK"
        self.bg.setColor(Color.parseColor("#2E7D32" if on else "#C62828"))
        self.bg.setStroke(self.px(3), Color.WHITE)
        self.view.setText("AÇIK" if on else "KAPALI")
        self.view.setTextSize(TypedValue.COMPLEX_UNIT_SP, float(sp_size))

        if add:
            self.wm.addView(self.view, p)
        else:
            self.wm.updateViewLayout(self.view, p)

    def _destroy(self):
        try:
            if self.view is not None:
                self.wm.removeView(self.view)
        except Exception:
            traceback.print_exc()
        self.view = None

    def on_touch(self, event):
        action = event.getActionMasked()  # 0=DOWN 1=UP 2=MOVE 3=CANCEL
        rx, ry = event.getRawX(), event.getRawY()

        if action == 0:
            self._down = (rx, ry)
            self._start = (self.x, self.y)
            self._moved = False
        elif action == 2 and self._down:
            dx, dy = rx - self._down[0], ry - self._down[1]
            if self._moved or abs(dx) > self.slop or abs(dy) > self.slop:
                self._moved = True
                self.x = int(self._start[0] + dx)
                self.y = int(self._start[1] + dy)
                self._apply()
        elif action == 1:
            if not self._moved:  # sürükleme değil, dokunma
                self.state = "KAPALI" if self.state == "AÇIK" else "AÇIK"
                self._apply()
            self._down = None
        elif action == 3:
            self._down = None
        return True


class MicMeter:
    """Yalnızca ses SEVİYESİ ölçer. Ses verisi hiçbir yere kaydedilmez."""
    RATE = 16000
    CHUNK = 3200  # ~100 ms

    def __init__(self):
        self.thread = None
        self.stop_evt = threading.Event()
        self.level = 0.0
        self.error = ""

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.running:
            return
        self.stop_evt.clear()
        self.level = 0.0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_evt.set()
        if self.thread is not None:
            self.thread.join(1.0)
        self.thread = None
        self.level = 0.0

    def _run(self):
        rec = None
        try:
            ch = AudioFormat.CHANNEL_IN_MONO
            enc = AudioFormat.ENCODING_PCM_16BIT
            min_buf = AudioRecord.getMinBufferSize(self.RATE, ch, enc)
            if min_buf <= 0:
                raise RuntimeError("Ses arabelleği alınamadı")
            rec = AudioRecord(AudioSource.MIC, self.RATE, ch, enc,
                              max(min_buf, self.CHUNK) * 2)
            if rec.getState() != AudioRecord.STATE_INITIALIZED:
                raise RuntimeError("Mikrofon başlatılamadı (izin/başka uygulama?)")

            bb = ByteBuffer.allocateDirect(self.CHUNK)
            bb.order(ByteOrder.nativeOrder())
            rec.startRecording()

            while not self.stop_evt.is_set():
                n = rec.read(bb, self.CHUNK)
                if n < 0:
                    raise RuntimeError("Mikrofon okuma hatası: %d" % n)
                acc, cnt = 0, 0
                for i in range(0, n - 1, 32):  # seyrek örnekle, sadece seviye
                    v = bb.getShort(i)
                    acc += v * v
                    cnt += 1
                if cnt:
                    rms = math.sqrt(acc / cnt)
                    self.level = min(1.0, rms / 6000.0)
        except Exception as e:
            traceback.print_exc()
            self.error = str(e)
        finally:
            try:
                if rec is not None:
                    rec.stop()
                    rec.release()
            except Exception:
                pass
            self.level = 0.0


def write_status(overlay, meter, error):
    shared.write_json("status.json", {
        "state": overlay.state,
        "x": overlay.x,
        "y": overlay.y,
        "level": round(meter.level, 3),
        "alive": time.time(),
        "error": error,
    })


def main():
    settings = shared.read_json("settings.json", shared.DEFAULT_SETTINGS)
    status = shared.read_json("status.json", shared.DEFAULT_STATUS)

    if not Settings.canDrawOverlays(svc):
        status.update(state="KAPALI", level=0.0, alive=time.time(),
                      error="Overlay izni verilmemiş")
        shared.write_json("status.json", status)
        time.sleep(2)
        svc.stopSelf()
        return

    overlay = Overlay(settings["size"], status["x"], status["y"])
    meter = MicMeter()
    error = ""
    overlay.create()

    try:
        while True:
            settings = shared.read_json("settings.json", shared.DEFAULT_SETTINGS)
            if settings.get("quit"):
                break

            new_size = settings.get("size")
            if new_size in shared.SIZES and new_size != overlay.size_name:
                overlay.set_size(new_size)

            if meter.error:  # mikrofon açılamadıysa butonu KAPALI'ya çek
                error = meter.error
                meter.error = ""
                meter.stop()
                overlay.set_state("KAPALI")
            if overlay.error:
                error = overlay.error

            want_mic = overlay.state == "AÇIK"
            if want_mic and not meter.running:
                error = ""
                meter.start()
            elif not want_mic and meter.running:
                meter.stop()

            write_status(overlay, meter, error)
            time.sleep(0.25)
    finally:
        meter.stop()  # mikrofonu kesinlikle bırak
        overlay.destroy()
        time.sleep(0.4)
        shared.write_json("status.json", {
            "state": "KAPALI", "x": overlay.x, "y": overlay.y,
            "level": 0.0, "alive": 0.0, "error": error,
        })
        svc.stopSelf()


try:
    main()
except Exception:
    traceback.print_exc()
