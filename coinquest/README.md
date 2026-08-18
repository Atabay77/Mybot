# 🏰 CoinQuest — Telegram Oyun Botu

Oyun oyna → coin kazan → **gerçek paraya çevir**.
Her şey **ekrandaki (inline) butonlarla** yapılır, kullanıcı komut yazmaz.
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
| 1 TMT | 100.000 coin | `config.py` → `COINS_PER_MONEY` |
| Günlük çevirme limiti | 0.70 TMT | `config.py` → `DAILY_MONEY_CAP` |
| En az çekim | 5 TMT | `config.py` → `MIN_WITHDRAW` |
| USDT kuru | 1 USDT = 19.65 TMT | `.env` → `TMT_PER_USDT` |
| Gereken seviye | 10 | `config.py` → `WITHDRAW_MIN_LEVEL` |
| Hesap yaşı | 7 gün | `config.py` → `WITHDRAW_MIN_DAYS` |

**Günlük limit yüzünden 5 TMT'ye en erken 8 günde ulaşılır** (0.70 × 7 = 4.90).
Oyuncu ne kadar zengin olursa olsun bunu hızlandıramaz.

Oyuncu parayı **TMT** ya da **USDT** olarak isteyebilir (USDT → CryptoBot).
Kuru `.env` içinden değiştirirsin: `TMT_PER_USDT=19.65`

**Ödeme akışı:** Oyuncu tutarı, para birimini ve ödeme bilgisini butonlarla seçer → sana bildirim gelir →
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
# BİLGİSAYARINDAN sunucuya atmak için (kendi bilgisayarında çalıştır):
scp menu.jpg root@SUNUCU_IP:/opt/coinquest/images/

# Resimler zaten sunucudaysa (örn. /root içinde), sadece taşı:
mkdir -p /opt/coinquest/images && mv /root/*.jpg /opt/coinquest/images/
systemctl restart coinquest
```
Bot resimleri şu klasörlerde arar: `.env` içindeki `IMAGES_DIR` →
`/opt/coinquest/images` → `/root/images` → `/root`.
Açılış logunda hangilerini bulduğunu yazar.

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

## 🛠 Yönetim paneli

Ana menüde **🛠 YÖNETİM PANELİ** düğmesi çıkar — bu düğmeyi sadece yetkililer görür.
(Gizli komut olarak `/admin` de çalışır.)
Panelde hiçbir yere ID veya miktar yazılmaz; her şey hazır düğmelerle yapılır.

**Roller**
| Rol | Nereden | Yapabildikleri |
|---|---|---|
| 👑 Kurucu | `.env` → `ADMIN_IDS` | her şey + yetkili ekleme/silme |
| 🛠 Yönetici | panelden eklenir | kurucunun açtığı izinler kadar |
| 🎧 Destek | panelden eklenir | varsayılan: sadece destek kutusu |

**İzinler tek tek açılır/kapanır** (👮 Yetkililer → ⚙️ İzinler):
ödeme onaylama · coin/elmas verme · gerçek para ekleme · enerji verme · ban ·
reklam · destek · oyuncu listesi · istatistik · canavar/çekiliş · kayıtlar.
İzinsiz düğmeye basan "bu işlem için iznin yok" uyarısı alır.

**Özellikler**
- 💸 Ödeme talepleri — tek tuşla Ödedim / Reddet (ret otomatik iade)
- 🎧 Destek kutusu — oyuncularla iki yönlü yazışma (fotoğraf, video, ses)
- 📣 Reklam/duyuru — **her tür medya**, arka planda gönderilir, bot çalışmaya devam eder,
  canlı ilerleme çubuğu
- 👤 Oyuncu kartı: bakiye, geçmiş, ödemeler, bot koruması durumu
- 🪙 Coin / 💎 elmas / 💵 gerçek para / ⚡ enerji verme — hazır miktar düğmeleriyle
- ♾ Sınırsız enerji açma-kapama, coin/para sıfırlama
- 👥 Oyuncu listesi (son katılanlar / son görülenler / en zenginler / parası olanlar / banlılar)
- 🚫 Ban / ban kaldırma (yetkililer banlanamaz)
- 👮 Yetkili ekle-sil, 📊 istatistik, 📜 hareket kayıtları
- 🐉 Canavar çıkarma, 🎟 çekiliş yapma

**Güvenlik:** yetkililer sıralamalarda görünmez, her yönetici işlemi kayda geçer,
her düğme rol kontrolünden geçer.

## 🆘 Destek sistemi
Oyuncu ana menüden **🆘 Destek**'e basar, yazar (fotoğraf/video da olur) →
tüm yetkililere düşer → **💬 Cevapla** ile yanıt oyuncuya birebir iletilir.

## 🤖 Bot koruması
Yeni oyuncu dil seçiminden sonra matematik sorusu çözer.
İlk denemede bilirse davet edene **tam ödül** (10.000 🪙),
2-3. denemede bilirse **yarım ödül**, daha fazlasında ödül yok.

## ⛏ Madenciler
15 kademeli pasif gelir sistemi (`miners.py`). Coin ile alınır, her madencinin
bir **gücü** vardır ve gücü kadar **4 saatte bir** coin üretir.
Aynı madenciden birden fazla alınabilir; kasa en fazla 6 döngü (24 saat) biriktirir.
Hepsi kendini ~22 saatte amorti eder.

| # | Madenci | Fiyat | 4 saatlik güç | Seviye |
|---|---|---|---|---|
| 1 | ⛏ El Kazması | 5.000 | 900 | 1 |
| 5 | 💠 Elmas Delici | 350.000 | 62.000 | 8 |
| 10 | 🏭 Yeraltı Fabrikası | 40.000.000 | 7.200.000 | 22 |
| 15 | 🌟 Yıldız Fabrikası | 5.000.000.000 | 900.000.000 | 40 |

Tam liste `miners.py` → `MINERS`. Yeni kademe eklemek için listeye bir satır ekle.
Görseller: `images/miner_m01.jpg` … `miner_m15.jpg` ve genel ekran için `images/madenler.jpg`.

## 🌐 Online düello (grup gerekmez)
⚔️ Düello → 🌐 Online rakip bul → oyun + bahis seç → bot rakip eşleştirir.
Taş-kağıt-makas, emoji zar, arena, gizemli kutu online oynanır;
XOX ve açık lobi gruplarda devam eder. Rakip 10 dakikada bulunmazsa bahis iade edilir.

Herkes aynı anda **5 ilana kadar** oyun açabilir (farklı oyun/bahis); eşleşen ikili
otomatik savaşır, diğer ilanlar bozulmadan bekler. Oyun düğmelerinde bekleyen ilan
sayısı ateşle gösterilir: `🎲 Emoji Zar  2🔥`. **📋 Açık oyunlar** ekranından
başkasının ilanına tek tuşla katılınır, **📋 İlanlarım** ekranından tek tek iptal edilir.

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
