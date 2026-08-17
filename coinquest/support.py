# -*- coding: utf-8 -*-
"""Destek sistemi: oyuncu ile yetkili arasında iki yönlü yazışma.

Fotoğraf, video, ses, dosya — her şey gönderilebilir (copy_message ile birebir iletilir).
"""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import db
import i18n
import ui

log = logging.getLogger(__name__)


def open_ticket(user_id: int) -> int:
    row = db.one("SELECT * FROM tickets WHERE user_id=? AND state='acik' ORDER BY id DESC", (user_id,))
    if row:
        return row["id"]
    cur = db.run("INSERT INTO tickets (user_id, created_ts, last_ts) VALUES (?,?,?)",
                 (user_id, ui.now(), ui.now()))
    return int(cur.lastrowid)


def add_msg(ticket_id: int, sender: int, is_staff: bool, kind: str, text: str) -> None:
    db.run("INSERT INTO ticket_msgs (ticket_id, sender, is_staff, kind, text, ts) VALUES (?,?,?,?,?,?)",
           (ticket_id, sender, int(is_staff), kind, text[:400], ui.now()))
    db.run("UPDATE tickets SET last_ts=?, unread=? WHERE id=?",
           (ui.now(), 0 if is_staff else 1, ticket_id))


def kind_of(msg) -> str:
    for attr, name in (("photo", "fotoğraf"), ("video", "video"), ("animation", "gif"),
                       ("document", "dosya"), ("voice", "ses"), ("audio", "ses"),
                       ("sticker", "çıkartma"), ("video_note", "video")):
        if getattr(msg, attr, None):
            return name
    return "yazı"


# ---------------------------------------------------------------------------
# OYUNCU TARAFI
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    ticket = db.one("SELECT * FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    msgs = db.all_("SELECT * FROM ticket_msgs WHERE ticket_id=? ORDER BY id DESC LIMIT 6",
                   (ticket["id"],)) if ticket else []
    text = f"{i18n.t(lang, 'sup_title')}\n{ui.LINE}\n{i18n.t(lang, 'sup_info')}"
    if msgs:
        text += "\n\n<blockquote><b>" + i18n.t(lang, "sup_last") + "</b>\n"
        for row in reversed(msgs):
            who = "🎧" if row["is_staff"] else "👤"
            body = ui.esc(row["text"][:60]) if row["text"] else f"[{row['kind']}]"
            text += f"{who} {body}\n"
        text += "</blockquote>"
    return text


def panel_kb(user_id: int):
    lang = i18n.lang_of(user_id)
    return ui.kb([
        [(i18n.t(lang, "sup_write"), "sup:write")],
        [(i18n.t(lang, "b_home"), "m:main")],
    ])


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    parts = query.data.split(":")
    action = parts[1]
    lang = i18n.lang_of(user_id)
    await query.answer()

    if action == "menu":
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
    elif action == "write":
        context.user_data["await"] = {"kind": "support_msg"}
        await ui.safe_edit(query, (
            f"{i18n.t(lang, 'sup_title')}\n{ui.LINE}\n{i18n.t(lang, 'sup_ask')}"
        ), ui.kb([[(i18n.t(lang, "b_back"), "sup:menu")]]))
    elif action == "reply":                       # yetkili cevaplıyor
        if not db.staff_role(user_id):
            await query.answer("Yetkin yok.", show_alert=True)
            return
        ticket_id = int(parts[2])
        context.user_data["await"] = {"kind": "support_reply", "ticket": ticket_id}
        ticket = db.one("SELECT * FROM tickets WHERE id=?", (ticket_id,))
        target = db.get_user(ticket["user_id"]) if ticket else None
        await query.message.chat.send_message(
            f"💬 <b>#{ticket_id} — {ui.name_of(target)}</b> için cevabını yaz.\n"
            "<i>Fotoğraf/video da gönderebilirsin.</i>", parse_mode=ParseMode.HTML)
    elif action == "close":
        if not db.staff_role(user_id):
            return
        db.run("UPDATE tickets SET state='kapali', unread=0 WHERE id=?", (int(parts[2]),))
        await query.answer("Kapatıldı.")
        await ui.safe_edit(query, inbox_text(), inbox_kb())
    elif action == "inbox":
        if not db.staff_role(user_id):
            return
        await ui.safe_edit(query, inbox_text(), inbox_kb())


# ---------------------------------------------------------------------------
# YETKİLİ TARAFI
# ---------------------------------------------------------------------------

def inbox_text() -> str:
    rows = db.all_("SELECT * FROM tickets WHERE state='acik' ORDER BY unread DESC, last_ts DESC LIMIT 10")
    lines = [f"🎧 <b>DESTEK KUTUSU</b>\n{ui.LINE}"]
    if not rows:
        lines.append("Açık destek talebi yok 👌")
    for row in rows:
        user = db.get_user(row["user_id"])
        last = db.one("SELECT * FROM ticket_msgs WHERE ticket_id=? ORDER BY id DESC LIMIT 1",
                      (row["id"],))
        body = (ui.esc(last["text"][:70]) if last and last["text"] else
                f"[{last['kind']}]" if last else "—")
        lines.append(
            f"\n{'🔴' if row['unread'] else '⚪'} <b>#{row['id']}</b> {ui.name_of(user)} "
            f"<code>{row['user_id']}</code>\n<blockquote>{body}</blockquote>")
    return "\n".join(lines)


def inbox_kb():
    rows_db = db.all_("SELECT * FROM tickets WHERE state='acik' ORDER BY unread DESC, last_ts DESC LIMIT 10")
    rows = [[(f"💬 #{r['id']} cevapla", f"sup:reply:{r['id']}"),
             ("✅", f"sup:close:{r['id']}")] for r in rows_db]
    rows.append([("🔄 Yenile", "sup:inbox"), ("⬅️ Panel", "ad:home")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# MESAJ AKIŞI
# ---------------------------------------------------------------------------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Destek yazışmasını işler (her tür medya)."""
    pending = context.user_data.get("await")
    if not pending or pending.get("kind") not in ("support_msg", "support_reply"):
        return False
    msg = update.message
    user_id = update.effective_user.id
    kind = pending["kind"]
    context.user_data.pop("await", None)
    body = (msg.text or msg.caption or "").strip()

    # --- oyuncudan yetkiliye ---
    if kind == "support_msg":
        lang = i18n.lang_of(user_id)
        ticket_id = open_ticket(user_id)
        add_msg(ticket_id, user_id, False, kind_of(msg), body)
        user = db.get_user(user_id)
        header = (
            f"🎧 <b>DESTEK #{ticket_id}</b>\n"
            f"👤 {ui.mention(user)} <code>{user_id}</code>\n"
            f"🎚 Sv.{user['level']} • 🪙 {ui.fmt(user['coins'])} • 💵 {ui.money(user['tmt'])}"
        )
        kb = ui.kb([[("💬 Cevapla", f"sup:reply:{ticket_id}"), ("✅ Kapat", f"sup:close:{ticket_id}")],
                    [("👤 Oyuncu kartı", f"ad:card:{user_id}")]])
        sent = 0
        for staff_id in db.staff_ids("admin", "support"):
            try:
                await context.bot.send_message(staff_id, header, parse_mode=ParseMode.HTML)
                await context.bot.copy_message(chat_id=staff_id, from_chat_id=msg.chat_id,
                                               message_id=msg.message_id, reply_markup=kb)
                sent += 1
            except Exception:
                continue
        await ui.send(update, i18n.t(lang, "sup_sent"),
                      ui.kb([[(i18n.t(lang, "b_home"), "m:main")]]))
        if sent == 0:
            log.warning("destek mesajı iletilemedi, yetkili yok")
        return True

    # --- yetkiliden oyuncuya ---
    if not db.staff_role(user_id):
        return True
    ticket_id = pending.get("ticket")
    ticket = db.one("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    if not ticket:
        await ui.send(update, "Talep bulunamadı.")
        return True
    target = ticket["user_id"]
    lang = i18n.lang_of(target)
    add_msg(ticket_id, user_id, True, kind_of(msg), body)
    db.run("UPDATE tickets SET staff_id=? WHERE id=?", (user_id, ticket_id))
    try:
        await context.bot.send_message(target, i18n.t(lang, "sup_from_staff"),
                                       parse_mode=ParseMode.HTML)
        await context.bot.copy_message(chat_id=target, from_chat_id=msg.chat_id,
                                       message_id=msg.message_id,
                                       reply_markup=ui.kb([[(i18n.t(lang, "sup_write"), "sup:write")]]))
        await ui.send(update, f"✅ Cevap gönderildi (#{ticket_id}).",
                      ui.kb([[("🎧 Destek kutusu", "sup:inbox")]]))
        db.log_action(user_id, "support_reply", f"#{ticket_id} -> {target}")
    except Exception as exc:
        await ui.send(update, f"❌ Gönderilemedi: {exc}")
    return True


async def cmd_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.send(update, panel_text(user_id), panel_kb(user_id))
