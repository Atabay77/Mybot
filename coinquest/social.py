# -*- coding: utf-8 -*-
"""Sosyal sistemler: profil, günlük ödül, banka, transfer, soygun, klanlar,
sıralamalar, davet sistemi ve yardım ekranları."""
import random
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
import economy
import events
import items
import ui

CLAN_COST = 75_000


# ---------------------------------------------------------------------------
# PROFİL
# ---------------------------------------------------------------------------

def profile_text(user_id: int) -> str:
    user = db.get_user(user_id)
    if not user:
        return "Önce /start yaz."
    economy.sync_energy(user_id)
    user = db.get_user(user_id)
    stats = economy.power(user)
    need = economy.xp_needed(user["level"])
    clan = db.one("SELECT * FROM clans WHERE id=?", (user["clan_id"],)) if user["clan_id"] else None
    weapon = db.inv_get(user["weapon_id"], user_id) if user["weapon_id"] else None
    armor = db.inv_get(user["armor_id"], user_id) if user["armor_id"] else None
    pet = db.inv_get(user["pet_id"], user_id) if user["pet_id"] else None
    biz = items.get(user["business_key"]) if user["business_key"] else None
    ach = int(db.scalar("SELECT COUNT(*) FROM achievements WHERE user_id=?", (user_id,)))
    rank = int(db.scalar("SELECT COUNT(*)+1 FROM users WHERE coins+bank > ?", (user["coins"] + user["bank"],)))
    winrate = (user["wins"] / max(1, user["wins"] + user["losses"])) * 100

    lines = [
        f"👤 <b>{ui.name_of(user)}</b>  <i>{ui.esc(user['title'] or economy.title_for(user['level']))}</i>",
        f"🏅 Servet sıralaması: <b>#{rank}</b>",
        "",
        f"🎚 Seviye <b>{user['level']}</b>  {ui.bar(user['xp'], need, 10)}  {ui.fmt(user['xp'])}/{ui.fmt(need)} XP",
        f"⚡ Enerji {user['energy']}/{economy.max_energy(user['level'])}",
        "",
        f"🪙 Cüzdan: <b>{ui.fmt(user['coins'])}</b>",
        f"🏦 Banka: <b>{ui.fmt(user['bank'])}</b>",
        f"💎 Elmas: <b>{ui.fmt(user['gems'])}</b>",
        f"💰 Toplam servet: <b>{ui.fmt(user['coins'] + user['bank'])}</b>",
        "",
        f"⚔️ Saldırı {stats['atk']}  🛡 Savunma {stats['dfn']}  ❤️ Can {stats['hp']}  💥 Kritik %{stats['crit'] * 100:.0f}",
        f"🗡 Silah: {items.label(weapon['item_key'], weapon['item_lvl']) if weapon else '—'}",
        f"🛡 Zırh: {items.label(armor['item_key'], armor['item_lvl']) if armor else '—'}",
        f"🐾 Dost: {items.label(pet['item_key'], pet['item_lvl']) if pet else '—'}",
        f"🏭 İşletme: {biz['emoji'] + ' ' + biz['name'] if biz else '—'}",
        f"🏰 Klan: {ui.esc(clan['name']) if clan else '—'}",
        "",
        f"🎮 Oyun: <b>{ui.fmt(user['games'])}</b>  •  Kazanma oranı %{winrate:.0f}",
        f"⚔️ PVP: <b>{user['pvp_wins']}</b>G / {user['pvp_losses']}Y",
        f"🐉 Boss vuruşu: {user['boss_kills']}",
        f"💥 En büyük kazanç: {ui.fmt(user['biggest_win'])} 🪙",
        f"📅 Günlük seri: <b>{user['streak']}</b> gün",
        f"👥 Davet: {user['refs']} kişi",
        f"🏅 Başarım: {ach}/{len(events.ACHIEVEMENTS)}",
    ]
    buffs = []
    now = ui.now()
    if user["luck_until"] > now:
        buffs.append(f"🍀 şans ({ui.dur(user['luck_until'] - now)})")
    if user["xpboost_until"] > now:
        buffs.append(f"📜 2x XP ({ui.dur(user['xpboost_until'] - now)})")
    if user["shield_until"] > now:
        buffs.append(f"🛡 kalkan ({ui.dur(user['shield_until'] - now)})")
    if buffs:
        lines.append("\n✨ Aktif etkiler: " + ", ".join(buffs))
    return "\n".join(lines)


def profile_kb():
    return ui.kb([
        [("🎒 Envanter", "mk:inv"), ("📜 Görevler", "ev:quests")],
        [("🏅 Başarımlar", "ev:ach"), ("👥 Davet Et", "s:ref")],
        [("🏠 Menü", "m:main")],
    ])


# ---------------------------------------------------------------------------
# GÜNLÜK / SAATLİK
# ---------------------------------------------------------------------------

def daily(user_id: int) -> str:
    user = db.get_user(user_id)
    now = ui.now()
    if now - user["last_daily"] < 20 * 3600:
        left = user["last_daily"] + 20 * 3600 - now
        return f"⏳ Günlük ödülünü aldın. Yenisi için: <b>{ui.dur(left)}</b>"
    streak = user["streak"] + 1 if now - user["last_daily"] < 48 * 3600 else 1
    reward = config.DAILY_BASE + config.DAILY_STREAK_BONUS * min(streak, 30) + user["level"] * 200
    reward = economy.payout(user, reward)
    gems = 0
    extra = ""
    if streak % 7 == 0:
        gems = 5
        extra = f"\n🎉 <b>{streak}. gün bonusu:</b> +5 💎"
    db.upd(user_id, last_daily=now, streak=streak)
    economy.add_coins(user_id, reward, "günlük ödül")
    if gems:
        economy.add_gems(user_id, gems, "günlük seri bonusu")
    economy.add_xp(user_id, 50)
    economy.add_energy(user_id, 10)
    # rastgele sürpriz
    surprise = ""
    if economy.roll(0.25):
        drop = random.choice(["c_energy", "c_clover", "c_potion", "c_scroll"])
        db.inv_add(user_id, drop, 1, stackable=True)
        surprise = f"\n🎁 Sürpriz: {items.label(drop)}"
    return (
        f"🎁 <b>GÜNLÜK ÖDÜL</b>\n\n"
        f"💰 +{ui.fmt(reward)} 🪙\n⚡ +10 enerji  ✨ +50 XP\n"
        f"🔥 Seri: <b>{streak}</b> gün{extra}{surprise}\n\n"
        f"<i>Her gün gel, seri arttıkça ödül büyür (30 güne kadar).</i>"
    )


def hourly(user_id: int) -> str:
    user = db.get_user(user_id)
    left = economy.cooldown_left(user["last_hourly"], config.HOURLY_COOLDOWN)
    if left > 0:
        return f"⏳ Saatlik bonus için {ui.dur(left)} kaldı."
    reward = economy.payout(user, config.HOURLY_REWARD + user["level"] * 60)
    db.upd(user_id, last_hourly=ui.now())
    economy.add_coins(user_id, reward, "saatlik bonus")
    economy.add_energy(user_id, 3)
    return f"⏰ <b>Saatlik bonus:</b> +{ui.fmt(reward)} 🪙, +3 ⚡"


# ---------------------------------------------------------------------------
# BANKA
# ---------------------------------------------------------------------------

def bank_limit(user) -> int:
    return user["level"] * config.BANK_MAX_MULT * 1_000 + 50_000


def bank_text(user_id: int) -> str:
    user = db.get_user(user_id)
    return (
        "🏦 <b>DİYAR BANKASI</b>\n\n"
        f"🪙 Cüzdan: <b>{ui.fmt(user['coins'])}</b>\n"
        f"🏦 Kasa: <b>{ui.fmt(user['bank'])}</b> / {ui.fmt(bank_limit(user))} limit\n\n"
        f"📈 Faiz: günde %{int(config.BANK_INTEREST * 100)} (otomatik işler)\n"
        "🛡 Bankadaki para <b>soygundan korunur</b>.\n\n"
        "<i>Kasa limiti seviyenle büyür.</i>"
    )


def bank_kb():
    return ui.kb([
        [("⬇️ 10K Yatır", "s:dep:10000"), ("⬇️ 100K Yatır", "s:dep:100000")],
        [("⬇️ Hepsini Yatır", "s:dep:all")],
        [("⬆️ 10K Çek", "s:wd:10000"), ("⬆️ Hepsini Çek", "s:wd:all")],
        [("🏠 Menü", "m:main")],
    ])


def deposit(user_id: int, amount) -> str:
    user = db.get_user(user_id)
    room = bank_limit(user) - user["bank"]
    if room <= 0:
        return "Banka kasan dolu! Seviye atlayarak limiti büyüt."
    amount = user["coins"] if amount == "all" else int(amount)
    amount = min(amount, user["coins"], room)
    if amount <= 0:
        return "Yatıracak altın yok."
    if not economy.take_coins(user_id, amount, "bankaya yatırma"):
        return "İşlem başarısız."
    db.bump(user_id, bank=amount)
    if not user["last_bank"]:
        db.upd(user_id, last_bank=ui.now())
    return f"⬇️ {ui.fmt(amount)} 🪙 bankaya yatırıldı."


def withdraw(user_id: int, amount) -> str:
    user = db.get_user(user_id)
    amount = user["bank"] if amount == "all" else int(amount)
    amount = min(amount, user["bank"])
    if amount <= 0:
        return "Bankada para yok."
    db.bump(user_id, bank=-amount)
    economy.add_coins(user_id, amount, "bankadan çekme")
    return f"⬆️ {ui.fmt(amount)} 🪙 çekildi."


# ---------------------------------------------------------------------------
# TRANSFER & SOYGUN
# ---------------------------------------------------------------------------

def transfer(sender_id: int, target_name: str, amount: int) -> str:
    target = db.find_user_by_name(target_name)
    if not target:
        return "Bu oyuncu bulunamadı. Kişinin bota /start yazmış olması gerekir."
    if target["user_id"] == sender_id:
        return "Kendine para gönderemezsin. 🙃"
    if amount < 100:
        return "En az 100 altın gönderebilirsin."
    sender = db.get_user(sender_id)
    if sender["level"] < 3:
        return "Transfer için Seviye 3 gerekiyor (kötüye kullanım koruması)."
    tax = int(amount * config.TRANSFER_TAX)
    if not economy.take_coins(sender_id, amount, "transfer"):
        return f"Yeterli altının yok ({ui.fmt(sender['coins'])} 🪙)."
    economy.add_coins(target["user_id"], amount - tax, f"transfer: {sender_id}")
    return (f"💸 {ui.fmt(amount - tax)} 🪙 → <b>{ui.name_of(target)}</b>\n"
            f"<i>Vergi: {ui.fmt(tax)} 🪙 (%{int(config.TRANSFER_TAX * 100)})</i>")


def rob(robber_id: int, target_name: str) -> str:
    target = db.find_user_by_name(target_name)
    robber = db.get_user(robber_id)
    if not target:
        return "Hedef bulunamadı."
    if target["user_id"] == robber_id:
        return "Kendini soymak? 🤨"
    if robber["level"] < 5:
        return "Soygun için Seviye 5 gerekiyor."
    left = economy.cooldown_left(robber["last_rob"], config.ROB_COOLDOWN)
    if left > 0:
        return f"⏳ Polis peşinde! {ui.dur(left)} sonra dene."
    if target["shield_until"] > ui.now():
        return f"🛡 {ui.name_of(target)} kalkan kullanıyor, soyulamaz."
    if target["coins"] < 5_000:
        return f"{ui.name_of(target)} cebinde soyulacak kadar para taşımıyor (min 5.000 🪙)."
    db.upd(robber_id, last_rob=ui.now())
    boost = db.meta_get(f"rob_boost_{robber_id}")
    chance = 0.42 + (robber["level"] - target["level"]) * 0.015 + economy.luck(robber) * 0.5
    chance = max(0.12, min(0.85, chance))
    if boost:
        chance = 1.0
        db.meta_set(f"rob_boost_{robber_id}", 0)
    if random.random() < chance:
        pct = random.uniform(0.05, 0.16)
        stolen = int(target["coins"] * pct)
        stolen = min(stolen, 2_000_000)
        economy.take_coins(target["user_id"], stolen, f"soyuldu: {robber_id}")
        economy.add_coins(robber_id, stolen, f"soygun: {target['user_id']}")
        economy.add_xp(robber_id, 40)
        return (
            f"🥷 <b>SOYGUN BAŞARILI!</b>\n\n"
            f"{ui.name_of(target)} oyuncusundan <b>{ui.fmt(stolen)}</b> 🪙 aldın!\n"
            f"<i>Şans: %{chance * 100:.0f}</i>\n\n"
            f"💡 Paranı korumak için bankaya yatır: /banka"
        )
    fine = min(robber["coins"], int(3_000 + robber["level"] * 700))
    economy.take_coins(robber_id, fine, "soygun cezası")
    return (
        f"🚨 <b>YAKALANDIN!</b>\n\n"
        f"{ui.name_of(target)} seni fark etti, bekçilere {ui.fmt(fine)} 🪙 ceza ödedin.\n"
        f"<i>Şans: %{chance * 100:.0f}</i>"
    )


# ---------------------------------------------------------------------------
# KLANLAR
# ---------------------------------------------------------------------------

def clan_text(user_id: int) -> str:
    user = db.get_user(user_id)
    if not user["clan_id"]:
        top = db.all_(
            "SELECT c.*, (SELECT COUNT(*) FROM clan_members m WHERE m.clan_id=c.id) AS cnt "
            "FROM clans c ORDER BY c.level DESC, c.treasury DESC LIMIT 8")
        lines = [
            "🏰 <b>KLANLAR</b>",
            "<i>Klan üyeleri tüm kazançlarda bonus alır (klan seviyesi x %2).</i>",
            "",
            f"Klan kurmak: {ui.fmt(CLAN_COST)} 🪙",
            "",
            "<b>En güçlü klanlar</b>",
        ]
        for clan in top:
            lines.append(f"🏰 <b>{ui.esc(clan['name'])}</b> — Sv.{clan['level']} • "
                         f"{clan['cnt']} üye • kasa {ui.fmt(clan['treasury'])} 🪙")
        if not top:
            lines.append("Henüz klan yok — ilkini sen kur!")
        lines.append("\nKatılmak için aşağıdaki listeden seç 👇")
        return "\n".join(lines)

    clan = db.one("SELECT * FROM clans WHERE id=?", (user["clan_id"],))
    members = db.all_(
        "SELECT m.*, u.first_name, u.level FROM clan_members m JOIN users u ON u.user_id=m.user_id "
        "WHERE m.clan_id=? ORDER BY m.contributed DESC LIMIT 15", (user["clan_id"],))
    lines = [
        f"🏰 <b>{ui.esc(clan['name'])}</b>  (Seviye {clan['level']})",
        f"<i>{ui.esc(clan['motto'] or 'Şeref ve altın!')}</i>",
        "",
        f"💰 Kasa: <b>{ui.fmt(clan['treasury'])}</b> 🪙",
        f"✨ Klan XP: {ui.fmt(clan['xp'])} / {ui.fmt(5000 * clan['level'])}",
        f"🎁 Üye bonusu: +%{int(economy.clan_bonus(user) * 100)} kazanç",
        f"👥 Üyeler ({len(members)}):",
    ]
    for member in members:
        role = {"lider": "👑", "yonetici": "⭐", "uye": "•"}.get(member["role"], "•")
        lines.append(f"{role} {ui.esc(member['first_name'])} (Sv.{member['level']}) — "
                     f"bağış {ui.fmt(member['contributed'])} 🪙")
    lines.append("\n<i>Bağış yaptıkça klan seviyesi ve herkesin bonusu artar.</i>")
    return "\n".join(lines)


def clan_kb(user_id: int):
    user = db.get_user(user_id)
    if not user["clan_id"]:
        clans = db.all_("SELECT * FROM clans WHERE open_join=1 ORDER BY level DESC LIMIT 6")
        rows = [[(f"🏰 {c['name'][:18]} (Sv.{c['level']})", f"s:cjoin:{c['id']}")] for c in clans]
        rows.append([("➕ Klan Kur", "s:ccreate")])
        rows.append([("🏠 Menü", "m:main")])
        return ui.kb(rows)
    return ui.kb([
        [("💰 Bağış Yap", "s:cdonate")],
        [("🚪 Klandan Ayrıl", "s:cleave")],
        [("🏆 Klan Sıralaması", "s:top:clan")],
        [("🏠 Menü", "m:main")],
    ])


def clan_create(user_id: int, name: str) -> str:
    name = " ".join(name.split())[:24]
    if len(name) < 3:
        return "Klan adı en az 3 karakter olmalı."
    user = db.get_user(user_id)
    if user["clan_id"]:
        return "Zaten bir klandasın."
    if user["level"] < 8:
        return "Klan kurmak için Seviye 8 gerekiyor."
    if db.one("SELECT id FROM clans WHERE lower(name)=lower(?)", (name,)):
        return "Bu isimde bir klan var, başka bir isim dene."
    if not economy.take_coins(user_id, CLAN_COST, "klan kurma"):
        return f"Klan kurmak {ui.fmt(CLAN_COST)} altın tutuyor."
    cur = db.run(
        "INSERT INTO clans (name, owner_id, treasury, created_ts) VALUES (?,?,0,?)",
        (name, user_id, ui.now()))
    clan_id = int(cur.lastrowid)
    db.run("INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_ts) VALUES (?,?, 'lider', ?)",
           (clan_id, user_id, ui.now()))
    db.upd(user_id, clan_id=clan_id)
    return f"🏰 <b>{ui.esc(name)}</b> klanı kuruldu! Arkadaşlarını davet et."


def clan_join(user_id: int, clan_id: int) -> str:
    user = db.get_user(user_id)
    if user["clan_id"]:
        return "Zaten bir klandasın. Önce ayrılman gerekir."
    clan = db.one("SELECT * FROM clans WHERE id=?", (clan_id,))
    if not clan:
        return "Klan bulunamadı."
    count = int(db.scalar("SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (clan_id,)))
    if count >= 20 + clan["level"] * 2:
        return "Klan kontenjanı dolu."
    db.run("INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_ts) VALUES (?,?, 'uye', ?)",
           (clan_id, user_id, ui.now()))
    db.upd(user_id, clan_id=clan_id)
    return f"🏰 <b>{ui.esc(clan['name'])}</b> klanına katıldın!"


def clan_leave(user_id: int) -> str:
    user = db.get_user(user_id)
    if not user["clan_id"]:
        return "Bir klanda değilsin."
    clan = db.one("SELECT * FROM clans WHERE id=?", (user["clan_id"],))
    db.run("DELETE FROM clan_members WHERE user_id=?", (user_id,))
    db.upd(user_id, clan_id=0)
    if clan and clan["owner_id"] == user_id:
        nxt = db.one("SELECT * FROM clan_members WHERE clan_id=? ORDER BY contributed DESC LIMIT 1",
                     (clan["id"],))
        if nxt:
            db.run("UPDATE clans SET owner_id=? WHERE id=?", (nxt["user_id"], clan["id"]))
            db.run("UPDATE clan_members SET role='lider' WHERE user_id=?", (nxt["user_id"],))
        else:
            db.run("DELETE FROM clans WHERE id=?", (clan["id"],))
    return "🚪 Klandan ayrıldın."


def clan_donate(user_id: int, amount: int) -> str:
    user = db.get_user(user_id)
    if not user["clan_id"]:
        return "Bir klanda değilsin."
    if amount < 1_000:
        return "En az 1.000 altın bağışlanabilir."
    if not economy.take_coins(user_id, amount, "klan bağışı"):
        return "Yeterli altının yok."
    db.run("UPDATE clans SET treasury=treasury+? WHERE id=?", (amount, user["clan_id"]))
    db.run("UPDATE clan_members SET contributed=contributed+? WHERE user_id=?", (amount, user_id))
    economy.clan_add_xp(user["clan_id"], amount // 100)
    economy.add_xp(user_id, amount // 500)
    return f"💰 Klan kasasına {ui.fmt(amount)} 🪙 bağışladın! Klan XP +{ui.fmt(amount // 100)}"


# ---------------------------------------------------------------------------
# SIRALAMALAR
# ---------------------------------------------------------------------------
TOPS = {
    "rich": ("💰 En Zenginler", "SELECT first_name, coins+bank AS v FROM users ORDER BY v DESC LIMIT 10", "🪙"),
    "level": ("🎚 En Yüksek Seviye", "SELECT first_name, level AS v FROM users ORDER BY v DESC, xp DESC LIMIT 10", "sv"),
    "pvp": ("⚔️ PVP Kralları", "SELECT first_name, pvp_wins AS v FROM users ORDER BY v DESC LIMIT 10", "galibiyet"),
    "win": ("💥 En Büyük Vuruş", "SELECT first_name, biggest_win AS v FROM users ORDER BY v DESC LIMIT 10", "🪙"),
    "games": ("🎮 En Çok Oynayan", "SELECT first_name, games AS v FROM users ORDER BY v DESC LIMIT 10", "oyun"),
    "boss": ("🐉 Boss Avcıları", "SELECT first_name, boss_kills AS v FROM users ORDER BY v DESC LIMIT 10", "vuruş"),
}


def top_text(kind: str = "rich") -> str:
    if kind == "clan":
        rows = db.all_("SELECT name, level, treasury FROM clans ORDER BY level DESC, treasury DESC LIMIT 10")
        lines = ["🏆 <b>KLAN SIRALAMASI</b>\n"]
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        for i, row in enumerate(rows):
            lines.append(f"{medals[i]} <b>{ui.esc(row['name'])}</b> — Sv.{row['level']} • "
                         f"{ui.fmt(row['treasury'])} 🪙")
        if not rows:
            lines.append("Henüz klan yok.")
        return "\n".join(lines)
    title, sql, unit = TOPS.get(kind, TOPS["rich"])
    rows = db.all_(sql)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"🏆 <b>{title.upper()}</b>\n"]
    for i, row in enumerate(rows):
        if not row["v"]:
            continue
        lines.append(f"{medals[i]} {ui.esc(row['first_name'])} — <b>{ui.fmt(row['v'])}</b> {unit}")
    if len(lines) == 1:
        lines.append("Henüz veri yok.")
    return "\n".join(lines)


def top_kb():
    return ui.kb([
        [("💰 Zengin", "s:top:rich"), ("🎚 Seviye", "s:top:level")],
        [("⚔️ PVP", "s:top:pvp"), ("💥 Vuruş", "s:top:win")],
        [("🎮 Oyun", "s:top:games"), ("🐉 Boss", "s:top:boss")],
        [("🏰 Klanlar", "s:top:clan")],
        [("🏠 Menü", "m:main")],
    ])


# ---------------------------------------------------------------------------
# DAVET
# ---------------------------------------------------------------------------

def ref_text(user_id: int) -> str:
    user = db.get_user(user_id)
    link = f"https://t.me/{config.BOT_USERNAME}?start=ref{user_id}" if config.BOT_USERNAME else \
        f"Botun kullanıcı adını .env dosyasına ekle (BOT_USERNAME) ki link üretilebilsin. Kod: ref{user_id}"
    invited = db.all_("SELECT first_name, level FROM users WHERE referrer=? ORDER BY level DESC LIMIT 10",
                      (user_id,))
    lines = [
        "👥 <b>ARKADAŞINI DAVET ET</b>\n",
        "Her davet için:\n"
        "• Sen: <b>+10.000 🪙</b> ve <b>+2 💎</b>\n"
        "• Arkadaşın: <b>+5.000 🪙</b> başlangıç bonusu\n",
        f"🔗 Davet linkin:\n<code>{ui.esc(link)}</code>\n",
        f"📊 Davet ettiğin: <b>{user['refs']}</b> kişi",
    ]
    if invited:
        lines.append("\n<b>Davet ettiklerin</b>")
        for row in invited:
            lines.append(f"• {ui.esc(row['first_name'])} (Sv.{row['level']})")
    lines.append("\n<i>Arkadaşlarınla grup kurup düello yapın, birlikte boss avlayın!</i>")
    return "\n".join(lines)


def grant_referral(new_user_id: int, referrer_id: int) -> None:
    if not referrer_id or referrer_id == new_user_id:
        return
    ref = db.get_user(referrer_id)
    if not ref:
        return
    economy.add_coins(referrer_id, 10_000, "davet ödülü")
    economy.add_gems(referrer_id, 2, "davet ödülü")
    db.bump(referrer_id, refs=1)
    economy.add_coins(new_user_id, 5_000, "davet bonusu")


# ---------------------------------------------------------------------------
# YARDIM METİNLERİ
# ---------------------------------------------------------------------------
HELP_TEXT = (
    "❓ <b>NASIL OYNANIR?</b>\n\n"
    "Çok basit, 3 adım:\n\n"
    "<b>1️⃣ Coin kazan</b>\n"
    "🎮 Oyunlar butonuna bas, oyna. Ya da her gün 🎁 hediyeni al, 💼 çalış, ⛏ maden kaz.\n\n"
    "<b>2️⃣ Coini büyüt</b>\n"
    "🏪 Marketten silah-zırh al, güçlen. ⚔️ Arkadaşınla yarış, onun coinini kazan. "
    "🐉 Canavarı birlikte dövün, ödülü paylaşın.\n\n"
    "<b>3️⃣ Gerçek paraya çevir</b>\n"
    "💵 Para Çek butonundan coinini paraya çevirirsin. Yeterince birikince ödemeni istersin.\n\n"
    "<b>Diğerleri</b>\n"
    "🏦 Banka — paranı sakla, faiz kazan, kimse çalamasın\n"
    "🥷 Soygun — başkasının cebindekini çalmayı dene\n"
    "🏭 İş Yerim — sen uyurken bile para kazan\n"
    "🛒 Pazar — eşyanı istediğin fiyata sat\n"
    "🎟 Çekiliş — bilet al, büyük ikramiyeyi kap\n"
    "🏰 Klan — arkadaşlarınla takım kur, herkes daha çok kazansın\n"
    "📜 Görevler — her gün 3 küçük görev, ekstra ödül\n\n"
    "<i>Hiçbir şey yazmana gerek yok, hepsi butonlarla 👇</i>"
)

EARN_TEXT = (
    "💸 <b>COİN KAZANMA YOLLARI</b>\n\n"
    "🎁 <b>Günlük Hediye</b> — her gün gel, üst üste geldikçe artar\n"
    "⏰ <b>Saatlik bonus</b> — her saat küçük hediye\n"
    "💼 <b>Çalış</b> — 45 dakikada bir kesin para\n"
    "⛏ <b>Maden</b> — 20 dakikada bir, elmas çıkabilir\n"
    "🗡 <b>Arena</b> — canavar avla, silahın iyiyse çok kazanırsın\n"
    "🧠 <b>Bilgi/Kelime oyunları</b> — risksiz, kaybetmezsin\n"
    "🐉 <b>Canavar</b> — en büyük ödül, herkes birlikte döver\n"
    "🎟 <b>Çekiliş</b> — şansına, büyük ikramiye\n"
    "🏭 <b>İş Yerim</b> — uyurken kazan\n"
    "🏦 <b>Banka</b> — her gün %2 faiz\n"
    "👥 <b>Arkadaş Çağır</b> — her arkadaş için 10.000 🪙 + 2 💎\n"
    "⚔️ <b>Düello</b> — arkadaşının coinini kap\n"
    "🛒 <b>Pazar</b> — ucuza al, pahalıya sat\n\n"
    "<i>Not: Kazandığını bankaya koy, kimse soyamaz.</i>"
)


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "profile"
    user_id = update.effective_user.id
    await query.answer()
    user = db.get_user(user_id)
    if user is None:
        await ui.safe_edit(query, "Önce /start yaz.")
        return

    if action == "profile":
        await ui.safe_edit(query, profile_text(user_id), profile_kb())
    elif action == "daily":
        msg = daily(user_id)
        unlocked = events.check_achievements(user_id)
        if unlocked:
            msg += "\n\n🏅 <b>YENİ BAŞARIM!</b>\n" + "\n".join(unlocked)
        await ui.safe_edit(query, msg, ui.kb([
            [("⏰ Saatlik Bonus", "s:hourly")], [("🏠 Menü", "m:main")]]))
    elif action == "hourly":
        await ui.safe_edit(query, hourly(user_id), ui.kb([
            [("🎁 Günlük Ödül", "s:daily")], [("🏠 Menü", "m:main")]]))
    elif action == "bank":
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "dep":
        await query.answer(deposit(user_id, parts[2]), show_alert=True)
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "wd":
        await query.answer(withdraw(user_id, parts[2]), show_alert=True)
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "top":
        kind = parts[2] if len(parts) > 2 else "rich"
        await ui.safe_edit(query, top_text(kind), top_kb())
    elif action == "clan":
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "ccreate":
        context.user_data["await"] = {"kind": "clan_name"}
        await ui.safe_edit(query, (
            f"🏰 <b>KLAN KUR</b>\n\nMaliyet: {ui.fmt(CLAN_COST)} 🪙 • Seviye 8 gerekli\n\n"
            "Klan adını yaz (3-24 karakter). İptal: /iptal"
        ), ui.back_kb("s:clan"))
    elif action == "cjoin":
        await query.answer(clan_join(user_id, int(parts[2])).replace("<b>", "").replace("</b>", ""),
                           show_alert=True)
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "cleave":
        await query.answer(clan_leave(user_id), show_alert=True)
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "cdonate":
        context.user_data["await"] = {"kind": "clan_donate"}
        await ui.safe_edit(query, (
            "💰 <b>KLAN BAĞIŞI</b>\n\nBağışlamak istediğin altın miktarını yaz (min 1.000).\n"
            "Bağış klan seviyesini yükseltir, tüm üyeler kazanır. İptal: /iptal"
        ), ui.back_kb("s:clan"))
    elif action == "ref":
        await ui.safe_edit(query, ref_text(user_id), ui.back_kb("m:main"))
    elif action == "help":
        await ui.safe_edit(query, HELP_TEXT, ui.kb([
            [("💸 Kazanç Yolları", "s:earn")], [("🏠 Menü", "m:main")]]))
    elif action == "earn":
        await ui.safe_edit(query, EARN_TEXT, ui.kb([
            [("ℹ️ Yardım", "s:help")], [("🏠 Menü", "m:main")]]))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending:
        return False
    kind = pending.get("kind")
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    if kind == "clan_name":
        context.user_data.pop("await", None)
        await ui.send(update, clan_create(user_id, text), ui.kb([[("🏰 Klan", "s:clan")]]))
        return True
    if kind == "clan_donate":
        raw = text.replace(".", "").replace(",", "")
        if not raw.isdigit():
            await ui.send(update, "Sadece sayı yaz ya da /iptal.")
            return True
        context.user_data.pop("await", None)
        await ui.send(update, clan_donate(user_id, int(raw)), ui.kb([[("🏰 Klan", "s:clan")]]))
        return True
    if kind == "custom_bet":
        raw = text.replace(".", "").replace(",", "")
        if not raw.isdigit():
            await ui.send(update, "Sadece sayı yaz ya da /iptal.")
            return True
        context.user_data.pop("await", None)
        prefix = pending["prefix"]
        amount = int(raw)
        await ui.send(update, f"Bahis: <b>{ui.fmt(amount)}</b> 🪙 — onaylıyor musun?", ui.kb([
            [("✅ Oyna", f"{prefix}:{amount}")],
            [("🎮 Oyunlar", "g:menu")],
        ]))
        return True
    return False


# ---------------------------------------------------------------------------
# KOMUTLAR
# ---------------------------------------------------------------------------

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, profile_text(update.effective_user.id), profile_kb())


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_user.id)
    await ui.send(update, (
        f"💰 <b>{ui.name_of(user)}</b>\n\n"
        f"🪙 Cüzdan: <b>{ui.fmt(user['coins'])}</b>\n"
        f"🏦 Banka: <b>{ui.fmt(user['bank'])}</b>\n"
        f"💎 Elmas: <b>{ui.fmt(user['gems'])}</b>\n"
        f"🎚 Seviye: <b>{user['level']}</b>"
    ), ui.kb([[("🎮 Oyunlar", "g:menu"), ("🎁 Günlük", "s:daily")]]))


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, daily(update.effective_user.id), ui.kb([[("🎮 Oyunlar", "g:menu")]]))


async def cmd_hourly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, hourly(update.effective_user.id))


async def cmd_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, bank_text(update.effective_user.id), bank_kb())


async def cmd_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    target = None
    amount = None
    if update.message.reply_to_message and args:
        target = str(update.message.reply_to_message.from_user.id)
        amount = args[0]
    elif len(args) >= 2:
        target, amount = args[0], args[1]
    if not target or not amount:
        await ui.send(update, (
            "💸 <b>PARA GÖNDER</b>\n\n"
            "<code>/transfer @kullanici 5000</code>\n"
            "veya birinin mesajını yanıtlayıp <code>/transfer 5000</code>\n\n"
            f"<i>Vergi: %{int(config.TRANSFER_TAX * 100)}</i>"))
        return
    raw = amount.replace(".", "").replace(",", "")
    if not raw.isdigit():
        await ui.send(update, "Miktar sayı olmalı.")
        return
    await ui.send(update, transfer(update.effective_user.id, target, int(raw)))


async def cmd_rob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if update.message.reply_to_message:
        target = str(update.message.reply_to_message.from_user.id)
    elif args:
        target = args[0]
    else:
        await ui.send(update, "🥷 Kullanım: <code>/soy @kullanici</code> ya da birinin mesajını yanıtla.")
        return
    await ui.send(update, rob(update.effective_user.id, target))


async def cmd_clan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, clan_text(update.effective_user.id), clan_kb(update.effective_user.id))


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, top_text("rich"), top_kb())


async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, ref_text(update.effective_user.id))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, HELP_TEXT, ui.kb([[("💸 Kazanç Yolları", "s:earn"), ("🏠 Menü", "m:main")]]))
