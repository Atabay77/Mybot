#!/usr/bin/env bash
# CoinQuest güncelleme betiği.
#   bash guncelle.sh
# Son kodu GitHub'dan indirir, /opt/coinquest içine kopyalar ve botu yeniden başlatır.
# Veritabanı (coinquest.db), .env dosyası ve resimler SİLİNMEZ.
set -e

BRANCH="${BRANCH:-claude/telegram-game-bot-q5l98b}"
REPO="${REPO:-https://github.com/Atabay77/Mybot.git}"
SRC="${SRC:-/root/Mybot}"
DIR="${DIR:-/opt/coinquest}"

command -v git >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq git >/dev/null; }

echo "==> Son kod indiriliyor ($BRANCH)..."
if [ -d "$SRC/.git" ]; then
    git -C "$SRC" fetch -q origin "$BRANCH"
    git -C "$SRC" reset -q --hard "origin/$BRANCH"
else
    rm -rf "$SRC"
    git clone -q -b "$BRANCH" "$REPO" "$SRC"
fi

echo "==> Dosyalar $DIR dizinine kopyalanıyor..."
mkdir -p "$DIR"
cp "$SRC"/coinquest/*.py "$DIR"/
cp "$SRC"/coinquest/requirements.txt "$DIR"/
# 3D arena web dosyaları
if [ -d "$SRC/coinquest/webapp" ]; then
    mkdir -p "$DIR/webapp"
    cp "$SRC"/coinquest/webapp/* "$DIR/webapp/"
fi
if [ -d "$SRC/coinquest/images" ]; then
    mkdir -p "$DIR/images"
    cp -n "$SRC"/coinquest/images/* "$DIR/images/" 2>/dev/null || true
fi
if [ -f "$SRC/coinquest/coinquest.service" ] && [ -d /etc/systemd/system ]; then
    cp "$SRC"/coinquest/coinquest.service /etc/systemd/system/coinquest.service
fi

if [ ! -x "$DIR/venv/bin/pip" ]; then
    echo "==> Sanal ortam kuruluyor..."
    python3 -m venv "$DIR/venv"
    "$DIR/venv/bin/pip" install -q --upgrade pip
fi
"$DIR/venv/bin/pip" install -q -r "$DIR/requirements.txt"

if command -v systemctl >/dev/null 2>&1; then
    echo "==> Bot yeniden başlatılıyor..."
    systemctl daemon-reload || true
    if systemctl restart coinquest; then
        sleep 2
        systemctl status coinquest --no-pager -l | head -12
    else
        echo "!!! Servis başlatılamadı. Hatayı görmek için:  journalctl -u coinquest -n 30 --no-pager"
    fi
fi
echo ""
echo "✅ Güncelleme bitti.  Log:  tail -f /var/log/coinquest.log"
