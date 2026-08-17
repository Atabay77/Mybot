# -*- coding: utf-8 -*-
"""Eşya kataloğu: silahlar, zırhlar, evcil hayvanlar, sarf malzemeleri ve işletmeler."""
from typing import Optional

RARITY = {
    "common": ("⚪", "Sıradan"),
    "uncommon": ("🟢", "Nadir"),
    "rare": ("🔵", "Değerli"),
    "epic": ("🟣", "Destansı"),
    "legendary": ("🟠", "Efsanevi"),
    "mythic": ("🔴", "Mitik"),
}

ITEMS: dict[str, dict] = {}


def _add(**kw) -> None:
    kw.setdefault("atk", 0)
    kw.setdefault("dfn", 0)
    kw.setdefault("rarity", "common")
    kw.setdefault("min_level", 1)
    kw.setdefault("currency", "coins")
    kw.setdefault("desc", "")
    kw.setdefault("upgradable", kw["kind"] in ("weapon", "armor"))
    kw.setdefault("stackable", kw["kind"] in ("consumable", "tool"))
    ITEMS[kw["key"]] = kw


# ---------------- SİLAHLAR ----------------
_add(key="w_stick", kind="weapon", name="Meşe Sopa", emoji="🏏", atk=6, price=600, rarity="common", min_level=1)
_add(key="w_axe", kind="weapon", name="Demir Balta", emoji="🪓", atk=14, price=2_400, rarity="common", min_level=3)
_add(key="w_hammer", kind="weapon", name="Savaş Çekici", emoji="🔨", atk=25, price=7_500, rarity="uncommon", min_level=6)
_add(key="w_spear", kind="weapon", name="Gümüş Mızrak", emoji="🔱", atk=38, price=18_000, rarity="rare", min_level=10)
_add(key="w_dagger", kind="weapon", name="Gölge Hançeri", emoji="🗡", atk=54, price=45_000, rarity="epic", min_level=15,
     desc="Kritik şansı +8%")
_add(key="w_blade", kind="weapon", name="Ejder Kılıcı", emoji="⚔️", atk=82, price=130_000, rarity="legendary", min_level=22)
_add(key="w_scythe", kind="weapon", name="Boşluk Tırpanı", emoji="🌑", atk=135, price=260, rarity="mythic", min_level=30,
     currency="gems", desc="Kritik şansı +12%")

# ---------------- ZIRHLAR ----------------
_add(key="a_robe", kind="armor", name="Kumaş Cübbe", emoji="🧥", dfn=6, price=500, rarity="common", min_level=1)
_add(key="a_leather", kind="armor", name="Deri Yelek", emoji="🦺", dfn=14, price=2_200, rarity="common", min_level=3)
_add(key="a_chain", kind="armor", name="Zincir Zırh", emoji="⛓", dfn=24, price=6_800, rarity="uncommon", min_level=6)
_add(key="a_plate", kind="armor", name="Şövalye Plakası", emoji="🛡", dfn=38, price=17_000, rarity="rare", min_level=10)
_add(key="a_rune", kind="armor", name="Rün Zırhı", emoji="🔰", dfn=55, price=42_000, rarity="epic", min_level=15)
_add(key="a_scale", kind="armor", name="Ejder Pulu", emoji="🐲", dfn=88, price=125_000, rarity="legendary", min_level=22)
_add(key="a_aegis", kind="armor", name="Aegis Kalkanı", emoji="🌟", dfn=145, price=260, rarity="mythic", min_level=30,
     currency="gems")

# ---------------- EVCİL HAYVANLAR ----------------
_add(key="p_chick", kind="pet", name="Civciv", emoji="🐣", price=2_000, rarity="common", min_level=2,
     desc="Kazançlar +3%", bonus={"income": 0.03})
_add(key="p_cat", kind="pet", name="Kara Kedi", emoji="🐈‍⬛", price=6_500, rarity="uncommon", min_level=5,
     desc="Şans +6%", bonus={"luck": 0.06})
_add(key="p_wolf", kind="pet", name="Bozkurt", emoji="🐺", price=15_000, rarity="rare", min_level=8,
     desc="Saldırı +10", bonus={"atk": 10})
_add(key="p_owl", kind="pet", name="Bilge Baykuş", emoji="🦉", price=24_000, rarity="rare", min_level=10,
     desc="XP +15%", bonus={"xp": 0.15})
_add(key="p_dragon", kind="pet", name="Ejder Yavrusu", emoji="🐉", price=95_000, rarity="legendary", min_level=18,
     desc="Kazançlar +15%, Saldırı +12", bonus={"income": 0.15, "atk": 12})
_add(key="p_phoenix", kind="pet", name="Anka Kuşu", emoji="🔥", price=420, rarity="mythic", min_level=25,
     currency="gems", desc="Kazançlar +25%, Saldırı +20, Şans +10%",
     bonus={"income": 0.25, "atk": 20, "luck": 0.10})

# ---------------- SARF MALZEMELERİ ----------------
_add(key="c_energy", kind="consumable", name="Enerji İçeceği", emoji="⚡", price=900, rarity="common",
     desc="+15 enerji verir", effect="energy")
_add(key="c_clover", kind="consumable", name="Şanslı Yonca", emoji="🍀", price=1_800, rarity="uncommon",
     desc="30 dakika +12% şans", effect="luck")
_add(key="c_scroll", kind="consumable", name="XP Parşömeni", emoji="📜", price=3_200, rarity="rare",
     desc="1 saat 2x XP", effect="xp")
_add(key="c_shield", kind="consumable", name="Koruma Kalkanı", emoji="🛡", price=4_500, rarity="rare",
     desc="6 saat soygun koruması", effect="shield")
_add(key="c_potion", kind="consumable", name="Şifa İksiri", emoji="❤️", price=1_200, rarity="common",
     desc="Arena savaşında +60 can", effect="heal")
_add(key="c_bomb", kind="consumable", name="Duman Bombası", emoji="💨", price=2_500, rarity="uncommon",
     desc="Bir sonraki soygununu garantiler", effect="rob")
_add(key="c_lucky_dice", kind="consumable", name="Hileli Zar", emoji="🎲", price=6, rarity="epic", currency="gems",
     desc="Emoji düellosunda bir kez zarını yükseltir", effect="dice")

# ---------------- ALETLER ----------------
_add(key="t_pickaxe", kind="tool", name="Kazma", emoji="⛏", price=1_500, rarity="common",
     desc="Maden dayanıklılığı +60", effect="pickaxe")

# ---------------- İŞLETMELER ----------------
_add(key="b_simit", kind="business", name="Simit Tezgahı", emoji="🥨", price=25_000, rarity="common", min_level=4,
     income=2_200)
_add(key="b_coffee", kind="business", name="Kahve Dükkanı", emoji="☕", price=75_000, rarity="uncommon", min_level=8,
     income=6_500)
_add(key="b_market", kind="business", name="Semt Marketi", emoji="🏪", price=200_000, rarity="rare", min_level=12,
     income=18_000)
_add(key="b_hotel", kind="business", name="Butik Otel", emoji="🏨", price=550_000, rarity="epic", min_level=18,
     income=52_000)
_add(key="b_casino", kind="business", name="Kumarhane", emoji="🎲", price=1_600_000, rarity="legendary", min_level=25,
     income=165_000)
_add(key="b_holding", kind="business", name="Holding", emoji="📈", price=5_000_000, rarity="mythic", min_level=32,
     income=560_000)


def get(key: str) -> Optional[dict]:
    return ITEMS.get(key)


def by_kind(kind: str) -> list[dict]:
    return [i for i in ITEMS.values() if i["kind"] == kind]


def rarity_icon(key_or_item) -> str:
    item = get(key_or_item) if isinstance(key_or_item, str) else key_or_item
    if not item:
        return "⚪"
    return RARITY.get(item["rarity"], ("⚪", ""))[0]


def label(item_key: str, item_lvl: int = 0) -> str:
    item = get(item_key)
    if not item:
        return "Bilinmeyen Eşya"
    star = f" +{item_lvl}" if item_lvl else ""
    return f"{item['emoji']} {item['name']}{star}"


def stat_at(item: dict, item_lvl: int, field: str) -> int:
    """Yükseltme seviyesine göre ölçeklenmiş istatistik (her seviye +12%)."""
    base = item.get(field, 0)
    if not base:
        return 0
    return int(round(base * (1 + 0.12 * item_lvl)))


def upgrade_cost(item: dict, item_lvl: int) -> int:
    base = max(400, int(item.get("price", 1000) * 0.22))
    if item.get("currency") == "gems":
        base = 40_000
    return int(base * (1.65 ** item_lvl))


def upgrade_chance(item_lvl: int) -> float:
    return max(0.22, 0.92 - 0.075 * item_lvl)


def sell_price(item: dict, item_lvl: int = 0) -> int:
    """Eşyayı NPC'ye satma fiyatı (alış fiyatının %40'ı)."""
    if item.get("currency") == "gems":
        return int(item["price"] * 3_000 * 0.4 * (1 + 0.25 * item_lvl))
    return int(item["price"] * 0.4 * (1 + 0.25 * item_lvl))


MAX_UPGRADE = 10
