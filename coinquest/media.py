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

import config

log = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).resolve().parent
# Resimler önce ayarlanan klasörde, sonra bilinen yerlerde aranır.
DIRS = [d for d in [
    pathlib.Path(config.IMAGES_DIR) if config.IMAGES_DIR else None,
    _HERE / "images",
    pathlib.Path("/opt/coinquest/images"),
    pathlib.Path("/root/images"),
    pathlib.Path("/root"),
] if d]
DIR = DIRS[0] if config.IMAGES_DIR else _HERE / "images"
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
    "miners": "madenler",
}
SCREENS["perks"] = "ustalik"
# her madencinin kendi görseli: images/miner_m01.jpg ... miner_m15.jpg
for _i in range(1, 16):
    SCREENS[f"miner_m{_i:02d}"] = f"miner_m{_i:02d}"
# her canavarın kendi görseli: images/boss_1.jpg ... boss_9.jpg
# (bkz. images/BOSS-PROMPTLAR.md — hepsi ejderha olmasın diye ayrı ayrı)
for _i in range(1, 10):
    SCREENS[f"boss_{_i}"] = f"boss_{_i}"

# Telegram bir kez yükledikten sonra file_id'yi saklarız (tekrar yükleme olmasın)
_file_ids: dict[str, str] = {}


def path(screen: str):
    """Ekrana ait resim dosyasını döner, yoksa None."""
    name = SCREENS.get(screen)
    if not name:
        return None
    for folder in DIRS:
        try:
            if not folder.is_dir():
                continue
        except OSError:
            continue
        for ext in EXTS:
            candidate = folder / f"{name}{ext}"
            if candidate.is_file():
                return candidate
    return None


def cached(screen: str):
    return _file_ids.get(screen)


def remember(screen: str, file_id: str) -> None:
    _file_ids[screen] = file_id


def available() -> list[str]:
    return [s for s in SCREENS if path(s)]
