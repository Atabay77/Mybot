# 🏰 CoinQuest — Telegram Oyun & Ekonomi Botu

Altın (🪙) ve elmas (💎) ekonomili, PVP düellolu, marketli, klanlı, boss savaşlı Telegram oyun botu.
Tamamen Türkçe. Tek bağımlılık: `python-telegram-bot`. Veritabanı: SQLite (kurulum gerektirmez).

---

## ⚡ VPS'e 5 dakikada kurulum (Termius / SSH)

```bash
# 1) Sunucuya bağlan, dosyaları çek
cd /opt
git clone -b claude/telegram-game-bot-q5l98b https://github.com/Atabay77/Mybot.git
cd Mybot/coinquest

# 2) Otomatik kurulum
bash kurulum.sh

# 3) Token'ını gir
nano /opt/coinquest/.env
#    BOT_TOKEN=123456:ABC...      <- BotFather'dan aldığın token
#    ADMIN_IDS=123456789          <- @userinfobot ile öğrendiğin kendi ID'in
#    CTRL+O, ENTER, CTRL+X ile kaydet

# 4) Başlat
systemctl enable --now coinquest

# 5) Kontrol
systemctl status coinquest
tail -f /var/log/coinquest.log
```

### Elle kurulum (script kullanmadan)

```bash
apt update && apt install -y python3 python3-venv python3-pip git
cd /opt/coinquest
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env      # token'ı yaz
venv/bin/python bot.py                 # test için ekranda çalıştır
```

### Servis komutları

| İşlem | Komut |
|---|---|
| Başlat | `systemctl start coinquest` |
| Durdur | `systemctl stop coinquest` |
| Yeniden başlat | `systemctl restart coinquest` |
| Durum | `systemctl status coinquest` |
| Canlı log | `tail -f /var/log/coinquest.log` |
| Otomatik başlat | `systemctl enable coinquest` |
| Güncelle | `cd /opt/Mybot && git pull && bash coinquest/kurulum.sh && systemctl restart coinquest` |

---

## 🎮 İçerik

### Bahisli oyunlar (özel sohbet)
| Oyun | Açıklama |
|---|---|
| 🎰 Slot | 3 makara, üçlü kombinasyonda 700x'e kadar |
| 💣 Mayın Tarlası | 5x5 kutu, 3/5/10/15 mayın seçenekli, istediğin an "çek" |
| 🃏 Blackjack | 21, gerçek deste, iki katı (double) desteği |
| 🎴 Yüksek/Düşük | Kart tahmini, zincir çarpanı birikir |
| 🎡 Rulet | Renk / tek-çift / düzine / sıfır (35x) |
| 🎯 Şans Çarkı | Tek tık, 12 dilim |
| 🪙 Yazı Tura | 1.9x |
| 🎲 Zar | Telegram'ın **gerçek zar animasyonu** ile |
| 🚀 Roket (Crash) | Patlamadan önce çık, 40x'e kadar |

### Beceri oyunları (bedava, bilgiyle kazan)
🧠 Bilgi Yarışması · ➗ Matematik Sprint · 🔤 Kelime Bulmaca · ⚡ Refleks Testi

### ⚔️ PVP (gruplarda, gerçek altın karşılığı)
`/duello` ile kur, arkadaşın "KABUL EDİYORUM" der; kazanan havuzu alır (%4 komisyon).
- ✂️ Taş-Kağıt-Makas (3 raunt, gizli seçim)
- ❌⭕ XOX (sıralı tahta)
- 🎲 Emoji Zar (Telegram zarı/dart/bowling/basket/futbol)
- ⚔️ Arena Savaşı (ekipmanların tur tur savaşır)
- 🎁 Gizemli Kutu

### 🎉 Parti oyunları (grup, bedava)
`/parti` — Bilgi yarışı, hızlı matematik, kelime avı, refleks düellosu, hazine sandığı.
İlk bilen altını kapar. Kişi başı günlük ödül limiti vardır (spam koruması).

### 🏪 Ekonomi
- **Market:** 7 silah, 7 zırh, 6 evcil hayvan, 7 sarf malzemesi — 6 nadirlik seviyesi
- **Yükseltme:** eşyalar +10'a kadar, her seviye +%12 güç, başarısızlık riski
- **🛒 Oyuncu Pazarı:** kendi fiyatını koy, başkasına sat (%5 vergi) — gerçek tüccarlık
- **🏭 İşletmeler:** simit tezgahından holdinge, 4 saatte bir pasif gelir
- **🏦 Banka:** günlük %2 faiz + soygundan korunma
- **🥷 Soygun:** `/soy @kisi` — seviye ve şansa bağlı
- **💸 Transfer:** arkadaşına para gönder (%3 vergi)

### 🌍 Sosyal
- **🐉 Dünya Bossu:** 3 saatte bir doğar, tüm oyuncular birlikte vurur, hasara göre ödül paylaşılır
- **🏰 Klanlar:** kur/katıl/bağış yap, klan seviyesi tüm üyelere kazanç bonusu verir
- **🎟 Piyango:** 4 saatte bir çekiliş, havuzun tamamı kazanana
- **📜 Görevler:** her gün 3 rastgele görev · **🏅 13 başarım**
- **🏆 Sıralamalar:** zengin / seviye / PVP / en büyük vuruş / oyun / boss / klan
- **👥 Davet sistemi:** kişi başı 10.000 🪙 + 2 💎

### 🎚 İlerleme
Seviye + XP, enerji (yenilenen), unvanlar, evcil hayvan bonusları, geçici etkiler (şans/XP/kalkan).

---

## 📋 Komutlar

```
/start /menu /profil /bakiye /yardim
/oyunlar                 → oyun salonu
/duello /kabul           → PVP (grupta)
/parti /sandik           → grup oyunları
/market /envanter /pazar /isletme
/gunluk /saatlik /banka /transfer /soy
/klan /gorevler /siralama /boss /piyango /davet
/admin                   → yönetici paneli (sadece ADMIN_IDS)
```

## 🛠 Yönetici paneli
`/admin` → istatistikler, altın/elmas verme, ban/unban, toplu duyuru, boss doğurma,
piyango çekme, oyuncu sorgulama (son işlem geçmişiyle).

---

## 📁 Dosya yapısı

| Dosya | Görev |
|---|---|
| `bot.py` | Giriş noktası, komut/callback yönlendirme, zamanlanmış işler |
| `config.py` | `.env` okuma + tüm ekonomi ayarları (bahis limitleri, ödüller, süreler) |
| `db.py` | SQLite şeması ve veri katmanı |
| `economy.py` | Para, XP/seviye, enerji, savaş gücü, bonuslar |
| `items.py` | Eşya kataloğu (silah/zırh/pet/sarf/işletme) |
| `games.py` | Tek kişilik oyunlar + çalış/maden/arena |
| `pvp.py` | Düello sistemi (5 mod) |
| `party.py` | Grup parti oyunları |
| `market.py` | Market, envanter, yükseltme, oyuncu pazarı, işletmeler |
| `social.py` | Profil, günlük, banka, transfer, soygun, klan, sıralama, davet |
| `events.py` | Görevler, başarımlar, dünya bossu, piyango |
| `admin.py` | Yönetici paneli |
| `ui.py` | Klavyeler, biçimlendirme, güvenli mesaj düzenleme |

## ⚙️ Ayarları değiştirmek
Tüm dengeler `config.py` içinde tek yerde: başlangıç parası, minimum bahis, bahis limiti,
günlük ödül, banka faizi, boss aralığı, piyango süresi, vergiler...
Değiştirdikten sonra `systemctl restart coinquest`.

## 💾 Yedek
Tek dosya: `/opt/coinquest/coinquest.db`
```bash
cp /opt/coinquest/coinquest.db /root/yedek-$(date +%F).db
```

## ❓ Sorun giderme
| Belirti | Çözüm |
|---|---|
| `BOT_TOKEN bulunamadı` | `.env` dosyası yok veya boş → `nano /opt/coinquest/.env` |
| `Conflict: terminated by other getUpdates` | Bot iki yerde çalışıyor → `systemctl stop coinquest` ve diğer kopyayı kapat |
| Grup komutları çalışmıyor | BotFather → `/setprivacy` → **Disable** (grup mesajlarını görebilsin) |
| Butonlar tepkisiz | Log'a bak: `tail -f /var/log/coinquest.log` |
| Zar animasyonu gelmiyor | Bot gruba mesaj gönderme yetkisine sahip olmalı |
