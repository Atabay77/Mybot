# Canavar (Boss) görselleri — AI promptları

Botta **9 farklı canavar** var ama hepsinin resmi ejderha gibi görünüyordu.
Aşağıda her canavarın **kendi türüne özel** promptu var — ejderha sadece birinde.

## Nasıl kullanılır
1. Aşağıdaki promptu olduğu gibi AI'a ver (her başlık ayrı resim).
2. Çıkan resmi başlıktaki **dosya adıyla** kaydet (`boss_1.jpg` gibi).
3. Sunucuya at:
   `scp boss_*.jpg root@SUNUCU_IP:/opt/coinquest/images/`
4. `systemctl restart coinquest`

## Ortak kurallar (hepsinde aynı olmalı — böylece set gibi durur)
- Stil: **dark fantasy game boss card art, painterly, dramatic rim lighting**
- Kompozisyon: canavar **tam boy ve ortada**, hafif alttan bakış (heybetli görünsün)
- Arka plan: **koyu, sade, dumanlı** — manzara detayı yok, canavar öne çıksın
- Her resimde **aynı boyda küçük bir savaşçı silueti** (canavarın ne kadar büyük
  olduğu anlaşılsın — madenci resimlerindeki mantığın aynısı)
- Sonuna mutlaka: `no text, no watermark, 16:9`

---

## boss_1.jpg — 🐉 Kızıl Ejder Vermathrax
```
Colossal red dragon boss, molten cracks glowing through crimson scales, vast leathery
wings half-spread, smoke curling from jaws, perched on scorched rubble, tiny armored
warrior silhouette at its feet for scale, dark fantasy game boss card art, painterly,
dramatic rim lighting, dark smoky background, low angle, no text, no watermark, 16:9
```

## boss_2.jpg — 💀 Kemik Kralı Morgul
```
Towering skeletal lich king boss, crowned bare skull with burning violet eye sockets,
tattered royal robes over exposed ribcage, bone staff wreathed in purple soul-fire,
floating shards of bone around him, tiny armored warrior silhouette at his feet for
scale, dark fantasy game boss card art, painterly, dramatic rim lighting, dark smoky
background, low angle, NO dragon, no text, no watermark, 16:9
```

## boss_3.jpg — 🧊 Buz Devi Ymir
```
Enormous ice giant boss, body carved from cracked blue glacier ice, frost beard,
jagged icicle spikes along shoulders and back, breath freezing the air white, huge
frozen club in one fist, tiny armored warrior silhouette at his feet for scale, dark
fantasy game boss card art, painterly, cold blue rim lighting, dark misty background,
low angle, NO dragon, no text, no watermark, 16:9
```

## boss_4.jpg — 🌑 Gölge Lordu Nyx
```
Faceless shadow lord boss, humanoid figure made of living black smoke, only two white
glowing eyes visible in the void of the hood, tendrils of darkness spreading outward
and swallowing the light around it, tattered shadow cloak, tiny armored warrior
silhouette at its feet for scale, dark fantasy game boss card art, painterly, harsh
white rim lighting against pure black, low angle, NO dragon, no text, no watermark, 16:9
```

## boss_5.jpg — 🪱 Kum Solucanı Shai
```
Gigantic desert sand worm boss bursting up out of a dune, circular gaping maw ringed
with concentric rows of teeth, thick armored segmented body, cascading sand pouring off
its hide, tiny armored warrior silhouette on the dune below for scale, dark fantasy game
boss card art, painterly, warm dusty rim lighting, dark sandstorm background, low angle,
NO dragon, no text, no watermark, 16:9
```

## boss_6.jpg — 🗿 Kıyamet Golemi
```
Massive stone golem boss, body built from ancient cracked megalith blocks bound by
glowing orange runes, moss and roots in the seams, fists like boulders, dust falling
from its joints as it moves, tiny armored warrior silhouette at its feet for scale,
dark fantasy game boss card art, painterly, orange rune rim lighting, dark cavern
background, low angle, NO dragon, no text, no watermark, 16:9
```

## boss_7.jpg — 🧙‍♀️ Cadı Kraliçe Morgana
```
Witch queen boss, tall regal sorceress in flowing black-and-emerald gown, thorned crown,
green witchfire swirling around her raised hands, spellbook orbiting her, long dark hair
lifted by magic wind, tiny armored warrior silhouette at her feet for scale, dark fantasy
game boss card art, painterly, emerald green rim lighting, dark ritual chamber background,
low angle, NO dragon, no text, no watermark, 16:9
```

## boss_8.jpg — 🐙 Kraken
```
Colossal kraken boss rising from stormy black sea, enormous suckered tentacles coiling
skyward and crushing a ship's mast, huge single glowing eye, water sheeting off its
slick hide, tiny armored warrior silhouette on the wreck for scale, dark fantasy game
boss card art, painterly, cold teal rim lighting, dark storm background, low angle,
NO dragon, no text, no watermark, 16:9
```

## boss_9.jpg — 🔥 Alev Şeytanı Ifrit
```
Infernal fire demon boss, muscular charcoal-black body with lava veins glowing beneath
cracked skin, curved horns, mane and beard of living flame, flaming scimitar in hand,
embers rising all around, tiny armored warrior silhouette at its feet for scale, dark
fantasy game boss card art, painterly, orange-red rim lighting, dark ember background,
low angle, NO dragon, no text, no watermark, 16:9
```

---

## Not
`NO dragon` yazısı önemli — AI'lar "boss" deyince otomatik ejderha çiziyor.
Bu satır olmadan yine hepsi ejderhaya benziyor.

Resim koymazsan bot yine sorunsuz çalışır, sadece yazıyla gösterir.
