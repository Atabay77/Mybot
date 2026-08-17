# -*- coding: utf-8 -*-
"""Grup (parti) oyunları: arkadaş gruplarında herkesin birlikte oynadığı hızlı turlar."""
import asyncio
import random
import time
import uuid

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import db
import economy
import events
import games
import ui

ROUND_COOLDOWN = 60          # aynı gruptaki turlar arası bekleme
ANSWER_WINDOW = 45           # cevap süresi
DAILY_WIN_CAP = 12           # kişi başı günlük parti ödülü limiti

PARTY_GAMES = {
    "quiz": ("🧠", "Bilgi Yarışı", "Soruyu ilk doğru yazan kazanır"),
    "math": ("➗", "Hızlı Matematik", "İşlemi ilk çözen kazanır"),
    "word": ("🔤", "Kelime Avı", "Karışık harfleri ilk çözen kazanır"),
    "reflex": ("⚡", "Refleks Düellosu", "Butona ilk basan kazanır"),
    "chest": ("🎁", "Hazine Sandığı", "Sandığı ilk açan altını alır"),
}


def party_menu_text() -> str:
    lines = ["🎉 <b>PARTİ OYUNLARI</b>",
             "<i>Grupta herkes birlikte oynar, ilk bilen ödülü kapar.</i>", ""]
    for emoji, name, desc in PARTY_GAMES.values():
        lines.append(f"{emoji} <b>{name}</b> — {desc}")
    lines.append("\nÖdüller kasadan çıkar, bahis yoktur — tamamen bedava! 🎈")
    lines.append("Altın karşılığı 1v1 için: /duello")
    return "\n".join(lines)


def party_menu_kb():
    rows = [[(f"{e} {n}", f"pt:start:{k}")] for k, (e, n, _d) in PARTY_GAMES.items()]
    rows.append([("⚔️ Düello Kur", "pvp:menu"), ("🐉 Boss", "ev:boss")])
    return ui.kb(rows)


def _reward_for(chat_members: int = 1) -> int:
    return random.randint(1_800, 5_000)


def _win_count(user_id: int) -> int:
    return int(db.meta_get(f"party_{user_id}_{events.today()}", 0) or 0)


def _register_win(user_id: int) -> None:
    db.meta_set(f"party_{user_id}_{events.today()}", _win_count(user_id) + 1)


async def _grant(update, user_id: int, reward_base: int) -> tuple[int, str]:
    """Parti ödülünü verir; günlük limit aşıldıysa 0 döner."""
    if _win_count(user_id) >= DAILY_WIN_CAP:
        return 0, (f"\n⚠️ Bugünkü parti ödülü limitine ({DAILY_WIN_CAP}) ulaştın — "
                   f"bu tur sadece şeref için! Altın için /oyunlar ve /duello.")
    user = db.get_user(user_id)
    reward = economy.payout(user, reward_base)
    economy.add_coins(user_id, reward, "parti oyunu")
    economy.add_xp(user_id, 40)
    events.track(user_id, "skill")
    _register_win(user_id)
    return reward, ""


async def start_round(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str) -> None:
    chat = update.effective_chat
    if chat.type == "private":
        await _reply(update, "🎉 Parti oyunları gruplarda oynanır! Beni bir arkadaş grubuna ekle "
                             "ve orada /parti yaz. Tek başına oynamak için: /oyunlar")
        return
    party = context.chat_data.get("party")
    now = time.time()
    if party and party.get("active") and now - party["ts"] < ANSWER_WINDOW:
        await _reply(update, "⏳ Şu anda devam eden bir tur var, önce onu bitirin!")
        return
    if now - context.chat_data.get("last_party", 0) < ROUND_COOLDOWN:
        left = int(ROUND_COOLDOWN - (now - context.chat_data.get("last_party", 0)))
        await _reply(update, f"⏳ Yeni tur için {left} saniye bekleyin.")
        return
    context.chat_data["last_party"] = now
    reward = _reward_for()

    if kind == "quiz":
        question, options, correct = random.choice(games.QUIZ)
        answer = options[correct]
        context.chat_data["party"] = {"kind": "quiz", "answer": answer.lower(), "reward": reward,
                                      "ts": now, "active": True}
        text = (f"🧠 <b>BİLGİ YARIŞI</b>\n\n{ui.esc(question)}\n\n"
                f"Cevabı <b>yazarak</b> ilk bilen {ui.fmt(reward)} 🪙 kazanır!\n"
                f"⏱ {ANSWER_WINDOW} saniye")
        await _send(update, text)

    elif kind == "math":
        a, b, c = random.randint(5, 40), random.randint(2, 20), random.randint(2, 12)
        op = random.choice(["+", "-", "*"])
        expr = f"{a} {op} {b} + {c}"
        answer = str(eval(expr))  # ifade yalnızca burada üretildi, kullanıcı girdisi değil
        context.chat_data["party"] = {"kind": "math", "answer": answer, "reward": reward,
                                     "ts": now, "active": True}
        await _send(update, (f"➗ <b>HIZLI MATEMATİK</b>\n\n<code>{expr} = ?</code>\n\n"
                             f"İlk doğru cevap {ui.fmt(reward)} 🪙 alır!\n⏱ {ANSWER_WINDOW} saniye"))

    elif kind == "word":
        word = random.choice(games.WORDS)
        context.chat_data["party"] = {"kind": "word", "answer": word, "reward": reward,
                                     "ts": now, "active": True}
        await _send(update, (f"🔤 <b>KELİME AVI</b>\n\n<code>{games.scramble(word)}</code>\n\n"
                             f"Doğru kelimeyi ilk yazan {ui.fmt(reward)} 🪙 kazanır!\n"
                             f"⏱ {ANSWER_WINDOW} saniye"))

    elif kind == "reflex":
        token = uuid.uuid4().hex[:8]
        context.chat_data["party"] = {"kind": "reflex", "token": token, "reward": reward * 2,
                                     "ts": now, "active": True, "taken": False}
        msg = await _send(update, "⚡ <b>REFLEKS DÜELLOSU</b>\n\nHazır olun...")
        await asyncio.sleep(random.uniform(1.5, 4.0))
        party = context.chat_data.get("party")
        if not party or party.get("token") != token:
            return
        party["ts"] = time.time()
        try:
            await msg.edit_text(
                f"⚡ <b>ŞİMDİ!</b>\n\nButona ilk basan <b>{ui.fmt(reward * 2)}</b> 🪙 kazanır!",
                parse_mode=ParseMode.HTML,
                reply_markup=ui.kb([[("🔥 BAS!", f"pt:tap:{token}")]]))
        except Exception:
            pass

    elif kind == "chest":
        token = uuid.uuid4().hex[:8]
        amount = random.randint(4_000, 20_000)
        context.chat_data["party"] = {"kind": "chest", "token": token, "reward": amount,
                                     "ts": now, "active": True, "taken": False}
        await _send(update, (
            f"🎁 <b>HAZİNE SANDIĞI DÜŞTÜ!</b>\n\n"
            f"İçinde <b>{ui.fmt(amount)}</b> 🪙 var.\nSandığı ilk açan alır!"
        ), ui.kb([[("🗝 SANDIĞI AÇ", f"pt:tap:{token}")]]))


async def _send(update: Update, text: str, kb=None):
    return await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _reply(update: Update, text: str):
    if update.callback_query:
        await ui.answer(update.callback_query, text, alert=True)
        return None
    return await _send(update, text)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Grup turlarındaki metin cevaplarını kontrol eder."""
    party = context.chat_data.get("party")
    if not party or not party.get("active") or party["kind"] not in ("quiz", "math", "word"):
        return False
    if time.time() - party["ts"] > ANSWER_WINDOW:
        context.chat_data.pop("party", None)
        return False
    guess = (update.message.text or "").strip().lower()
    target = str(party["answer"]).lower()
    if guess.replace(" ", "") != target.replace(" ", ""):
        return False
    context.chat_data.pop("party", None)
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if user is None:
        await _send(update, "Doğru cevap! Ama önce bota özelden /start yazmalısın ki ödül alabilsin. 🙂")
        return True
    reward, note = await _grant(update, user_id, party["reward"])
    elapsed = time.time() - party["ts"]
    prize = f"💰 +{ui.fmt(reward)} 🪙  ✨ +40 XP" if reward else "🏅 Ödülsüz zafer"
    await update.message.reply_text(
        f"🎉 <b>DOĞRU!</b> {ui.mention(user)} {elapsed:.1f} saniyede bildi.\n"
        f"{prize}{note}\n\nYeni tur: /parti",
        parse_mode=ParseMode.HTML)
    return True


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id

    if action == "menu":
        await ui.answer(query)
        await ui.safe_edit(query, party_menu_text(), party_menu_kb())
        return
    if action == "start":
        await ui.answer(query)
        await start_round(update, context, parts[2])
        return
    if action == "tap":
        token = parts[2]
        party = context.chat_data.get("party")
        if not party or party.get("token") != token or party.get("taken"):
            await ui.answer(query, "Çok geç kaldın! 😅", alert=True)
            return
        if party["kind"] == "reflex" and time.time() - party["ts"] < 0.05:
            await ui.answer(query, "Erken bastın!", alert=True)
            return
        party["taken"] = True
        context.chat_data.pop("party", None)
        user = db.get_user(user_id)
        if user is None:
            await ui.answer(query, "Önce bota özelden /start yaz!", alert=True)
            return
        reward = economy.payout(user, party["reward"])
        economy.add_coins(user_id, reward, "parti oyunu")
        economy.add_xp(user_id, 35)
        elapsed = time.time() - party["ts"]
        head = "⚡ <b>EN HIZLI SEN!</b>" if party["kind"] == "reflex" else "🗝 <b>SANDIK AÇILDI!</b>"
        await ui.answer(query, f"+{ui.fmt(reward)} altın! ({elapsed:.2f} sn)")
        await ui.safe_edit(query, (
            f"{head}\n\n{ui.mention(user)} {elapsed:.2f} saniyede kaptı!\n"
            f"💰 +{ui.fmt(reward)} 🪙  ✨ +35 XP\n\nYeni tur: /parti"
        ))


async def cmd_party(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = (context.args or [])
    if args and args[0].lower() in PARTY_GAMES:
        await start_round(update, context, args[0].lower())
        return
    await ui.send(update, party_menu_text(), party_menu_kb())


async def cmd_chest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_round(update, context, "chest")
