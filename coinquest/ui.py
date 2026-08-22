# -*- coding: utf-8 -*-
"""Arayüz yardımcıları: para biçimlendirme, klavyeler, güvenli mesaj düzenleme."""
import html
import logging
import time
from typing import Iterable, Optional

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove,
                      Update)
from telegram.constants import ParseMode
from telegram.error import BadRequest

import config
import db
import economy
import i18n
import media

log = logging.getLogger(__name__)

E_COIN = "🪙"
E_GEM = "💎"
E_EN = "⚡"
LINE = "━━━━━━━━━━━━━━"


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


def _duel_fire() -> str:
    """Ana menüdeki Düello butonuna bekleyen açık oyun sayısını ekler: '⚔️ Düello 3🔥'"""
    try:
        import pvp
        total = sum(pvp.open_counts().values())
        return f"  {total}🔥" if total else ""
    except Exception:
        return ""


def main_menu_kb(lang: str = i18n.DEFAULT, user_id: int = 0) -> InlineKeyboardMarkup:
    """Ana menü. Yönetim düğmesi yalnızca yetkililere görünür."""
    rows = [
        [(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_money"), "cash:menu")],
        [(i18n.t(lang, "b_gift"), "s:daily"), (i18n.t(lang, "b_shop"), "mk:menu")],
        [(i18n.t(lang, "b_arena"), "ar:menu"),
         (i18n.t(lang, "b_duel") + _duel_fire(), "pvp:menu")],
        [(i18n.t(lang, "b_boss"), "ev:boss"),
         (i18n.t(lang, "b_lottery"), "ev:lottery")],
        [(i18n.t(lang, "b_miners"), "mi:menu:0"), (i18n.t(lang, "b_bank"), "s:bank")],
        [(i18n.t(lang, "b_clan"), "s:clan"), (i18n.t(lang, "b_war"), "w:menu")],
        [(i18n.t(lang, "b_bazaar"), "mk:bazaar"), (i18n.t(lang, "b_perks"), "pk:menu")],
        [(i18n.t(lang, "b_items"), "mk:inv"), (i18n.t(lang, "b_profile"), "s:profile")],
        [(i18n.t(lang, "b_top"), "s:top"), (i18n.t(lang, "b_quests"), "ev:quests")],
        [(i18n.t(lang, "b_friends"), "s:ref"), (i18n.t(lang, "b_more"), "m:more")],
    ]
    if user_id and db.staff_role(user_id):
        rows.append([("🛠 YÖNETİM PANELİ", "ad:home")])
    return kb(rows)


def more_menu_kb(lang: str = i18n.DEFAULT) -> InlineKeyboardMarkup:
    return kb([
        [(i18n.t(lang, "b_biz"), "mk:biz"), (i18n.t(lang, "b_support"), "sup:menu")],
        [(i18n.t(lang, "b_notify"), "nt:menu"), (i18n.t(lang, "b_help"), "s:help")],
        [(i18n.t(lang, "b_lang"), "m:lang")],
        [(i18n.t(lang, "b_home"), "m:main")],
    ])


def lang_kb() -> InlineKeyboardMarkup:
    rows = [[(label, f"m:setlang:{code}")] for code, label in i18n.LANGS.items()]
    return kb(rows)


def remove_bottom() -> ReplyKeyboardRemove:
    """Eski sürümden kalan alt klavyeyi temizler. Artık sadece inline buton var."""
    return ReplyKeyboardRemove()


def back_kb(target: str = "m:main", label: str = None, lang: str = i18n.DEFAULT) -> InlineKeyboardMarkup:
    return kb([[(label or i18n.t(lang, "b_back"), target)]])


def money(value: int) -> str:
    """500 -> '5.00 TMT'"""
    return f"{value / 100:.2f} {config.MONEY_NAME}"


def header(user, with_money: bool = False) -> str:
    """Cüzdan satırı — alıntı kutusu içinde, her dilde aynı (emoji)."""
    en = economy.sync_energy(user["user_id"])
    mx = economy.max_energy(user["level"], user["user_id"])
    line = (f"{E_COIN} <b>{fmt(user['coins'])}</b>   {E_GEM} {fmt(user['gems'])}   "
            f"{E_EN} {en}/{mx}   🎚 {user['level']}")
    if with_money:
        line += f"\n💵 <b>{money(user['tmt'])}</b>"
    return f"<blockquote>{line}</blockquote>"


_answered: set = set()


async def answer(query, text: str = "", alert: bool = False, quiet: bool = False) -> bool:
    """Butona cevap verir.

    Telegram bir butona sadece BİR kez cevap verilmesine izin verir. İkinci kez
    uyarı göstermek istersek sessizce kaybolur — bu yüzden ikinci uyarıyı
    sohbete mesaj olarak gönderiyoruz ki kullanıcı mutlaka görsün.
    """
    qid = getattr(query, "id", None)
    if qid in _answered:
        if text and not quiet:
            try:
                await query.message.chat.send_message(
                    f"⚠️ {text}", parse_mode=None,
                    reply_markup=kb([[("🏠", "m:main")]]) if alert else None)
            except Exception:
                pass
        return False
    if qid:
        if len(_answered) > 800:
            _answered.clear()
        _answered.add(qid)
    long_text = len(text) > 190
    try:
        if long_text:               # Telegram uyarısı 200 karakterle sınırlı
            await query.answer(text[:150] + "…", show_alert=True)
            try:
                await query.message.chat.send_message(text, reply_markup=kb([[("🏠", "m:main")]]))
            except Exception:
                pass
        else:
            await query.answer(text or None, show_alert=alert)
        return True
    except Exception as exc:
        log.debug("cevap verilemedi: %s", exc)
        return False


async def safe_edit(query, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    """Mesajı düzenler. Başarısız olursa eski mesajı silip yenisini gönderir,
    böylece kullanıcı asla 'tepki vermeyen buton' ile karşılaşmaz."""
    has_photo = bool(getattr(query.message, "photo", None))
    try:
        if has_photo and len(text) <= 1000:
            return await query.edit_message_caption(
                caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        if not has_photo:
            return await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=parse_mode,
                disable_web_page_preview=True)
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return None
        log.warning("düzenleme başarısız (%s): %s", getattr(query, "data", "?"), exc)
    except Exception as exc:
        log.warning("düzenleme hatası (%s): %s", getattr(query, "data", "?"), exc)
    # yedek yol: eskiyi sil, yenisini gönder
    try:
        await query.message.delete()
    except Exception:
        pass
    try:
        return await query.message.chat.send_message(
            text, reply_markup=reply_markup, parse_mode=parse_mode,
            disable_web_page_preview=True)
    except Exception as exc:
        log.error("mesaj gönderilemedi (%s): %s", getattr(query, "data", "?"), exc)
        return None


async def send(update: Update, text: str, reply_markup=None):
    return await update.effective_chat.send_message(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def nav(query, key: str, text: str, reply_markup=None):
    """Inline gezinme. Hedef ekranın resmi varsa eski mesajı silip fotoğraflı gönderir."""
    want_photo = bool(key) and len(text) <= 1000 and (media.cached(key) or media.path(key))
    has_photo = bool(getattr(query.message, "photo", None))
    if not want_photo and not has_photo:
        return await safe_edit(query, text, reply_markup)
    chat = query.message.chat
    try:
        await query.message.delete()
    except Exception:
        pass
    if want_photo:
        file_id = media.cached(key)
        try:
            if file_id:
                return await chat.send_photo(file_id, caption=text, parse_mode=ParseMode.HTML,
                                             reply_markup=reply_markup)
            with open(media.path(key), "rb") as fh:
                msg = await chat.send_photo(fh, caption=text, parse_mode=ParseMode.HTML,
                                            reply_markup=reply_markup)
            if msg and msg.photo:
                media.remember(key, msg.photo[-1].file_id)
            return msg
        except Exception:
            pass
    return await chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                                   disable_web_page_preview=True)


async def screen(update: Update, key: str, text: str, reply_markup=None):
    """Ekranın resmi varsa fotoğraf + altyazı, yoksa düz yazı gönderir."""
    if len(text) <= 1000:
        file_id = media.cached(key)
        if file_id:
            try:
                return await update.effective_chat.send_photo(
                    file_id, caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            except Exception:
                pass
        path = media.path(key)
        if path:
            try:
                with open(path, "rb") as fh:
                    msg = await update.effective_chat.send_photo(
                        fh, caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                if msg and msg.photo:
                    media.remember(key, msg.photo[-1].file_id)
                return msg
            except Exception:
                pass
    return await send(update, text, reply_markup)


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
