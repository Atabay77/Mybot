# Madenci görselleri — AI promptları

**Amaç:** 15 madencinin *makinesi* çizilecek (maden içi manzara değil), ve güç farkı
**boy farkından** anlaşılacak. Bunun için her resimde **aynı boyda küçük bir insan silueti**
duruyor. İnsan hep aynı kalıyor, makine büyüdükçe fark gözle görülüyor.

## Nasıl kullanılır
1. Aşağıdaki promptu olduğu gibi AI'a ver (her satır ayrı resim).
2. Çıkan resmi `miner_m01.jpg` … `miner_m15.jpg` adıyla kaydet.
3. Sunucuya at:
   `scp miner_m*.jpg root@SUNUCU_IP:/opt/coinquest/images/`
4. `systemctl restart coinquest`

## Ortak kurallar (hepsinde aynı olmalı)
- Aynı kamera açısı: **isometric / hafif yandan**
- Aynı arka plan: **düz koyu lacivert degrade**, manzara yok
- Aynı ışık: yumuşak stüdyo ışığı
- **Her resimde aynı boyda insan silueti** (ölçek referansı)
- Sonuna mutlaka: `no text, no watermark, 16:9`

## ORTAK KALIP
```
Isometric 3D game asset of {MAKİNE}, approximately {BOY} tall,
a small human worker silhouette standing at its base for scale,
centered on a plain dark navy gradient background, no landscape,
soft studio lighting, clean mobile game icon style, highly detailed,
no text, no watermark, 16:9
```

---

## 15 MADENCİ

| Dosya | {MAKİNE} | {BOY} |
|---|---|---|
| `miner_m01.jpg` | a simple hand-crank ore drill with a pickaxe leaning on it | **1 meter** |
| `miner_m02.jpg` | a small coal mine cart with a hand-crank winch | **2 meters** |
| `miner_m03.jpg` | an iron ore rail cart with a mechanical loading arm | **3 meters** |
| `miner_m04.jpg` | a brass steam-powered drilling machine with a chimney and pressure gauges | **5 meters** |
| `miner_m05.jpg` | a diamond-tipped rotary drilling rig with blue glowing crystals in its collector | **8 meters** |
| `miner_m06.jpg` | a gold washing and sifting plant with conveyor belts and golden dust | **12 meters** |
| `miner_m07.jpg` | an industrial laser cutting rig with a red beam emitter and cooling fins | **18 meters** |
| `miner_m08.jpg` | a humanoid mining robot with glowing blue eyes and a plasma drill arm | **25 meters** |
| `miner_m09.jpg` | a giant bucket-wheel excavator with a huge rotating digging wheel | **40 meters** |
| `miner_m10.jpg` | a mobile underground factory complex on massive tracks, with furnaces and pipes | **70 meters** |
| `miner_m11.jpg` | a seismic drilling tower with glowing orange lava veins running through it | **120 meters** |
| `miner_m12.jpg` | a quantum drill machine with floating rotating rings and purple energy | **200 meters** |
| `miner_m13.jpg` | an asteroid mining ship with grappling arms and ore containers | **400 meters** |
| `miner_m14.jpg` | a black hole harvester ring station with a glowing accretion disk | **1 kilometer** |
| `miner_m15.jpg` | a colossal star-forging megastructure with golden plasma streams | **10 kilometers** |

## Örnek (kopyala-yapıştır, 1. madenci)
```
Isometric 3D game asset of a simple hand-crank ore drill with a pickaxe leaning on it,
approximately 1 meter tall, a small human worker silhouette standing at its base for scale,
centered on a plain dark navy gradient background, no landscape,
soft studio lighting, clean mobile game icon style, highly detailed,
no text, no watermark, 16:9
```

## Örnek (9. madenci — fark burada belli olur)
```
Isometric 3D game asset of a giant bucket-wheel excavator with a huge rotating digging wheel,
approximately 40 meters tall, a small human worker silhouette standing at its base for scale,
centered on a plain dark navy gradient background, no landscape,
soft studio lighting, clean mobile game icon style, highly detailed,
no text, no watermark, 16:9
```

## İpuçları
- İnsan silueti **çok küçük** çıkmalı büyük makinelerde — bu kasıtlı, güç farkı böyle anlaşılıyor.
- AI insanı unutursa prompta `with a tiny 1.8m human silhouette for scale` diye tekrar ekle.
- Hepsini **aynı AI ve aynı ayarlarla** üret, yoksa stil tutmaz.
- Genel ekran için: `images/madenler.jpg` →
  *"Isometric 3D lineup of mining machines from tiny to gigantic, side by side, size progression,
  plain dark navy background, clean mobile game style, no text, 16:9"*
