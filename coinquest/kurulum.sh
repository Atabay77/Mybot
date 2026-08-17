#!/usr/bin/env bash
# CoinQuest tek komutluk VPS kurulumu (Ubuntu/Debian, root ile çalıştır)
#   bash kurulum.sh
set -e

DIR=/opt/coinquest

echo "==> Paketler kuruluyor..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git >/dev/null

echo "==> Dosyalar $DIR dizinine kopyalanıyor..."
mkdir -p "$DIR"
cp -r "$(dirname "$(readlink -f "$0")")"/*.py "$DIR"/
cp -n "$(dirname "$(readlink -f "$0")")"/.env.example "$DIR"/.env.example 2>/dev/null || true
cp "$(dirname "$(readlink -f "$0")")"/requirements.txt "$DIR"/
cp "$(dirname "$(readlink -f "$0")")"/coinquest.service /etc/systemd/system/coinquest.service

echo "==> Sanal ortam ve bağımlılıklar..."
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q --upgrade pip
"$DIR/venv/bin/pip" install -q -r "$DIR/requirements.txt"

systemctl daemon-reload

if [ ! -f "$DIR/.env" ]; then
    cp "$DIR/.env.example" "$DIR/.env"
    echo ""
    echo "!!!  ŞİMDİ TOKEN'INI GİR:  nano $DIR/.env"
    echo "!!!  BOT_TOKEN=... ve ADMIN_IDS=... satırlarını doldur, CTRL+O CTRL+X ile kaydet."
    echo "!!!  Sonra: systemctl enable --now coinquest"
    exit 0
fi

echo "==> Servis başlatılıyor..."
systemctl daemon-reload
systemctl enable --now coinquest
sleep 2
systemctl status coinquest --no-pager -l | head -20
echo ""
echo "✅ Kurulum bitti.  Log:  tail -f /var/log/coinquest.log"
