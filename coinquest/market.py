# -*- coding: utf-8 -*-
"""Market, envanter, ekipman, yükseltme, oyuncu pazarı (bazaar) ve işletmeler."""
import math
import random
import time

from telegram import Update
from telegram.ext import ContextTypes

import config
import db
import economy
import events
import items
import ui

CATS = [
    ("weapon", "⚔️ Silahlar"),
    ("armor", "🛡 Zırhlar"),
    ("pet", "🐾 Evcil Hayvanlar"),
    ("consumable", "🧪 Sarf Malzemeleri"),
    ("tool", "⛏ Aletler"),
]
PAGE = 8


# ---------------------------------------------------------------------------
# MARKET
# ---------------------------------------------------------------------------

def market_text(user) -> str:
    return (
        "🏪 <b>DİYAR MARKETİ</b>\n"
        f"{ui.header(user)}\n\n"
        "Ekipman al, güçlen, arenada ve boss savaşlarında fark yarat.\n"
        "Mitik eşyalar sadece 💎 elmas ile alınır.\n\n"
        "<i>Sattığın eşyaların %40'ını geri alırsın; oyuncu pazarında ise fiyatı sen belirlersin.</i>"
    )


def market_kb():
    rows = [[(label, f"mk:cat:{kind}")] for kind, label in CATS]
    rows.append([("💎 Elmas Dükkanı", "mk:gems"), ("🏭 İşletmeler", "mk:biz")])
    rows.append([("🎒 Envanter", "mk:inv"), ("🛒 Oyuncu Pazarı", "mk:bazaar")])
    rows.append([("🏠 Menü", "m:main")])
    return ui.kb(rows)


def cat_text(kind: str, user) -> str:
    label = dict(CATS)[kind]
    lines = [f"🏪 <b>{label.upper()}</b>", ui.header(user), ""]
    for item in sorted(items.by_kind(kind), key=lambda i: (i["currency"] == "gems", i["price"])):
        cur = "💎" if item["currency"] == "gems" else "🪙"
        stat = ""
        if item["atk"]:
            stat = f" ⚔️{item['atk']}"
        if item["dfn"]:
            stat = f" 🛡{item['dfn']}"
        desc = f" — <i>{item['desc']}</i>" if item["desc"] else ""
        lock = "" if user["level"] >= item["min_level"] else f" 🔒Sv.{item['min_level']}"
        lines.append(
            f"{items.rarity_icon(item)} {item['emoji']} <b>{item['name']}</b>{stat}{lock}\n"
            f"    {ui.fmt(item['price'])} {cur}{desc}"
        )
    lines.append("\nSatın almak için butona bas 👇")
    return "\n".join(lines)


def cat_kb(kind: str, user):
    rows = []
    line = []
    for item in sorted(items.by_kind(kind), key=lambda i: (i["currency"] == "gems", i["price"])):
        if user["level"] < item["min_level"]:
            continue
        cur = "💎" if item["currency"] == "gems" else "🪙"
        line.append((f"{item['emoji']} {ui.fmt(item['price'])}{cur}", f"mk:buy:{item['key']}"))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append([("⬅️ Market", "mk:menu"), ("🎒 Envanter", "mk:inv")])
    return ui.kb(rows)


def buy_item(user_id: int, key: str) -> tuple[bool, str]:
    item = items.get(key)
    if not item:
        return False, "Böyle bir eşya yok."
    user = db.get_user(user_id)
    if user["level"] < item["min_level"]:
        return False, f"Bu eşya için Seviye {item['min_level']} gerekiyor."
    if item["kind"] == "business":
        return False, "İşletmeler 🏭 İşletme panelinden alınır."
    if item["currency"] == "gems":
        if not economy.take_gems(user_id, item["price"], f"satın alma: {key}"):
            return False, f"Yeterli elmasın yok ({user['gems']}💎)."
    else:
        if not economy.take_coins(user_id, item["price"], f"satın alma: {key}"):
            return False, f"Yeterli altının yok ({ui.fmt(user['coins'])}🪙)."
    if item["key"] == "t_pickaxe":
        db.upd(user_id, pickaxe=user["pickaxe"] + 60)
        events.track(user_id, "buy")
        return True, f"⛏ Kazma alındı! Dayanıklılık: {user['pickaxe'] + 60}"
    db.inv_add(user_id, key, 1, stackable=item["stackable"])
    events.track(user_id, "buy")
    return True, f"✅ {items.label(key)} envanterine eklendi!"


# ---------------------------------------------------------------------------
# ENVANTER
# ---------------------------------------------------------------------------

def inv_text(user_id: int, page: int = 0) -> str:
    user = db.get_user(user_id)
    rows = db.inv_list(user_id)
    stats = economy.power(user)
    lines = [
        "🎒 <b>ENVANTER</b>",
        ui.header(user),
        f"⚔️ Saldırı: <b>{stats['atk']}</b>  🛡 Savunma: <b>{stats['dfn']}</b>  ❤️ Can: <b>{stats['hp']}</b>",
        f"💥 Kritik: %{stats['crit'] * 100:.0f}  ⛏ Kazma: {user['pickaxe']}",
        "",
    ]
    equipped = {user["weapon_id"]: "⚔️", user["armor_id"]: "🛡", user["pet_id"]: "🐾"}
    if not rows:
        lines.append("Envanterin boş. Marketten alışveriş yap! 🏪")
        return "\n".join(lines)
    total = len(rows)
    pages = max(1, math.ceil(total / PAGE))
    page = max(0, min(page, pages - 1))
    for row in rows[page * PAGE:(page + 1) * PAGE]:
        item = items.get(row["item_key"])
        if not item:
            continue
        tag = equipped.get(row["id"], "")
        qty = f" x{row['qty']}" if row["qty"] > 1 else ""
        stat = ""
        if item["atk"]:
            stat = f" ⚔️{items.stat_at(item, row['item_lvl'], 'atk')}"
        if item["dfn"]:
            stat = f" 🛡{items.stat_at(item, row['item_lvl'], 'dfn')}"
        lines.append(f"{items.rarity_icon(item)} {items.label(row['item_key'], row['item_lvl'])}{qty}{stat} {tag}")
    lines.append(f"\nSayfa {page + 1}/{pages} • Eşya detayı için butona bas 👇")
    return "\n".join(lines)


def inv_kb(user_id: int, page: int = 0):
    rows_db = db.inv_list(user_id)
    pages = max(1, math.ceil(len(rows_db) / PAGE))
    page = max(0, min(page, pages - 1))
    rows = []
    line = []
    for row in rows_db[page * PAGE:(page + 1) * PAGE]:
        item = items.get(row["item_key"])
        if not item:
            continue
        line.append((f"{item['emoji']} {item['name'][:12]}", f"mk:item:{row['id']}"))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    nav = []
    if page > 0:
        nav.append(("⬅️", f"mk:inv:{page - 1}"))
    if page < pages - 1:
        nav.append(("➡️", f"mk:inv:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("🏪 Market", "mk:menu"), ("🏠 Menü", "m:main")])
    return ui.kb(rows)


def item_detail(user_id: int, inv_id: int) -> tuple[str, object]:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil.", ui.back_kb("mk:inv")
    item = items.get(row["item_key"])
    user = db.get_user(user_id)
    if not item:
        return "Bilinmeyen eşya.", ui.back_kb("mk:inv")
    equipped = inv_id in (user["weapon_id"], user["armor_id"], user["pet_id"])
    lines = [
        f"{items.rarity_icon(item)} <b>{items.label(row['item_key'], row['item_lvl'])}</b>",
        f"<i>{items.RARITY[item['rarity']][1]} • {item['kind']}</i>",
        "",
    ]
    if item["atk"]:
        lines.append(f"⚔️ Saldırı: <b>{items.stat_at(item, row['item_lvl'], 'atk')}</b> (temel {item['atk']})")
    if item["dfn"]:
        lines.append(f"🛡 Savunma: <b>{items.stat_at(item, row['item_lvl'], 'dfn')}</b> (temel {item['dfn']})")
    if item["desc"]:
        lines.append(f"✨ {item['desc']}")
    if row["qty"] > 1:
        lines.append(f"📦 Adet: {row['qty']}")
    if equipped:
        lines.append("\n✅ <b>Şu anda kuşanılmış</b>")
    if item["upgradable"] and row["item_lvl"] < items.MAX_UPGRADE:
        cost = items.upgrade_cost(item, row["item_lvl"])
        chance = items.upgrade_chance(row["item_lvl"])
        lines.append(
            f"\n🔨 Yükseltme +{row['item_lvl'] + 1}: {ui.fmt(cost)} 🪙 • başarı %{chance * 100:.0f}\n"
            f"<i>Başarısız olursa altın gider, eşya kalır.</i>")
    lines.append(f"\n💰 Markete satış: {ui.fmt(items.sell_price(item, row['item_lvl']))} 🪙")

    rows = []
    if item["kind"] in ("weapon", "armor", "pet"):
        rows.append([("✅ Kuşan", f"mk:eq:{inv_id}")])
    if item["kind"] in ("consumable", "tool"):
        rows.append([("🧪 Kullan", f"mk:use:{inv_id}")])
    if item["upgradable"] and row["item_lvl"] < items.MAX_UPGRADE:
        rows.append([("🔨 Yükselt", f"mk:up:{inv_id}")])
    rows.append([("💰 Markete Sat", f"mk:sell:{inv_id}"), ("🛒 Pazara Koy", f"mk:list:{inv_id}")])
    rows.append([("⬅️ Envanter", "mk:inv"), ("🏠 Menü", "m:main")])
    return "\n".join(lines), ui.kb(rows)


def equip(user_id: int, inv_id: int) -> str:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil."
    item = items.get(row["item_key"])
    user = db.get_user(user_id)
    if not item or item["kind"] not in ("weapon", "armor", "pet"):
        return "Bu eşya kuşanılamaz."
    if user["level"] < item["min_level"]:
        return f"Seviye {item['min_level']} gerekiyor."
    slot = {"weapon": "weapon_id", "armor": "armor_id", "pet": "pet_id"}[item["kind"]]
    db.upd(user_id, **{slot: inv_id})
    return f"✅ {items.label(row['item_key'], row['item_lvl'])} kuşanıldı!"


def use_item(user_id: int, inv_id: int) -> str:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil."
    item = items.get(row["item_key"])
    if not item:
        return "Bilinmeyen eşya."
    effect = item.get("effect")
    user = db.get_user(user_id)
    now = ui.now()
    if effect == "energy":
        economy.add_energy(user_id, 15)
        msg = "⚡ +15 enerji!"
    elif effect == "luck":
        db.upd(user_id, luck_until=max(now, user["luck_until"]) + 1800)
        msg = "🍀 30 dakika boyunca +%12 şans!"
    elif effect == "xp":
        db.upd(user_id, xpboost_until=max(now, user["xpboost_until"]) + 3600)
        msg = "📜 1 saat boyunca 2x XP!"
    elif effect == "shield":
        db.upd(user_id, shield_until=max(now, user["shield_until"]) + 6 * 3600)
        msg = "🛡 6 saat soygun koruması aktif!"
    elif effect == "pickaxe":
        db.upd(user_id, pickaxe=user["pickaxe"] + 60)
        msg = f"⛏ Kazma dayanıklılığı: {user['pickaxe'] + 60}"
    elif effect == "heal":
        return "❤️ Şifa iksiri arena savaşında otomatik kullanılır, elinde tut."
    elif effect == "rob":
        db.meta_set(f"rob_boost_{user_id}", 1)
        msg = "💨 Sonraki soygunun garanti başarılı!"
    elif effect == "dice":
        db.meta_set(f"dice_boost_{user_id}", 1)
        msg = "🎲 Sonraki emoji düellonda zarın yükseltilecek!"
    else:
        return "Bu eşyanın kullanımı yok."
    db.inv_remove(inv_id, 1)
    return msg


def upgrade(user_id: int, inv_id: int) -> str:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil."
    item = items.get(row["item_key"])
    if not item or not item["upgradable"]:
        return "Bu eşya yükseltilemez."
    if row["item_lvl"] >= items.MAX_UPGRADE:
        return f"Bu eşya maksimum seviyede (+{items.MAX_UPGRADE})."
    cost = items.upgrade_cost(item, row["item_lvl"])
    if not economy.take_coins(user_id, cost, "yükseltme"):
        return f"Yükseltme için {ui.fmt(cost)} altın gerekiyor."
    events.track(user_id, "upgrade")
    user = db.get_user(user_id)
    chance = items.upgrade_chance(row["item_lvl"]) + economy.luck(user) * 0.25
    if random.random() < chance:
        db.run("UPDATE inventory SET item_lvl=item_lvl+1 WHERE id=?", (inv_id,))
        economy.add_xp(user_id, 40)
        return (f"🔨✨ <b>BAŞARILI!</b> {items.label(row['item_key'], row['item_lvl'] + 1)} "
                f"artık daha güçlü. (-{ui.fmt(cost)} 🪙)")
    return f"💔 <b>Yükseltme başarısız!</b> {ui.fmt(cost)} altın kayboldu, eşya sağlam."


def sell_to_npc(user_id: int, inv_id: int) -> str:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil."
    item = items.get(row["item_key"])
    if not item:
        return "Bilinmeyen eşya."
    price = items.sell_price(item, row["item_lvl"])
    db.inv_remove(inv_id, 1)
    economy.add_coins(user_id, price, "markete satış")
    return f"💰 {items.label(row['item_key'], row['item_lvl'])} satıldı: +{ui.fmt(price)} 🪙"


# ---------------------------------------------------------------------------
# OYUNCU PAZARI (BAZAAR)
# ---------------------------------------------------------------------------

def bazaar_text(page: int = 0) -> str:
    rows = db.all_("SELECT * FROM bazaar WHERE sold_to=0 ORDER BY id DESC LIMIT 60")
    lines = [
        "🛒 <b>OYUNCU PAZARI</b>",
        "<i>Oyuncuların sattığı eşyalar. Satıcı %5 vergi öder.</i>",
        "",
    ]
    if not rows:
        lines.append("Pazarda hiç ilan yok. İlk ilanı sen ver! 🎒 Envanter → Pazara Koy")
        return "\n".join(lines)
    pages = max(1, math.ceil(len(rows) / PAGE))
    page = max(0, min(page, pages - 1))
    for row in rows[page * PAGE:(page + 1) * PAGE]:
        seller = db.get_user(row["seller_id"])
        item = items.get(row["item_key"])
        if not item:
            continue
        base = item["price"] if item["currency"] == "coins" else item["price"] * 3000
        tag = "🔥 fırsat" if row["price"] < base * 0.8 else ("💸 pahalı" if row["price"] > base * 1.5 else "")
        lines.append(
            f"#{row['id']} {items.rarity_icon(item)} <b>{items.label(row['item_key'], row['item_lvl'])}</b>"
            f" — {ui.fmt(row['price'])} 🪙 {tag}\n"
            f"    satıcı: {ui.esc(seller['first_name']) if seller else '?'}"
        )
    lines.append(f"\nSayfa {page + 1}/{pages}")
    return "\n".join(lines)


def bazaar_kb(page: int = 0):
    rows_db = db.all_("SELECT * FROM bazaar WHERE sold_to=0 ORDER BY id DESC LIMIT 60")
    pages = max(1, math.ceil(len(rows_db) / PAGE))
    page = max(0, min(page, pages - 1))
    rows = []
    line = []
    for row in rows_db[page * PAGE:(page + 1) * PAGE]:
        item = items.get(row["item_key"])
        if not item:
            continue
        line.append((f"{item['emoji']} #{row['id']}", f"mk:bbuy:{row['id']}"))
        if len(line) == 3:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    nav = []
    if page > 0:
        nav.append(("⬅️", f"mk:bazaar:{page - 1}"))
    if page < pages - 1:
        nav.append(("➡️", f"mk:bazaar:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("📄 İlanlarım", "mk:bmine"), ("🔄 Yenile", "mk:bazaar")])
    rows.append([("🏪 Market", "mk:menu"), ("🏠 Menü", "m:main")])
    return ui.kb(rows)


def bazaar_buy(user_id: int, listing_id: int) -> str:
    row = db.one("SELECT * FROM bazaar WHERE id=? AND sold_to=0", (listing_id,))
    if not row:
        return "Bu ilan satılmış ya da kaldırılmış."
    if row["seller_id"] == user_id:
        return "Kendi ilanını satın alamazsın. İptal için 📄 İlanlarım."
    if not economy.take_coins(user_id, row["price"], f"pazar alım #{listing_id}"):
        return "Yeterli altının yok."
    net = int(row["price"] * (1 - config.BAZAAR_TAX))
    db.run("UPDATE bazaar SET sold_to=?, sold_ts=? WHERE id=?", (user_id, ui.now(), listing_id))
    db.inv_add(user_id, row["item_key"], row["qty"], row["item_lvl"],
               stackable=bool(items.get(row["item_key"]) and items.get(row["item_key"])["stackable"]))
    economy.add_coins(row["seller_id"], net, f"pazar satış #{listing_id}")
    events.track(user_id, "buy")
    return (f"✅ {items.label(row['item_key'], row['item_lvl'])} satın alındı!\n"
            f"-{ui.fmt(row['price'])} 🪙 (satıcıya {ui.fmt(net)} 🪙 gitti)")


def bazaar_list_item(user_id: int, inv_id: int, price: int) -> str:
    row = db.inv_get(inv_id, user_id)
    if not row:
        return "Bu eşya sende değil."
    user = db.get_user(user_id)
    if inv_id in (user["weapon_id"], user["armor_id"], user["pet_id"]):
        return "Kuşandığın eşyayı satamazsın, önce başka bir şey kuşan."
    open_count = int(db.scalar("SELECT COUNT(*) FROM bazaar WHERE seller_id=? AND sold_to=0", (user_id,)))
    if open_count >= 10:
        return "En fazla 10 aktif ilanın olabilir."
    if price < 100 or price > 500_000_000:
        return "Fiyat 100 ile 500.000.000 arasında olmalı."
    db.run(
        "INSERT INTO bazaar (seller_id, item_key, item_lvl, qty, price, created_ts) VALUES (?,?,?,?,?,?)",
        (user_id, row["item_key"], row["item_lvl"], 1, price, ui.now()),
    )
    db.inv_remove(inv_id, 1)
    return f"🛒 İlan verildi: {items.label(row['item_key'], row['item_lvl'])} — {ui.fmt(price)} 🪙"


def my_listings_text(user_id: int) -> str:
    rows = db.all_("SELECT * FROM bazaar WHERE seller_id=? AND sold_to=0 ORDER BY id DESC", (user_id,))
    sold = db.all_(
        "SELECT * FROM bazaar WHERE seller_id=? AND sold_to<>0 ORDER BY sold_ts DESC LIMIT 5", (user_id,))
    lines = ["📄 <b>İLANLARIM</b>\n"]
    if rows:
        for row in rows:
            lines.append(f"#{row['id']} {items.label(row['item_key'], row['item_lvl'])} — {ui.fmt(row['price'])} 🪙")
    else:
        lines.append("Aktif ilanın yok.")
    if sold:
        lines.append("\n<b>Son satışlar</b>")
        for row in sold:
            buyer = db.get_user(row["sold_to"])
            lines.append(f"✅ {items.label(row['item_key'], row['item_lvl'])} → "
                         f"{ui.esc(buyer['first_name']) if buyer else '?'} ({ui.fmt(row['price'])} 🪙)")
    return "\n".join(lines)


def my_listings_kb(user_id: int):
    rows_db = db.all_("SELECT * FROM bazaar WHERE seller_id=? AND sold_to=0 ORDER BY id DESC", (user_id,))
    rows = [[(f"🚫 #{r['id']} geri al", f"mk:bcancel:{r['id']}")] for r in rows_db[:8]]
    rows.append([("🛒 Pazar", "mk:bazaar"), ("🏠 Menü", "m:main")])
    return ui.kb(rows)


def bazaar_cancel(user_id: int, listing_id: int) -> str:
    row = db.one("SELECT * FROM bazaar WHERE id=? AND seller_id=? AND sold_to=0", (listing_id, user_id))
    if not row:
        return "Böyle bir aktif ilanın yok."
    db.run("DELETE FROM bazaar WHERE id=?", (listing_id,))
    item = items.get(row["item_key"])
    db.inv_add(user_id, row["item_key"], row["qty"], row["item_lvl"],
               stackable=bool(item and item["stackable"]))
    return "🚫 İlan geri alındı, eşya envanterine döndü."


# ---------------------------------------------------------------------------
# İŞLETMELER
# ---------------------------------------------------------------------------

def biz_text(user) -> str:
    lines = ["🏭 <b>İŞLETMELER</b>",
             "<i>Pasif gelir: her 4 saatte bir kasayı topla.</i>", ""]
    if user["business_key"]:
        item = items.get(user["business_key"])
        elapsed = ui.now() - user["business_ts"]
        cycles = elapsed // config.BUSINESS_COLLECT_SEC
        pending = int(item["income"] * min(6, cycles))
        lines.append(f"Sahip olduğun: {item['emoji']} <b>{item['name']}</b>")
        lines.append(f"💵 Döngü geliri: {ui.fmt(item['income'])} 🪙 / 4 saat")
        if pending:
            lines.append(f"\n💰 <b>Toplanmaya hazır: {ui.fmt(pending)} 🪙</b> ({min(6, cycles)} döngü)")
        else:
            left = config.BUSINESS_COLLECT_SEC - (elapsed % config.BUSINESS_COLLECT_SEC)
            lines.append(f"\n⏳ Sonraki tahsilat: {ui.dur(left)}")
        lines.append("<i>En fazla 6 döngü birikir, düzenli topla!</i>\n")
    else:
        lines.append("Henüz işletmen yok. Bir tane al ve uyurken bile kazan! 💤\n")
    lines.append("<b>Satılık işletmeler</b>")
    for item in items.by_kind("business"):
        lock = "" if user["level"] >= item["min_level"] else f" 🔒Sv.{item['min_level']}"
        roi = item["price"] / item["income"] * 4
        lines.append(f"{item['emoji']} <b>{item['name']}</b>{lock} — {ui.fmt(item['price'])} 🪙\n"
                     f"    {ui.fmt(item['income'])} 🪙/4s • kendini {roi:.0f} saatte amorti eder")
    return "\n".join(lines)


def biz_kb(user):
    rows = []
    if user["business_key"]:
        rows.append([("💰 KASAYI TOPLA", "mk:bizcollect")])
    line = []
    for item in items.by_kind("business"):
        if user["level"] < item["min_level"]:
            continue
        line.append((f"{item['emoji']} {item['name']}", f"mk:bizbuy:{item['key']}"))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append([("🏪 Market", "mk:menu"), ("🏠 Menü", "m:main")])
    return ui.kb(rows)


def biz_buy(user_id: int, key: str) -> str:
    item = items.get(key)
    user = db.get_user(user_id)
    if not item or item["kind"] != "business":
        return "Böyle bir işletme yok."
    if user["level"] < item["min_level"]:
        return f"Bu işletme için Seviye {item['min_level']} gerekiyor."
    if user["business_key"] == key:
        return "Bu işletme zaten senin."
    if not economy.take_coins(user_id, item["price"], f"işletme: {key}"):
        return f"Yeterli altının yok ({ui.fmt(item['price'])} 🪙 gerekli)."
    old = items.get(user["business_key"]) if user["business_key"] else None
    refund = 0
    if old:
        refund = int(old["price"] * 0.5)
        economy.add_coins(user_id, refund, "eski işletme satışı")
    db.upd(user_id, business_key=key, business_ts=ui.now())
    events.track(user_id, "buy")
    extra = f"\nEski işletmen satıldı: +{ui.fmt(refund)} 🪙" if refund else ""
    return f"🏭 {item['emoji']} <b>{item['name']}</b> senin! İlk tahsilat 4 saat sonra.{extra}"


def biz_collect(user_id: int) -> str:
    user = db.get_user(user_id)
    if not user["business_key"]:
        return "İşletmen yok."
    item = items.get(user["business_key"])
    elapsed = ui.now() - user["business_ts"]
    cycles = min(6, elapsed // config.BUSINESS_COLLECT_SEC)
    if cycles <= 0:
        left = config.BUSINESS_COLLECT_SEC - (elapsed % config.BUSINESS_COLLECT_SEC)
        return f"⏳ Henüz kasa dolmadı. {ui.dur(left)} sonra tekrar gel."
    total = economy.payout(user, int(item["income"] * cycles))
    db.upd(user_id, business_ts=ui.now())
    economy.add_coins(user_id, total, "işletme geliri")
    economy.add_xp(user_id, 20 * int(cycles))
    return f"💰 {item['emoji']} {item['name']} kasası: <b>+{ui.fmt(total)}</b> 🪙 ({cycles} döngü)"


# ---------------------------------------------------------------------------
# ELMAS DÜKKANI
# ---------------------------------------------------------------------------

def gems_text(user) -> str:
    return (
        "💎 <b>ELMAS DÜKKANI</b>\n"
        f"Elmasın: <b>{user['gems']}</b> 💎\n\n"
        "Elmas nasıl kazanılır?\n"
        "• 🐉 Boss savaşlarında hasar vererek\n"
        "• 🏅 Başarımlardan\n"
        "• 🎚 Her 5 seviyede\n"
        "• ⛏ Madende şanslı kazmalarda\n"
        "• 🎟 Piyango kazanınca\n\n"
        f"<b>Elmas → Altın:</b> 1 💎 = {ui.fmt(config.GEM_TO_COIN)} 🪙\n"
        "<b>Mitik eşyalar</b> sadece elmasla alınır (Market → Silah/Zırh/Evcil)."
    )


def gems_kb():
    return ui.kb([
        [("🔁 1💎 → Altın", "mk:gex:1"), ("🔁 5💎 → Altın", "mk:gex:5")],
        [("🔁 25💎 → Altın", "mk:gex:25")],
        [("⚡ 10💎 → Tam Enerji", "mk:genergy")],
        [("🏪 Market", "mk:menu"), ("🏠 Menü", "m:main")],
    ])


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await query.answer("🏪 Market özel sohbette açılır. Bana özelden yaz!", show_alert=True)
        return
    await query.answer()
    user = db.get_user(user_id)
    if user is None:
        await ui.safe_edit(query, "Önce /start yaz.")
        return

    if action == "menu":
        await ui.nav(query, "market", market_text(user), market_kb())
    elif action == "cat":
        kind = parts[2]
        await ui.safe_edit(query, cat_text(kind, user), cat_kb(kind, user))
    elif action == "buy":
        ok, msg = buy_item(user_id, parts[2])
        await query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
        item = items.get(parts[2])
        kind = item["kind"] if item else "weapon"
        user = db.get_user(user_id)
        await ui.safe_edit(query, cat_text(kind, user), cat_kb(kind, user))
    elif action == "inv":
        page = int(parts[2]) if len(parts) > 2 else 0
        await ui.safe_edit(query, inv_text(user_id, page), inv_kb(user_id, page))
    elif action == "item":
        text, kb = item_detail(user_id, int(parts[2]))
        await ui.safe_edit(query, text, kb)
    elif action == "eq":
        await query.answer(equip(user_id, int(parts[2])), show_alert=True)
        text, kb = item_detail(user_id, int(parts[2]))
        await ui.safe_edit(query, text, kb)
    elif action == "use":
        msg = use_item(user_id, int(parts[2]))
        await query.answer(msg, show_alert=True)
        await ui.safe_edit(query, inv_text(user_id), inv_kb(user_id))
    elif action == "up":
        msg = upgrade(user_id, int(parts[2]))
        await query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
        text, kb = item_detail(user_id, int(parts[2]))
        await ui.safe_edit(query, text, kb)
    elif action == "sell":
        msg = sell_to_npc(user_id, int(parts[2]))
        await query.answer(msg, show_alert=True)
        await ui.safe_edit(query, inv_text(user_id), inv_kb(user_id))
    elif action == "list":
        inv_id = int(parts[2])
        row = db.inv_get(inv_id, user_id)
        if not row:
            await query.answer("Bu eşya sende değil.", show_alert=True)
            return
        item = items.get(row["item_key"])
        context.user_data["await"] = {"kind": "bazaar_price", "inv_id": inv_id}
        suggested = items.sell_price(item, row["item_lvl"]) * 2 if item else 1000
        await ui.safe_edit(query, (
            f"🛒 <b>PAZARA KOY</b>\n\n"
            f"Eşya: {items.label(row['item_key'], row['item_lvl'])}\n"
            f"Önerilen fiyat: ~{ui.fmt(suggested)} 🪙\n\n"
            f"Fiyatı yaz (sadece sayı). Satışta %{int(config.BAZAAR_TAX * 100)} vergi kesilir.\n"
            f"İptal için /iptal"
        ), ui.back_kb(f"mk:item:{inv_id}"))
    elif action == "bazaar":
        page = int(parts[2]) if len(parts) > 2 else 0
        await ui.safe_edit(query, bazaar_text(page), bazaar_kb(page))
    elif action == "bbuy":
        msg = bazaar_buy(user_id, int(parts[2]))
        await query.answer(msg.replace("<b>", "").replace("</b>", ""), show_alert=True)
        await ui.safe_edit(query, bazaar_text(), bazaar_kb())
    elif action == "bmine":
        await ui.safe_edit(query, my_listings_text(user_id), my_listings_kb(user_id))
    elif action == "bcancel":
        await query.answer(bazaar_cancel(user_id, int(parts[2])), show_alert=True)
        await ui.safe_edit(query, my_listings_text(user_id), my_listings_kb(user_id))
    elif action == "biz":
        await ui.safe_edit(query, biz_text(user), biz_kb(user))
    elif action == "bizbuy":
        await query.answer(biz_buy(user_id, parts[2]).replace("<b>", "").replace("</b>", ""), show_alert=True)
        user = db.get_user(user_id)
        await ui.safe_edit(query, biz_text(user), biz_kb(user))
    elif action == "bizcollect":
        await query.answer(biz_collect(user_id).replace("<b>", "").replace("</b>", ""), show_alert=True)
        user = db.get_user(user_id)
        await ui.safe_edit(query, biz_text(user), biz_kb(user))
    elif action == "gems":
        await ui.safe_edit(query, gems_text(user), gems_kb())
    elif action == "gex":
        count = int(parts[2])
        if economy.take_gems(user_id, count, "elmas takası"):
            economy.add_coins(user_id, count * config.GEM_TO_COIN, "elmas takası")
            await query.answer(f"🔁 {count} 💎 → {ui.fmt(count * config.GEM_TO_COIN)} 🪙", show_alert=True)
        else:
            await query.answer("Yeterli elmasın yok.", show_alert=True)
        user = db.get_user(user_id)
        await ui.safe_edit(query, gems_text(user), gems_kb())
    elif action == "genergy":
        if economy.take_gems(user_id, 10, "enerji dolumu"):
            db.upd(user_id, energy=economy.max_energy(user["level"]), energy_ts=ui.now())
            await query.answer("⚡ Enerji tamamen doldu!", show_alert=True)
        else:
            await query.answer("10 elmas gerekiyor.", show_alert=True)
        user = db.get_user(user_id)
        await ui.safe_edit(query, gems_text(user), gems_kb())


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Pazar fiyatı girişini işler."""
    pending = context.user_data.get("await")
    if not pending or pending.get("kind") != "bazaar_price":
        return False
    raw = (update.message.text or "").strip().replace(".", "").replace(",", "")
    if not raw.isdigit():
        await ui.send(update, "Sadece sayı yaz (örn. 25000) ya da /iptal.")
        return True
    context.user_data.pop("await", None)
    msg = bazaar_list_item(update.effective_user.id, pending["inv_id"], int(raw))
    await ui.send(update, msg, ui.kb([[("🛒 Pazar", "mk:bazaar"), ("🎒 Envanter", "mk:inv")]]))
    return True


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "🏪 Market özel sohbette açılıyor.", ui.pm_link())
        return
    user = db.get_user(update.effective_user.id)
    await ui.screen(update, "market", market_text(user), market_kb())


async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "🎒 Envanter özel sohbette görüntülenir.", ui.pm_link())
        return
    await ui.send(update, inv_text(update.effective_user.id), inv_kb(update.effective_user.id))


async def cmd_bazaar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "🛒 Pazar özel sohbette açılıyor.", ui.pm_link())
        return
    await ui.send(update, bazaar_text(), bazaar_kb())
