# Arenayı daha da iyi yapmak için gereken dosyalar

Şu an arena **hiçbir dosya olmadan** çalışıyor: karakterler, arena, sesler —
hepsi kodla üretiliyor. Aşağıdakiler **isteğe bağlı**; koyduğun anda devreye
girer, koymazsan oyun aynen çalışmaya devam eder.

Dosyaları şuraya at:

```
scp DOSYA root@62.113.200.134:/opt/coinquest/webapp/
systemctl restart coinquest
```

---

## 1. 🎵 Müzik  —  `music.mp3`  (en kolay, en çok fark eden)

**Ne:** Arena dövüşü sırasında dönen fon müziği.
**Nasıl olmalı:** 1–3 dakikalık, döngüye uygun (başı ve sonu birbirine bağlansın),
dövüş havası — davul, epik/orta tempo. **2 MB'ı geçmesin** (yavaş bağlantı).
**Dosya adı:** tam olarak `music.mp3`

**Nereden bulursun (ücretsiz ve ticari kullanıma açık):**
- pixabay.com/music/ → "epic battle" ara → indir
- incompetech.com → Kevin MacLeod, "Epic" bölümü
- freepd.com → tamamen telifsiz

Koyduğun an oyunda çalar. Oyuncu 🔊 düğmesiyle kapatabilir.

---

## 2. 🖼 Arena zemin dokusu  —  `ground.jpg`

**Ne:** Arenanın kum/toprak zemini. Şu an düz renk + halkalar var; doku
koyunca gerçek kum gibi olur.
**Nasıl olmalı:** Kare (1024×1024), **kenarları birbirine geçen (seamless/tileable)**
kum ya da toprak dokusu. Üstünde yazı/logo olmasın.
**Nereden:** polyhaven.com/textures → "sand" veya "ground" → 1K JPG indir (ücretsiz)

## 3. 🧱 Duvar dokusu  —  `wall.jpg`

Aynı şekilde: 1024×1024, seamless, **taş duvar**.
polyhaven.com/textures → "brick" / "stone wall"

---

## 4. 🗿 3D karakter modeli  —  `knight.glb`  (en büyük fark, en çok iş)

**Ne:** Kutu şövalye yerine gerçek 3D model.
**Nasıl olmalı:**
- Dosya biçimi **`.glb`** (tek dosya, dokusu içinde)
- **Düşük poligonlu** (10.000 üçgenin altında) — telefonda takılmasın
- **İskeletli ve animasyonlu** olursa çok iyi: `idle`, `run`, `attack`, `block`, `death`
- 2 MB'ı geçmesin

**Nereden (hepsi ücretsiz, ticari kullanıma açık):**
- **quaternius.com** → "Ultimate Modular Characters" / "Animated Knight" — animasyonlu, tam bu iş için
- **kenney.nl/assets** → "Blocky Characters" — çok hafif, telefona uygun
- **poly.pizza** → arama kutusuna "knight" yaz

⚠️ Bunu göndermeden önce söyle: modeli okuyabilmem için oyuna bir **model
okuyucu** yazmam gerekiyor (yarım günlük iş). Dosyayı at, ben motoru ona göre
genişleteyim.

---

## Öncelik sırası (bence)

1. **`music.mp3`** — 5 dakikalık iş, oyunun havasını tamamen değiştirir
2. **`ground.jpg` + `wall.jpg`** — arena birden "yapılmış" görünür
3. **`knight.glb`** — en büyük sıçrama ama kod tarafında da iş var

Hiçbirini göndermezsen de oyun eksiksiz çalışır — bunlar süs değil ama şart da değil.
