# -*- coding: utf-8 -*-
"""Ekran görselleri.

Resim eklemek için tek yapman gereken: dosyayı  images/  klasörüne
aşağıdaki adlarla koymak. Bot açılışta bulur, yoksa sadece yazı gönderir.

    images/karsilama.jpg   -> ilk açılış
    images/menu.jpg        -> ana menü
    images/para.jpg        -> gerçek para ekranı
    images/oyunlar.jpg     -> oyunlar ekranı
    images/hediye.jpg      -> günlük hediye
    images/market.jpg      -> market
    images/yardim.jpg      -> nasıl oynanır
    images/duello.jpg      -> düello ekranı
    images/canavar.jpg     -> boss/canavar
    images/kazandin.jpg    -> büyük kazanç
"""
import logging
import pathlib

log = logging.getLogger(__name__)

DIR = pathlib.Path(__file__).resolve().parent / "images"
EXTS = (".jpg", ".jpeg", ".png", ".webp")

SCREENS = {
    "welcome": "karsilama",
    "menu": "menu",
    "cash": "para",
    "games": "oyunlar",
    "daily": "hediye",
    "market": "market",
    "help": "yardim",
    "duel": "duello",
    "boss": "canavar",
    "bigwin": "kazandin",
}

# Telegram bir kez yükledikten sonra file_id'yi saklarız (tekrar yükleme olmasın)
_file_ids: dict[str, str] = {}


def path(screen: str):
    """Ekrana ait resim dosyasını döner, yoksa None."""
    name = SCREENS.get(screen)
    if not name or not DIR.is_dir():
        return None
    for ext in EXTS:
        candidate = DIR / f"{name}{ext}"
        if candidate.is_file():
            return candidate
    return None


def cached(screen: str):
    return _file_ids.get(screen)


def remember(screen: str, file_id: str) -> None:
    _file_ids[screen] = file_id


def available() -> list[str]:
    return [s for s in SCREENS if path(s)]
