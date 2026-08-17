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
import ui

METHODS = {
    "karta": "💳 Banka kartı",
    "telefon": "📱 Telefon numarası",
    "diger": "✍️ Diğer",
}


def money(value: int) -> str:
    """500 -> '5.00 TMT'"""
    return f"{value / 100:.2f} {config.MONEY_NAME}"


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
# EKRANLAR
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    _reset_if_new_day(user_id)
    user = db.get_user(user_id)
    kalan = max(0, config.MIN_WITHDRAW - user["tmt"])
    return (
        "💵 <b>GERÇEK PARA</b>\n\n"
        f"💰 Paran: <b>{money(user['tmt'])}</b>\n"
        f"🪙 Coinin: <b>{ui.fmt(user['coins'])}</b>\n\n"
        f"📅 Bugün çevirebileceğin: <b>{money(left_today(user))}</b>\n"
        f"🎯 Para çekmek için gereken: <b>{money(config.MIN_WITHDRAW)}</b>"
        + (f" (daha {money(kalan)} lazım)" if kalan else " ✅ hazır!") + "\n\n"
        "<b>Nasıl çalışır?</b>\n"
        "1️⃣ Oyun oynarsın, coin toplarsın\n"
        f"2️⃣ Coini paraya çevirirsin ({ui.fmt(config.COINS_PER_MONEY)} coin = 1.00 {config.MONEY_NAME})\n"
        f"3️⃣ Günde en fazla {money(config.DAILY_MONEY_CAP)} çevirebilirsin\n"
        f"4️⃣ {money(config.MIN_WITHDRAW)} olunca çekim istersin, ben elden öderim\n\n"
        f"<i>Günlük limit yüzünden {money(config.MIN_WITHDRAW)} en erken 8 günde dolar. "
        "Yani her gün gelip oynaman lazım 😊</i>"
    )


def panel_kb(user_id: int):
    user = db.get_user(user_id)
    rows = []
    for amount in (10, 25, 50):
        if amount <= left_today(user):
            rows.append([(f"🔁 {ui.fmt(coins_for(amount))} coin ➜ {money(amount)}", f"cash:ex:{amount}")])
    if left_today(user) > 0:
        rows.append([("⚡ Bugünlük limiti doldur", "cash:exmax")])
    else:
        rows.append([("✅ Bugünlük limit doldu", "cash:none")])
    rows.append([("💸 Para Çek", "cash:wd"), ("📜 Geçmiş", "cash:hist")])
    rows.append([("🎮 Oyunlar", "g:menu"), ("🏠 Menü", "m:main")])
    return ui.kb(rows)


def exchange(user_id: int, amount: int) -> str:
    """Coin -> para çevirir. amount kuruş cinsindendir."""
    _reset_if_new_day(user_id)
    user = db.get_user(user_id)
    if amount <= 0:
        return "Çevrilecek miktar yok."
    limit = left_today(user)
    if limit <= 0:
        return f"Bugünlük limitin doldu. Yarın devam! (günlük {money(config.DAILY_MONEY_CAP)})"
    if amount > limit:
        amount = limit
    need = coins_for(amount)
    if user["coins"] < need:
        return (f"Yeterli coinin yok.\nGereken: {ui.fmt(need)} 🪙\n"
                f"Sende: {ui.fmt(user['coins'])} 🪙")
    if not economy.take_coins(user_id, need, "paraya çevirme"):
        return "İşlem olmadı, tekrar dene."
    db.bump(user_id, tmt=amount, tmt_today=amount)
    db.upd(user_id, tmt_day=_today())
    user = db.get_user(user_id)
    return (f"✅ {ui.fmt(need)} coin ➜ <b>{money(amount)}</b>\n"
            f"💰 Toplam paran: <b>{money(user['tmt'])}</b>")


# ---------------------------------------------------------------------------
# PARA ÇEKME
# ---------------------------------------------------------------------------

def can_withdraw(user) -> tuple[bool, str]:
    if user["tmt"] < config.MIN_WITHDRAW:
        return False, (f"En az {money(config.MIN_WITHDRAW)} biriktirmen lazım.\n"
                       f"Şu an: {money(user['tmt'])}")
    if user["level"] < config.WITHDRAW_MIN_LEVEL:
        return False, f"Seviye {config.WITHDRAW_MIN_LEVEL} olman lazım (şu an {user['level']})."
    if days_old(user) < config.WITHDRAW_MIN_DAYS:
        return False, (f"Hesabın en az {config.WITHDRAW_MIN_DAYS} günlük olmalı "
                       f"(şu an {days_old(user)} gün).")
    pending = db.scalar(
        "SELECT COUNT(*) FROM withdrawals WHERE user_id=? AND state='bekliyor'", (user["user_id"],))
    if pending:
        return False, "Zaten bekleyen bir çekim talebin var. Önce o ödensin."
    return True, ""


def create_request(user_id: int, amount: int, method: str, details: str) -> str:
    user = db.get_user(user_id)
    ok, msg = can_withdraw(user)
    if not ok:
        return "❌ " + msg
    amount = min(amount, user["tmt"])
    if amount < config.MIN_WITHDRAW:
        return f"❌ En az {money(config.MIN_WITHDRAW)} çekebilirsin."
    db.bump(user_id, tmt=-amount)
    cur = db.run(
        "INSERT INTO withdrawals (user_id, amount, method, details, created_ts) VALUES (?,?,?,?,?)",
        (user_id, amount, method, details[:120], ui.now()))
    db.log_tx(user_id, 0, f"çekim talebi #{cur.lastrowid}")
    return (
        f"✅ <b>TALEBİN ALINDI!</b>\n\n"
        f"💵 Tutar: <b>{money(amount)}</b>\n"
        f"📮 Yöntem: {METHODS.get(method, method)}\n"
        f"📝 Bilgi: {ui.esc(details[:120])}\n"
        f"🔖 Talep no: #{cur.lastrowid}\n\n"
        "Yönetici en kısa sürede ödemeyi yapacak. Ödeme yapılınca sana mesaj gelir."
    )


def history_text(user_id: int) -> str:
    rows = db.all_("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
    user = db.get_user(user_id)
    lines = ["📜 <b>ÇEKİM GEÇMİŞİN</b>\n",
             f"💰 Şu anki paran: <b>{money(user['tmt'])}</b>",
             f"✅ Bugüne kadar ödenen: <b>{money(user['tmt_paid'])}</b>\n"]
    if not rows:
        lines.append("Henüz çekim talebin yok.")
    for row in rows:
        icon = {"bekliyor": "⏳", "odendi": "✅", "reddedildi": "❌"}.get(row["state"], "•")
        date = dt.datetime.fromtimestamp(row["created_ts"]).strftime("%d.%m.%Y")
        lines.append(f"{icon} #{row['id']} — {money(row['amount'])} • {date} • {row['state']}")
        if row["note"]:
            lines.append(f"    <i>{ui.esc(row['note'])}</i>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await query.answer("Bu bölüm sadece bota özelden yazınca açılır.", show_alert=True)
        return
    await query.answer()
    user = db.get_user(user_id)

    if action == "menu":
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
    elif action == "none":
        await query.answer("Bugünlük limit doldu, yarın tekrar gel 🙂", show_alert=True)
    elif action == "ex":
        await query.answer(_plain(exchange(user_id, int(parts[2]))), show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
    elif action == "exmax":
        _reset_if_new_day(user_id)
        user = db.get_user(user_id)
        possible = min(left_today(user), user["coins"] * 100 // config.COINS_PER_MONEY)
        if possible <= 0:
            await query.answer("Çevirecek kadar coinin yok. Biraz daha oyna! 🎮", show_alert=True)
        else:
            await query.answer(_plain(exchange(user_id, possible)), show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
    elif action == "wd":
        ok, msg = can_withdraw(user)
        if not ok:
            await ui.safe_edit(query, (
                f"💸 <b>PARA ÇEKME</b>\n\n❌ Henüz olmaz:\n{msg}\n\n"
                f"<b>Şartlar</b>\n"
                f"• En az {money(config.MIN_WITHDRAW)} biriktir\n"
                f"• Seviye {config.WITHDRAW_MIN_LEVEL} ol\n"
                f"• Hesabın {config.WITHDRAW_MIN_DAYS} günlük olsun\n\n"
                "Oyna, kazan, yarın tekrar gel 🙂"
            ), ui.kb([[("💵 Para Ekranı", "cash:menu")], [("🎮 Oyunlar", "g:menu")]]))
            return
        rows = [[(f"💸 {money(config.MIN_WITHDRAW)}", f"cash:amt:{config.MIN_WITHDRAW}")]]
        if user["tmt"] >= 1000:
            rows.append([("💸 10.00 " + config.MONEY_NAME, "cash:amt:1000")])
        rows.append([(f"💸 Hepsi ({money(user['tmt'])})", f"cash:amt:{user['tmt']}")])
        rows.append([("⬅️ Geri", "cash:menu")])
        await ui.safe_edit(query, (
            f"💸 <b>PARA ÇEKME</b>\n\n💰 Paran: <b>{money(user['tmt'])}</b>\n\n"
            "Ne kadar çekmek istersin?"
        ), ui.kb(rows))
    elif action == "amt":
        amount = int(parts[2])
        rows = [[(label, f"cash:mth:{amount}:{key}")] for key, label in METHODS.items()]
        rows.append([("⬅️ Geri", "cash:wd")])
        await ui.safe_edit(query, (
            f"💸 <b>PARA ÇEKME</b>\n\nTutar: <b>{money(amount)}</b>\n\n"
            "Parayı nasıl almak istersin?"
        ), ui.kb(rows))
    elif action == "mth":
        amount, method = int(parts[2]), parts[3]
        context.user_data["await"] = {"kind": "cash_details", "amount": amount, "method": method}
        ornek = {"karta": "kart numaran", "telefon": "telefon numaran",
                 "diger": "ödeme bilgin"}.get(method, "bilgin")
        await ui.safe_edit(query, (
            f"💸 <b>SON ADIM</b>\n\nTutar: <b>{money(amount)}</b>\n"
            f"Yöntem: {METHODS[method]}\n\n"
            f"Şimdi <b>{ornek}</b> yaz ve gönder.\n"
            "<i>Vazgeçmek için aşağıdaki butona bas.</i>"
        ), ui.kb([[("⬅️ Vazgeç", "cash:menu")]]))
    elif action == "hist":
        await ui.safe_edit(query, history_text(user_id), ui.kb([
            [("💵 Para Ekranı", "cash:menu")], [("🏠 Menü", "m:main")]]))


def _plain(text: str) -> str:
    return text.replace("<b>", "").replace("</b>", "")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending or pending.get("kind") != "cash_details":
        return False
    context.user_data.pop("await", None)
    user_id = update.effective_user.id
    details = (update.message.text or "").strip()
    if len(details) < 3:
        await ui.send(update, "Bilgi çok kısa görünüyor, tekrar dene.", ui.kb([[("💸 Para Çek", "cash:wd")]]))
        return True
    result = create_request(user_id, pending["amount"], pending["method"], details)
    await ui.send(update, result, ui.kb([[("💵 Para Ekranı", "cash:menu")], [("🏠 Menü", "m:main")]]))

    # yöneticilere haber ver
    row = db.one("SELECT * FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    if row and row["state"] == "bekliyor":
        user = db.get_user(user_id)
        text = (
            f"💸 <b>YENİ ÇEKİM TALEBİ #{row['id']}</b>\n\n"
            f"👤 {ui.mention(user)} (<code>{user_id}</code>)\n"
            f"💵 Tutar: <b>{money(row['amount'])}</b>\n"
            f"📮 {METHODS.get(row['method'], row['method'])}\n"
            f"📝 <code>{ui.esc(row['details'])}</code>\n\n"
            f"🎚 Seviye {user['level']} • {days_old(user)} günlük hesap\n"
            f"🎮 {ui.fmt(user['games'])} oyun • bugüne kadar ödenen {money(user['tmt_paid'])}"
        )
        kb = ui.kb([[("✅ Ödedim", f"ad:pay:{row['id']}"), ("❌ Reddet", f"ad:rej:{row['id']}")]])
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, text, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                pass
    return True


async def cmd_cash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "💵 Para ekranı özelde açılır.", ui.pm_link())
        return
    await ui.send(update, panel_text(update.effective_user.id), panel_kb(update.effective_user.id))
