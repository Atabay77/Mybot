# -*- coding: utf-8 -*-
"""CoinQuest yapılandırması. Tüm gizli bilgiler .env dosyasından okunur."""
import os
import pathlib


def _load_env() -> None:
    """Basit .env okuyucu (ekstra bağımlılık gerektirmez)."""
    path = pathlib.Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BOT_USERNAME = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
ADMIN_IDS = {
    int(x) for x in os.environ.get("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
}
DB_PATH = os.environ.get("DB_PATH", str(pathlib.Path(__file__).resolve().parent / "coinquest.db"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# Ekran resimlerinin klasörü (.env içinden değiştirilebilir)
IMAGES_DIR = os.environ.get("IMAGES_DIR", "").strip()

# --- Ekonomi ayarları ---
START_COINS = 2_500
START_GEMS = 3
MIN_BET = 50
BET_CAP_BASE = 2_000        # seviye başına bahis limiti artışı
BET_CAP_MAX = 500_000
TRANSFER_TAX = 0.03         # oyuncular arası para transferi vergisi
BAZAAR_TAX = 0.05           # pazar satış vergisi
PVP_RAKE = 0.04             # PVP ödül havuzundan kesinti

DAILY_BASE = 1_500          # günlük ödül taban
DAILY_STREAK_BONUS = 450    # her seri günü için ek
HOURLY_REWARD = 350
WORK_COOLDOWN = 45 * 60
MINE_COOLDOWN = 20 * 60
ROB_COOLDOWN = 90 * 60
SKILL_COOLDOWN = 90         # bilgi/matematik/kelime oyunları arası bekleme
MATH_SECONDS = 5            # matematik için süre
WORD_SECONDS = 12           # kelime bulmaca süresi
QUIZ_SECONDS = 10           # bilgi sorusu süresi
HOURLY_COOLDOWN = 60 * 60

BANK_INTEREST = 0.02        # 24 saatte bir uygulanan faiz
BANK_MAX_MULT = 25          # seviye * bu = banka limiti (bin cinsinden)

ENERGY_REGEN_SEC = 200
ENERGY_MAX_BASE = 20

GEM_TO_COIN = 10_000        # 1 elmas = kaç altın

# --- Etkinlik ayarları ---
BOSS_INTERVAL_MIN = 180     # kaç dakikada bir boss doğar
BOSS_DURATION_MIN = 150
BOSS_ATTACK_ENERGY = 5
LOTTERY_TICKET_PRICE = 750
LOTTERY_INTERVAL_MIN = 240
LOTTERY_SEED = 5_000        # her çekiliş sonrası havuza eklenen taban
BUSINESS_COLLECT_SEC = 4 * 3600

# --- GERÇEK PARA (ÇEKİM) AYARLARI ---
# Bakiye "kuruş" olarak tutulur: 100 = 1 TMT.  Böylece kuruş hassasiyeti kaybolmaz.
MONEY_NAME = os.environ.get("MONEY_NAME", "TMT")   # para birimi adı
COINS_PER_MONEY = 100_000          # 1 TMT kaç oyun coin'i eder
DAILY_MONEY_CAP = 70               # günde en fazla 0.70 TMT çevrilebilir
MIN_WITHDRAW = 500                 # en az 5.00 TMT çekilebilir
WITHDRAW_MIN_LEVEL = 10            # çekim için gereken seviye
WITHDRAW_MIN_DAYS = 7              # hesabın en az kaç günlük olması gerektiği
# 0.70 x 7 gün = 4.90 TMT  ->  5 TMT'ye ulaşmak matematiksel olarak en az 8 gün sürer.

# USDT seçeneği (CryptoBot ile ödeme)
USDT_ENABLED = os.environ.get("USDT_ENABLED", "1") != "0"
TMT_PER_USDT = float(os.environ.get("TMT_PER_USDT", "19.65"))   # 1 USDT kaç TMT
CRYPTOBOT_NAME = os.environ.get("CRYPTOBOT_NAME", "@CryptoBot")

# Davet ödülü (elmas yok, sadece coin)
REF_REWARD_COINS = 10_000
REF_REWARD_NEW = 5_000          # davet edilene verilen
CAPTCHA_MAX_TRIES = 3           # bu kadar denemede bilemezse ödül yok
