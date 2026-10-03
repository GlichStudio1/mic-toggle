"""Uygulama ile arka plan servisi arasında ortak yardımcılar.

settings.json -> yalnızca uygulama yazar (boyut, çıkış komutu)
status.json   -> yalnızca servis yazar (durum, konum, seviye, nabız)
"""
import json
import os

# boyut adı -> (daire çapı dp, yazı boyutu sp)
SIZES = {
    "KÜÇÜK": (64, 11),
    "ORTA": (88, 14),
    "BÜYÜK": (120, 18),
}

DEFAULT_SETTINGS = {"size": "ORTA", "quit": False}
DEFAULT_STATUS = {
    "state": "KAPALI",
    "x": -1,
    "y": -1,
    "level": 0.0,
    "alive": 0.0,
    "error": "",
}


def data_dir():
    base = os.environ.get("ANDROID_PRIVATE")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".mictoggle")
    os.makedirs(base, exist_ok=True)
    return base


def read_json(name, defaults):
    data = dict(defaults)
    try:
        with open(os.path.join(data_dir(), name), "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data.update(loaded)
    except (OSError, ValueError):
        pass
    return data


def write_json(name, data):
    path = os.path.join(data_dir(), name)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass
