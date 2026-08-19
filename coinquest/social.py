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
import i18n
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
    hidden = db.hidden_ids()
    marks = ",".join("?" * len(hidden)) if hidden else "0"
    rank = int(db.scalar(
        f"SELECT COUNT(*)+1 FROM users WHERE coins+bank > ? AND user_id NOT IN ({marks})",
        (user["coins"] + user["bank"], *hidden)))
    winrate = (user["wins"] / max(1, user["wins"] + user["losses"])) * 100

    lines = [
        f"👤 <b>{ui.name_of(user)}</b>"
        + (f"  @{ui.esc(user['username'])}" if user["username"] else ""),
        f"🆔 <code>{user_id}</code>",
        f"<i>{ui.esc(user['title'] or economy.title_for(user['level']))}</i>  •  🏅 #{rank}",
        ui.LINE,
        f"<blockquote>🎚 <b>Seviye {user['level']}</b>\n"
        f"{ui.bar(user['xp'], need, 12)}\n"
        f"{ui.fmt(user['xp'])} / {ui.fmt(need)} XP\n"
        f"⚡ Enerji {user['energy']}/{economy.max_energy(user['level'])}</blockquote>",
        f"<blockquote>🪙 Cüzdan: <b>{ui.fmt(user['coins'])}</b>\n"
        f"🏦 Banka: <b>{ui.fmt(user['bank'])}</b>\n"
        f"💎 Elmas: <b>{ui.fmt(user['gems'])}</b>\n"
        f"💵 Gerçek para: <b>{ui.money(user['tmt'])}</b></blockquote>",
        f"<blockquote>⚔️ Saldırı <b>{stats['atk']}</b>   🛡 Savunma <b>{stats['dfn']}</b>\n"
        f"❤️ Can <b>{stats['hp']}</b>   💥 Kritik <b>%{stats['crit'] * 100:.0f}</b>\n"
        f"🗡 {items.label(weapon['item_key'], weapon['item_lvl']) if weapon else '—'}\n"
        f"🛡 {items.label(armor['item_key'], armor['item_lvl']) if armor else '—'}\n"
        f"🐾 {items.label(pet['item_key'], pet['item_lvl']) if pet else '—'}</blockquote>",
        f"<blockquote>🎮 Oyun: <b>{ui.fmt(user['games'])}</b>  (kazanma %{winrate:.0f})\n"
        f"⚔️ Düello: <b>{user['pvp_wins']}</b> galibiyet / {user['pvp_losses']} yenilgi\n"
        f"🐉 Canavar vuruşu: {user['boss_kills']}\n"
        f"💥 En büyük kazanç: {ui.fmt(user['biggest_win'])} 🪙\n"
        f"📅 Seri: <b>{user['streak']}</b> gün   👥 Davet: {user['refs']}\n"
        f"🏅 Başarım: {ach}/{len(events.ACHIEVEMENTS)}</blockquote>",
        f"🏭 {biz['emoji'] + ' ' + biz['name'] if biz else '—'}   "
        f"🏰 {ui.esc(clan['name']) if clan else '—'}",
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
    lang = i18n.lang_of(user_id)
    now = ui.now()
    if now - user["last_daily"] < 20 * 3600:
        left = user["last_daily"] + 20 * 3600 - now
        return i18n.t(lang, "d_wait", time=ui.dur(left))
    streak = user["streak"] + 1 if now - user["last_daily"] < 48 * 3600 else 1
    reward = config.DAILY_BASE + config.DAILY_STREAK_BONUS * min(streak, 30) + user["level"] * 200
    reward = economy.payout(user, reward)
    gems = 5 if streak % 7 == 0 else 0
    db.upd(user_id, last_daily=now, streak=streak)
    economy.add_coins(user_id, reward, "günlük ödül")
    if gems:
        economy.add_gems(user_id, gems, "günlük seri bonusu")
    economy.add_xp(user_id, 50)
    economy.add_energy(user_id, 10)
    surprise = ""
    if economy.roll(0.25):
        drop = random.choice(["c_energy", "c_clover", "c_potion", "c_scroll"])
        db.inv_add(user_id, drop, 1, stackable=True)
        surprise = f"\n🎁 {items.label(drop)}"
    return (
        f"{i18n.t(lang, 'd_title')}\n{ui.LINE}\n"
        f"<blockquote>💰 <b>+{ui.fmt(reward)}</b> 🪙\n"
        f"⚡ +10   ✨ +50 XP"
        + (f"\n💎 <b>+{gems}</b>" if gems else "") + f"{surprise}</blockquote>\n"
        f"{i18n.t(lang, 'd_streak', n=streak)}\n\n"
        f"{i18n.t(lang, 'd_note')}"
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
        f"🏦 <b>BANKA</b>\n{ui.LINE}\n"
        f"<blockquote>🪙 Cüzdan: <b>{ui.fmt(user['coins'])}</b>\n"
        f"🏦 Kasa: <b>{ui.fmt(user['bank'])}</b>\n"
        f"📦 Kasa limiti: {ui.fmt(bank_limit(user))}</blockquote>\n"
        f"📈 Her gün <b>%{int(config.BANK_INTEREST * 100)}</b> faiz işler\n"
        "🛡 Bankadaki paraya <b>kimse dokunamaz</b> (soygundan korunur)\n\n"
        "<i>Kasa limiti seviyen arttıkça büyür.</i>"
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

def _plain(text: str) -> str:
    for tag in ("<b>", "</b>", "<i>", "</i>", "<blockquote>", "</blockquote>"):
        text = text.replace(tag, "")
    return text


ROLE_ICON = {"lider": "👑", "yonetici": "⭐", "uye": "•"}
ROLE_NAME = {"lider": "Lider", "yonetici": "Yönetici", "uye": "Üye"}
EMBLEMS = ["🏰", "🐉", "⚔️", "🦅", "🐺", "🔥", "⭐", "💎", "👑", "🛡", "🌙", "☠️"]
CLAN_PAGE = 8


def clan_of(user_id: int):
    user = db.get_user(user_id)
    if not user or not user["clan_id"]:
        return None
    return db.one("SELECT * FROM clans WHERE id=?", (user["clan_id"],))


def my_role(user_id: int) -> str:
    row = db.one("SELECT role FROM clan_members WHERE user_id=?", (user_id,))
    return row["role"] if row else ""


def can_manage(user_id: int) -> bool:
    return my_role(user_id) in ("lider", "yonetici")


def member_count(clan_id: int) -> int:
    return int(db.scalar("SELECT COUNT(*) FROM clan_members WHERE clan_id=?", (clan_id,)))


def member_limit(clan) -> int:
    return 20 + clan["level"] * 2


def clan_perks(clan) -> str:
    return (f"💰 Kazanç bonusu: <b>+%{min(20, clan['level'] * 2)}</b>\n"
            f"👥 Üye kontenjanı: <b>{member_limit(clan)}</b>")


# ---------------------------------------------------------------------------
# KLAN — ANA EKRAN
# ---------------------------------------------------------------------------

def clan_text(user_id: int) -> str:
    clan = clan_of(user_id)
    if not clan:
        return ("🏰 <b>KLANLAR</b>\n" + ui.LINE + "\n"
                "<blockquote>Klan = takım. Üyeler her kazançta bonus alır, "
                "birlikte kasa büyütür, sıralamada yarışır.</blockquote>\n"
                f"💰 Klan kurma bedeli: <b>{ui.fmt(CLAN_COST)}</b> 🪙  (Seviye 8)\n\n"
                "Aşağıdan bir klana katıl ya da kendi klanını kur 👇")
    role = my_role(user_id)
    reqs = int(db.scalar("SELECT COUNT(*) FROM clan_requests WHERE clan_id=?", (clan["id"],)))
    top_rank = int(db.scalar(
        "SELECT COUNT(*)+1 FROM clans WHERE level > ? OR (level = ? AND treasury > ?)",
        (clan["level"], clan["level"], clan["treasury"])))
    lines = [
        f"{clan['emblem']} <b>{ui.esc(clan['name'])}</b>",
        f"<i>{ui.esc(clan['motto'] or 'Şeref ve altın!')}</i>",
        ui.LINE,
        f"<blockquote>🎚 Seviye <b>{clan['level']}</b>   🏆 Sıra <b>#{top_rank}</b>\n"
        f"{ui.bar(clan['xp'], 5000 * clan['level'], 12)}\n"
        f"{ui.fmt(clan['xp'])} / {ui.fmt(5000 * clan['level'])} klan XP</blockquote>",
        f"<blockquote>💰 Kasa: <b>{ui.fmt(clan['treasury'])}</b> 🪙\n"
        f"👥 Üye: <b>{member_count(clan['id'])}</b> / {member_limit(clan)}\n"
        f"🚪 Katılım: <b>{'herkese açık' if clan['open_join'] else 'istekle'}</b>"
        + (f"  (min Sv.{clan['min_level']})" if clan["min_level"] > 1 else "") + "</blockquote>",
        clan_perks(clan),
        f"\n{ROLE_ICON.get(role, '•')} Senin rolün: <b>{ROLE_NAME.get(role, 'Üye')}</b>",
    ]
    if reqs and can_manage(user_id):
        lines.append(f"\n🔔 <b>{reqs} katılma isteği bekliyor!</b>")
    return "\n".join(lines)


def clan_kb(user_id: int):
    clan = clan_of(user_id)
    if not clan:
        return ui.kb([
            [("📋 Klan Listesi", "s:clist:0")],
            [("➕ Klan Kur", "s:ccreate")],
            [("🏆 Klan Sıralaması", "s:top:clan")],
            [("🏠 Ana menü", "m:main")],
        ])
    rows = [[("💰 Kasaya Bağış", "s:cdonate"), ("👥 Üyeler", "s:cmem:0")]]
    if can_manage(user_id):
        reqs = int(db.scalar("SELECT COUNT(*) FROM clan_requests WHERE clan_id=?", (clan["id"],)))
        rows.append([(f"🔔 Katılma İstekleri{f'  ({reqs})' if reqs else ''}", "s:creqs")])
    if my_role(user_id) == "lider":
        rows.append([("⚙️ Klan Ayarları", "s:cset")])
    rows.append([("🏆 Klan Sıralaması", "s:top:clan")])
    rows.append([("🚪 Klandan Ayrıl", "s:cleave"), ("🏠 Ana menü", "m:main")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# KLAN LİSTESİ / KATILMA
# ---------------------------------------------------------------------------

def clan_list_text(page: int = 0) -> str:
    rows = db.all_("SELECT * FROM clans ORDER BY level DESC, treasury DESC "
                   f"LIMIT {CLAN_PAGE} OFFSET {page * CLAN_PAGE}")
    total = int(db.scalar("SELECT COUNT(*) FROM clans"))
    lines = [f"📋 <b>KLAN LİSTESİ</b>\n{ui.LINE}",
             f"<i>Toplam {total} klan. Açık olana direkt katılırsın, "
             f"kapalı olana istek gönderirsin.</i>\n"]
    for clan in rows:
        lines.append(
            f"{clan['emblem']} <b>{ui.esc(clan['name'])}</b>  Sv.{clan['level']}\n"
            f"<blockquote>👥 {member_count(clan['id'])}/{member_limit(clan)}   "
            f"💰 {ui.fmt(clan['treasury'])} 🪙\n"
            f"{'🔓 Herkese açık' if clan['open_join'] else '🔒 İstekle'}"
            + (f"  •  min Sv.{clan['min_level']}" if clan["min_level"] > 1 else "")
            + "</blockquote>")
    if not rows:
        lines.append("Henüz klan yok — ilkini sen kur! 👑")
    return "\n".join(lines)


def clan_list_kb(user_id: int, page: int = 0):
    rows_db = db.all_("SELECT * FROM clans ORDER BY level DESC, treasury DESC "
                      f"LIMIT {CLAN_PAGE} OFFSET {page * CLAN_PAGE}")
    total = int(db.scalar("SELECT COUNT(*) FROM clans"))
    rows = []
    for clan in rows_db:
        pending = db.one("SELECT 1 FROM clan_requests WHERE clan_id=? AND user_id=?",
                         (clan["id"], user_id))
        if pending:
            rows.append([(f"⏳ {clan['name'][:16]} — istek gönderildi", f"s:ccancel:{clan['id']}")])
        elif clan["open_join"]:
            rows.append([(f"🔓 {clan['emblem']} {clan['name'][:16]} — Katıl", f"s:cjoin:{clan['id']}")])
        else:
            rows.append([(f"🔒 {clan['emblem']} {clan['name'][:16]} — İstek gönder",
                          f"s:cjoin:{clan['id']}")])
    nav = []
    if page > 0:
        nav.append(("⬅️", f"s:clist:{page - 1}"))
    if (page + 1) * CLAN_PAGE < total:
        nav.append(("➡️", f"s:clist:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("➕ Klan Kur", "s:ccreate"), ("⬅️ Geri", "s:clan")])
    return ui.kb(rows)


def clan_join(user_id: int, clan_id: int) -> str:
    user = db.get_user(user_id)
    if user["clan_id"]:
        return "Zaten bir klandasın. Önce ayrılman gerekir."
    clan = db.one("SELECT * FROM clans WHERE id=?", (clan_id,))
    if not clan:
        return "Klan bulunamadı."
    if user["level"] < clan["min_level"]:
        return f"🔒 Bu klan en az Seviye {clan['min_level']} istiyor (sen Sv.{user['level']})."
    if member_count(clan_id) >= member_limit(clan):
        return "👥 Klan kontenjanı dolu."
    if not clan["open_join"]:
        db.run("INSERT OR IGNORE INTO clan_requests (clan_id, user_id, ts) VALUES (?,?,?)",
               (clan_id, user_id, ui.now()))
        return f"📨 <b>{ui.esc(clan['name'])}</b> klanına katılma isteğin gönderildi.\nLider onaylayınca gireceksin."
    db.run("INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_ts) "
           "VALUES (?,?, 'uye', ?)", (clan_id, user_id, ui.now()))
    db.upd(user_id, clan_id=clan_id)
    db.run("DELETE FROM clan_requests WHERE user_id=?", (user_id,))
    return f"🏰 <b>{ui.esc(clan['name'])}</b> klanına katıldın!"


def clan_cancel_request(user_id: int, clan_id: int) -> str:
    db.run("DELETE FROM clan_requests WHERE clan_id=? AND user_id=?", (clan_id, user_id))
    return "🚫 İstek geri çekildi."


# ---------------------------------------------------------------------------
# İSTEKLER (lider/yönetici)
# ---------------------------------------------------------------------------

def requests_text(user_id: int) -> str:
    clan = clan_of(user_id)
    if not clan:
        return "Klanda değilsin."
    rows = db.all_("SELECT r.*, u.first_name, u.level, u.games FROM clan_requests r "
                   "JOIN users u ON u.user_id=r.user_id WHERE r.clan_id=? ORDER BY r.ts",
                   (clan["id"],))
    lines = [f"🔔 <b>KATILMA İSTEKLERİ</b>\n{ui.LINE}"]
    if not rows:
        lines.append("Bekleyen istek yok 👌\n\n"
                     "<i>Klan ayarlarından katılımı 'herkese açık' yaparsan "
                     "istek beklemeden girerler.</i>")
    for row in rows:
        lines.append(f"👤 <b>{ui.esc(row['first_name'])}</b>\n"
                     f"<blockquote>🎚 Seviye {row['level']}  •  🎮 {ui.fmt(row['games'])} oyun</blockquote>")
    return "\n".join(lines)


def requests_kb(user_id: int):
    clan = clan_of(user_id)
    rows = []
    if clan:
        for row in db.all_("SELECT r.*, u.first_name FROM clan_requests r "
                           "JOIN users u ON u.user_id=r.user_id WHERE r.clan_id=? LIMIT 10",
                           (clan["id"],)):
            rows.append([(f"✅ {row['first_name'][:12]}", f"s:cok:{row['user_id']}"),
                         ("❌", f"s:cno:{row['user_id']}")])
    rows.append([("🔄 Yenile", "s:creqs"), ("⬅️ Geri", "s:clan")])
    return ui.kb(rows)


def approve_request(leader_id: int, target_id: int, ok: bool) -> str:
    clan = clan_of(leader_id)
    if not clan or not can_manage(leader_id):
        return "Yetkin yok."
    if not db.one("SELECT 1 FROM clan_requests WHERE clan_id=? AND user_id=?",
                  (clan["id"], target_id)):
        return "Bu istek artık yok."
    db.run("DELETE FROM clan_requests WHERE clan_id=? AND user_id=?", (clan["id"], target_id))
    target = db.get_user(target_id)
    if not ok:
        return f"❌ {ui.name_of(target)} reddedildi."
    if target["clan_id"]:
        return "Bu oyuncu başka bir klana girmiş."
    if member_count(clan["id"]) >= member_limit(clan):
        return "👥 Kontenjan dolu, önce klanı büyüt."
    db.run("INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_ts) "
           "VALUES (?,?, 'uye', ?)", (clan["id"], target_id, ui.now()))
    db.upd(target_id, clan_id=clan["id"])
    return f"✅ {ui.name_of(target)} klana alındı!"


# ---------------------------------------------------------------------------
# ÜYELER
# ---------------------------------------------------------------------------

def members_text(user_id: int, page: int = 0) -> str:
    clan = clan_of(user_id)
    if not clan:
        return "Klanda değilsin."
    rows = db.all_(
        "SELECT m.*, u.first_name, u.level, u.pvp_wins FROM clan_members m "
        "JOIN users u ON u.user_id=m.user_id WHERE m.clan_id=? "
        "ORDER BY CASE m.role WHEN 'lider' THEN 0 WHEN 'yonetici' THEN 1 ELSE 2 END, "
        f"m.contributed DESC LIMIT {CLAN_PAGE} OFFSET {page * CLAN_PAGE}", (clan["id"],))
    lines = [f"👥 <b>{clan['emblem']} {ui.esc(clan['name'])} ÜYELERİ</b>\n{ui.LINE}",
             f"<i>{member_count(clan['id'])}/{member_limit(clan)} üye</i>\n"]
    for row in rows:
        lines.append(
            f"{ROLE_ICON.get(row['role'], '•')} <b>{ui.esc(row['first_name'])}</b> "
            f"({ROLE_NAME.get(row['role'], 'Üye')})\n"
            f"<blockquote>🎚 Sv.{row['level']}  •  ⚔️ {row['pvp_wins']}G  •  "
            f"💰 bağış {ui.fmt(row['contributed'])} 🪙</blockquote>")
    return "\n".join(lines)


def members_kb(user_id: int, page: int = 0):
    clan = clan_of(user_id)
    rows = []
    if clan and can_manage(user_id):
        for row in db.all_(
                "SELECT m.*, u.first_name FROM clan_members m JOIN users u ON u.user_id=m.user_id "
                f"WHERE m.clan_id=? AND m.user_id<>? LIMIT {CLAN_PAGE} OFFSET {page * CLAN_PAGE}",
                (clan["id"], user_id)):
            rows.append([(f"⚙️ {row['first_name'][:14]}", f"s:cm:{row['user_id']}")])
    total = member_count(clan["id"]) if clan else 0
    nav = []
    if page > 0:
        nav.append(("⬅️", f"s:cmem:{page - 1}"))
    if (page + 1) * CLAN_PAGE < total:
        nav.append(("➡️", f"s:cmem:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("⬅️ Geri", "s:clan")])
    return ui.kb(rows)


def member_card(leader_id: int, target_id: int):
    clan = clan_of(leader_id)
    target = db.get_user(target_id)
    row = db.one("SELECT * FROM clan_members WHERE user_id=?", (target_id,))
    if not clan or not row or not target:
        return "Üye bulunamadı.", ui.kb([[("⬅️ Geri", "s:cmem:0")]])
    text = (f"👤 <b>{ui.name_of(target)}</b>  {ROLE_ICON.get(row['role'], '•')}\n{ui.LINE}\n"
            f"<blockquote>🎚 Seviye {target['level']}\n"
            f"⚔️ {target['pvp_wins']} düello galibiyeti\n"
            f"💰 Klana bağışı: {ui.fmt(row['contributed'])} 🪙\n"
            f"🎖 Rol: {ROLE_NAME.get(row['role'], 'Üye')}</blockquote>")
    rows = []
    if my_role(leader_id) == "lider" and row["role"] != "lider":
        if row["role"] == "uye":
            rows.append([("⭐ Yönetici yap", f"s:cprom:{target_id}")])
        else:
            rows.append([("⬇️ Üyeliğe düşür", f"s:cdem:{target_id}")])
        rows.append([("👑 Liderliği devret", f"s:cgive:{target_id}")])
    if can_manage(leader_id) and row["role"] != "lider":
        rows.append([("🚪 Klandan at", f"s:ckick:{target_id}")])
    rows.append([("⬅️ Üyeler", "s:cmem:0")])
    return text, ui.kb(rows)


def member_action(leader_id: int, target_id: int, action: str) -> str:
    clan = clan_of(leader_id)
    row = db.one("SELECT * FROM clan_members WHERE user_id=?", (target_id,))
    if not clan or not row or row["clan_id"] != clan["id"]:
        return "Üye bulunamadı."
    if row["role"] == "lider":
        return "Lidere işlem yapılamaz."
    if action == "kick":
        if not can_manage(leader_id):
            return "Yetkin yok."
        db.run("DELETE FROM clan_members WHERE user_id=?", (target_id,))
        db.upd(target_id, clan_id=0)
        return f"🚪 {ui.name_of(db.get_user(target_id))} klandan çıkarıldı."
    if my_role(leader_id) != "lider":
        return "Bunu sadece lider yapabilir."
    if action == "prom":
        db.run("UPDATE clan_members SET role='yonetici' WHERE user_id=?", (target_id,))
        return f"⭐ {ui.name_of(db.get_user(target_id))} yönetici yapıldı."
    if action == "dem":
        db.run("UPDATE clan_members SET role='uye' WHERE user_id=?", (target_id,))
        return f"⬇️ {ui.name_of(db.get_user(target_id))} üyeliğe düşürüldü."
    if action == "give":
        db.run("UPDATE clan_members SET role='uye' WHERE user_id=?", (leader_id,))
        db.run("UPDATE clan_members SET role='lider' WHERE user_id=?", (target_id,))
        db.run("UPDATE clans SET owner_id=? WHERE id=?", (target_id, clan["id"]))
        return f"👑 Liderlik {ui.name_of(db.get_user(target_id))} kişisine devredildi."
    return "?"


# ---------------------------------------------------------------------------
# AYARLAR (lider)
# ---------------------------------------------------------------------------

def settings_text(user_id: int) -> str:
    clan = clan_of(user_id)
    if not clan:
        return "Klanda değilsin."
    return (f"⚙️ <b>KLAN AYARLARI</b>\n{ui.LINE}\n"
            f"{clan['emblem']} <b>{ui.esc(clan['name'])}</b>\n"
            f"<blockquote>🚪 Katılım: <b>{'herkese açık' if clan['open_join'] else 'istekle'}</b>\n"
            f"🎚 En az seviye: <b>{clan['min_level']}</b>\n"
            f"🏳 Amblem: <b>{clan['emblem']}</b>\n"
            f"💬 Slogan: <i>{ui.esc(clan['motto'] or '—')}</i></blockquote>\n"
            "<i>Katılım 'istekle' olursa gelenleri sen onaylarsın.</i>")


def settings_kb(user_id: int):
    clan = clan_of(user_id)
    if not clan:
        return ui.kb([[("⬅️ Geri", "s:clan")]])
    rows = [
        [("🔓 Herkese açık" if not clan["open_join"] else "🔒 İstekle yap", "s:copen")],
        [("🎚 Seviye şartı", "s:cminlvl")],
        [("🏳 Amblem değiştir", "s:cemblem")],
        [("💬 Slogan yaz", "s:cmotto")],
        [("⬅️ Geri", "s:clan")],
    ]
    return ui.kb(rows)


def emblem_kb():
    rows, line = [], []
    for emoji in EMBLEMS:
        line.append((emoji, f"s:cem:{emoji}"))
        if len(line) == 4:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append([("⬅️ Geri", "s:cset")])
    return ui.kb(rows)


def minlevel_kb():
    rows = [[(f"Sv.{lv}+", f"s:cminlv:{lv}") for lv in (1, 5, 10)],
            [(f"Sv.{lv}+", f"s:cminlv:{lv}") for lv in (15, 20, 30)],
            [("⬅️ Geri", "s:cset")]]
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# KURMA / AYRILMA / BAĞIŞ
# ---------------------------------------------------------------------------

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
        return i18n.t(i18n.lang_of(user_id), "no_money", need=ui.fmt(CLAN_COST),
                      have=ui.fmt(user["coins"]))
    cur = db.run("INSERT INTO clans (name, owner_id, treasury, created_ts) VALUES (?,?,0,?)",
                 (name, user_id, ui.now()))
    clan_id = int(cur.lastrowid)
    db.run("INSERT OR REPLACE INTO clan_members (clan_id, user_id, role, joined_ts) "
           "VALUES (?,?, 'lider', ?)", (clan_id, user_id, ui.now()))
    db.upd(user_id, clan_id=clan_id)
    db.run("DELETE FROM clan_requests WHERE user_id=?", (user_id,))
    return (f"🏰 <b>{ui.esc(name)}</b> klanı kuruldu, sen lidersin! 👑\n"
            "Ayarlardan amblem ve katılım şeklini seçebilirsin.")


def clan_leave(user_id: int) -> str:
    clan = clan_of(user_id)
    if not clan:
        return "Bir klanda değilsin."
    role = my_role(user_id)
    others = member_count(clan["id"]) - 1
    if role == "lider" and others > 0:
        return ("👑 Lider ayrılamaz!\nÖnce üyeler ekranından birine liderliği devret "
                "ya da tüm üyeleri çıkar.")
    db.run("DELETE FROM clan_members WHERE user_id=?", (user_id,))
    db.upd(user_id, clan_id=0)
    if others <= 0:
        db.run("DELETE FROM clans WHERE id=?", (clan["id"],))
        db.run("DELETE FROM clan_requests WHERE clan_id=?", (clan["id"],))
        return "🚪 Klandan ayrıldın. Son üye sen olduğun için klan kapandı."
    return "🚪 Klandan ayrıldın."


DONATE_AMOUNTS = [1_000, 10_000, 100_000, 1_000_000]


def donate_kb(user_id: int):
    rows = [[(f"💰 {ui.fmt(a)} 🪙", f"s:cdon:{a}")] for a in DONATE_AMOUNTS]
    rows.append([("🔥 Hepsini bağışla", "s:cdon:all")])
    rows.append([("⬅️ Geri", "s:clan")])
    return ui.kb(rows)


def clan_donate(user_id: int, amount) -> str:
    clan = clan_of(user_id)
    if not clan:
        return "Bir klanda değilsin."
    user = db.get_user(user_id)
    amount = user["coins"] if amount == "all" else int(amount)
    if amount < 1_000:
        return "En az 1.000 altın bağışlanabilir."
    if not economy.take_coins(user_id, amount, "klan bağışı"):
        return i18n.t(i18n.lang_of(user_id), "no_money", need=ui.fmt(amount),
                      have=ui.fmt(user["coins"]))
    db.run("UPDATE clans SET treasury=treasury+? WHERE id=?", (amount, clan["id"]))
    db.run("UPDATE clan_members SET contributed=contributed+? WHERE user_id=?", (amount, user_id))
    before = clan["level"]
    economy.clan_add_xp(clan["id"], amount // 100)
    economy.add_xp(user_id, amount // 500)
    after = db.one("SELECT level FROM clans WHERE id=?", (clan["id"],))["level"]
    extra = f"\n\n🎉 <b>KLAN SEVİYE ATLADI: {after}!</b>" if after > before else ""
    return (f"💰 Klan kasasına <b>{ui.fmt(amount)}</b> 🪙 bağışladın!\n"
            f"✨ Klan XP +{ui.fmt(amount // 100)}{extra}")


# ---------------------------------------------------------------------------
# SIRALAMALAR
# ---------------------------------------------------------------------------
# NOT: yetkililer (admin/destek) sıralamalarda görünmez.
TOPS = {
    "rich":  ("💰 En Zenginler", "coins+bank", "🪙"),
    "level": ("🎚 En Yüksek Seviye", "level", "sv"),
    "pvp":   ("⚔️ PVP Kralları", "pvp_wins", "galibiyet"),
    "win":   ("💥 En Büyük Vuruş", "biggest_win", "🪙"),
    "games": ("🎮 En Çok Oynayan", "games", "oyun"),
    "boss":  ("🐉 Canavar Avcıları", "boss_kills", "vuruş"),
}


def top_text(kind: str = "rich") -> str:
    if kind == "clan":
        rows = db.all_("SELECT * FROM clans ORDER BY level DESC, treasury DESC LIMIT 10")
        lines = ["🏆 <b>KLAN SIRALAMASI</b>\n"]
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        for i, row in enumerate(rows):
            lines.append(f"{medals[i]} {row['emblem']} <b>{ui.esc(row['name'])}</b> — "
                         f"Sv.{row['level']} • {ui.fmt(row['treasury'])} 🪙 • "
                         f"{member_count(row['id'])} üye")
        if not rows:
            lines.append("Henüz klan yok.")
        return "\n".join(lines)
    title, column, unit = TOPS.get(kind, TOPS["rich"])
    hidden = db.hidden_ids()
    marks = ",".join("?" * len(hidden)) if hidden else "0"
    rows = db.all_(
        f"SELECT first_name, {column} AS v FROM users "
        f"WHERE banned=0 AND user_id NOT IN ({marks}) ORDER BY v DESC LIMIT 10",
        hidden)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"🏆 <b>{title.upper()}</b>\n{ui.LINE}"]
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
        f"<blockquote>Her davet için:\n"
        f"• Sen: <b>+{ui.fmt(config.REF_REWARD_COINS)} 🪙</b>\n"
        f"• Arkadaşın: <b>+{ui.fmt(config.REF_REWARD_NEW)} 🪙</b></blockquote>\n"
        "<i>Arkadaşın bot korumasını ilk denemede geçerse tam ödül, "
        "2-3. denemede geçerse yarım ödül alırsın.</i>\n",
        f"🔗 Davet linkin:\n<code>{ui.esc(link)}</code>\n",
        f"📊 Davet ettiğin: <b>{user['refs']}</b> kişi",
    ]
    if invited:
        lines.append("\n<b>Davet ettiklerin</b>")
        for row in invited:
            lines.append(f"• {ui.esc(row['first_name'])} (Sv.{row['level']})")
    lines.append("\n<i>Arkadaşlarınla grup kurup düello yapın, birlikte boss avlayın!</i>")
    return "\n".join(lines)


def grant_referral(new_user_id: int, referrer_id: int, factor: float = 1.0) -> None:
    """Davet ödülü. factor: bot koruması 1. denemede geçildiyse 1.0, 2-3. denemede 0.5."""
    if not referrer_id or referrer_id == new_user_id:
        return
    ref = db.get_user(referrer_id)
    if not ref:
        return
    db.bump(referrer_id, refs=1)
    reward = int(config.REF_REWARD_COINS * factor)
    if reward > 0:
        economy.add_coins(referrer_id, reward, "davet ödülü")
    economy.add_coins(new_user_id, config.REF_REWARD_NEW, "davet bonusu")
    db.log_action(referrer_id, "referral", f"{new_user_id} x{factor}")


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
    TOASTS = {"profile": "👤 Hesabın", "daily": "🎁 Günlük hediye", "hourly": "⏰ Saatlik bonus",
              "bank": "🏦 Banka", "top": "🏆 Sıralama", "clan": "🏰 Klan",
              "ref": "👥 Davet linkin", "help": "❓ Yardım", "earn": "💸 Kazanma yolları",
              "ccreate": "🏰 Klan adı yaz", "cdonate": "💰 Miktar yaz"}
    context.user_data["_toast"] = TOASTS.get(action, "")
    user = db.get_user(user_id)
    if user is None:
        await ui.safe_edit(query, "Önce botu yeniden başlat (/start).")
        return

    if action == "profile":
        await ui.safe_edit(query, profile_text(user_id), profile_kb())
    elif action == "daily":
        msg = daily(user_id)
        unlocked = events.check_achievements(user_id)
        if unlocked:
            msg += "\n\n🏅 <b>YENİ BAŞARIM!</b>\n" + "\n".join(unlocked)
        lang = i18n.lang_of(user_id)
        await ui.nav(query, "daily", msg, ui.kb([
            [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_money"), "cash:menu")],
            [(i18n.t(lang, "b_home"), "m:main")]]))
    elif action == "hourly":
        await ui.safe_edit(query, hourly(user_id), ui.kb([
            [("🎁 Günlük Ödül", "s:daily")], [("🏠 Menü", "m:main")]]))
    elif action == "bank":
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "dep":
        await ui.answer(query, deposit(user_id, parts[2]), alert=True)
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "wd":
        await ui.answer(query, withdraw(user_id, parts[2]), alert=True)
        await ui.safe_edit(query, bank_text(user_id), bank_kb())
    elif action == "top":
        kind = parts[2] if len(parts) > 2 else "rich"
        await ui.safe_edit(query, top_text(kind), top_kb())
    elif action == "clan":
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "clist":
        page = int(parts[2]) if len(parts) > 2 else 0
        await ui.safe_edit(query, clan_list_text(page), clan_list_kb(user_id, page))
    elif action == "ccreate":
        context.user_data["await"] = {"kind": "clan_name"}
        await ui.safe_edit(query, (
            f"🏰 <b>KLAN KUR</b>\n{ui.LINE}\n"
            f"<blockquote>💰 Bedel: <b>{ui.fmt(CLAN_COST)}</b> 🪙\n"
            f"🎚 Seviye 8 gerekli</blockquote>\n"
            "Klan adını yaz (3-24 karakter) 👇"
        ), ui.kb([[("⬅️ Vazgeç", "s:clan")]]))
    elif action == "cjoin":
        await ui.answer(query, _plain(clan_join(user_id, int(parts[2]))), alert=True)
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "ccancel":
        await ui.answer(query, clan_cancel_request(user_id, int(parts[2])))
        await ui.safe_edit(query, clan_list_text(0), clan_list_kb(user_id, 0))
    elif action == "cleave":
        await ui.answer(query, _plain(clan_leave(user_id)), alert=True)
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "cdonate":
        await ui.safe_edit(query, (
            f"💰 <b>KLAN KASASINA BAĞIŞ</b>\n{ui.LINE}\n"
            f"{ui.header(user)}\n"
            "<blockquote>Bağış klan XP'si kazandırır, klan seviyesi yükselir,\n"
            "<b>bütün üyeler</b> daha çok kazanır.</blockquote>\n"
            "Ne kadar bağışlıyorsun? 👇"
        ), donate_kb(user_id))
    elif action == "cdon":
        amount = parts[2]
        await ui.answer(query, _plain(clan_donate(user_id, amount)), alert=True)
        await ui.safe_edit(query, clan_text(user_id), clan_kb(user_id))
    elif action == "creqs":
        await ui.safe_edit(query, requests_text(user_id), requests_kb(user_id))
    elif action in ("cok", "cno"):
        msg = approve_request(user_id, int(parts[2]), action == "cok")
        await ui.answer(query, _plain(msg), alert=True)
        if action == "cok":
            try:
                clan = clan_of(user_id)
                await context.bot.send_message(
                    int(parts[2]), f"🏰 <b>{ui.esc(clan['name'])}</b> klanına kabul edildin!",
                    parse_mode=ParseMode.HTML,
                    reply_markup=ui.kb([[("🏰 Klanım", "s:clan")]]))
            except Exception:
                pass
        await ui.safe_edit(query, requests_text(user_id), requests_kb(user_id))
    elif action == "cmem":
        page = int(parts[2]) if len(parts) > 2 else 0
        await ui.safe_edit(query, members_text(user_id, page), members_kb(user_id, page))
    elif action == "cm":
        text, kb = member_card(user_id, int(parts[2]))
        await ui.safe_edit(query, text, kb)
    elif action in ("ckick", "cprom", "cdem", "cgive"):
        act = {"ckick": "kick", "cprom": "prom", "cdem": "dem", "cgive": "give"}[action]
        await ui.answer(query, _plain(member_action(user_id, int(parts[2]), act)), alert=True)
        await ui.safe_edit(query, members_text(user_id), members_kb(user_id))
    elif action == "cset":
        if my_role(user_id) != "lider":
            await ui.answer(query, "⛔ Bunu sadece klan lideri yapabilir.", alert=True)
            return
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "copen":
        clan = clan_of(user_id)
        if clan and my_role(user_id) == "lider":
            new_val = 0 if clan["open_join"] else 1
            db.run("UPDATE clans SET open_join=? WHERE id=?", (new_val, clan["id"]))
            await ui.answer(query, "🔓 Katılım herkese açık." if new_val
                            else "🔒 Katılım artık istekle. İstekleri sen onaylayacaksın.",
                            alert=True)
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "cminlvl":
        await ui.safe_edit(query, (
            f"🎚 <b>SEVİYE ŞARTI</b>\n{ui.LINE}\n"
            "Klana girebilmek için en az kaçıncı seviye gerekli olsun?"
        ), minlevel_kb())
    elif action == "cminlv":
        clan = clan_of(user_id)
        if clan and my_role(user_id) == "lider":
            db.run("UPDATE clans SET min_level=? WHERE id=?", (int(parts[2]), clan["id"]))
            await ui.answer(query, f"✅ Artık en az Seviye {parts[2]} gerekiyor.", alert=True)
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "cemblem":
        await ui.safe_edit(query, (
            f"🏳 <b>AMBLEM SEÇ</b>\n{ui.LINE}\nKlanının simgesi listelerde görünür."
        ), emblem_kb())
    elif action == "cem":
        clan = clan_of(user_id)
        if clan and my_role(user_id) == "lider":
            db.run("UPDATE clans SET emblem=? WHERE id=?", (parts[2], clan["id"]))
            await ui.answer(query, f"✅ Amblem: {parts[2]}")
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "cmotto":
        context.user_data["await"] = {"kind": "clan_motto"}
        await ui.safe_edit(query, (
            f"💬 <b>KLAN SLOGANI</b>\n{ui.LINE}\n"
            "Klanının sloganını yaz (en fazla 60 karakter) 👇"
        ), ui.kb([[("⬅️ Vazgeç", "s:cset")]]))
    elif action == "ref":
        await ui.safe_edit(query, ref_text(user_id), ui.back_kb("m:main"))
    elif action == "help":
        lang = i18n.lang_of(user_id)
        await ui.nav(query, "help", help_text(lang), ui.kb([
            [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_money"), "cash:menu")],
            [(i18n.t(lang, "b_home"), "m:main")]]))
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
    if kind == "clan_motto":
        context.user_data.pop("await", None)
        clan = clan_of(user_id)
        if clan and my_role(user_id) == "lider":
            db.run("UPDATE clans SET motto=? WHERE id=?", (text[:60], clan["id"]))
            await ui.send(update, "✅ Slogan kaydedildi.", ui.kb([[("🏰 Klan", "s:clan")]]))
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
    lang = i18n.lang_of(update.effective_user.id)
    await ui.screen(update, "daily", daily(update.effective_user.id), ui.kb([
        [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_money"), "cash:menu")]]))


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


def help_text(lang: str) -> str:
    return f"{i18n.t(lang, 'h_title')}\n{ui.LINE}\n{i18n.t(lang, 'h_body')}"


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = i18n.lang_of(update.effective_user.id)
    await ui.screen(update, "help", help_text(lang), ui.kb([
        [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_money"), "cash:menu")],
        [(i18n.t(lang, "b_home"), "m:main")]]))
