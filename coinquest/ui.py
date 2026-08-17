# -*- coding: utf-8 -*-
"""Arayüz yardımcıları: para biçimlendirme, klavyeler, güvenli mesaj düzenleme."""
import html
import time
from typing import Iterable, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest

import config
import economy

E_COIN = "🪙"
E_GEM = "💎"
E_EN = "⚡"


def fmt(n) -> str:
    """1234567 -> 1.234.567"""
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def esc(text) -> str:
    return html.escape(str(text or ""))


def name_of(user_row) -> str:
    if user_row is None:
        return "Bilinmeyen"
    base = user_row["first_name"] or "Gezgin"
    return esc(base[:20])


def mention(user_row) -> str:
    return f'<a href="tg://user?id={user_row["user_id"]}">{name_of(user_row)}</a>'


def bar(cur: int, mx: int, size: int = 10, fill: str = "█", empty: str = "░") -> str:
    if mx <= 0:
        return empty * size
    filled = int(round(size * min(1.0, max(0.0, cur / mx))))
    return fill * filled + empty * (size - filled)


def dur(seconds: int) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}s {m}dk"
    if m:
        return f"{m}dk {s}sn"
    return f"{s}sn"


def kb(rows: Iterable[Iterable[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """[[('metin','callback')]] -> InlineKeyboardMarkup"""
    out = []
    for row in rows:
        line = []
        for text, data in row:
            if data.startswith("url:"):
                line.append(InlineKeyboardButton(text, url=data[4:]))
            else:
                line.append(InlineKeyboardButton(text, callback_data=data))
        if line:
            out.append(line)
    return InlineKeyboardMarkup(out)


def main_menu_kb() -> InlineKeyboardMarkup:
    return kb([
        [("🎮 Oyunlar", "g:menu"), ("💵 Para Çek", "cash:menu")],
        [("⚔️ Düello", "pvp:menu"), ("💰 Cüzdanım", "s:profile")],
        [("🏪 Market", "mk:menu"), ("🎒 Eşyalarım", "mk:inv")],
        [("🛒 Pazar", "mk:bazaar"), ("🏭 İş Yerim", "mk:biz")],
        [("🎁 Günlük Hediye", "s:daily"), ("🏦 Banka", "s:bank")],
        [("🐉 Canavar", "ev:boss"), ("🎟 Çekiliş", "ev:lottery")],
        [("📜 Görevler", "ev:quests"), ("🏆 Sıralama", "s:top")],
        [("👥 Arkadaş Çağır", "s:ref"), ("❓ Nasıl Oynanır", "s:help")],
    ])


# Ekranın altında sürekli duran butonlar — kullanıcı hiç komut yazmak zorunda kalmasın
BOTTOM_BUTTONS = [
    ["🎮 Oyunlar", "💰 Cüzdanım"],
    ["🎁 Günlük Hediye", "💵 Para Çek"],
    ["🏪 Market", "🎒 Eşyalarım"],
    ["👥 Arkadaş Çağır", "📖 Menü"],
]


def bottom_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(BOTTOM_BUTTONS, resize_keyboard=True, is_persistent=True)


def back_kb(target: str = "m:main", label: str = "⬅️ Geri") -> InlineKeyboardMarkup:
    return kb([[(label, target)]])


def header(user) -> str:
    en = economy.sync_energy(user["user_id"])
    mx = economy.max_energy(user["level"])
    return (
        f"{E_COIN} <b>{fmt(user['coins'])}</b>   {E_GEM} {fmt(user['gems'])}   "
        f"{E_EN} {en}/{mx}   🎚 Sv.{user['level']}"
    )


async def safe_edit(query, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    """'message is not modified' hatasını yutarak mesajı düzenler."""
    try:
        return await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return None
        try:
            return await query.message.reply_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
        except Exception:
            return None


async def send(update: Update, text: str, reply_markup=None):
    return await update.effective_chat.send_message(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def bet_rows(prefix: str, user, extra: str = "") -> list[list[tuple[str, str]]]:
    """Bahis seçim klavyesi. prefix örn: 'g:play:slots' -> 'g:play:slots:500'"""
    balance = user["coins"]
    cap = economy.max_bet(user)
    presets = [100, 500, 1_000, 5_000, 25_000, 100_000]
    rows: list[list[tuple[str, str]]] = []
    line: list[tuple[str, str]] = []
    for amount in presets:
        if amount > cap:
            continue
        tag = fmt(amount) if amount < 1000 else f"{amount // 1000}K"
        line.append((f"{E_COIN}{tag}", f"{prefix}:{amount}{extra}"))
        if len(line) == 3:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    allin = min(balance, cap)
    rows.append([
        ("✏️ Özel Tutar", f"bet:custom:{prefix}{extra}"),
        (f"🔥 Hepsi ({fmt(allin)})", f"{prefix}:{allin}{extra}"),
    ])
    rows.append([("⬅️ Oyunlar", "g:menu"), ("🏠 Menü", "m:main")])
    return rows


def is_private(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and chat.type == "private"


def pm_link(text: str = "🤖 Bota Özelden Yaz") -> InlineKeyboardMarkup:
    if config.BOT_USERNAME:
        return kb([[(text, f"url:https://t.me/{config.BOT_USERNAME}")]])
    return kb([[("🏠 Menü", "m:main")]])


def now() -> int:
    return int(time.time())
