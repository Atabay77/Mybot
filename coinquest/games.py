# -*- coding: utf-8 -*-
"""Tek kişilik oyunlar: slot, mayın, blackjack, rulet, çark, yazı-tura, zar,
beceri oyunları (bilgi/matematik/kelime/refleks) ve PvE aktiviteleri (çalış, maden, arena)."""
import asyncio
import math
import random
import time
from typing import Optional

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

# ---------------------------------------------------------------------------
# ORTAK YARDIMCILAR
# ---------------------------------------------------------------------------

GAMES_INFO = {
    "slots": ("🎰", "Slot Makinesi", "3 aynı sembol tut, 700x'e kadar kazan"),
    "mines": ("💣", "Mayın Tarlası", "Elmas topla, patlamadan çekil"),
    "bj": ("🃏", "Blackjack", "21'i geçmeden krupiyeyi yen"),
    "hilo": ("🎴", "Yüksek / Düşük", "Sonraki kart yüksek mi düşük mü?"),
    "rlt": ("🎡", "Rulet", "Renk, tek/çift veya sayıya oyna"),
    "wheel": ("🎯", "Şans Çarkı", "Tek tıkla çarkı çevir"),
    "cf": ("🪙", "Yazı Tura", "Klasik 50/50"),
    "dice": ("🎲", "Zar Oyunu", "Telegram zarıyla gerçek atış"),
    "crash": ("🚀", "Roket", "Patlamadan önce çık"),
}


def games_menu_text(user, lang: str = i18n.DEFAULT) -> str:
    """Sade oyun menüsü: 3 kategori."""
    return (
        f"{i18n.t(lang, 'g_title')}\n{ui.LINE}\n"
        f"{ui.header(user)}\n"
        f"<blockquote>🎲 {i18n.t(lang, 'g_luck_info')}\n"
        f"🧠 {i18n.t(lang, 'g_brain_info')}\n"
        f"⚒ {i18n.t(lang, 'g_work_info')}</blockquote>\n"
        f"{i18n.t(lang, 'g_pick')}"
    )


def games_menu_kb(lang: str = i18n.DEFAULT):
    return ui.kb([
        [(i18n.t(lang, "g_luck"), "g:cat:luck")],
        [(i18n.t(lang, "g_brain"), "g:cat:brain")],
        [(i18n.t(lang, "g_work"), "g:cat:work")],
        [(i18n.t(lang, "b_money"), "cash:menu"), (i18n.t(lang, "b_home"), "m:main")],
    ])


CATEGORIES = {
    "luck": [
        [("🎰 Slot", "g:pick:slots"), ("💣 Mina", "g:pick:mines")],
        [("🃏 Blackjack", "g:pick:bj"), ("🎴 Hi-Lo", "g:pick:hilo")],
        [("🎡 Ruletka", "g:pick:rlt"), ("🎯 Wheel", "g:pick:wheel")],
        [("🪙 Orёl/Reşka", "g:pick:cf"), ("🎲 Zar", "g:pick:dice")],
        [("🚀 Raketa", "g:pick:crash")],
    ],
    "brain": [
        [("🧠 Sorag-jogap", "g:sk:quiz")],
        [("➗ Matematika", "g:sk:math")],
        [("🔤 Söz", "g:sk:word")],
        [("⚡ Refleks", "g:sk:reflex")],
    ],
    "work": [
        [("💼 Iş / Работа", "g:work")],
        [("⛏ Magdan / Шахта", "g:mine")],
        [("🗡 Arena", "g:arena")],
    ],
}


def category_kb(cat: str, lang: str = i18n.DEFAULT):
    rows = [list(row) for row in CATEGORIES[cat]]
    rows.append([(i18n.t(lang, "b_back"), "g:menu"), (i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


def category_text(cat: str, user, lang: str = i18n.DEFAULT) -> str:
    title = {"luck": "g_luck", "brain": "g_brain", "work": "g_work"}[cat]
    info = {"luck": "g_luck_info", "brain": "g_brain_info", "work": "g_work_info"}[cat]
    text = (f"<b>{i18n.t(lang, title)}</b>\n{ui.LINE}\n"
            f"{ui.header(user)}\n<i>{i18n.t(lang, info)}</i>\n")
    if cat == "luck":
        text += "\n" + i18n.t(lang, "g_bet_range", min=ui.fmt(config.MIN_BET),
                              max=ui.fmt(economy.max_bet(user)))
    return text + "\n" + i18n.t(lang, "g_pick")


def validate_bet(user, amount: int) -> tuple[bool, str]:
    if amount < config.MIN_BET:
        return False, f"Minimum bahis {ui.fmt(config.MIN_BET)} altın."
    cap = economy.max_bet(user)
    if amount > cap:
        return False, f"Seviyende maksimum bahis {ui.fmt(cap)} altın. Seviye atlayarak limiti yükselt!"
    if amount > user["coins"]:
        return False, f"Bakiyen yetersiz ({ui.fmt(user['coins'])} 🪙)."
    return True, ""


def clear_sessions(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in ("mines", "hilo", "bj", "crash", "skill"):
        context.user_data.pop(key, None)


def settle(user_id: int, bet: int, won: int, game: str) -> str:
    """Bahis sonucunu işler ve sonuç satırını döner."""
    user = db.get_user(user_id)
    if won > 0:
        won = economy.payout(user, won)
        economy.add_coins(user_id, won, f"{game} kazanç")
    economy.register_game(user_id, bet, won)
    economy.add_xp(user_id, max(5, min(200, bet // 100 + 8)))
    events.track(user_id, "play")
    events.track(user_id, "wager", bet)
    if won > bet:
        events.track(user_id, "win")
    profit = won - bet
    if profit > 0:
        return f"✅ <b>+{ui.fmt(profit)}</b> 🪙 kâr!"
    if profit == 0:
        return "➖ Berabere, bahsin geri döndü."
    return f"❌ <b>-{ui.fmt(bet - won)}</b> 🪙 kayıp."


async def result_screen(query, user_id: int, text: str, again_cb: str) -> None:
    unlocked = events.check_achievements(user_id)
    if unlocked:
        text += "\n\n🏅 <b>YENİ BAŞARIM!</b>\n" + "\n".join(unlocked)
    user = db.get_user(user_id)
    text += f"\n\n{ui.header(user)}"
    lang = i18n.lang_of(user_id)
    await ui.safe_edit(query, text, ui.kb([
        [(i18n.t(lang, "b_again"), again_cb)],
        [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_home"), "m:main")],
    ]))


# ---------------------------------------------------------------------------
# 1) SLOT MAKİNESİ
# ---------------------------------------------------------------------------
SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣", "🃏"]
SLOT_WEIGHTS = [30, 25, 18, 12, 8, 5, 2]
SLOT_TRIPLE = {"🍒": 9, "🍋": 14, "🍇": 25, "🔔": 45, "💎": 90, "7️⃣": 200, "🃏": 700}
SLOT_PAIR = {"💎": 3, "7️⃣": 4, "🃏": 10}


def spin_slots() -> tuple[list[str], float, str]:
    reels = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    if reels[0] == reels[1] == reels[2]:
        return reels, SLOT_TRIPLE[reels[0]], f"ÜÇLÜ {reels[0]}{reels[0]}{reels[0]}"
    for sym, mult in SLOT_PAIR.items():
        if reels.count(sym) == 2:
            return reels, mult, f"ÇİFT {sym}{sym}"
    return reels, 0.0, ""


async def play_slots(query, context, user_id: int, bet: int) -> None:
    reels, mult, label = spin_slots()
    won = int(bet * mult)
    line = settle(user_id, bet, won, "slot")
    frames = ["🎰 | ❓ ❓ ❓ |", f"🎰 | {reels[0]} ❓ ❓ |", f"🎰 | {reels[0]} {reels[1]} ❓ |"]
    for frame in frames:
        await ui.safe_edit(query, f"<b>{frame}</b>\n\nBahis: {ui.fmt(bet)} 🪙")
        await asyncio.sleep(0.45)
    text = (
        f"🎰 <b>SLOT MAKİNESİ</b>\n\n"
        f"┏━━━━━━━━━━━┓\n"
        f"┃  {reels[0]}  {reels[1]}  {reels[2]}  ┃\n"
        f"┗━━━━━━━━━━━┛\n\n"
        f"Bahis: {ui.fmt(bet)} 🪙\n"
    )
    if mult:
        text += f"🎉 <b>{label}</b> — {mult:g}x → {ui.fmt(won)} 🪙\n{line}"
    else:
        text += f"😔 Kazanan kombinasyon yok.\n{line}"
    await result_screen(query, user_id, text, f"g:play:slots:{bet}")


# ---------------------------------------------------------------------------
# 2) ŞANS ÇARKI
# ---------------------------------------------------------------------------
WHEEL = [(0, "💀 Boş"), (0, "💀 Boş"), (0, "💀 Boş"), (0, "💀 Boş"), (0, "💀 Boş"),
         (0.5, "😐 0.5x"), (0.5, "😐 0.5x"), (0.5, "😐 0.5x"),
         (1, "🙂 1x"), (1.5, "😄 1.5x"), (2, "🤩 2x"), (5, "🚀 5x")]


async def play_wheel(query, context, user_id: int, bet: int) -> None:
    for _ in range(3):
        await ui.safe_edit(query, f"🎯 <b>ÇARK DÖNÜYOR...</b>\n\n{random.choice(WHEEL)[1]}\n\nBahis: {ui.fmt(bet)} 🪙")
        await asyncio.sleep(0.4)
    mult, label = random.choice(WHEEL)
    won = int(bet * mult)
    line = settle(user_id, bet, won, "çark")
    text = (
        f"🎯 <b>ŞANS ÇARKI</b>\n\n"
        f"Çark durdu: <b>{label}</b>\n"
        f"Bahis: {ui.fmt(bet)} 🪙 → Kazanç: {ui.fmt(won)} 🪙\n\n{line}"
    )
    await result_screen(query, user_id, text, f"g:play:wheel:{bet}")


# ---------------------------------------------------------------------------
# 3) YAZI TURA
# ---------------------------------------------------------------------------
async def play_coinflip(query, context, user_id: int, bet: int, side: str) -> None:
    result = random.choice(["y", "t"])
    win = result == side
    won = int(bet * 1.9) if win else 0
    line = settle(user_id, bet, won, "yazı-tura")
    names = {"y": "🅨 Yazı", "t": "🅣 Tura"}
    for emoji in ("🪙", "💫", "🪙", "💫"):
        await ui.safe_edit(query, f"{emoji} <b>Para havada...</b>")
        await asyncio.sleep(0.3)
    text = (
        f"🪙 <b>YAZI TURA</b>\n\n"
        f"Senin seçimin: {names[side]}\n"
        f"Sonuç: <b>{names[result]}</b>\n\n"
        f"{'🎉 Kazandın! 1.9x → ' + ui.fmt(won) + ' 🪙' if win else '😔 Kaybettin.'}\n{line}"
    )
    await result_screen(query, user_id, text, f"g:cfbet:{bet}")


# ---------------------------------------------------------------------------
# 4) ZAR (Telegram yerel zarı)
# ---------------------------------------------------------------------------
DICE_BETS = {
    "hi": ("Yüksek (4-6)", 1.9, lambda v: v >= 4),
    "lo": ("Düşük (1-3)", 1.9, lambda v: v <= 3),
    "even": ("Çift", 1.9, lambda v: v % 2 == 0),
    "six": ("Tam 6", 5.0, lambda v: v == 6),
    "one": ("Tam 1", 5.0, lambda v: v == 1),
}


async def play_dice(query, context, user_id: int, bet: int, choice: str) -> None:
    label, mult, check = DICE_BETS[choice]
    chat_id = query.message.chat_id
    try:
        msg = await context.bot.send_dice(chat_id, emoji="🎲")
        value = msg.dice.value
        await asyncio.sleep(3.6)
    except Exception:
        value = random.randint(1, 6)
    win = check(value)
    won = int(bet * mult) if win else 0
    line = settle(user_id, bet, won, "zar")
    text = (
        f"🎲 <b>ZAR OYUNU</b>\n\n"
        f"Tahminin: <b>{label}</b> ({mult:g}x)\n"
        f"Zar: <b>{value}</b>\n\n"
        f"{'🎉 Doğru tahmin! → ' + ui.fmt(won) + ' 🪙' if win else '😔 Tutmadı.'}\n{line}"
    )
    await result_screen(query, user_id, text, f"g:dicebet:{bet}")


# ---------------------------------------------------------------------------
# 5) RULET
# ---------------------------------------------------------------------------
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def roulette_eval(sel: str, number: int) -> tuple[bool, float, str]:
    if sel == "red":
        return number in RED, 2.0, "🔴 Kırmızı"
    if sel == "black":
        return number != 0 and number not in RED, 2.0, "⚫ Siyah"
    if sel == "even":
        return number != 0 and number % 2 == 0, 2.0, "Çift"
    if sel == "odd":
        return number % 2 == 1, 2.0, "Tek"
    if sel == "low":
        return 1 <= number <= 18, 2.0, "1-18"
    if sel == "high":
        return 19 <= number <= 36, 2.0, "19-36"
    if sel.startswith("d"):
        idx = int(sel[1])
        lo, hi = (idx - 1) * 12 + 1, idx * 12
        return lo <= number <= hi, 3.0, f"{lo}-{hi} düzine"
    if sel == "zero":
        return number == 0, 35.0, "🟢 0"
    return False, 0.0, "?"


async def play_roulette(query, context, user_id: int, bet: int, sel: str) -> None:
    for _ in range(3):
        await ui.safe_edit(query, f"🎡 <b>RULET DÖNÜYOR...</b>\n\n🔵 {random.randint(0, 36)} 🔵")
        await asyncio.sleep(0.4)
    number = random.randint(0, 36)
    win, mult, label = roulette_eval(sel, number)
    won = int(bet * mult) if win else 0
    line = settle(user_id, bet, won, "rulet")
    color = "🟢" if number == 0 else ("🔴" if number in RED else "⚫")
    text = (
        f"🎡 <b>RULET</b>\n\n"
        f"Bahsin: <b>{label}</b> ({mult:g}x)\n"
        f"Sonuç: {color} <b>{number}</b>\n\n"
        f"{'🎉 Kazandın! → ' + ui.fmt(won) + ' 🪙' if win else '😔 Kaybettin.'}\n{line}"
    )
    await result_screen(query, user_id, text, f"g:rltbet:{bet}")


# ---------------------------------------------------------------------------
# 6) MAYIN TARLASI
# ---------------------------------------------------------------------------
def mines_mult(mines: int, picks: int) -> float:
    total = 25
    mult = 0.95
    for i in range(picks):
        mult *= (total - i) / (total - mines - i)
    return round(mult, 3)


def mines_kb(session: dict, revealed: bool = False):
    rows = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            if idx in session["picked"]:
                label = "💎"
            elif revealed and idx in session["bombs"]:
                label = "💥"
            else:
                label = "⬜"
            row.append((label, f"g:mnp:{idx}" if not revealed else "g:noop"))
        rows.append(row)
    if not revealed:
        cash = int(session["bet"] * mines_mult(session["mines"], len(session["picked"])))
        if session["picked"]:
            rows.append([(f"💰 ÇEK ({ui.fmt(cash)} 🪙)", "g:mnc")])
        rows.append([("🏳 Vazgeç", "g:mnq")])
    else:
        rows.append([("🔄 Tekrar", f"g:mnbet:{session['bet']}"), ("🎮 Oyunlar", "g:menu")])
    return ui.kb(rows)


def mines_text(session: dict, extra: str = "") -> str:
    picks = len(session["picked"])
    mult = mines_mult(session["mines"], picks)
    nxt = mines_mult(session["mines"], picks + 1)
    return (
        f"💣 <b>MAYIN TARLASI</b>\n\n"
        f"Bahis: {ui.fmt(session['bet'])} 🪙  •  Mayın: {session['mines']} 💣\n"
        f"Açılan: {picks} 💎  •  Çarpan: <b>{mult:g}x</b>\n"
        f"Sıradaki kutu: {nxt:g}x ({ui.fmt(int(session['bet'] * nxt))} 🪙)\n"
        f"{extra}"
    )


async def start_mines(query, context, user_id: int, bet: int, mines: int) -> None:
    session = {
        "bet": bet, "mines": mines,
        "bombs": set(random.sample(range(25), mines)),
        "picked": set(),
    }
    context.user_data["mines"] = session
    await ui.safe_edit(query, mines_text(session, "\nBir kutu seç 👇"), mines_kb(session))


async def mines_pick(query, context, user_id: int, idx: int) -> None:
    session = context.user_data.get("mines")
    if not session:
        await query.answer("Aktif oyun bulunamadı, yeniden başlat.", show_alert=True)
        return
    if idx in session["picked"]:
        await query.answer("Bu kutu zaten açık.")
        return
    if idx in session["bombs"]:
        context.user_data.pop("mines", None)
        line = settle(user_id, session["bet"], 0, "mayın")
        text = (
            f"💥 <b>BOOM! Mayına bastın.</b>\n\n"
            f"Bahis: {ui.fmt(session['bet'])} 🪙 kaybedildi.\n{line}"
        )
        await ui.safe_edit(query, text, mines_kb(session, revealed=True))
        return
    session["picked"].add(idx)
    if len(session["picked"]) >= 25 - session["mines"]:
        await mines_cash(query, context, user_id, perfect=True)
        return
    await query.answer("💎 Elmas!")
    await ui.safe_edit(query, mines_text(session, "\nDevam et ya da parayı çek 👇"), mines_kb(session))


async def mines_cash(query, context, user_id: int, perfect: bool = False) -> None:
    session = context.user_data.pop("mines", None)
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    picks = len(session["picked"])
    if picks == 0:
        settle(user_id, session["bet"], session["bet"], "mayın")
        await ui.safe_edit(query, "🏳 Oyundan çıktın, bahsin geri verildi.", games_menu_kb(i18n.lang_of(user_id)))
        return
    mult = mines_mult(session["mines"], picks)
    won = int(session["bet"] * mult)
    line = settle(user_id, session["bet"], won, "mayın")
    head = "🏆 <b>MÜKEMMEL! Tüm elmasları topladın!</b>" if perfect else "💰 <b>Parayı çektin!</b>"
    text = (
        f"{head}\n\n"
        f"{picks} elmas • {mult:g}x çarpan\n"
        f"Kazanç: <b>{ui.fmt(won)}</b> 🪙\n{line}"
    )
    await result_screen(query, user_id, text, f"g:mnbet:{session['bet']}")


# ---------------------------------------------------------------------------
# 7) YÜKSEK / DÜŞÜK
# ---------------------------------------------------------------------------
RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}
SUITS = ["♠️", "♥️", "♦️", "♣️"]


def card_str(card: tuple[int, str]) -> str:
    rank, suit = card
    return f"{RANK_NAMES.get(rank, rank)}{suit}"


def new_deck() -> list[tuple[int, str]]:
    deck = [(r, s) for r in range(2, 15) for s in SUITS]
    random.shuffle(deck)
    return deck


def hilo_kb(session: dict):
    rows = [[("⬆️ Yüksek", "g:hlg:hi"), ("⬇️ Düşük", "g:hlg:lo")]]
    if session["mult"] > 1:
        rows.append([(f"💰 ÇEK ({ui.fmt(int(session['bet'] * session['mult']))} 🪙)", "g:hlc")])
    rows.append([("🏳 Vazgeç", "g:hlq")])
    return ui.kb(rows)


def hilo_text(session: dict, extra: str = "") -> str:
    remaining = session["deck"]
    cur = session["card"][0]
    higher = sum(1 for r, _ in remaining if r > cur)
    lower = sum(1 for r, _ in remaining if r < cur)
    total = len(remaining) or 1
    return (
        f"🎴 <b>YÜKSEK / DÜŞÜK</b>\n\n"
        f"Kart: <b>{card_str(session['card'])}</b>\n"
        f"Seri: {session['streak']}  •  Çarpan: <b>{session['mult']:.2f}x</b>\n"
        f"Potansiyel: {ui.fmt(int(session['bet'] * session['mult']))} 🪙\n\n"
        f"⬆️ Yüksek şansı: %{higher / total * 100:.0f}   ⬇️ Düşük şansı: %{lower / total * 100:.0f}\n"
        f"{extra}"
    )


async def start_hilo(query, context, user_id: int, bet: int) -> None:
    deck = new_deck()
    card = deck.pop()
    session = {"bet": bet, "deck": deck, "card": card, "mult": 1.0, "streak": 0}
    context.user_data["hilo"] = session
    await ui.safe_edit(query, hilo_text(session, "Tahminini yap 👇"), hilo_kb(session))


async def hilo_guess(query, context, user_id: int, guess: str) -> None:
    session = context.user_data.get("hilo")
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    deck = session["deck"]
    cur = session["card"][0]
    total = len(deck)
    if total == 0:
        await hilo_cash(query, context, user_id)
        return
    if guess == "hi":
        favorable = sum(1 for r, _ in deck if r > cur)
    else:
        favorable = sum(1 for r, _ in deck if r < cur)
    prob = favorable / total if total else 0
    nxt = deck.pop()
    session["card"] = nxt
    if nxt[0] == cur:
        await query.answer("➖ Eşit kart! Çarpan korundu.")
        await ui.safe_edit(query, hilo_text(session, f"Eşit çıktı ({card_str(nxt)}), devam!"), hilo_kb(session))
        return
    correct = (nxt[0] > cur) if guess == "hi" else (nxt[0] < cur)
    if not correct:
        context.user_data.pop("hilo", None)
        line = settle(user_id, session["bet"], 0, "yüksek-düşük")
        text = (
            f"❌ <b>YANLIŞ TAHMİN</b>\n\n"
            f"Kart: <b>{card_str(nxt)}</b> geldi.\n"
            f"{session['streak']} serilik zincir koptu, {ui.fmt(session['bet'])} 🪙 gitti.\n{line}"
        )
        await result_screen(query, user_id, text, f"g:hlbet:{session['bet']}")
        return
    step = min(6.0, (0.94 / prob) if prob > 0 else 1.0)
    session["mult"] = round(session["mult"] * step, 3)
    session["streak"] += 1
    await query.answer(f"✅ Doğru! {step:.2f}x")
    await ui.safe_edit(query, hilo_text(session, f"Gelen kart: <b>{card_str(nxt)}</b> — devam?"), hilo_kb(session))


async def hilo_cash(query, context, user_id: int) -> None:
    session = context.user_data.pop("hilo", None)
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    won = int(session["bet"] * session["mult"])
    line = settle(user_id, session["bet"], won, "yüksek-düşük")
    text = (
        f"💰 <b>PARAYI ÇEKTİN</b>\n\n"
        f"{session['streak']} doğru tahmin • {session['mult']:.2f}x\n"
        f"Kazanç: <b>{ui.fmt(won)}</b> 🪙\n{line}"
    )
    await result_screen(query, user_id, text, f"g:hlbet:{session['bet']}")


# ---------------------------------------------------------------------------
# 8) BLACKJACK
# ---------------------------------------------------------------------------
def hand_value(hand: list[tuple[int, str]]) -> int:
    total, aces = 0, 0
    for rank, _ in hand:
        if rank == 14:
            aces += 1
            total += 11
        elif rank >= 11:
            total += 10
        else:
            total += rank
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def hand_str(hand: list[tuple[int, str]]) -> str:
    return " ".join(card_str(c) for c in hand)


def bj_text(session: dict, reveal: bool = False, extra: str = "") -> str:
    dealer = session["dealer"]
    dealer_view = hand_str(dealer) if reveal else f"{card_str(dealer[0])} 🂠"
    dealer_val = hand_value(dealer) if reveal else "?"
    return (
        f"🃏 <b>BLACKJACK</b>\n\n"
        f"🎩 Krupiye: {dealer_view}  (<b>{dealer_val}</b>)\n"
        f"👤 Sen: {hand_str(session['player'])}  (<b>{hand_value(session['player'])}</b>)\n\n"
        f"Bahis: {ui.fmt(session['bet'])} 🪙\n{extra}"
    )


async def start_bj(query, context, user_id: int, bet: int) -> None:
    deck = new_deck()
    session = {"bet": bet, "deck": deck, "player": [deck.pop(), deck.pop()],
               "dealer": [deck.pop(), deck.pop()], "doubled": False}
    context.user_data["bj"] = session
    if hand_value(session["player"]) == 21:
        await bj_finish(query, context, user_id, natural=True)
        return
    await ui.safe_edit(query, bj_text(session, extra="Kartını çek ya da dur 👇"), ui.kb([
        [("🃏 Kart Çek", "g:bjm:hit"), ("✋ Dur", "g:bjm:stand")],
        [("💥 Iki Katı", "g:bjm:double")],
    ]))


async def bj_move(query, context, user_id: int, move: str) -> None:
    session = context.user_data.get("bj")
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    if move == "double":
        if session["doubled"] or len(session["player"]) > 2:
            await query.answer("İki katı sadece başta yapılabilir.", show_alert=True)
            return
        user = db.get_user(user_id)
        if user["coins"] < session["bet"]:
            await query.answer("İki katı için yeterli altın yok.", show_alert=True)
            return
        economy.take_coins(user_id, session["bet"], "blackjack iki katı")
        session["bet"] *= 2
        session["doubled"] = True
        session["player"].append(session["deck"].pop())
        await bj_finish(query, context, user_id)
        return
    if move == "hit":
        session["player"].append(session["deck"].pop())
        value = hand_value(session["player"])
        if value > 21:
            await bj_finish(query, context, user_id)
            return
        if value == 21:
            await bj_finish(query, context, user_id)
            return
        await ui.safe_edit(query, bj_text(session, extra="Devam?"), ui.kb([
            [("🃏 Kart Çek", "g:bjm:hit"), ("✋ Dur", "g:bjm:stand")],
        ]))
        return
    await bj_finish(query, context, user_id)


async def bj_finish(query, context, user_id: int, natural: bool = False) -> None:
    session = context.user_data.pop("bj", None)
    if not session:
        return
    player = hand_value(session["player"])
    while hand_value(session["dealer"]) < 17:
        session["dealer"].append(session["deck"].pop())
    dealer = hand_value(session["dealer"])
    bet = session["bet"]

    if natural and player == 21:
        won = int(bet * 2.5)
        verdict = "🌟 <b>BLACKJACK!</b> 2.5x ödeme!"
    elif player > 21:
        won, verdict = 0, "💥 <b>Battın!</b> 21'i geçtin."
    elif dealer > 21:
        won, verdict = bet * 2, "🎉 <b>Krupiye battı, kazandın!</b>"
    elif player > dealer:
        won, verdict = bet * 2, "🎉 <b>Kazandın!</b>"
    elif player == dealer:
        won, verdict = bet, "➖ <b>Berabere</b> (push)."
    else:
        won, verdict = 0, "😔 <b>Krupiye kazandı.</b>"

    line = settle(user_id, bet, won, "blackjack")
    text = bj_text(session, reveal=True, extra=f"{verdict}\n{line}")
    await result_screen(query, user_id, text, f"g:bjbet:{bet // (2 if session['doubled'] else 1)}")


# ---------------------------------------------------------------------------
# 9) ROKET (crash)
# ---------------------------------------------------------------------------
def crash_point() -> float:
    """%4 ev avantajıyla üstel dağılım."""
    r = random.random()
    if r < 0.04:
        return 1.0
    return round(max(1.01, 0.96 / (1 - r)), 2)


def crash_kb(session: dict):
    return ui.kb([
        [(f"💰 ÇIK ({ui.fmt(int(session['bet'] * session['mult']))} 🪙)", "g:crc")],
        [("⏭ 1 Adım İlerle", "g:crs")],
    ])


CRASH_STEPS = [1.15, 1.35, 1.6, 1.9, 2.3, 2.8, 3.5, 4.4, 5.6, 7.2, 9.5, 12.5, 17.0, 25.0, 40.0]


def crash_text(session: dict, extra: str = "") -> str:
    return (
        f"🚀 <b>ROKET</b>\n\n"
        f"{'▁' * session['step']}🚀\n\n"
        f"Çarpan: <b>{session['mult']:.2f}x</b>\n"
        f"Şu an çıkarsan: <b>{ui.fmt(int(session['bet'] * session['mult']))}</b> 🪙\n"
        f"Bahis: {ui.fmt(session['bet'])} 🪙\n\n"
        f"{extra}"
    )


async def start_crash(query, context, user_id: int, bet: int) -> None:
    session = {"bet": bet, "mult": 1.0, "step": 0, "crash": crash_point()}
    context.user_data["crash"] = session
    await ui.safe_edit(query, crash_text(session, "Roket kalkıyor! Ne zaman çıkacaksın?"), crash_kb(session))


async def crash_step(query, context, user_id: int) -> None:
    session = context.user_data.get("crash")
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    step = min(len(CRASH_STEPS) - 1, session["step"])
    target = CRASH_STEPS[step]
    session["step"] += 1
    if target >= session["crash"]:
        context.user_data.pop("crash", None)
        line = settle(user_id, session["bet"], 0, "roket")
        text = (
            f"💥 <b>ROKET PATLADI — {session['crash']:.2f}x</b>\n\n"
            f"{ui.fmt(session['bet'])} 🪙 uzaya gitti.\n{line}"
        )
        await result_screen(query, user_id, text, f"g:crbet:{session['bet']}")
        return
    session["mult"] = target
    await query.answer(f"🚀 {target:.2f}x")
    await ui.safe_edit(query, crash_text(session, "Devam mı, çıkış mı?"), crash_kb(session))


async def crash_cash(query, context, user_id: int) -> None:
    session = context.user_data.pop("crash", None)
    if not session:
        await query.answer("Aktif oyun yok.", show_alert=True)
        return
    won = int(session["bet"] * session["mult"])
    line = settle(user_id, session["bet"], won, "roket")
    text = (
        f"🪂 <b>TAM ZAMANINDA ÇIKTIN!</b>\n\n"
        f"Çarpan: {session['mult']:.2f}x  (roket {session['crash']:.2f}x'te patlayacaktı)\n"
        f"Kazanç: <b>{ui.fmt(won)}</b> 🪙\n{line}"
    )
    await result_screen(query, user_id, text, f"g:crbet:{session['bet']}")


# ---------------------------------------------------------------------------
# BECERİ OYUNLARI
# ---------------------------------------------------------------------------
QUIZ = [
    ("Türkiye'nin başkenti neresidir?", ["Ankara", "İstanbul", "İzmir", "Bursa"], 0),
    ("Bir futbol maçı kaç dakikadır?", ["90", "80", "100", "120"], 0),
    ("Güneş sistemindeki en büyük gezegen?", ["Jüpiter", "Satürn", "Dünya", "Mars"], 0),
    ("Suyun kimyasal formülü?", ["H2O", "CO2", "O2", "NaCl"], 0),
    ("İstiklal Marşı'nın şairi?", ["Mehmet Akif Ersoy", "Namık Kemal", "Ziya Gökalp", "Tevfik Fikret"], 0),
    ("Bir yılda kaç hafta vardır?", ["52", "48", "50", "56"], 0),
    ("En kalabalık ülke hangisidir?", ["Hindistan", "Çin", "ABD", "Rusya"], 0),
    ("Mona Lisa'yı kim çizdi?", ["Leonardo da Vinci", "Picasso", "Van Gogh", "Michelangelo"], 0),
    ("Kaç kıta vardır?", ["7", "5", "6", "8"], 0),
    ("Türkiye'nin en uzun nehri?", ["Kızılırmak", "Fırat", "Sakarya", "Dicle"], 0),
    ("Işık hızı yaklaşık kaç km/s?", ["300.000", "150.000", "1.000.000", "30.000"], 0),
    ("Hangi kan grubu herkese verilebilir?", ["0 Rh-", "AB Rh+", "A Rh+", "B Rh-"], 0),
    ("Dünyanın en yüksek dağı?", ["Everest", "K2", "Kilimanjaro", "Ağrı"], 0),
    ("Bilgisayarın beyni sayılan parça?", ["CPU", "RAM", "GPU", "SSD"], 0),
    ("Osmanlı Devleti hangi yılda kuruldu?", ["1299", "1453", "1071", "1326"], 0),
    ("Bir düzine kaç tanedir?", ["12", "10", "20", "6"], 0),
    ("Hangi hayvan en hızlı koşar?", ["Çita", "Aslan", "At", "Kanguru"], 0),
    ("Python nedir?", ["Programlama dili", "İşletim sistemi", "Oyun", "Tarayıcı"], 0),
    ("Altının kimyasal sembolü?", ["Au", "Ag", "Fe", "Al"], 0),
    ("Kaç renk gökkuşağında bulunur?", ["7", "5", "6", "9"], 0),
    ("İnsan vücudunda kaç kemik var?", ["206", "180", "250", "300"], 0),
    ("Hangi ülkenin parası Yen'dir?", ["Japonya", "Çin", "Kore", "Tayland"], 0),
    ("Satrançta kaç kare vardır?", ["64", "81", "100", "49"], 0),
    ("Dünyanın en büyük okyanusu?", ["Pasifik", "Atlantik", "Hint", "Arktik"], 0),
    ("Bir üçgenin iç açıları toplamı?", ["180", "360", "90", "270"], 0),
    ("Telegram hangi yıl kuruldu?", ["2013", "2010", "2016", "2008"], 0),
    ("En küçük asal sayı?", ["2", "1", "3", "0"], 0),
    ("Hangi vitamin güneşten alınır?", ["D", "C", "B12", "A"], 0),
    ("Ampulü kim geliştirdi?", ["Edison", "Tesla", "Newton", "Bell"], 0),
    ("Kaç saniye bir saattir?", ["3600", "60", "1440", "600"], 0),
]

WORDS = [
    "kelebek", "bilgisayar", "portakal", "kütüphane", "yıldız", "denizanası", "kahvaltı",
    "şemsiye", "tornavida", "papatya", "kaplumbağa", "buzdolabı", "gökkuşağı", "sandalye",
    "telefon", "penguen", "helikopter", "çilek", "kalem", "orman", "ejderha", "kılıç",
    "hazine", "korsan", "labirent", "maden", "zümrüt", "şampiyon", "arena", "büyücü",
    "kristal", "volkan", "fener", "balon", "salatalık", "karpuz", "muhabbet", "yolculuk",
]


def scramble(word: str) -> str:
    letters = list(word)
    for _ in range(12):
        random.shuffle(letters)
        if "".join(letters) != word:
            break
    return " ".join(letters).upper()


def skill_cooldown_left(user) -> int:
    return economy.cooldown_left(user["last_skill"], config.SKILL_COOLDOWN)


async def start_skill(query, context, user_id: int, kind: str) -> None:
    user = db.get_user(user_id)
    left = skill_cooldown_left(user)
    if left > 0:
        await query.answer(
            f"⏳ BU OYUN ŞU AN TEKRAR OYNANAMAZ\n\n"
            f"Bilgi oyunları arasında {config.SKILL_COOLDOWN} saniye beklemek gerekiyor.\n"
            f"Kalan süre: {ui.dur(left)}\n\n"
            f"Bu arada 🎲 şans oyunlarını ya da 💼 çalışmayı dene.",
            show_alert=True)
        return
    db.upd(user_id, last_skill=ui.now())
    reward_base = 700 + user["level"] * 70

    if kind == "quiz":
        question, options, correct_idx = random.choice(QUIZ)
        order = list(range(len(options)))
        random.shuffle(order)
        shuffled = [options[i] for i in order]
        answer_pos = order.index(correct_idx)
        context.user_data["skill"] = {"kind": "quiz", "answer": answer_pos, "reward": reward_base,
                                      "ts": time.time(), "limit": config.QUIZ_SECONDS}
        rows = [[(f"{chr(65 + i)}) {opt}", f"g:qa:{i}")] for i, opt in enumerate(shuffled)]
        rows.append([("🎮 Oyunlar", "g:menu")])
        await ui.safe_edit(query, (
            f"🧠 <b>BİLGİ</b>\n{ui.LINE}\n"
            f"<blockquote>{ui.esc(question)}</blockquote>\n"
            f"⏱ <b>{config.QUIZ_SECONDS} saniye</b>  •  🏆 {ui.fmt(reward_base)} 🪙 + 30 XP"
        ), ui.kb(rows))

    elif kind == "math":
        a, b = random.randint(12, 99), random.randint(3, 25)
        op = random.choice(["+", "-", "*"])
        if op == "*":
            a, b = random.randint(3, 19), random.randint(3, 15)
        answer = {"+": a + b, "-": a - b, "*": a * b}[op]
        reward = int(reward_base * (1.6 if op == "*" else 1.2))
        secs = config.MATH_SECONDS
        context.user_data["skill"] = {"kind": "math", "answer": str(answer), "reward": reward,
                                      "ts": time.time(), "limit": secs}
        await ui.safe_edit(query, (
            f"➗ <b>MATEMATİK</b>\n{ui.LINE}\n"
            f"<blockquote><b>   {a} {op} {b} = ?   </b></blockquote>\n"
            f"⏱ <b>{secs} saniyen var!</b>  Cevabı hemen yaz.\n"
            f"🏆 Ödül: {ui.fmt(reward)} 🪙"
        ), ui.kb([[("🎮 Oyunlar", "g:menu")]]))

    elif kind == "word":
        word = random.choice(WORDS)
        reward = int(reward_base * 1.3)
        secs = config.WORD_SECONDS
        context.user_data["skill"] = {"kind": "word", "answer": word, "reward": reward,
                                      "ts": time.time(), "limit": secs}
        await ui.safe_edit(query, (
            f"🔤 <b>KELİME</b>\n{ui.LINE}\n"
            f"<blockquote><b>{scramble(word)}</b></blockquote>\n"
            f"⏱ <b>{secs} saniyen var!</b>\n🏆 Ödül: {ui.fmt(reward)} 🪙"
        ), ui.kb([[("🎮 Oyunlar", "g:menu")]]))

    elif kind == "reflex":
        target = random.randint(0, 8)
        context.user_data["skill"] = {"kind": "reflex", "answer": target, "reward": reward_base * 2,
                                      "ts": 0.0}
        await ui.safe_edit(query, "⚡ <b>REFLEKS TESTİ</b>\n\nHazır ol...")
        await asyncio.sleep(random.uniform(1.2, 2.6))
        session = context.user_data.get("skill")
        if not session or session["kind"] != "reflex":
            return
        session["ts"] = time.time()
        rows = []
        for r in range(3):
            row = []
            for c in range(3):
                idx = r * 3 + c
                row.append(("🎯" if idx == target else "⬛", f"g:rf:{idx}"))
            rows.append(row)
        await ui.safe_edit(query, (
            "⚡ <b>REFLEKS TESTİ</b>\n\n🎯 işaretine <b>hemen</b> bas!\n"
            f"Ne kadar hızlı, o kadar çok altın (max {ui.fmt(reward_base * 2)} 🪙)"
        ), ui.kb(rows))


async def skill_quiz_answer(query, context, user_id: int, idx: int) -> None:
    session = context.user_data.pop("skill", None)
    if not session or session["kind"] != "quiz":
        await query.answer("Bu soru artık geçerli değil.", show_alert=True)
        return
    elapsed = time.time() - session.get("ts", 0)
    if elapsed > session.get("limit", 10):
        await result_screen(query, user_id,
                            f"⏰ <b>SÜRE DOLDU!</b> ({elapsed:.0f} sn)\n\n"
                            f"Çok yavaş kaldın, ödül yok.", "g:sk:quiz")
        return
    if idx == session["answer"]:
        won = economy.payout(db.get_user(user_id), session["reward"])
        economy.add_coins(user_id, won, "bilgi yarışması")
        economy.add_xp(user_id, 30)
        events.track(user_id, "skill")
        events.track(user_id, "play")
        text = f"✅ <b>DOĞRU CEVAP!</b>\n\n+{ui.fmt(won)} 🪙  +30 XP"
    else:
        text = "❌ <b>Yanlış cevap.</b>\n\nBir sonraki soruda bol şans!"
    await result_screen(query, user_id, text, "g:sk:quiz")


async def skill_reflex_answer(query, context, user_id: int, idx: int) -> None:
    session = context.user_data.pop("skill", None)
    if not session or session["kind"] != "reflex":
        await query.answer("Bu tur bitti.", show_alert=True)
        return
    if not session["ts"]:
        await query.answer("Çok acele ettin! Hedef daha belirmemişti.", show_alert=True)
        return
    elapsed = time.time() - session["ts"]
    if idx != session["answer"]:
        text = f"❌ <b>Yanlış kare!</b>\n\nSüre: {elapsed:.2f} sn — ödül yok."
    else:
        factor = max(0.10, min(1.0, 1.0 - elapsed * 0.9))
        won = economy.payout(db.get_user(user_id), int(session["reward"] * factor))
        economy.add_coins(user_id, won, "refleks")
        economy.add_xp(user_id, 25)
        events.track(user_id, "skill")
        events.track(user_id, "play")
        rating = ("⚡ ŞİMŞEK GİBİ!" if elapsed < 0.6 else
                  "🔥 Hızlı!" if elapsed < 1.0 else "🐢 Yavaş kaldın")
        text = (
            f"🎯 <b>VURDUN!</b>\n\n{rating}\n"
            f"Tepki süresi: <b>{elapsed:.2f} sn</b>\n+{ui.fmt(won)} 🪙  +25 XP"
        )
    await result_screen(query, user_id, text, "g:sk:reflex")


async def on_text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Matematik/kelime oyunlarının metin cevabını işler. İşlediyse True döner."""
    session = context.user_data.get("skill")
    if not session or session["kind"] not in ("math", "word"):
        return False
    context.user_data.pop("skill", None)
    user_id = update.effective_user.id
    given = (update.message.text or "").strip().lower()
    elapsed = time.time() - session["ts"]
    if elapsed > session.get("limit", 10):
        await ui.send(update, f"⏰ <b>SÜRE DOLDU!</b> ({elapsed:.1f} saniye sürdü)\n"
                              f"Doğru cevap: <b>{session['answer']}</b>\n"
                              f"<i>Bir dahakine daha hızlı ol!</i>",
                      games_menu_kb(i18n.lang_of(update.effective_user.id)))
        return True
    if given.replace(" ", "") == str(session["answer"]).lower():
        won = economy.payout(db.get_user(user_id), session["reward"])
        bonus = int(won * 0.4) if elapsed < session.get("limit", 10) * 0.4 else 0
        economy.add_coins(user_id, won + bonus, "beceri oyunu")
        economy.add_xp(user_id, 35)
        events.track(user_id, "skill")
        events.track(user_id, "play")
        extra = f"\n⚡ Hız bonusu: +{ui.fmt(bonus)} 🪙" if bonus else ""
        unlocked = events.check_achievements(user_id)
        text = (f"✅ <b>DOĞRU!</b> ({elapsed:.1f} sn)\n\n+{ui.fmt(won)} 🪙  +35 XP{extra}")
        if unlocked:
            text += "\n\n🏅 <b>YENİ BAŞARIM!</b>\n" + "\n".join(unlocked)
        await ui.send(update, text, games_menu_kb(i18n.lang_of(update.effective_user.id)))
    else:
        await ui.send(update, f"❌ <b>{session['answer']}</b>", games_menu_kb(i18n.lang_of(user_id)))
    return True


# ---------------------------------------------------------------------------
# AKTİVİTELER: ÇALIŞ / MADEN / ARENA
# ---------------------------------------------------------------------------
JOBS = [
    ("🍕 Pizza kuryeliği", "Yağmurda 12 pizza dağıttın"),
    ("🧹 Han temizliği", "Meyhanenin zeminini pırıl pırıl yaptın"),
    ("🐴 Ahır bakıcılığı", "Şövalyenin atını tımar ettin"),
    ("📦 Liman hamallığı", "Gemiden 40 sandık indirdin"),
    ("🍺 Meyhane garsonluğu", "Sarhoş müşterilerle boğuştun"),
    ("🧑‍🌾 Tarla işçiliği", "Buğday hasadına yardım ettin"),
    ("🗺 Haritacılık", "Kayıp bir patikayı haritaya işledin"),
    ("🧪 Simyacı çırağı", "İksir şişelerini etiketledin"),
    ("🎻 Sokak müzikçiliği", "Meydanda çalıp bahşiş topladın"),
    ("🐕 Köpek gezdirme", "Lordun tazılarını gezdirdin"),
]

ORES = [
    ("🪨 Taş", 1, 250), ("🪵 Kömür", 1, 500), ("⛓ Demir", 1, 1_200),
    ("🥈 Gümüş", 1, 3_000), ("🥇 Altın damarı", 1, 7_500), ("💠 Kristal", 1, 18_000),
]

MONSTERS = [
    ("🐀 Dev Sıçan", 0.6), ("🦇 Mağara Yarasası", 0.8), ("🐍 Zehirli Yılan", 1.0),
    ("🐺 Aç Kurt", 1.15), ("👺 Goblin Yağmacı", 1.3), ("🧟 Yürüyen Ceset", 1.5),
    ("🕷 Dev Örümcek", 1.7), ("👹 Ork Savaşçısı", 2.0), ("🦂 Kum Akrebi", 2.3),
    ("🐲 Genç Ejder", 2.8),
]


async def do_work(query, context, user_id: int) -> None:
    user = db.get_user(user_id)
    left = economy.cooldown_left(user["last_work"], config.WORK_COOLDOWN)
    if left > 0:
        await query.answer(f"⏳ Yorgunsun! {ui.dur(left)} sonra tekrar çalışabilirsin.", show_alert=True)
        return
    title, story = random.choice(JOBS)
    base = 1_200 + user["level"] * 380
    earned = economy.payout(user, int(base * random.uniform(0.8, 1.35)))
    tip = 0
    if economy.roll(0.18 + economy.luck(user)):
        tip = int(earned * random.uniform(0.5, 1.5))
    db.upd(user_id, last_work=ui.now())
    economy.add_coins(user_id, earned + tip, "çalışma")
    economy.add_xp(user_id, 30)
    events.track(user_id, "work")
    text = (
        f"💼 <b>{title}</b>\n\n"
        f"<i>{story}</i>\n\n"
        f"💰 Kazanç: <b>{ui.fmt(earned)}</b> 🪙\n"
        + (f"🤑 Bahşiş: <b>+{ui.fmt(tip)}</b> 🪙\n" if tip else "")
        + f"✨ +30 XP\n⏳ Sonraki: {ui.dur(config.WORK_COOLDOWN)}"
    )
    await result_screen(query, user_id, text, "g:work")


async def do_mine(query, context, user_id: int) -> None:
    user = db.get_user(user_id)
    left = economy.cooldown_left(user["last_mine"], config.MINE_COOLDOWN)
    if left > 0:
        await query.answer(f"⏳ Kazman soğuyor: {ui.dur(left)}", show_alert=True)
        return
    if user["pickaxe"] <= 0:
        await query.answer("⛏ Kazman kırıldı! Marketten yeni kazma al.", show_alert=True)
        return
    if not economy.spend_energy(user_id, 2):
        await query.answer("⚡ Enerjin yetersiz (2 gerekli).", show_alert=True)
        return
    weights = [40, 26, 16, 10, 6, 2]
    idx = random.choices(range(len(ORES)), weights=weights)[0]
    name, _qty, value = ORES[idx]
    amount = random.randint(1, 3 + user["level"] // 5)
    total = economy.payout(user, value * amount)
    gem = 0
    if economy.roll(0.06 + economy.luck(user) * 0.2):
        gem = random.randint(1, 2)
        economy.add_gems(user_id, gem, "madende elmas")
    db.upd(user_id, last_mine=ui.now(), pickaxe=user["pickaxe"] - 1)
    economy.add_coins(user_id, total, "madencilik")
    economy.add_xp(user_id, 25)
    events.track(user_id, "mine")
    text = (
        f"⛏ <b>MADEN OCAĞI</b>\n\n"
        f"Kazmayı savurdun ve buldun:\n"
        f"<b>{name} x{amount}</b> → {ui.fmt(total)} 🪙\n"
        + (f"💎 <b>Ham elmas x{gem}</b> buldun!\n" if gem else "")
        + f"\n⛏ Kazma dayanıklılığı: {user['pickaxe'] - 1}\n"
        f"⏳ Sonraki kazma: {ui.dur(config.MINE_COOLDOWN)}"
    )
    await result_screen(query, user_id, text, "g:mine")


def simulate_fight(atk_a: dict, name_a: str, atk_b: dict, name_b: str, max_rounds: int = 14) -> dict:
    """İki taraf arasında tur bazlı savaş simülasyonu."""
    hp_a, hp_b = atk_a["hp"], atk_b["hp"]
    log = []
    for rnd in range(1, max_rounds + 1):
        for attacker, defender, is_a in ((atk_a, atk_b, True), (atk_b, atk_a, False)):
            crit = random.random() < attacker["crit"]
            dmg = attacker["atk"] * random.uniform(0.85, 1.2) - defender["dfn"] * 0.45
            dmg = max(3, int(dmg * (1.85 if crit else 1.0)))
            if is_a:
                hp_b -= dmg
                log.append(f"⚔️ {name_a} → {dmg} hasar{' 💥KRİTİK' if crit else ''}")
                if hp_b <= 0:
                    return {"winner": "a", "log": log, "rounds": rnd, "hp_a": hp_a, "hp_b": 0}
            else:
                hp_a -= dmg
                log.append(f"🛡 {name_b} → {dmg} hasar{' 💥KRİTİK' if crit else ''}")
                if hp_a <= 0:
                    return {"winner": "b", "log": log, "rounds": rnd, "hp_a": 0, "hp_b": hp_b}
    winner = "a" if hp_a >= hp_b else "b"
    return {"winner": winner, "log": log, "rounds": max_rounds, "hp_a": max(0, hp_a), "hp_b": max(0, hp_b)}


async def do_arena(query, context, user_id: int) -> None:
    user = db.get_user(user_id)
    if not economy.spend_energy(user_id, 3):
        await query.answer("⚡ Enerjin yetersiz (3 gerekli). Enerji içeceği kullanabilirsin.", show_alert=True)
        return
    stats = economy.power(user)
    pool = MONSTERS[:max(3, min(len(MONSTERS), 3 + user["level"] // 3))]
    mname, scale = random.choice(pool)
    monster = {
        "atk": int((10 + user["level"] * 2.6) * scale),
        "dfn": int((5 + user["level"] * 1.6) * scale),
        "hp": int((90 + user["level"] * 11) * scale),
        "crit": 0.08,
    }
    heal = 0
    if db.inv_count(user_id, "c_potion") > 0 and stats["hp"] < monster["hp"]:
        row = db.one("SELECT id FROM inventory WHERE user_id=? AND item_key='c_potion' LIMIT 1", (user_id,))
        if row:
            db.inv_remove(row["id"], 1)
            heal = 60
            stats["hp"] += heal
    fight = simulate_fight(stats, "Sen", monster, mname, max_rounds=12)
    log_lines = fight["log"][-6:]
    if fight["winner"] == "a":
        reward = economy.payout(user, int((900 + user["level"] * 260) * scale * random.uniform(0.9, 1.25)))
        economy.add_coins(user_id, reward, "arena")
        economy.add_xp(user_id, int(45 * scale))
        db.bump(user_id, wins=1)
        drop_line = ""
        if economy.roll(0.12 + economy.luck(user) * 0.3):
            drop = random.choice(["c_potion", "c_energy", "c_clover", "t_pickaxe"])
            db.inv_add(user_id, drop, 1, stackable=True)
            drop_line = f"\n🎁 Ganimet: {items.label(drop)}"
        head = f"🏆 <b>{mname} yenildi!</b>"
        outcome = f"💰 +{ui.fmt(reward)} 🪙  ✨ +{int(45 * scale)} XP{drop_line}"
    else:
        loss = min(user["coins"], int(300 + user["level"] * 90))
        economy.take_coins(user_id, loss, "arena kaybı")
        db.bump(user_id, losses=1)
        head = f"💀 <b>{mname} seni yendi!</b>"
        outcome = f"🩹 Şifacıya ödediğin: -{ui.fmt(loss)} 🪙"
    events.track(user_id, "arena")
    text = (
        f"🗡 <b>ARENA</b>\n\n"
        f"👤 Sen — ⚔️{stats['atk']} 🛡{stats['dfn']} ❤️{stats['hp']}\n"
        f"{mname} — ⚔️{monster['atk']} 🛡{monster['dfn']} ❤️{monster['hp']}\n"
        + (f"❤️ Şifa iksiri kullanıldı (+{heal} can)\n" if heal else "")
        + f"\n<b>Savaş kaydı</b>\n" + "\n".join(log_lines)
        + f"\n\n{head}\n{outcome}\n⚡ Enerji -3"
    )
    await result_screen(query, user_id, text, "g:arena")


# ---------------------------------------------------------------------------
# CALLBACK YÖNLENDİRİCİ
# ---------------------------------------------------------------------------
BET_PREFIX = {
    "slots": ("g:play:slots", None),
    "wheel": ("g:play:wheel", None),
    "cf": ("g:cfbet", None),
    "dice": ("g:dicebet", None),
    "rlt": ("g:rltbet", None),
    "mines": ("g:mnbet", None),
    "hilo": ("g:hlbet", None),
    "bj": ("g:bjbet", None),
    "crash": ("g:crbet", None),
}


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id

    if not ui.is_private(update):
        await query.answer("🎮 Oyunlar sadece bota özelden açılır. Bana özelden yaz!",
                           show_alert=True)
        return
    TOASTS = {"menu": "🎮 Oyunlar", "cat": "👇 Seç", "pick": "💵 Bahsini seç",
              "work": "💼 İşe gidiliyor...", "mine": "⛏ Maden kazılıyor...",
              "arena": "🗡 Savaş başlıyor...", "sk": "🧠 Hazır ol!",
              "play": "🎲 Oynanıyor...", "mn": "💣 Dikkat, mayın var!",
              "hlbet": "🎴 Kartlar dağıtılıyor", "bjbet": "🃏 Kartlar dağıtılıyor",
              "crbet": "🚀 Roket kalkıyor", "cfbet": "🪙 Tahminini seç",
              "dicebet": "🎲 Tahminini seç", "rltbet": "🎡 Nereye oynuyorsun?",
              "mnbet": "💣 Kaç mayın olsun?"}
    await query.answer(TOASTS.get(action, ""))
    user = db.get_user(user_id)
    if user is None:
        await ui.safe_edit(query, "Önce /start yaz.")
        return

    # --- menü ---
    lang = i18n.lang_of(user_id)
    if action == "menu":
        clear_sessions(context)
        await ui.nav(query, "games", games_menu_text(user, lang), games_menu_kb(lang))
        return
    if action == "cat":
        clear_sessions(context)
        cat = parts[2]
        await ui.safe_edit(query, category_text(cat, user, lang), category_kb(cat, lang))
        return
    if action == "noop":
        return

    # --- bahis seçimi ---
    if action == "pick":
        game = parts[2]
        emoji, name, desc = GAMES_INFO[game]
        prefix = BET_PREFIX[game][0]
        text = (
            f"{emoji} <b>{name.upper()}</b>\n{ui.LINE}\n"
            f"{ui.header(user)}\n" + i18n.t(lang, "g_choose_bet")
        )
        await ui.safe_edit(query, text, ui.kb(ui.bet_rows(prefix, user)))
        return

    # --- doğrudan oynanan oyunlar ---
    if action == "play":
        game, bet = parts[2], int(parts[3])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, f"{game} bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        if game == "slots":
            await play_slots(query, context, user_id, bet)
        elif game == "wheel":
            await play_wheel(query, context, user_id, bet)
        return

    # --- iki aşamalı oyunlar: tutar seçildi, şimdi seçenek ---
    if action == "cfbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        await ui.safe_edit(query, (
            f"🪙 <b>YAZI TURA</b>\n\nBahis: {ui.fmt(bet)} 🪙 • Ödeme 1.9x\n\nTahminin?"
        ), ui.kb([
            [("🅨 Yazı", f"g:cf:{bet}:y"), ("🅣 Tura", f"g:cf:{bet}:t")],
            [("⬅️ Geri", "g:pick:cf")],
        ]))
        return
    if action == "cf":
        bet, side = int(parts[2]), parts[3]
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "yazı-tura bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await play_coinflip(query, context, user_id, bet, side)
        return

    if action == "dicebet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        rows = [[(f"{label} — {mult:g}x", f"g:dice:{bet}:{key}")]
                for key, (label, mult, _f) in DICE_BETS.items()]
        rows.append([("⬅️ Geri", "g:pick:dice")])
        await ui.safe_edit(query, (
            f"🎲 <b>ZAR OYUNU</b>\n\nBahis: {ui.fmt(bet)} 🪙\n"
            "Telegram'ın gerçek zarı atılır. Tahminini seç 👇"
        ), ui.kb(rows))
        return
    if action == "dice":
        bet, choice = int(parts[2]), parts[3]
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "zar bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await play_dice(query, context, user_id, bet, choice)
        return

    if action == "rltbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        await ui.safe_edit(query, (
            f"🎡 <b>RULET</b>\n\nBahis: {ui.fmt(bet)} 🪙\nNereye oynuyorsun?"
        ), ui.kb([
            [("🔴 Kırmızı 2x", f"g:rlt:{bet}:red"), ("⚫ Siyah 2x", f"g:rlt:{bet}:black")],
            [("Tek 2x", f"g:rlt:{bet}:odd"), ("Çift 2x", f"g:rlt:{bet}:even")],
            [("1-18 2x", f"g:rlt:{bet}:low"), ("19-36 2x", f"g:rlt:{bet}:high")],
            [("1-12 3x", f"g:rlt:{bet}:d1"), ("13-24 3x", f"g:rlt:{bet}:d2"), ("25-36 3x", f"g:rlt:{bet}:d3")],
            [("🟢 Sıfır 35x", f"g:rlt:{bet}:zero")],
            [("⬅️ Geri", "g:pick:rlt")],
        ]))
        return
    if action == "rlt":
        bet, sel = int(parts[2]), parts[3]
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "rulet bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await play_roulette(query, context, user_id, bet, sel)
        return

    # --- mayın ---
    if action == "mnbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        await ui.safe_edit(query, (
            f"💣 <b>MAYIN TARLASI</b>\n\nBahis: {ui.fmt(bet)} 🪙\n"
            "Kaç mayın olsun? (çok mayın = yüksek risk, yüksek çarpan)"
        ), ui.kb([
            [("3 💣 (kolay)", f"g:mn:{bet}:3"), ("5 💣 (orta)", f"g:mn:{bet}:5")],
            [("10 💣 (zor)", f"g:mn:{bet}:10"), ("15 💣 (çılgın)", f"g:mn:{bet}:15")],
            [("⬅️ Geri", "g:pick:mines")],
        ]))
        return
    if action == "mn":
        bet, mines = int(parts[2]), int(parts[3])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "mayın bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await start_mines(query, context, user_id, bet, mines)
        return
    if action == "mnp":
        await mines_pick(query, context, user_id, int(parts[2]))
        return
    if action == "mnc":
        await mines_cash(query, context, user_id)
        return
    if action == "mnq":
        session = context.user_data.get("mines")
        if session and not session["picked"]:
            await mines_cash(query, context, user_id)
        else:
            await mines_cash(query, context, user_id)
        return

    # --- yüksek/düşük ---
    if action == "hlbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "yüksek-düşük bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await start_hilo(query, context, user_id, bet)
        return
    if action == "hlg":
        await hilo_guess(query, context, user_id, parts[2])
        return
    if action in ("hlc", "hlq"):
        await hilo_cash(query, context, user_id)
        return

    # --- blackjack ---
    if action == "bjbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "blackjack bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await start_bj(query, context, user_id, bet)
        return
    if action == "bjm":
        await bj_move(query, context, user_id, parts[2])
        return

    # --- roket ---
    if action == "crbet":
        bet = int(parts[2])
        ok, msg = validate_bet(user, bet)
        if not ok:
            await query.answer(msg, show_alert=True)
            return
        if not economy.take_coins(user_id, bet, "roket bahis"):
            await query.answer("Bakiye yetersiz.", show_alert=True)
            return
        await start_crash(query, context, user_id, bet)
        return
    if action == "crs":
        await crash_step(query, context, user_id)
        return
    if action == "crc":
        await crash_cash(query, context, user_id)
        return

    # --- beceri oyunları ---
    if action == "sk":
        await start_skill(query, context, user_id, parts[2])
        return
    if action == "qa":
        await skill_quiz_answer(query, context, user_id, int(parts[2]))
        return
    if action == "rf":
        await skill_reflex_answer(query, context, user_id, int(parts[2]))
        return

    # --- aktiviteler ---
    if action == "work":
        await do_work(query, context, user_id)
        return
    if action == "mine":
        await do_mine(query, context, user_id)
        return
    if action == "arena":
        await do_arena(query, context, user_id)
        return


async def cmd_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(update.effective_user.id), "only_private"),
                      ui.pm_link())
        return
    user = db.get_user(update.effective_user.id)
    lang = i18n.lang_of(user["user_id"])
    await ui.screen(update, "games", games_menu_text(user, lang), games_menu_kb(lang))
