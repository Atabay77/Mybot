# -*- coding: utf-8 -*-
"""PVP: arkadaşlarla altın karşılığı düellolar.
Modlar: taş-kağıt-makas, XOX, emoji zar, gerçek arena savaşı, gizemli kutu."""
import asyncio
import json
import logging
import random

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
import economy
import events
import games
import i18n
import ui

log = logging.getLogger(__name__)

MODES = {
    "rps": ("✂️", "Taş-Kağıt-Makas", "3 rauntta 2 kazanan alır"),
    "xox": ("❌", "XOX", "Klasik tic-tac-toe, sırayla oyna"),
    "dice": ("🎲", "Emoji Zar", "Telegram zarı — yüksek atan kazanır"),
    "arena": ("⚔️", "Arena Savaşı", "Ekipmanların savaşır, güçlü olan kazanır"),
    "box": ("🎁", "Gizemli Kutu", "Kutu seç, yüksek değer kazanır"),
}
DUEL_TIMEOUT = 15 * 60


# ---------------------------------------------------------------------------
# ORTAK
# ---------------------------------------------------------------------------

def load(duel_id: int):
    row = db.one("SELECT * FROM duels WHERE id=?", (duel_id,))
    if row is None:
        return None, {}
    try:
        data = json.loads(row["data"])
    except ValueError:
        data = {}
    return row, data


def save(duel_id: int, data: dict, state: str = None) -> None:
    if state:
        db.run("UPDATE duels SET data=?, state=? WHERE id=?",
               (json.dumps(data, ensure_ascii=False), state, duel_id))
    else:
        db.run("UPDATE duels SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), duel_id))


ONLINE_GAMES = ["rps", "dice", "arena", "box"]
QUEUE_TIMEOUT = 10 * 60


def is_online(duel) -> bool:
    return duel["chat_id"] == 0


async def render(context, duel, data, text, kb=None) -> None:
    """Düello ekranını gösterir: onlineda iki oyuncuya da, grupta tek mesaja."""
    if not is_online(duel):
        try:
            await context.bot.edit_message_text(
                text, chat_id=duel["chat_id"], message_id=duel["message_id"],
                parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            pass
        return
    for slot, uid in (("m1", duel["p1"]), ("m2", duel["p2"])):
        mid = data.get(slot)
        try:
            if mid:
                await context.bot.edit_message_text(
                    text, chat_id=uid, message_id=mid,
                    parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                msg = await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML,
                                                     reply_markup=kb)
                data[slot] = msg.message_id
        except Exception:
            continue
    save(duel["id"], data)


def pot_of(stake: int) -> int:
    return int(stake * 2 * (1 - config.PVP_RAKE))


async def finish(context, duel, winner_id: int | None, text_head: str, extra: str = "") -> None:
    """Düelloyu kapatır, ödülü dağıtır ve mesajı günceller."""
    db.run("UPDATE duels SET state='done' WHERE id=?", (duel["id"],))
    p1 = db.get_user(duel["p1"])
    p2 = db.get_user(duel["p2"])
    stake = duel["stake"]
    if winner_id is None:
        economy.add_coins(duel["p1"], stake, "pvp berabere")
        economy.add_coins(duel["p2"], stake, "pvp berabere")
        result = f"🤝 <b>BERABERE!</b> Bahisler geri verildi ({ui.fmt(stake)} 🪙)."
    else:
        loser_id = duel["p2"] if winner_id == duel["p1"] else duel["p1"]
        prize = pot_of(stake)
        economy.add_coins(winner_id, prize, "pvp kazanç")
        db.bump(winner_id, pvp_wins=1)
        db.bump(loser_id, pvp_losses=1)
        economy.add_xp(winner_id, 80)
        economy.add_xp(loser_id, 25)
        events.track(winner_id, "pvp")
        winner = db.get_user(winner_id)
        result = (
            f"🏆 <b>KAZANAN: {ui.mention(winner)}</b>\n"
            f"💰 Ödül: <b>{ui.fmt(prize)}</b> 🪙 (havuz {ui.fmt(stake * 2)}, komisyon %{int(config.PVP_RAKE * 100)})"
        )
        for uid in (winner_id, loser_id):
            unlocked = events.check_achievements(uid)
            if unlocked:
                try:
                    await context.bot.send_message(
                        uid, "🏅 <b>YENİ BAŞARIM!</b>\n" + "\n".join(unlocked), parse_mode=ParseMode.HTML)
                except Exception:
                    pass
    text = (
        f"{text_head}\n\n"
        f"{ui.mention(p1)} 🆚 {ui.mention(p2)}\n"
        f"{extra}\n\n{result}"
    )
    if is_online(duel):
        _row, data = load(duel["id"])
        kb = ui.kb([[("🔄 Ýene / Ещё / Tekrar", f"pvp:onq:{duel['game']}:{stake}")],
                    [("🏠", "m:main")]])
        for slot, uid in (("m1", duel["p1"]), ("m2", duel["p2"])):
            mid = data.get(slot)
            try:
                if mid:
                    await context.bot.edit_message_text(
                        text, chat_id=uid, message_id=mid,
                        parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML,
                                                   reply_markup=kb)
            except Exception:
                continue
        return
    try:
        await context.bot.edit_message_text(
            text, chat_id=duel["chat_id"], message_id=duel["message_id"],
            parse_mode=ParseMode.HTML,
            reply_markup=ui.kb([[("🔄 Yeni Düello", f"pvp:new:{duel['game']}")]]),
        )
    except Exception:
        await context.bot.send_message(duel["chat_id"], text, parse_mode=ParseMode.HTML)


def open_duels_text() -> str:
    rows = db.all_(
        "SELECT d.*, u.first_name FROM duels d JOIN users u ON u.user_id=d.p1 "
        "WHERE d.state='open' AND d.created_ts > ? ORDER BY d.stake DESC LIMIT 12",
        (ui.now() - DUEL_TIMEOUT,),
    )
    if not rows:
        return ("⚔️ <b>AÇIK DÜELLOLAR</b>\n\nŞu anda bekleyen düello yok.\n"
                "Sen bir tane aç, rakip gelsin! 👇")
    lines = ["⚔️ <b>AÇIK DÜELLOLAR</b>\n"]
    for row in rows:
        emoji, name, _ = MODES.get(row["game"], ("🎮", row["game"], ""))
        group = db.one("SELECT title FROM groups WHERE chat_id=?", (row["chat_id"],))
        where = f" • 💬 {ui.esc(group['title'])}" if group and group["title"] else ""
        lines.append(
            f"#{row['id']} {emoji} <b>{name}</b> — {ui.fmt(row['stake'])} 🪙\n"
            f"    Açan: {ui.esc(row['first_name'])}{where}\n"
            f"    Katılmak için o grupta: <code>/kabul {row['id']}</code>"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DÜELLO OLUŞTURMA / KABUL
# ---------------------------------------------------------------------------

async def create_duel(update, context, game: str, stake: int) -> None:
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if ui.is_private(update):
        await _answer(update, "Düellolar gruplarda kurulur — beni bir gruba ekle ve orada /duello yaz!")
        return
    ok, msg = games.validate_bet(user, stake)
    if not ok:
        await _answer(update, msg)
        return
    active = db.scalar(
        "SELECT COUNT(*) FROM duels WHERE p1=? AND state='open' AND created_ts>?",
        (user_id, ui.now() - DUEL_TIMEOUT))
    if active >= 3:
        await _answer(update, "Aynı anda en fazla 3 açık düellon olabilir.")
        return
    if not economy.take_coins(user_id, stake, "pvp bahis"):
        await _answer(update, "Bakiyen yetersiz.")
        return
    chat_id = update.effective_chat.id
    cur = db.run(
        "INSERT INTO duels (game, chat_id, p1, stake, state, data, created_ts) VALUES (?,?,?,?, 'open', '{}', ?)",
        (game, chat_id, user_id, stake, ui.now()),
    )
    duel_id = int(cur.lastrowid)
    emoji, name, desc = MODES[game]
    text = (
        f"{emoji} <b>DÜELLO #{duel_id} — {name.upper()}</b>\n"
        f"<i>{desc}</i>\n\n"
        f"👤 Meydan okuyan: {ui.mention(user)}\n"
        f"💰 Bahis: <b>{ui.fmt(stake)}</b> 🪙 kişi başı\n"
        f"🏆 Kazanan alır: <b>{ui.fmt(pot_of(stake))}</b> 🪙\n\n"
        f"Kim var? 👇  <i>(15 dakika içinde kabul edilmezse bahis iade edilir)</i>"
    )
    kb = ui.kb([
        [("⚔️ KABUL EDİYORUM", f"pvp:acc:{duel_id}")],
        [("🚫 İptal (açan kişi)", f"pvp:cancel:{duel_id}")],
    ])
    msg_obj = await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
    db.run("UPDATE duels SET message_id=? WHERE id=?", (msg_obj.message_id, duel_id))


async def _answer(update, text: str) -> None:
    if update.callback_query:
        await ui.answer(update.callback_query, text, alert=True)
    else:
        await ui.send(update, text)


async def accept_duel(update, context, duel_id: int) -> None:
    user_id = update.effective_user.id
    duel, data = load(duel_id)
    if duel is None or duel["state"] != "open":
        await _answer(update, "Bu düello artık geçerli değil.")
        return
    if duel["p1"] == user_id:
        await _answer(update, "Kendi düellonu kabul edemezsin! Rakip bekle.")
        return
    if duel["created_ts"] < ui.now() - DUEL_TIMEOUT:
        await _answer(update, "Bu düellonun süresi dolmuş.")
        return
    if update.effective_chat.id != duel["chat_id"]:
        group = db.one("SELECT title FROM groups WHERE chat_id=?", (duel["chat_id"],))
        where = f'"{group["title"]}" grubunda' if group and group["title"] else "açıldığı grupta"
        await _answer(update, f"Bu düelloyu {where} kabul etmelisin (tahta orada).")
        return
    user = db.get_user(user_id)
    if user["coins"] < duel["stake"]:
        await _answer(update, f"Bu düello için {ui.fmt(duel['stake'])} altın gerekiyor.")
        return
    if not economy.take_coins(user_id, duel["stake"], "pvp bahis"):
        await _answer(update, "Bakiyen yetersiz.")
        return
    db.run("UPDATE duels SET p2=?, state='playing' WHERE id=? AND state='open'", (user_id, duel_id))
    duel, data = load(duel_id)
    if duel["p2"] != user_id:
        economy.add_coins(user_id, duel["stake"], "pvp iade")
        await _answer(update, "Başka biri daha hızlıydı!")
        return
    if update.callback_query:
        await ui.answer(update.callback_query, "Düello başlıyor!")
    game = duel["game"]
    if game == "rps":
        await rps_start(context, duel)
    elif game == "xox":
        await xox_start(context, duel)
    elif game == "dice":
        await dice_start(context, duel)
    elif game == "arena":
        await arena_start(context, duel)
    elif game == "box":
        await box_start(context, duel)


async def cancel_duel(update, context, duel_id: int) -> None:
    user_id = update.effective_user.id
    duel, _ = load(duel_id)
    if duel is None or duel["state"] != "open":
        await _answer(update, "İptal edilecek açık düello yok.")
        return
    if duel["p1"] != user_id and user_id not in config.ADMIN_IDS:
        await _answer(update, "Sadece düelloyu açan iptal edebilir.")
        return
    db.run("UPDATE duels SET state='cancelled' WHERE id=?", (duel_id,))
    economy.add_coins(duel["p1"], duel["stake"], "pvp iptal iadesi")
    if update.callback_query:
        await ui.safe_edit(update.callback_query,
                           f"🚫 Düello #{duel_id} iptal edildi, {ui.fmt(duel['stake'])} 🪙 iade edildi.")
    else:
        await ui.send(update, f"🚫 Düello #{duel_id} iptal edildi, bahis iade edildi.")


# ---------------------------------------------------------------------------
# 1) TAŞ - KAĞIT - MAKAS
# ---------------------------------------------------------------------------
RPS = {"t": ("🪨", "Taş"), "k": ("📄", "Kağıt"), "m": ("✂️", "Makas")}
RPS_BEATS = {"t": "m", "k": "t", "m": "k"}


def rps_kb(duel_id: int):
    return ui.kb([[("🪨 Taş", f"pvp:rps:{duel_id}:t"),
                   ("📄 Kağıt", f"pvp:rps:{duel_id}:k"),
                   ("✂️ Makas", f"pvp:rps:{duel_id}:m")]])


def rps_text(duel, data) -> str:
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    picked = []
    if data.get("c1"):
        picked.append(f"✅ {ui.name_of(p1)} seçimini yaptı")
    if data.get("c2"):
        picked.append(f"✅ {ui.name_of(p2)} seçimini yaptı")
    history = "\n".join(data.get("log", []))
    return (
        f"✂️ <b>TAŞ-KAĞIT-MAKAS #{duel['id']}</b>\n\n"
        f"{ui.mention(p1)} <b>{data.get('s1', 0)}</b> — <b>{data.get('s2', 0)}</b> {ui.mention(p2)}\n"
        f"💰 Bahis: {ui.fmt(duel['stake'])} 🪙 • Havuz: {ui.fmt(pot_of(duel['stake']))} 🪙\n"
        f"🎯 Raunt {data.get('round', 1)} / 3 (ilk 2 kazanan)\n\n"
        + (history + "\n\n" if history else "")
        + ("\n".join(picked) if picked else "İki oyuncu da seçim yapmalı 👇")
    )


async def rps_start(context, duel) -> None:
    data = {"round": 1, "s1": 0, "s2": 0, "c1": None, "c2": None, "log": []}
    save(duel["id"], data)
    if is_online(duel):
        await render(context, duel, data, rps_text(duel, data), rps_kb(duel["id"]))
    else:
        await context.bot.edit_message_text(
            rps_text(duel, data), chat_id=duel["chat_id"], message_id=duel["message_id"],
            parse_mode=ParseMode.HTML, reply_markup=rps_kb(duel["id"]))


async def rps_pick(update, context, duel_id: int, choice: str) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    duel, data = load(duel_id)
    if duel is None or duel["state"] != "playing":
        await ui.answer(query, "Bu düello bitti.", alert=True)
        return
    if user_id not in (duel["p1"], duel["p2"]):
        await ui.answer(query, "Bu düelloda oyuncu değilsin. Kendi düellonu aç: /duello", alert=True)
        return
    slot = "c1" if user_id == duel["p1"] else "c2"
    if data.get(slot):
        await ui.answer(query, "Bu raunttaki seçimini zaten yaptın.")
        return
    data[slot] = choice
    await ui.answer(query, f"Seçimin: {RPS[choice][0]} {RPS[choice][1]}")
    if not (data.get("c1") and data.get("c2")):
        save(duel_id, data)
        if is_online(duel):
            await render(context, duel, data, rps_text(duel, data), rps_kb(duel_id))
        else:
            await ui.safe_edit(query, rps_text(duel, data), rps_kb(duel_id))
        return
    c1, c2 = data["c1"], data["c2"]
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    if c1 == c2:
        outcome = "🤝 berabere"
    elif RPS_BEATS[c1] == c2:
        data["s1"] += 1
        outcome = f"🏅 {ui.name_of(p1)}"
    else:
        data["s2"] += 1
        outcome = f"🏅 {ui.name_of(p2)}"
    data.setdefault("log", []).append(
        f"R{data['round']}: {RPS[c1][0]} vs {RPS[c2][0]} → {outcome}")
    data["c1"] = data["c2"] = None
    data["round"] += 1

    if data["s1"] >= 2 or data["s2"] >= 2 or data["round"] > 3:
        if data["s1"] > data["s2"]:
            winner = duel["p1"]
        elif data["s2"] > data["s1"]:
            winner = duel["p2"]
        else:
            winner = None
        save(duel_id, data)
        await finish(context, duel, winner,
                     f"✂️ <b>TAŞ-KAĞIT-MAKAS #{duel_id} BİTTİ</b>",
                     "\n".join(data["log"]) + f"\n\nSkor: <b>{data['s1']} - {data['s2']}</b>")
        return
    save(duel_id, data)
    if is_online(duel):
        await render(context, duel, data, rps_text(duel, data), rps_kb(duel_id))
    else:
        await ui.safe_edit(query, rps_text(duel, data), rps_kb(duel_id))


# ---------------------------------------------------------------------------
# 2) XOX
# ---------------------------------------------------------------------------
XOX_MARKS = {0: "▫️", 1: "❌", 2: "⭕"}
XOX_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def xox_kb(duel_id: int, board: list):
    rows = []
    for r in range(3):
        rows.append([(XOX_MARKS[board[r * 3 + c]], f"pvp:xox:{duel_id}:{r * 3 + c}") for c in range(3)])
    return ui.kb(rows)


def xox_text(duel, data) -> str:
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    turn_user = p1 if data["turn"] == 1 else p2
    return (
        f"❌⭕ <b>XOX #{duel['id']}</b>\n\n"
        f"❌ {ui.mention(p1)}  🆚  ⭕ {ui.mention(p2)}\n"
        f"💰 Havuz: {ui.fmt(pot_of(duel['stake']))} 🪙\n\n"
        f"▶️ Sıra: <b>{ui.name_of(turn_user)}</b> ({XOX_MARKS[data['turn']]})"
    )


async def xox_start(context, duel) -> None:
    data = {"board": [0] * 9, "turn": 1}
    save(duel["id"], data)
    await context.bot.edit_message_text(
        xox_text(duel, data), chat_id=duel["chat_id"], message_id=duel["message_id"],
        parse_mode=ParseMode.HTML, reply_markup=xox_kb(duel["id"], data["board"]))


def xox_winner(board: list) -> int:
    for a, b, c in XOX_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return 0


async def xox_move(update, context, duel_id: int, cell: int) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    duel, data = load(duel_id)
    if duel is None or duel["state"] != "playing":
        await ui.answer(query, "Bu düello bitti.", alert=True)
        return
    if user_id not in (duel["p1"], duel["p2"]):
        await ui.answer(query, "Bu düelloda oyuncu değilsin.", alert=True)
        return
    mark = 1 if user_id == duel["p1"] else 2
    if data["turn"] != mark:
        await ui.answer(query, "Sıra rakibinde!")
        return
    if data["board"][cell] != 0:
        await ui.answer(query, "Bu kare dolu.")
        return
    data["board"][cell] = mark
    win = xox_winner(data["board"])
    full = all(v != 0 for v in data["board"])
    board_str = "\n".join(
        " ".join(XOX_MARKS[data["board"][r * 3 + c]] for c in range(3)) for r in range(3))
    if win or full:
        winner = None if not win else (duel["p1"] if win == 1 else duel["p2"])
        save(duel_id, data)
        await finish(context, duel, winner, f"❌⭕ <b>XOX #{duel_id} BİTTİ</b>", board_str)
        return
    data["turn"] = 2 if mark == 1 else 1
    save(duel_id, data)
    await ui.answer(query)
    await ui.safe_edit(query, xox_text(duel, data), xox_kb(duel_id, data["board"]))


# ---------------------------------------------------------------------------
# 3) EMOJİ ZAR DÜELLOSU
# ---------------------------------------------------------------------------
DICE_EMOJIS = ["🎲", "🎯", "🎳", "⚽", "🏀"]


async def dice_start(context, duel) -> None:
    emoji = random.choice(DICE_EMOJIS)
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    if is_online(duel):
        _r, data = load(duel["id"])
        head = (f"{emoji} <b>{i18n.t('tk', 'd_found')}</b>\n"
                f"{ui.mention(p1)} 🆚 {ui.mention(p2)}\n"
                f"💰 {ui.fmt(pot_of(duel['stake']))} 🪙")
        await render(context, duel, data, head)
        rolls = []
        v1 = v2 = 0
        for attempt in range(5):
            v1, v2 = random.randint(1, 6), random.randint(1, 6)
            for uid in (duel["p1"], duel["p2"]):
                try:
                    await context.bot.send_dice(uid, emoji=emoji)
                except Exception:
                    pass
            rolls.append(f"{ui.name_of(p1)} <b>{v1}</b> — <b>{v2}</b> {ui.name_of(p2)}")
            if v1 != v2:
                break
        await asyncio.sleep(3.2)
        winner = duel["p1"] if v1 > v2 else (duel["p2"] if v2 > v1 else None)
        await finish(context, duel, winner, f"{emoji} <b>DUEL #{duel['id']}</b>", "\n".join(rolls))
        return
    await context.bot.edit_message_text(
        f"{emoji} <b>EMOJİ DÜELLOSU #{duel['id']}</b>\n\n"
        f"{ui.mention(p1)} 🆚 {ui.mention(p2)}\n"
        f"💰 Havuz: {ui.fmt(pot_of(duel['stake']))} 🪙\n\n"
        f"Atışlar yapılıyor...",
        chat_id=duel["chat_id"], message_id=duel["message_id"], parse_mode=ParseMode.HTML)

    v1 = v2 = 0
    rolls = []
    for attempt in range(5):
        try:
            m1 = await context.bot.send_dice(duel["chat_id"], emoji=emoji)
            await asyncio.sleep(3.2)
            m2 = await context.bot.send_dice(duel["chat_id"], emoji=emoji)
            await asyncio.sleep(3.2)
            v1, v2 = m1.dice.value, m2.dice.value
        except Exception:
            v1, v2 = random.randint(1, 6), random.randint(1, 6)
        rolls.append(f"Tur {attempt + 1}: {ui.name_of(db.get_user(duel['p1']))} <b>{v1}</b> — "
                     f"<b>{v2}</b> {ui.name_of(db.get_user(duel['p2']))}")
        if v1 != v2:
            break
    winner = duel["p1"] if v1 > v2 else (duel["p2"] if v2 > v1 else None)
    await finish(context, duel, winner, f"{emoji} <b>EMOJİ DÜELLOSU #{duel['id']}</b>", "\n".join(rolls))


# ---------------------------------------------------------------------------
# 4) ARENA DÜELLOSU (ekipman bazlı)
# ---------------------------------------------------------------------------
async def arena_start(context, duel) -> None:
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    s1, s2 = economy.power(p1), economy.power(p2)
    if is_online(duel):
        _r, data = load(duel["id"])
        await render(context, duel, data, (
            f"⚔️ <b>ARENA #{duel['id']}</b>\n"
            f"{ui.mention(p1)} ⚔️{s1['atk']} 🛡{s1['dfn']} ❤️{s1['hp']}\n"
            f"{ui.mention(p2)} ⚔️{s2['atk']} 🛡{s2['dfn']} ❤️{s2['hp']}\n\n🥁..."))
        await asyncio.sleep(2.0)
        fight = games.simulate_fight(s1, ui.name_of(p1), s2, ui.name_of(p2), max_rounds=16)
        winner = duel["p1"] if fight["winner"] == "a" else duel["p2"]
        extra = "\n".join(fight["log"][-8:]) + f"\n\n❤️ {fight['hp_a']} — {fight['hp_b']}"
        await finish(context, duel, winner, f"⚔️ <b>ARENA #{duel['id']}</b>", extra)
        return
    await context.bot.edit_message_text(
        f"⚔️ <b>ARENA DÜELLOSU #{duel['id']}</b>\n\n"
        f"{ui.mention(p1)} ⚔️{s1['atk']} 🛡{s1['dfn']} ❤️{s1['hp']}\n"
        f"{ui.mention(p2)} ⚔️{s2['atk']} 🛡{s2['dfn']} ❤️{s2['hp']}\n\n"
        f"Savaş başlıyor... 🥁",
        chat_id=duel["chat_id"], message_id=duel["message_id"], parse_mode=ParseMode.HTML)
    await asyncio.sleep(2.0)
    fight = games.simulate_fight(s1, ui.name_of(p1), s2, ui.name_of(p2), max_rounds=16)
    winner = duel["p1"] if fight["winner"] == "a" else duel["p2"]
    log_lines = fight["log"][-8:]
    extra = (
        f"{ui.name_of(p1)}: ⚔️{s1['atk']} 🛡{s1['dfn']} ❤️{s1['hp']}\n"
        f"{ui.name_of(p2)}: ⚔️{s2['atk']} 🛡{s2['dfn']} ❤️{s2['hp']}\n\n"
        f"<b>Son turlar</b>\n" + "\n".join(log_lines)
        + f"\n\nKalan can: {fight['hp_a']} — {fight['hp_b']}"
    )
    await finish(context, duel, winner, f"⚔️ <b>ARENA DÜELLOSU #{duel['id']} BİTTİ</b>", extra)


# ---------------------------------------------------------------------------
# 5) GİZEMLİ KUTU
# ---------------------------------------------------------------------------
def box_kb(duel_id: int, data: dict):
    rows = []
    line = []
    for i in range(6):
        taken = data["picks"].get(str(i))
        label = "📦" if not taken else "🔓"
        line.append((label, f"pvp:box:{duel_id}:{i}"))
        if len(line) == 3:
            rows.append(line)
            line = []
    return ui.kb(rows)


def box_text(duel, data) -> str:
    p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
    lines = [f"🎁 <b>GİZEMLİ KUTU #{duel['id']}</b>\n",
             f"{ui.mention(p1)} 🆚 {ui.mention(p2)}",
             f"💰 Havuz: {ui.fmt(pot_of(duel['stake']))} 🪙\n"]
    for slot, uid in (("v1", duel["p1"]), ("v2", duel["p2"])):
        who = db.get_user(uid)
        val = data.get(slot)
        lines.append(f"{ui.name_of(who)}: " + (f"<b>{val}</b> puan 🔓" if val is not None else "kutu seçmedi ⏳"))
    if data.get("v1") is None or data.get("v2") is None:
        lines.append("\nHer oyuncu bir kutu seçer. Yüksek puan kazanır! 👇")
    return "\n".join(lines)


async def box_start(context, duel) -> None:
    values = random.sample([5, 12, 20, 35, 50, 80, 100, 150], 6)
    data = {"values": values, "picks": {}, "v1": None, "v2": None}
    save(duel["id"], data)
    if is_online(duel):
        await render(context, duel, data, box_text(duel, data), box_kb(duel["id"], data))
    else:
        await context.bot.edit_message_text(
            box_text(duel, data), chat_id=duel["chat_id"], message_id=duel["message_id"],
            parse_mode=ParseMode.HTML, reply_markup=box_kb(duel["id"], data))


async def box_pick(update, context, duel_id: int, idx: int) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    duel, data = load(duel_id)
    if duel is None or duel["state"] != "playing":
        await ui.answer(query, "Bu düello bitti.", alert=True)
        return
    if user_id not in (duel["p1"], duel["p2"]):
        await ui.answer(query, "Bu düelloda oyuncu değilsin.", alert=True)
        return
    slot = "v1" if user_id == duel["p1"] else "v2"
    if data.get(slot) is not None:
        await ui.answer(query, "Zaten kutunu açtın.")
        return
    if str(idx) in data["picks"]:
        await ui.answer(query, "Bu kutu açılmış, başka seç.")
        return
    value = data["values"][idx]
    data["picks"][str(idx)] = slot
    data[slot] = value
    await ui.answer(query, f"📦 Kutuda {value} puan vardı!")
    if data.get("v1") is not None and data.get("v2") is not None:
        winner = duel["p1"] if data["v1"] > data["v2"] else (duel["p2"] if data["v2"] > data["v1"] else None)
        save(duel_id, data)
        p1, p2 = db.get_user(duel["p1"]), db.get_user(duel["p2"])
        extra = (f"{ui.name_of(p1)}: <b>{data['v1']}</b> puan\n"
                 f"{ui.name_of(p2)}: <b>{data['v2']}</b> puan")
        await finish(context, duel, winner, f"🎁 <b>GİZEMLİ KUTU #{duel_id} BİTTİ</b>", extra)
        return
    save(duel_id, data)
    if is_online(duel):
        await render(context, duel, data, box_text(duel, data), box_kb(duel_id, data))
    else:
        await ui.safe_edit(query, box_text(duel, data), box_kb(duel_id, data))


# ---------------------------------------------------------------------------
# ONLINE EŞLEŞME (grup gerekmez)
# ---------------------------------------------------------------------------

async def queue_join(update, context, game: str, stake: int) -> None:
    """Sıraya girer; uygun rakip varsa oyunu hemen başlatır."""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    ok, msg = games.validate_bet(user, stake)
    if not ok:
        await _answer(update, msg)
        return
    db.run("DELETE FROM queue WHERE created_ts < ?", (ui.now() - QUEUE_TIMEOUT,))
    if db.one("SELECT 1 FROM queue WHERE user_id=?", (user_id,)):
        await _answer(update, i18n.t(lang, "d_queued"))
        return
    rival = db.one(
        "SELECT * FROM queue WHERE game=? AND stake=? AND user_id<>? ORDER BY created_ts LIMIT 1",
        (game, stake, user_id))
    if not economy.take_coins(user_id, stake, "pvp bahis"):
        await _answer(update, i18n.t(lang, "no_money", need=ui.fmt(stake),
                                     have=ui.fmt(user["coins"])))
        return
    if rival is None:
        db.run("INSERT INTO queue (user_id, game, stake, created_ts) VALUES (?,?,?,?)",
               (user_id, game, stake, ui.now()))
        emoji, name, _d = MODES[game]
        text = i18n.t(lang, "d_search", game=f"{emoji} {name}", stake=ui.fmt(stake))
        kb = ui.kb([[(i18n.t(lang, "d_cancel"), "pvp:onc")]])
        if update.callback_query:
            await ui.safe_edit(update.callback_query, text, kb)
        else:
            await ui.send(update, text, kb)
        return

    db.run("DELETE FROM queue WHERE user_id=?", (rival["user_id"],))
    cur = db.run(
        "INSERT INTO duels (game, chat_id, p1, p2, stake, state, data, created_ts) "
        "VALUES (?,0,?,?,?, 'playing', '{}', ?)",
        (game, rival["user_id"], user_id, stake, ui.now()))
    duel, data = load(int(cur.lastrowid))
    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
    if game == "rps":
        await rps_start(context, duel)
    elif game == "box":
        await box_start(context, duel)
    elif game == "dice":
        await dice_start(context, duel)
    elif game == "arena":
        await arena_start(context, duel)


async def queue_leave(update, context) -> None:
    user_id = update.effective_user.id
    row = db.one("SELECT * FROM queue WHERE user_id=?", (user_id,))
    if row:
        db.run("DELETE FROM queue WHERE user_id=?", (user_id,))
        economy.add_coins(user_id, row["stake"], "pvp sıra iptali")
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    if update.callback_query:
        await ui.safe_edit(update.callback_query, pvp_menu_text(user, True), pvp_menu_kb(True))


async def job_queue_clean(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Uzun süre eşleşemeyenlerin parasını iade eder."""
    rows = db.all_("SELECT * FROM queue WHERE created_ts < ?", (ui.now() - QUEUE_TIMEOUT,))
    for row in rows:
        db.run("DELETE FROM queue WHERE user_id=?", (row["user_id"],))
        economy.add_coins(row["user_id"], row["stake"], "pvp sıra zaman aşımı")
        try:
            await context.bot.send_message(
                row["user_id"], "⏰ Rakip bulunamadı, bahsin geri verildi.",
                reply_markup=ui.kb([[("⚔️", "pvp:menu")]]))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# MENÜ / KOMUTLAR
# ---------------------------------------------------------------------------

def pvp_menu_text(user, private: bool = True) -> str:
    head = (
        "⚔️ <b>PVP ARENA</b>\n"
        f"{ui.header(user)}\n\n"
        f"🏅 PVP: <b>{user['pvp_wins']}</b> galibiyet / {user['pvp_losses']} yenilgi\n\n"
    )
    modes = "\n".join(f"{e} <b>{n}</b> — {d}" for e, n, d in MODES.values())
    if private:
        return head + (
            "🌐 <b>Online</b>: rakip botun kendisi bulur, grup gerekmez.\n"
            "👥 <b>Grup</b>: beni gruba ekle, orada düello kur.\n\n"
            + modes +
            "\n\n<i>Kazanan havuzun tamamını alır (%4 komisyon).</i>"
        )
    return head + "Bir mod seç, bahsini koy — grubundan biri kabul etsin 👇\n\n" + modes


def pvp_menu_kb(private: bool = True, lang: str = i18n.DEFAULT):
    if private:
        rows = [[(i18n.t(lang, "d_online"), "pvp:on")]]
        if config.BOT_USERNAME:
            rows.append([(i18n.t(lang, "d_group"),
                          f"url:https://t.me/{config.BOT_USERNAME}?startgroup=duello")])
        rows.append([("📋", "pvp:list"), (i18n.t(lang, "b_top"), "pvp:top")])
        rows.append([(i18n.t(lang, "b_home"), "m:main")])
        return ui.kb(rows)
    rows = [[(f"{e} {n}", f"pvp:new:{k}")] for k, (e, n, _d) in MODES.items()]
    rows.append([("📋 Açık Düellolar", "pvp:list"), ("🏆 PVP Sıralama", "pvp:top")])
    return ui.kb(rows)


def pvp_top_text() -> str:
    rows = db.all_(
        "SELECT first_name, pvp_wins, pvp_losses FROM users WHERE pvp_wins>0 "
        "ORDER BY pvp_wins DESC, pvp_losses ASC LIMIT 10")
    if not rows:
        return "🏆 <b>PVP SIRALAMASI</b>\n\nHenüz kimse düello kazanmadı. İlk sen ol!"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🏆 <b>PVP SIRALAMASI</b>\n"]
    for i, row in enumerate(rows):
        lines.append(f"{medals[i]} {ui.esc(row['first_name'])} — <b>{row['pvp_wins']}</b>G / {row['pvp_losses']}Y")
    return "\n".join(lines)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if user is None:
        await ui.answer(query, "Önce bota özelden /start yaz.", alert=True)
        return

    lang = i18n.lang_of(user_id)
    if action == "menu":
        await ui.answer(query)
        private = ui.is_private(update)
        await ui.nav(query, "duel", pvp_menu_text(user, private), pvp_menu_kb(private, lang))
    elif action == "on":
        await ui.answer(query)
        rows = [[(f"{MODES[g][0]} {MODES[g][1]}", f"pvp:ong:{g}")] for g in ONLINE_GAMES]
        rows.append([(i18n.t(lang, "b_back"), "pvp:menu")])
        await ui.safe_edit(query, (
            f"🌐 <b>{i18n.t(lang, 'd_online')}</b>\n{ui.LINE}\n{ui.header(user)}\n"
            f"{i18n.t(lang, 'g_pick')}"
        ), ui.kb(rows))
    elif action == "ong":
        await ui.answer(query)
        game = parts[2]
        emoji, name, desc = MODES[game]
        rows = ui.bet_rows(f"pvp:onq:{game}", user)[:-1]
        rows.append([(i18n.t(lang, "b_back"), "pvp:on")])
        await ui.safe_edit(query, (
            f"{emoji} <b>{name}</b>\n{ui.LINE}\n{ui.header(user)}\n"
            f"{i18n.t(lang, 'g_choose_bet')}"
        ), ui.kb(rows))
    elif action == "onq":
        await ui.answer(query)
        await queue_join(update, context, parts[2], int(parts[3]))
    elif action == "onc":
        await ui.answer(query)
        await queue_leave(update, context)
    elif action == "new":
        await ui.answer(query)
        if ui.is_private(update):
            await ui.answer(query, "Düellolar gruplarda kurulur. Beni bir gruba ekle!", alert=True)
            return
        game = parts[2]
        emoji, name, desc = MODES[game]
        await ui.safe_edit(query, (
            f"{emoji} <b>{name.upper()}</b>\n<i>{desc}</i>\n\n"
            f"{ui.header(user)}\n\nBahsi seç — rakip aynı tutarı yatırır 👇"
        ), ui.kb(ui.bet_rows(f"pvp:mk:{game}", user)[:-1] + [[("⬅️ PVP", "pvp:menu"), ("🏠 Menü", "m:main")]]))
    elif action == "mk":
        await ui.answer(query)
        await create_duel(update, context, parts[2], int(parts[3]))
    elif action == "acc":
        await accept_duel(update, context, int(parts[2]))
    elif action == "cancel":
        await cancel_duel(update, context, int(parts[2]))
    elif action == "rps":
        await rps_pick(update, context, int(parts[2]), parts[3])
    elif action == "xox":
        await xox_move(update, context, int(parts[2]), int(parts[3]))
    elif action == "box":
        await box_pick(update, context, int(parts[2]), int(parts[3]))
    elif action == "list":
        await ui.answer(query)
        await ui.safe_edit(query, open_duels_text(), ui.kb([
            [("🔄 Yenile", "pvp:list")], [("⚔️ PVP Menü", "pvp:menu")]]))
    elif action == "top":
        await ui.answer(query)
        await ui.safe_edit(query, pvp_top_text(), ui.back_kb("pvp:menu"))


ALIASES = {
    "tkm": "rps", "taş": "rps", "rps": "rps",
    "xox": "xox", "zar": "dice", "dice": "dice",
    "arena": "arena", "savaş": "arena", "kutu": "box", "box": "box",
}


async def cmd_duel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/duello [mod] [bahis]"""
    args = context.args or []
    user = db.get_user(update.effective_user.id)
    if ui.is_private(update):
        await ui.send(update, pvp_menu_text(user, True), pvp_menu_kb(True))
        return
    if len(args) >= 2 and args[0].lower() in ALIASES:
        try:
            stake = int(args[1].replace(".", "").replace("k", "000"))
        except ValueError:
            await ui.send(update, "Bahis sayı olmalı. Örnek: <code>/duello tkm 1000</code>")
            return
        await create_duel(update, context, ALIASES[args[0].lower()], stake)
        return
    rows = [[(f"{e} {n}", f"pvp:new:{k}")] for k, (e, n, _d) in MODES.items()]
    rows.append([("📋 Açık Düellolar", "pvp:list")])
    await ui.send(update, (
        "⚔️ <b>DÜELLO KUR</b>\n\n"
        f"{ui.header(user)}\n\n"
        "Bir mod seç ya da hızlı yol:\n"
        "<code>/duello tkm 1000</code>\n"
        "<code>/duello xox 5000</code>\n"
        "<code>/duello zar 500</code>\n"
        "<code>/duello arena 10000</code>\n"
        "<code>/duello kutu 2500</code>\n\n"
        "Açık düellolara katılmak için: <code>/kabul &lt;numara&gt;</code>"
    ), ui.kb(rows))


async def cmd_accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await ui.send(update, open_duels_text(), ui.kb([[("⚔️ Düello Kur", "pvp:menu")]]))
        return
    try:
        duel_id = int(args[0].lstrip("#"))
    except ValueError:
        await ui.send(update, "Örnek: <code>/kabul 42</code>")
        return
    await accept_duel(update, context, duel_id)


async def job_cleanup(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Süresi geçen açık düelloların bahsini iade eder."""
    rows = db.all_("SELECT * FROM duels WHERE state='open' AND created_ts < ?", (ui.now() - DUEL_TIMEOUT,))
    for row in rows:
        db.run("UPDATE duels SET state='expired' WHERE id=?", (row["id"],))
        economy.add_coins(row["p1"], row["stake"], "pvp süre doldu iadesi")
        try:
            await context.bot.edit_message_text(
                f"⏰ Düello #{row['id']} zaman aşımına uğradı. Bahis iade edildi.",
                chat_id=row["chat_id"], message_id=row["message_id"])
        except Exception:
            pass
