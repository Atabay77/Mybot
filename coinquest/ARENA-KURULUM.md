# 🏟 3D Arena — kurulum

Oyuncular tarayıcıda gerçek zamanlı dövüşür. Silah, zırh, seviye — hepsi bottan gelir.
Bot ve arena **aynı programda** çalışır, ayrı bir şey başlatmana gerek yok.

---

## 1. Güncelle

```
bash /root/Mybot/coinquest/guncelle.sh
```

Bu komut `aiohttp` paketini de kurar (arena sunucusu için gerekli).

## 2. Adresi ayarla

Arenanın çalışması için oyuncuların gireceği **dış adresi** yazman gerekiyor:

```
nano /opt/coinquest/.env
```

Şu satırı ekle (kendi sunucu IP'nle):

```
ARENA_URL=http://62.113.200.134:8080
```

Kaydet: `CTRL+O`, `ENTER`, `CTRL+X`. Sonra:

```
systemctl restart coinquest
```

## 3. Portu aç

```
ufw allow 8080/tcp
```

(`ufw` kurulu değilse bu komut hata verir, sorun değil — port zaten açıktır.)

## 4. Kontrol et

```
journalctl -u coinquest -n 20 --no-pager | grep -i arena
```

Şunu görmelisin:

```
🏟 Arena sunucusu açık: port 8080  (dış adres: http://62.113.200.134:8080)
```

Artık botta **🏟 3D Arena** düğmesi çalışıyor. Bas → "ARENAYI AÇ" → tarayıcı açılır.

---

## Telegram'ın İÇİNDE açılması (isteğe bağlı)

Yukarıdaki kurulumda oyun **tarayıcıda** açılır ve sorunsuz çalışır.
Oyunun Telegram'dan çıkmadan, uygulamanın içinde açılmasını istersen
**alan adı + HTTPS** gerekiyor — Telegram `http://` adresleri kabul etmiyor.

Bunun için:

1. Bir alan adı al (örn. `arena.siteadin.com`), sunucunun IP'sine yönlendir.
2. Nginx ve ücretsiz sertifika kur:

```
apt install -y nginx certbot python3-certbot-nginx
```

3. `/etc/nginx/sites-available/arena` dosyasını oluştur:

```
server {
    server_name arena.siteadin.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;      # WebSocket için şart
        proxy_set_header Connection "upgrade";        # WebSocket için şart
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
```

4. Etkinleştir ve sertifikayı al:

```
ln -s /etc/nginx/sites-available/arena /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d arena.siteadin.com
```

5. `.env` dosyasında adresi güncelle:

```
ARENA_URL=https://arena.siteadin.com
```

6. `systemctl restart coinquest`

7. BotFather'da: `/mybots` → botun → *Bot Settings* → *Menu Button* →
   *Configure Menu Button* → adresi gir.

---

## Ayarlar (`.env` içinden değiştirilebilir)

| Ayar | Varsayılan | Ne işe yarar |
|---|---|---|
| `ARENA_ENABLED` | `1` | `0` yaparsan arena tamamen kapanır |
| `ARENA_PORT` | `8080` | Sunucunun dinlediği port |
| `ARENA_URL` | boş | Oyuncuların gireceği dış adres (**şart**) |

Dövüş ayarları `arena.py` dosyasının başında: arena büyüklüğü, vuruş menzili,
maç süresi, dayanıklılık, blok kesme oranı, bahis seçenekleri.

---

## Sık sorulan

**Düğmeye basınca "Arena henüz açılmadı" diyor.**
`ARENA_URL` boş. 2. adımı yap.

**Sayfa açılmıyor.**
Portu kontrol et: `ss -tlnp | grep 8080`. Bir şey görünmüyorsa
`journalctl -u coinquest -n 40 --no-pager` ile hataya bak.

**"Bağlantının süresi dolmuş" diyor.**
Giriş bağlantısı 10 dakika geçerli. Bota dönüp düğmeye tekrar bas.

**Rakip bulunmuyor.**
Aynı bahiste bekleyen başka oyuncu gerekiyor. İki telefonda/iki hesapla
"Bedava" bahsi seçip aynı anda "RAKİP BUL" deneyin.

**Hile yapılabilir mi?**
Hayır. Konum, hasar, canlar — hepsi sunucuda hesaplanıyor. Tarayıcı sadece
"ileri git / vur / blokla" gönderiyor; gönderdiği hız bile sunucuda sınırlanıyor.
