# -*- coding: utf-8 -*-
"""Etkinlikler: günlük görevler, başarımlar, dünya bossu ve piyango."""
import asyncio
import datetime as dt
import logging
import random
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import items
import ui

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# GÖREVLER
# ----------------------------------------------------------------------------
QUEST_POOL = [
    ("play", "🎮 {t} oyun oyna", (5, 12), 2_500),
    ("win", "🏅 {t} oyun kazan", (3, 6), 3_500),
    ("wager", "💰 Toplam {t} altın bahis yap", (5_000, 25_000), 3_000),
    ("pvp", "⚔️ {t} PVP düellosu kazan", (1, 3), 5_000),
    ("boss", "🐉 Boss'a {t} kez saldır", (2, 5), 4_000),
    ("work", "💼 {t} kez çalış", (2, 4), 2_000),
    ("mine", "⛏ {t} kez maden kaz", (2, 4), 2_000),
    ("skill", "🧠 {t} beceri oyunu kazan", (2, 5), 3_000),
    ("buy", "🏪 Markete {t} kez uğra (alışveriş)", (1, 2), 2_500),
    ("upgrade", "🔨 {t} kez eşya yükseltmeyi dene", (1, 3), 3_000),
    ("arena", "🗡 Arena'da {t} yaratık avla", (3, 6), 3_500),
]
QUEST_BY_KEY = {q[0]: q for q in QUEST_POOL}


def today() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def daily_quests(user_id: int) -> list[dict]:
    """Bugünün görevlerini döner, yoksa deterministik olarak üretir."""
    day = today()
    rows = db.all_("SELECT * FROM quests WHERE user_id=? AND day=?", (user_id, day))
    if not rows:
        rnd = random.Random(f"{user_id}-{day}")
        chosen = rnd.sample(QUEST_POOL, 3)
        for key, _tpl, rng, _reward in chosen:
            target = rnd.randint(*rng)
            if key == "wager":
                target = round(target, -3)
            db.run(
                "INSERT OR IGNORE INTO quests (user_id, day, qkey, progress, target) VALUES (?,?,?,?,?)",
                (user_id, day, key, 0, target),
            )
        rows = db.all_("SELECT * FROM quests WHERE user_id=? AND day=?", (user_id, day))
    out = []
    for row in rows:
        spec = QUEST_BY_KEY.get(row["qkey"])
        if not spec:
            continue
        reward = int(spec[3] * (1 + row["target"] / max(1, spec[2][1])))
        out.append({
            "key": row["qkey"],
            "text": spec[1].format(t=ui.fmt(row["target"])),
            "progress": min(row["progress"], row["target"]),
            "target": row["target"],
            "claimed": row["claimed"],
            "reward": reward,
        })
    return out


def track(user_id: int, key: str, amount: int = 1) -> None:
    """Görev ilerlemesi kaydeder (sessiz)."""
    try:
        daily_quests(user_id)
        db.run(
            "UPDATE quests SET progress=progress+? WHERE user_id=? AND day=? AND qkey=? AND claimed=0",
            (amount, user_id, today(), key),
        )
    except Exception as exc:  # görev takibi asla oyunu bozmamalı
        log.warning("görev takibi hatası: %s", exc)


def claim_quests(user_id: int) -> tuple[int, int]:
    """Tamamlanmış görevlerin ödülünü verir. (altın, adet)"""
    total = 0
    count = 0
    for quest in daily_quests(user_id):
        if quest["claimed"] or quest["progress"] < quest["target"]:
            continue
        db.run(
            "UPDATE quests SET claimed=1 WHERE user_id=? AND day=? AND qkey=?",
            (user_id, today(), quest["key"]),
        )
        total += quest["reward"]
        count += 1
    if total:
        economy.add_coins(user_id, total, "görev ödülü")
        economy.add_xp(user_id, 40 * count)
        if count >= 3:
            economy.add_gems(user_id, 2, "tüm görevler")
    return total, count


# ----------------------------------------------------------------------------
# BAŞARIMLAR
# ----------------------------------------------------------------------------
ACHIEVEMENTS = [
    ("first_win", "🥇 İlk Zafer", lambda u: u["wins"] >= 1, 1_000, 0),
    ("gambler", "🎰 Kumarbaz", lambda u: u["games"] >= 100, 10_000, 1),
    ("addict", "🕹 Oyun Bağımlısı", lambda u: u["games"] >= 1000, 100_000, 5),
    ("rich1", "💰 İlk Servet", lambda u: u["coins"] + u["bank"] >= 100_000, 5_000, 1),
    ("rich2", "🏦 Milyoner", lambda u: u["coins"] + u["bank"] >= 1_000_000, 50_000, 5),
    ("rich3", "👑 Diyarın Zengini", lambda u: u["coins"] + u["bank"] >= 10_000_000, 250_000, 15),
    ("fighter", "⚔️ Düellocu", lambda u: u["pvp_wins"] >= 10, 8_000, 1),
    ("champion", "🏆 Arena Şampiyonu", lambda u: u["pvp_wins"] >= 100, 80_000, 6),
    ("slayer", "🐉 Ejder Katili", lambda u: u["boss_kills"] >= 1, 15_000, 2),
    ("legend", "🌟 Efsane", lambda u: u["level"] >= 25, 60_000, 5),
    ("social", "🤝 Sosyal Kelebek", lambda u: u["refs"] >= 5, 20_000, 3),
    ("streak", "📅 Sadık Oyuncu", lambda u: u["streak"] >= 7, 12_000, 2),
    ("bigwin", "💥 Büyük Vuruş", lambda u: u["biggest_win"] >= 250_000, 30_000, 3),
]


def check_achievements(user_id: int) -> list[str]:
    user = db.get_user(user_id)
    if not user:
        return []
    owned = {r["akey"] for r in db.all_("SELECT akey FROM achievements WHERE user_id=?", (user_id,))}
    unlocked = []
    for key, name, cond, coins, gems in ACHIEVEMENTS:
        if key in owned:
            continue
        try:
            if cond(user):
                db.run(
                    "INSERT OR IGNORE INTO achievements (user_id, akey, ts) VALUES (?,?,?)",
                    (user_id, key, ui.now()),
                )
                economy.add_coins(user_id, coins, f"başarım: {key}")
                if gems:
                    economy.add_gems(user_id, gems, f"başarım: {key}")
                unlocked.append(f"{name} (+{ui.fmt(coins)}🪙" + (f" +{gems}💎" if gems else "") + ")")
        except Exception:
            continue
    return unlocked


# ----------------------------------------------------------------------------
# DÜNYA BOSSU
# ----------------------------------------------------------------------------
BOSS_NAMES = [
    ("Kızıl Ejder Vermathrax", "🐉"), ("Kemik Kralı Morgul", "💀"), ("Buz Devi Ymir", "🧊"),
    ("Gölge Lordu Nyx", "🌑"), ("Kum Solucanı Shai", "🪱"), ("Kıyamet Golemi", "🗿"),
    ("Cadı Kraliçe Morgana", "🧙‍♀️"), ("Kraken", "🐙"), ("Alev Şeytanı Ifrit", "🔥"),
]


def active_boss():
    row = db.one("SELECT * FROM boss WHERE active=1 ORDER BY id DESC LIMIT 1")
    if row and row["end_ts"] < ui.now():
        db.run("UPDATE boss SET active=0 WHERE id=?", (row["id"],))
        return None
    return row


def spawn_boss() -> dict:
    """Oyuncu sayısına göre ölçeklenen yeni bir boss doğurur."""
    avg_level = int(db.scalar(
        "SELECT COALESCE(AVG(level),1) FROM users WHERE last_seen > ?", (ui.now() - 7 * 86400,), 1))
    players = int(db.scalar("SELECT COUNT(*) FROM users WHERE last_seen > ?", (ui.now() - 3 * 86400,)))
    name, emoji = random.choice(BOSS_NAMES)
    hp = int((3_000 + avg_level * 900) * max(1, min(60, players)) * random.uniform(0.85, 1.2))
    reward = int(hp * random.uniform(2.2, 3.4))
    now = ui.now()
    db.run("UPDATE boss SET active=0 WHERE active=1")
    cur = db.run(
        "INSERT INTO boss (name, emoji, hp, max_hp, reward, active, spawn_ts, end_ts) VALUES (?,?,?,?,?,1,?,?)",
        (name, emoji, hp, hp, reward, now, now + config.BOSS_DURATION_MIN * 60),
    )
    log.info("Boss doğdu: %s (%s HP)", name, hp)
    return {"id": int(cur.lastrowid), "name": name, "emoji": emoji, "hp": hp, "reward": reward}


def boss_panel_text(boss) -> str:
    if boss is None:
        return (
            "🐉 <b>DÜNYA BOSSU</b>\n\n"
            "Şu anda aktif bir boss yok. Yeni boss birazdan doğacak!\n"
            f"Bosslar ortalama her {config.BOSS_INTERVAL_MIN} dakikada bir uyanır.\n\n"
            "Boss'a vurmak için ekipmanını yükselt, enerjini biriktir."
        )
    top = db.all_(
        "SELECT b.user_id, b.damage, u.first_name FROM boss_hits b "
        "JOIN users u ON u.user_id=b.user_id WHERE b.boss_id=? ORDER BY b.damage DESC LIMIT 5",
        (boss["id"],),
    )
    lines = [
        f"{boss['emoji']} <b>{ui.esc(boss['name'])}</b>",
        f"❤️ {ui.bar(boss['hp'], boss['max_hp'], 14)}",
        f"<b>{ui.fmt(boss['hp'])}</b> / {ui.fmt(boss['max_hp'])} HP",
        f"🏆 Ödül havuzu: {ui.fmt(boss['reward'])} 🪙 + 💎",
        f"⏳ Kalan süre: {ui.dur(boss['end_ts'] - ui.now())}",
        f"⚡ Saldırı maliyeti: {config.BOSS_ATTACK_ENERGY} enerji",
    ]
    if top:
        lines.append("\n<b>🔥 En çok hasar verenler</b>")
        for i, row in enumerate(top, 1):
            lines.append(f"{i}. {ui.esc(row['first_name'])} — {ui.fmt(row['damage'])} hasar")
    lines.append("\nHasarın kadar ödülden pay alırsın. Son vuruşu yapan bonus kazanır!")
    return "\n".join(lines)


def attack_boss(user_id: int) -> dict:
    boss = active_boss()
    if boss is None:
        return {"ok": False, "msg": "Şu anda aktif bir boss yok."}
    user = db.get_user(user_id)
    if not economy.spend_energy(user_id, config.BOSS_ATTACK_ENERGY):
        return {"ok": False, "msg": f"Yeterli enerjin yok ({config.BOSS_ATTACK_ENERGY}⚡ gerekli)."}
    stats = economy.power(user)
    crit = economy.roll(stats["crit"])
    damage = int(stats["atk"] * random.uniform(2.0, 3.2) * (2.0 if crit else 1.0))
    damage = max(1, damage)
    new_hp = max(0, boss["hp"] - damage)
    db.run("UPDATE boss SET hp=? WHERE id=?", (new_hp, boss["id"]))
    db.run(
        "INSERT INTO boss_hits (boss_id, user_id, damage, hits) VALUES (?,?,?,1) "
        "ON CONFLICT(boss_id, user_id) DO UPDATE SET damage=damage+excluded.damage, hits=hits+1",
        (boss["id"], user_id, damage),
    )
    economy.add_xp(user_id, 25)
    track(user_id, "boss")
    result = {"ok": True, "damage": damage, "crit": crit, "hp": new_hp, "max_hp": boss["max_hp"],
              "boss": boss, "killed": False}
    if new_hp <= 0:
        result["killed"] = True
        result["rewards"] = _finish_boss(boss, user_id)
    return result


def _finish_boss(boss, killer_id: int) -> list[tuple[int, int, int]]:
    """Boss ölünce hasara göre ödül dağıtır. [(user_id, coins, gems)]"""
    db.run("UPDATE boss SET active=0, hp=0, killer_id=? WHERE id=?", (killer_id, boss["id"]))
    hits = db.all_("SELECT * FROM boss_hits WHERE boss_id=? ORDER BY damage DESC", (boss["id"],))
    total = sum(h["damage"] for h in hits) or 1
    payouts = []
    for i, hit in enumerate(hits):
        share = hit["damage"] / total
        coins = int(boss["reward"] * share)
        gems = 0
        if i == 0:
            coins = int(coins * 1.25)
            gems = 8
        elif i == 1:
            gems = 5
        elif i == 2:
            gems = 3
        elif share > 0.02:
            gems = 1
        if hit["user_id"] == killer_id:
            coins += int(boss["reward"] * 0.08)
            gems += 2
        economy.add_coins(hit["user_id"], coins, "boss ödülü")
        if gems:
            economy.add_gems(hit["user_id"], gems, "boss ödülü")
        economy.add_xp(hit["user_id"], 120 + int(300 * share))
        db.bump(hit["user_id"], boss_kills=1)
        # nadir eşya düşüşü
        if economy.roll(0.10 + share * 0.4):
            drop = random.choice(["c_scroll", "c_clover", "c_shield", "c_potion", "c_energy"])
            db.inv_add(hit["user_id"], drop, 1, stackable=True)
        payouts.append((hit["user_id"], coins, gems))
    return payouts


async def job_boss(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periyodik boss doğurma ve duyuru işi."""
    if active_boss() is not None:
        return
    boss = spawn_boss()
    text = (
        f"{boss['emoji']} <b>DÜNYA BOSSU UYANDI!</b>\n\n"
        f"<b>{ui.esc(boss['name'])}</b> diyara saldırıyor!\n"
        f"❤️ {ui.fmt(boss['hp'])} HP  •  🏆 {ui.fmt(boss['reward'])} 🪙 ödül havuzu\n\n"
        f"Herkes birlikte saldırmalı! /boss yazarak savaşa katıl."
    )
    await _broadcast_groups(context, text)


async def _broadcast_groups(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    rows = db.all_("SELECT chat_id FROM groups ORDER BY added_ts DESC LIMIT 200")
    for row in rows:
        try:
            await context.bot.send_message(row["chat_id"], text, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.05)
        except Exception:
            db.run("DELETE FROM groups WHERE chat_id=?", (row["chat_id"],))


# ----------------------------------------------------------------------------
# PİYANGO
# ----------------------------------------------------------------------------

def current_round():
    row = db.one("SELECT * FROM lottery WHERE done=0 ORDER BY round_no DESC LIMIT 1")
    if row is None:
        last = int(db.scalar("SELECT COALESCE(MAX(round_no),0) FROM lottery"))
        rnd = last + 1
        db.run(
            "INSERT INTO lottery (round_no, pot, end_ts, done) VALUES (?,?,?,0)",
            (rnd, config.LOTTERY_SEED, ui.now() + config.LOTTERY_INTERVAL_MIN * 60),
        )
        row = db.one("SELECT * FROM lottery WHERE round_no=?", (rnd,))
    return row


def buy_tickets(user_id: int, count: int) -> dict:
    rnd = current_round()
    cost = count * config.LOTTERY_TICKET_PRICE
    user = db.get_user(user_id)
    if user["coins"] < cost:
        return {"ok": False, "msg": i18n.t(i18n.lang_of(user_id), "no_money",
                                           need=ui.fmt(cost), have=ui.fmt(user["coins"]))}
    if not economy.take_coins(user_id, cost, "piyango bileti"):
        return {"ok": False, "msg": i18n.t(i18n.lang_of(user_id), "no_money",
                                           need=ui.fmt(cost), have=ui.fmt(user["coins"]))}
    db.run(
        "INSERT INTO lottery_tickets (round_no, user_id, tickets) VALUES (?,?,?) "
        "ON CONFLICT(round_no, user_id) DO UPDATE SET tickets=tickets+excluded.tickets",
        (rnd["round_no"], user_id, count),
    )
    db.run("UPDATE lottery SET pot=pot+? WHERE round_no=?", (int(cost * 0.92), rnd["round_no"]))
    mine = int(db.scalar(
        "SELECT tickets FROM lottery_tickets WHERE round_no=? AND user_id=?",
        (rnd["round_no"], user_id)))
    return {"ok": True, "cost": cost, "tickets": mine}


def lottery_text(user_id: int) -> str:
    rnd = current_round()
    total = int(db.scalar("SELECT COALESCE(SUM(tickets),0) FROM lottery_tickets WHERE round_no=?",
                          (rnd["round_no"],)))
    mine = int(db.scalar("SELECT COALESCE(tickets,0) FROM lottery_tickets WHERE round_no=? AND user_id=?",
                         (rnd["round_no"], user_id)))
    chance = (mine / total * 100) if total else 0
    return (
        f"🎟 <b>PİYANGO — {rnd['round_no']}. ÇEKİLİŞ</b>\n\n"
        f"💰 Havuz: <b>{ui.fmt(rnd['pot'])}</b> 🪙\n"
        f"🎫 Satılan bilet: {ui.fmt(total)}\n"
        f"🙋 Senin biletin: <b>{mine}</b>  (kazanma şansı %{chance:.1f})\n"
        f"⏳ Çekilişe kalan: {ui.dur(rnd['end_ts'] - ui.now())}\n"
        f"💵 Bilet fiyatı: {ui.fmt(config.LOTTERY_TICKET_PRICE)} 🪙\n\n"
        "Kazanan havuzun tamamını alır. Ne kadar çok bilet, o kadar çok şans!"
    )


async def job_lottery(context: ContextTypes.DEFAULT_TYPE) -> None:
    rnd = db.one("SELECT * FROM lottery WHERE done=0 AND end_ts<=? ORDER BY round_no LIMIT 1", (ui.now(),))
    if rnd is None:
        return
    rows = db.all_("SELECT * FROM lottery_tickets WHERE round_no=?", (rnd["round_no"],))
    if not rows:
        db.run("UPDATE lottery SET done=1 WHERE round_no=?", (rnd["round_no"],))
        db.run(
            "INSERT INTO lottery (round_no, pot, end_ts, done) VALUES (?,?,?,0)",
            (rnd["round_no"] + 1, rnd["pot"], ui.now() + config.LOTTERY_INTERVAL_MIN * 60),
        )
        return
    pool = []
    for row in rows:
        pool.extend([row["user_id"]] * row["tickets"])
    winner = random.choice(pool)
    economy.add_coins(winner, rnd["pot"], "piyango kazancı")
    economy.add_gems(winner, 1, "çekiliş")
    db.run("UPDATE lottery SET done=1, winner=? WHERE round_no=?", (winner, rnd["round_no"]))
    db.run(
        "INSERT INTO lottery (round_no, pot, end_ts, done) VALUES (?,?,?,0)",
        (rnd["round_no"] + 1, config.LOTTERY_SEED, ui.now() + config.LOTTERY_INTERVAL_MIN * 60),
    )
    user = db.get_user(winner)
    text = (
        f"🎉 <b>PİYANGO SONUCU — {rnd['round_no']}. ÇEKİLİŞ</b>\n\n"
        f"🏆 Kazanan: {ui.mention(user)}\n"
        f"💰 Ödül: <b>{ui.fmt(rnd['pot'])}</b> 🪙 + 1 💎\n\n"
        f"Yeni çekiliş başladı! /piyango"
    )
    try:
        await context.bot.send_message(winner, text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await _broadcast_groups(context, text)


async def job_interest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Banka faizi ve işletme hatırlatması (saatlik)."""
    now = ui.now()
    rows = db.all_("SELECT user_id, bank, last_bank FROM users WHERE bank>0 AND last_bank<?",
                   (now - 86400,))
    for row in rows:
        interest = int(row["bank"] * config.BANK_INTEREST)
        if interest > 0:
            db.run("UPDATE users SET bank=bank+?, last_bank=? WHERE user_id=?",
                   (interest, now, row["user_id"]))
            db.log_tx(row["user_id"], interest, "banka faizi")


# ----------------------------------------------------------------------------
# HANDLER'LAR
# ----------------------------------------------------------------------------

def quests_text(user_id: int) -> str:
    quests = daily_quests(user_id)
    lines = [f"📜 <b>GÜNLÜK GÖREVLER</b>\n{ui.LINE}",
             "<i>Her gün yenilenir. Hepsini bitirirsen +2 💎 ekstra.</i>\n"]
    ready = 0
    for quest in quests:
        done = quest["progress"] >= quest["target"]
        if quest["claimed"]:
            mark = "✅"
        elif done:
            mark = "🎁"
            ready += 1
        else:
            mark = "⬜"
        lines.append(
            f"{mark} <b>{quest['text']}</b>\n"
            f"<blockquote>{ui.bar(quest['progress'], quest['target'], 10)}  "
            f"{ui.fmt(quest['progress'])}/{ui.fmt(quest['target'])}\n"
            f"🎁 Ödül: <b>{ui.fmt(quest['reward'])}</b> 🪙</blockquote>"
        )
    owned = int(db.scalar("SELECT COUNT(*) FROM achievements WHERE user_id=?", (user_id,)))
    lines.append(f"\n🏅 Başarımlar: <b>{owned}/{len(ACHIEVEMENTS)}</b>")
    if ready:
        lines.append(f"\n🎁 <b>{ready} görevin ödülü hazır!</b>")
    return "\n".join(lines)


def achievements_text(user_id: int) -> str:
    owned = {r["akey"] for r in db.all_("SELECT akey FROM achievements WHERE user_id=?", (user_id,))}
    lines = ["🏅 <b>BAŞARIMLAR</b>\n"]
    for key, name, _cond, coins, gems in ACHIEVEMENTS:
        mark = "✅" if key in owned else "🔒"
        bonus = f"{ui.fmt(coins)}🪙" + (f" +{gems}💎" if gems else "")
        lines.append(f"{mark} {name} — {bonus}")
    lines.append(f"\nToplam: <b>{len(owned)}/{len(ACHIEVEMENTS)}</b>")
    return "\n".join(lines)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "quests"
    TOASTS = {"quests": "📜 Görevlerin", "ach": "🏅 Başarımlar", "boss": "🐉 Canavar",
              "lottery": "🎟 Çekiliş", "claim": "🎁 Ödüller"}
    context.user_data["_toast"] = TOASTS.get(action, "")

    if action == "quests":
        await ui.safe_edit(query, quests_text(user_id), ui.kb([
            [("🎁 Ödülleri Al", "ev:claim")],
            [("🏅 Başarımlar", "ev:ach")],
            [("🏠 Menü", "m:main")],
        ]))
    elif action == "claim":
        total, count = claim_quests(user_id)
        if count:
            await ui.answer(query, f"🎁 {count} görev ödülü alındı: +{ui.fmt(total)} altın!", alert=True)
        else:
            await ui.answer(query, "Alınacak hazır görev ödülü yok.", alert=True)
        await ui.safe_edit(query, quests_text(user_id), ui.kb([
            [("🎁 Ödülleri Al", "ev:claim")],
            [("🏅 Başarımlar", "ev:ach")],
            [("🏠 Menü", "m:main")],
        ]))
    elif action == "ach":
        await ui.safe_edit(query, achievements_text(user_id), ui.back_kb("ev:quests"))
    elif action == "boss":
        boss = active_boss()
        rows = [[("⚔️ SALDIR", "ev:hit")]] if boss else []
        rows.append([("🔄 Yenile", "ev:boss"), ("🏠 Menü", "m:main")])
        await ui.nav(query, "boss", boss_panel_text(boss), ui.kb(rows))
    elif action == "hit":
        res = attack_boss(user_id)
        if not res["ok"]:
            await ui.answer(query, res["msg"], alert=True)
            return
        note = "💥 KRİTİK! " if res["crit"] else ""
        if res["killed"]:
            mine = next((c for uid, c, _g in res["rewards"] if uid == user_id), 0)
            await ui.answer(query, 
                f"{note}{ui.fmt(res['damage'])} hasar — BOSS ÖLDÜ! Payın: {ui.fmt(mine)} altın 🎉",
                alert=True)
            await _broadcast_groups(context, (
                f"☠️ <b>{ui.esc(res['boss']['name'])} yenildi!</b>\n"
                f"Son vuruş: {ui.mention(db.get_user(user_id))}\n"
                f"Ödüller hasara göre dağıtıldı. Yeni boss yolda!"
            ))
        else:
            await ui.answer(query, f"{note}{ui.fmt(res['damage'])} hasar verdin!")
        boss = active_boss()
        rows = [[("⚔️ SALDIR", "ev:hit")]] if boss else []
        rows.append([("🔄 Yenile", "ev:boss"), ("🏠 Menü", "m:main")])
        await ui.safe_edit(query, boss_panel_text(boss), ui.kb(rows))
    elif action == "lottery":
        await ui.safe_edit(query, lottery_text(user_id), ui.kb([
            [("🎫 1 Bilet", "ev:buy:1"), ("🎫 5 Bilet", "ev:buy:5")],
            [("🎫 10 Bilet", "ev:buy:10"), ("🎫 50 Bilet", "ev:buy:50")],
            [("🔄 Yenile", "ev:lottery"), ("🏠 Menü", "m:main")],
        ]))
    elif action == "buy":
        count = max(1, min(500, int(parts[2])))
        res = buy_tickets(user_id, count)
        if not res["ok"]:
            await ui.answer(query, res["msg"], alert=True)
        else:
            await ui.answer(query, f"🎫 {count} bilet alındı! Toplam biletin: {res['tickets']}")
        await ui.safe_edit(query, lottery_text(user_id), ui.kb([
            [("🎫 1 Bilet", "ev:buy:1"), ("🎫 5 Bilet", "ev:buy:5")],
            [("🎫 10 Bilet", "ev:buy:10"), ("🎫 50 Bilet", "ev:buy:50")],
            [("🔄 Yenile", "ev:lottery"), ("🏠 Menü", "m:main")],
        ]))


async def cmd_boss(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    boss = active_boss()
    rows = [[("⚔️ SALDIR", "ev:hit")]] if boss else []
    rows.append([("🔄 Yenile", "ev:boss")])
    await ui.send(update, boss_panel_text(boss), ui.kb(rows))


async def cmd_lottery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, lottery_text(update.effective_user.id), ui.kb([
        [("🎫 1 Bilet", "ev:buy:1"), ("🎫 10 Bilet", "ev:buy:10")],
        [("🔄 Yenile", "ev:lottery")],
    ]))


async def cmd_quests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ui.send(update, quests_text(update.effective_user.id), ui.kb([
        [("🎁 Ödülleri Al", "ev:claim")], [("🏅 Başarımlar", "ev:ach")],
    ]))
