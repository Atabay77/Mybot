# 🏰 CoinQuest — Telegram Oyun Botu

Oyun oyna → coin kazan → **gerçek paraya çevir**.
Her şey **butonlarla** yapılır, kullanıcı komut yazmaz.
**3 dil:** 🇹🇲 Türkmençe (varsayılan) · 🇷🇺 Русский · 🇹🇷 Türkçe

---

## ⚡ VPS'e kurulum (Termius'ta root ile)

**1) İndir ve kur:**
```bash
apt update && apt install -y git python3 python3-venv
cd /opt && git clone -b claude/telegram-game-bot-q5l98b https://github.com/Atabay77/Mybot.git
bash /opt/Mybot/coinquest/kurulum.sh
```

**2) Token'ı yaz:**
```bash
nano /opt/coinquest/.env
```
`BOT_TOKEN=` satırına BotFather'dan aldığın tokenı yapıştır. `CTRL+O`, `ENTER`, `CTRL+X`.

**3) Başlat:**
```bash
systemctl enable --now coinquest
tail -f /var/log/coinquest.log
```

**4) BotFather'da 1 ayar:** `/setprivacy` → botunu seç → **Disable**
(grup oyunlarında cevapları görebilmesi için)

### Sık kullanılan komutlar
| Ne yapar | Komut |
|---|---|
| Yeniden başlat | `systemctl restart coinquest` |
| Durdur | `systemctl stop coinquest` |
| Log izle | `tail -f /var/log/coinquest.log` |
| Güncelle | `cd /opt/Mybot && git pull && bash coinquest/kurulum.sh && systemctl restart coinquest` |
| Yedek al | `cp /opt/coinquest/coinquest.db /root/yedek.db` |

---

## 💵 Gerçek para sistemi

Oyuncu coin toplar, **💵 Para Çek** butonundan coinini paraya çevirir.

| Ayar | Değer | Nerede değişir |
|---|---|---|
| 1 TMT | 1.000.000 coin | `config.py` → `COINS_PER_MONEY` |
| Günlük çevirme limiti | 0.70 TMT | `config.py` → `DAILY_MONEY_CAP` |
| En az çekim | 5 TMT | `config.py` → `MIN_WITHDRAW` |
| Gereken seviye | 10 | `config.py` → `WITHDRAW_MIN_LEVEL` |
| Hesap yaşı | 7 gün | `config.py` → `WITHDRAW_MIN_DAYS` |

**Günlük limit yüzünden 5 TMT'ye en erken 8 günde ulaşılır** (0.70 × 7 = 4.90).
Oyuncu ne kadar zengin olursa olsun bunu hızlandıramaz.

**Ödeme akışı:** Oyuncu tutarı ve ödeme bilgisini butonlarla seçer → sana bildirim gelir →
`/admin` → 💸 Çekim Talepleri → **✅ Ödedim** / **❌ Reddet**.
Reddedersen para oyuncuya otomatik geri yüklenir. Ödemeyi elden/havale sen yaparsın,
bot para tutmaz. Not: bot **para yatırma almaz**, coin sadece oynayarak kazanılır.

---

## 🌐 Diller
Yeni oyuncu ilk girişte dil seçer. Sonra istediği zaman
**⚙️ Başgalary → 🌐 Dil** ile değiştirir. Varsayılan Türkmençe.

Yazıları değiştirmek/eklemek: `i18n.py` içindeki `STR` sözlüğü.
Her satır şöyle: `"anahtar": {"tk": "...", "ru": "...", "tr": "..."}`

Şu an 3 dilde olan bölümler: menüler, butonlar, karşılama, para ekranı,
günlük hediye, yardım, oyun kategorileri, çekim akışı.
Derin ekranlar (market listesi, klan, sıralama, yönetici) şimdilik Türkçe.

## 🖼 Resim ekleme
`images/` klasörüne şu adlarla resim koy — bot o ekranı fotoğraflı gönderir.
Resim yoksa sadece yazı gider, hata olmaz.

`karsilama · menu · para · oyunlar · hediye · market · yardim · duello · canavar · kazandin`
(jpg/png/webp, önerilen 1280x720)

```bash
# bilgisayarından sunucuya resim atmak için:
scp menu.jpg root@SUNUCU_IP:/opt/coinquest/images/
systemctl restart coinquest
```

---

## 🎮 İçindekiler

**Şans oyunları (coin koyup katlama):** slot, mayın tarlası, blackjack, yüksek/düşük,
rulet, çark, yazı-tura, Telegram zarı, roket

**Bilgi oyunları (bedava, kaybetmezsin):** bilgi yarışması, matematik, kelime, refleks

**İş oyunları:** çalış (45 dk), maden (20 dk), canavar avı

**⚔️ Düello (grupta, coin karşılığı):** taş-kağıt-makas, XOX, emoji zar, silah savaşı, gizemli kutu

**🎉 Parti oyunları (grupta, bedava):** bilgi yarışı, matematik, kelime avı, refleks, hazine sandığı

**Ekonomi:** market (34 eşya), +10'a kadar eşya güçlendirme, oyuncu pazarı (kendi fiyatınla sat),
iş yerleri (pasif gelir), banka + faiz, soygun, arkadaşa para gönderme

**Sosyal:** dünya canavarı (herkes birlikte döver, ödül hasara göre), klanlar, çekiliş,
günlük görevler, 13 başarım, 7 sıralama, arkadaş davet

---

## 🛠 Yönetici paneli (`/admin`)
Çekim talepleri • istatistikler • coin/elmas verme • ban • toplu duyuru •
canavar doğurma • çekiliş yapma • oyuncu sorgulama

---

## 📁 Dosyalar

| Dosya | Ne yapar |
|---|---|
| `bot.py` | Başlangıç, butonların yönlendirmesi, zamanlı işler |
| `config.py` | **Tüm ayarlar burada** (para, limitler, ödüller) |
| `cash.py` | Gerçek para: çevirme + çekim talepleri |
| `db.py` | Veritabanı |
| `economy.py` | Coin, seviye, enerji, güç hesapları |
| `items.py` | Eşya listesi |
| `games.py` | Tek kişilik oyunlar |
| `pvp.py` | Düellolar |
| `party.py` | Grup oyunları |
| `market.py` | Market, eşyalar, pazar, iş yerleri |
| `social.py` | Profil, hediye, banka, klan, sıralama |
| `events.py` | Görevler, canavar, çekiliş |
| `admin.py` | Yönetici paneli |
| `ui.py` | Butonlar ve yazı biçimleri |

## ❓ Sorun olursa
| Sorun | Çözüm |
|---|---|
| `BOT_TOKEN bulunamadı` | `nano /opt/coinquest/.env` → tokenı yaz |
| `Conflict: terminated by other getUpdates` | Bot 2 yerde açık → `systemctl stop coinquest` |
| Grup oyunları çalışmıyor | BotFather → `/setprivacy` → Disable |
| Butonlar tepkisiz | `tail -f /var/log/coinquest.log` ile hataya bak |
