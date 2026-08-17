# -*- coding: utf-8 -*-
"""Gerçek para sistemi: coin -> para çevirme (günlük limitli) ve para çekme talepleri.

Bakiye 'kuruş' olarak tutulur: 100 = 1 TMT.
Günlük çevirme limiti sayesinde 5 TMT'ye ulaşmak en az 8 gün sürer.
"""
import datetime as dt

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import ui

METHOD_KEYS = {"karta": "pm_card", "telefon": "pm_phone", "diger": "pm_other"}
ASK_KEYS = {"karta": "pm_card_ask", "telefon": "pm_phone_ask", "diger": "pm_other_ask",
            "crypto": "pm_other_ask"}

money = ui.money            # 500 -> "5.00 TMT"


def method_name(key: str, lang: str = i18n.DEFAULT) -> str:
    if key == "crypto":
        return f"🪙 CryptoBot ({config.CRYPTOBOT_NAME})"
    return i18n.t(lang, METHOD_KEYS.get(key, "pm_other"))


def to_usdt(amount: int) -> float:
    """Kuruş cinsinden TMT -> USDT."""
    return round(amount / 100 / max(0.01, config.TMT_PER_USDT), 2)


def usdt_str(amount: int) -> str:
    return f"{to_usdt(amount):.2f} USDT"


def request_display(row) -> str:
    """Talebi para birimine göre yazar."""
    try:
        cur = row["currency"]
    except (KeyError, IndexError):
        cur = "TMT"
    if cur == "USDT":
        return f"<b>{usdt_str(row['amount'])}</b> ({money(row['amount'])})"
    return f"<b>{money(row['amount'])}</b>"


def _today() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def _reset_if_new_day(user_id: int) -> None:
    user = db.get_user(user_id)
    if user and user["tmt_day"] != _today():
        db.upd(user_id, tmt_day=_today(), tmt_today=0)


def left_today(user) -> int:
    if user["tmt_day"] != _today():
        return config.DAILY_MONEY_CAP
    return max(0, config.DAILY_MONEY_CAP - user["tmt_today"])


def days_old(user) -> int:
    return max(0, (ui.now() - user["created_ts"]) // 86400)


def coins_for(amount: int) -> int:
    """Kaç coin gerekir (amount kuruş cinsinden)."""
    return amount * config.COINS_PER_MONEY // 100


# ---------------------------------------------------------------------------
# ANA EKRAN
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    _reset_if_new_day(user_id)
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    kalan = max(0, config.MIN_WITHDRAW - user["tmt"])
    durum = i18n.t(lang, "m_left", v=money(kalan)) if kalan else i18n.t(lang, "m_ready")
    return (
        f"{i18n.t(lang, 'm_title')}\n{ui.LINE}\n"
        f"<blockquote>{i18n.t(lang, 'm_yours')}: <b>{money(user['tmt'])}</b>\n"
        f"{i18n.t(lang, 'm_coins')}: <b>{ui.fmt(user['coins'])}</b></blockquote>\n"
        + (f"<blockquote>💎 USDT: <b>{usdt_str(user['tmt'])}</b>\n"
           f"<i>1 USDT = {config.TMT_PER_USDT:g} {config.MONEY_NAME}</i>\n"
           f"{i18n.t(lang, 'cur_note')}</blockquote>\n" if config.USDT_ENABLED else "")
        + f"{i18n.t(lang, 'm_today')}: <b>{money(left_today(user))}</b>\n"
        f"{i18n.t(lang, 'm_need')}: <b>{money(config.MIN_WITHDRAW)}</b> ({durum})\n\n"
        + i18n.t(lang, "m_how", coins=ui.fmt(config.COINS_PER_MONEY), cur=config.MONEY_NAME,
                 cap=money(config.DAILY_MONEY_CAP), min=money(config.MIN_WITHDRAW))
    )


def panel_kb(user_id: int):
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    rows = []
    for amount in (10, 25, 50):
        if amount <= left_today(user):
            rows.append([(i18n.t(lang, "m_conv", coins=ui.fmt(coins_for(amount)),
                                 money=money(amount)), f"cash:ex:{amount}")])
    if left_today(user) > 0:
        rows.append([(i18n.t(lang, "m_max"), "cash:exmax")])
    else:
        rows.append([(i18n.t(lang, "m_full"), "cash:none")])
    rows.append([(i18n.t(lang, "m_wd"), "cash:wd"), (i18n.t(lang, "m_hist"), "cash:hist")])
    rows.append([(i18n.t(lang, "b_play"), "g:menu"), (i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


def exchange(user_id: int, amount: int) -> str:
    """Coin -> para çevirir (amount kuruş cinsinden)."""
    _reset_if_new_day(user_id)
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    if amount <= 0:
        return i18n.t(lang, "m_no_coins")
    limit = left_today(user)
    if limit <= 0:
        return i18n.t(lang, "m_cap_hit")
    amount = min(amount, limit)
    need = coins_for(amount)
    if user["coins"] < need:
        return i18n.t(lang, "m_no_coins")
    if not economy.take_coins(user_id, need, "paraya çevirme"):
        return i18n.t(lang, "m_no_coins")
    db.bump(user_id, tmt=amount, tmt_today=amount)
    db.upd(user_id, tmt_day=_today())
    user = db.get_user(user_id)
    return i18n.t(lang, "m_done", coins=ui.fmt(need), money=money(amount),
                  total=money(user["tmt"]))


# ---------------------------------------------------------------------------
# PARA ÇEKME
# ---------------------------------------------------------------------------

def can_withdraw(user) -> tuple[bool, str]:
    lang = i18n.lang_of(user["user_id"])
    if user["tmt"] < config.MIN_WITHDRAW:
        return False, f"{money(user['tmt'])} / {money(config.MIN_WITHDRAW)}"
    if user["level"] < config.WITHDRAW_MIN_LEVEL:
        return False, f"🎚 {user['level']} / {config.WITHDRAW_MIN_LEVEL}"
    if days_old(user) < config.WITHDRAW_MIN_DAYS:
        return False, f"📅 {days_old(user)} / {config.WITHDRAW_MIN_DAYS}"
    pending = db.scalar(
        "SELECT COUNT(*) FROM withdrawals WHERE user_id=? AND state='bekliyor'", (user["user_id"],))
    if pending:
        return False, "⏳ #" + str(db.scalar(
            "SELECT id FROM withdrawals WHERE user_id=? AND state='bekliyor' ORDER BY id DESC",
            (user["user_id"],)))
    return True, ""


def create_request(user_id: int, amount: int, method: str, details: str,
                   currency: str = "TMT") -> str:
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    ok, msg = can_withdraw(user)
    if not ok:
        return f"{i18n.t(lang, 'm_not_yet')} {msg}"
    amount = min(amount, user["tmt"])
    if amount < config.MIN_WITHDRAW:
        return f"{i18n.t(lang, 'm_not_yet')} {money(config.MIN_WITHDRAW)}"
    db.bump(user_id, tmt=-amount)
    cur = db.run(
        "INSERT INTO withdrawals (user_id, amount, currency, method, details, created_ts) "
        "VALUES (?,?,?,?,?,?)",
        (user_id, amount, currency, method, details[:120], ui.now()))
    db.upd(user_id, wd_currency=currency)
    db.log_tx(user_id, 0, f"çekim talebi #{cur.lastrowid}")
    shown = usdt_str(amount) + f" ({money(amount)})" if currency == "USDT" else money(amount)
    return i18n.t(lang, "m_req_ok", amount=shown,
                  method=method_name(method, lang), id=cur.lastrowid)


def history_text(user_id: int) -> str:
    rows = db.all_("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
    user = db.get_user(user_id)
    lang = i18n.lang_of(user_id)
    lines = [i18n.t(lang, "m_hist_title"), ui.LINE,
             f"<blockquote>{i18n.t(lang, 'm_yours')}: <b>{money(user['tmt'])}</b>\n"
             f"{i18n.t(lang, 'm_paid_total')}: <b>{money(user['tmt_paid'])}</b></blockquote>"]
    if not rows:
        lines.append(i18n.t(lang, "m_hist_empty"))
    for row in rows:
        icon = {"bekliyor": "⏳", "odendi": "✅", "reddedildi": "❌"}.get(row["state"], "•")
        date = dt.datetime.fromtimestamp(row["created_ts"]).strftime("%d.%m.%Y")
        lines.append(f"{icon} #{row['id']} — {request_display(row)} • {date}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    if not ui.is_private(update):
        await query.answer(i18n.t(lang, "only_private"), show_alert=True)
        return
    TOASTS = {"menu": "💵", "wd": "💸 Para çekme", "amt": "💰 Tutar seç",
              "cur": "💱 Para birimi", "mth": "📮 Ödeme yolu", "hist": "📜 Geçmiş"}
    await query.answer(TOASTS.get(action, ""))
    user = db.get_user(user_id)

    if action == "menu":
        await ui.nav(query, "cash", panel_text(user_id), panel_kb(user_id))

    elif action == "none":
        await query.answer(i18n.t(lang, "m_cap_hit"), show_alert=True)

    elif action == "ex":
        await query.answer(_plain(exchange(user_id, int(parts[2]))), show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))

    elif action == "exmax":
        _reset_if_new_day(user_id)
        user = db.get_user(user_id)
        possible = min(left_today(user), user["coins"] * 100 // config.COINS_PER_MONEY)
        if possible <= 0:
            await query.answer(i18n.t(lang, "m_no_coins"), show_alert=True)
        else:
            await query.answer(_plain(exchange(user_id, possible)), show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))

    elif action == "wd":
        ok, msg = can_withdraw(user)
        if not ok:
            await ui.safe_edit(query, (
                f"{i18n.t(lang, 'm_wd')}\n{ui.LINE}\n"
                f"{i18n.t(lang, 'm_not_yet')} <b>{msg}</b>\n\n"
                + i18n.t(lang, "m_rules", min=money(config.MIN_WITHDRAW),
                         lvl=config.WITHDRAW_MIN_LEVEL, days=config.WITHDRAW_MIN_DAYS)
            ), ui.kb([[(i18n.t(lang, "b_money"), "cash:menu")],
                      [(i18n.t(lang, "b_play"), "g:menu")]]))
            return
        rows = [[(f"💸 {money(config.MIN_WITHDRAW)}", f"cash:amt:{config.MIN_WITHDRAW}")]]
        if user["tmt"] >= 1000:
            rows.append([("💸 " + money(1000), "cash:amt:1000")])
        rows.append([(f"{i18n.t(lang, 'm_all')} ({money(user['tmt'])})", f"cash:amt:{user['tmt']}")])
        rows.append([(i18n.t(lang, "b_back"), "cash:menu")])
        await ui.safe_edit(query, (
            f"{i18n.t(lang, 'm_wd')}\n{ui.LINE}\n"
            f"<blockquote>{i18n.t(lang, 'm_yours')}: <b>{money(user['tmt'])}</b></blockquote>\n"
            f"{i18n.t(lang, 'm_ask_amount')}"
        ), ui.kb(rows))

    elif action == "amt":
        amount = int(parts[2])
        if not config.USDT_ENABLED:
            await _ask_method(query, lang, amount, "TMT")
            return
        await ui.safe_edit(query, (
            f"{i18n.t(lang, 'm_wd')}\n{ui.LINE}\n"
            f"<blockquote><b>{money(amount)}</b>  =  <b>{usdt_str(amount)}</b>\n"
            f"<i>1 USDT = {config.TMT_PER_USDT:g} {config.MONEY_NAME}</i></blockquote>\n"
            f"{i18n.t(lang, 'cur_pick')}"
        ), ui.kb([
            [(f"🇹🇲 {money(amount)}", f"cash:cur:{amount}:TMT")],
            [(f"💎 {usdt_str(amount)}", f"cash:cur:{amount}:USDT")],
            [(i18n.t(lang, "b_back"), "cash:wd")],
        ]))

    elif action == "cur":
        amount, currency = int(parts[2]), parts[3]
        await _ask_method(query, lang, amount, currency)

    elif action == "mth":
        amount, method = int(parts[2]), parts[3]
        currency = parts[4] if len(parts) > 4 else "TMT"
        context.user_data["await"] = {"kind": "cash_details", "amount": amount,
                                      "method": method, "currency": currency}
        shown = usdt_str(amount) if currency == "USDT" else money(amount)
        await ui.safe_edit(query, i18n.t(
            lang, "m_last", amount=shown, method=method_name(method, lang),
            what=i18n.t(lang, ASK_KEYS.get(method, "pm_other_ask"))
        ), ui.kb([[(i18n.t(lang, "m_cancel"), "cash:menu")]]))

    elif action == "hist":
        await ui.safe_edit(query, history_text(user_id), ui.kb([
            [(i18n.t(lang, "b_money"), "cash:menu")], [(i18n.t(lang, "b_home"), "m:main")]]))


async def _ask_method(query, lang: str, amount: int, currency: str):
    if currency == "USDT":
        rows = [[(f"🪙 CryptoBot ({config.CRYPTOBOT_NAME})", f"cash:mth:{amount}:crypto:USDT")]]
        note = f"\n<i>{i18n.t(lang, 'cur_note')}</i>"
        shown = f"{usdt_str(amount)}  ({money(amount)})"
    else:
        rows = [[(i18n.t(lang, key), f"cash:mth:{amount}:{code}:TMT")]
                for code, key in METHOD_KEYS.items()]
        note = ""
        shown = money(amount)
    rows.append([(i18n.t(lang, "b_back"), "cash:wd")])
    await ui.safe_edit(query, (
        f"{i18n.t(lang, 'm_wd')}\n{ui.LINE}\n"
        f"<blockquote><b>{shown}</b></blockquote>\n"
        f"{i18n.t(lang, 'm_ask_method')}{note}"
    ), ui.kb(rows))


def _plain(text: str) -> str:
    for tag in ("<b>", "</b>", "<blockquote>", "</blockquote>", "<i>", "</i>"):
        text = text.replace(tag, "")
    return text


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending or pending.get("kind") != "cash_details":
        return False
    context.user_data.pop("await", None)
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    details = (update.message.text or "").strip()
    if len(details) < 3:
        await ui.send(update, "❌", ui.kb([[(i18n.t(lang, "m_wd"), "cash:wd")]]))
        return True
    result = create_request(user_id, pending["amount"], pending["method"], details,
                            pending.get("currency", "TMT"))
    await ui.send(update, result, ui.kb([
        [(i18n.t(lang, "b_money"), "cash:menu")], [(i18n.t(lang, "b_home"), "m:main")]]))

    # yöneticilere haber ver (yönetici yazıları Türkçe kalır)
    row = db.one("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    if row and row["state"] == "bekliyor":
        user = db.get_user(user_id)
        text = (
            f"💸 <b>YENİ ÇEKİM TALEBİ #{row['id']}</b>\n{ui.LINE}\n"
            f"👤 {ui.mention(user)} (<code>{user_id}</code>)\n"
            f"💵 Tutar: {request_display(row)}\n"
            f"📮 {method_name(row['method'], 'tr')}\n"
            f"📝 <code>{ui.esc(row['details'])}</code>\n\n"
            f"<blockquote>🎚 Seviye {user['level']} • {days_old(user)} günlük hesap\n"
            f"🎮 {ui.fmt(user['games'])} oyun • toplam ödenen {money(user['tmt_paid'])}</blockquote>"
        )
        kb = ui.kb([[("✅ Ödedim", f"ad:pay:{row['id']}"), ("❌ Reddet", f"ad:rej:{row['id']}")]])
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, text, parse_mode=ParseMode.HTML,
                                               reply_markup=kb)
            except Exception:
                pass
    return True


async def cmd_cash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.screen(update, "cash", panel_text(user_id), panel_kb(user_id))
