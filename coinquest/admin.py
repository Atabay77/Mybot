# -*- coding: utf-8 -*-
"""Yönetici paneli.

Roller:
    owner   -> .env içindeki ADMIN_IDS. Her şeyi yapar, yetkili ekler/siler.
    admin   -> ödeme onayı, para verme, ban, reklam, destek.
    support -> sadece destek kutusu.
"""
import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import cash
import config
import db
import economy
import events
import i18n
import ui

log = logging.getLogger(__name__)

ROLE_NAMES = {"owner": "👑 Kurucu", "admin": "🛠 Yönetici", "support": "🎧 Destek"}
CAN = {                       # hangi rol neye erişir
    "owner":   {"all"},
    "admin":   {"wds", "bc", "users", "money", "ban", "support", "stats", "events", "logs"},
    "support": {"support"},
}


def role_of(user_id: int) -> str:
    return db.staff_role(user_id)


def is_staff(user_id: int) -> bool:
    return bool(role_of(user_id))


def allowed(user_id: int, what: str) -> bool:
    role = role_of(user_id)
    if not role:
        return False
    perms = CAN.get(role, set())
    return "all" in perms or what in perms


# ---------------------------------------------------------------------------
# ANA PANEL
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    now = ui.now()
    role = role_of(user_id)
    users = int(db.scalar("SELECT COUNT(*) FROM users"))
    day = int(db.scalar("SELECT COUNT(*) FROM users WHERE last_seen > ?", (now - 86400,)))
    new_day = int(db.scalar("SELECT COUNT(*) FROM users WHERE created_ts > ?", (now - 86400,)))
    wd_wait = int(db.scalar("SELECT COUNT(*) FROM withdrawals WHERE state='bekliyor'"))
    wd_sum = int(db.scalar("SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE state='bekliyor'"))
    tickets = int(db.scalar("SELECT COUNT(*) FROM tickets WHERE state='acik' AND unread>0"))
    return (
        f"🛠 <b>YÖNETİM PANELİ</b>\n{ui.LINE}\n"
        f"<blockquote>👤 Sen: {ROLE_NAMES.get(role, role)}\n"
        f"👥 Oyuncu: <b>{ui.fmt(users)}</b>  (bugün aktif {ui.fmt(day)}, yeni {ui.fmt(new_day)})</blockquote>\n"
        f"{'🔴' if wd_wait else '🟢'} Bekleyen ödeme: <b>{wd_wait}</b> ({cash.money(wd_sum)})\n"
        f"{'🔴' if tickets else '🟢'} Okunmamış destek: <b>{tickets}</b>\n\n"
        "Ne yapmak istersin?"
    )


def panel_kb(user_id: int):
    rows = []
    if allowed(user_id, "wds"):
        wait = int(db.scalar("SELECT COUNT(*) FROM withdrawals WHERE state='bekliyor'"))
        rows.append([(f"💸 Ödeme Talepleri{f' ({wait})' if wait else ''}", "ad:wds")])
    if allowed(user_id, "support"):
        unread = int(db.scalar("SELECT COUNT(*) FROM tickets WHERE state='acik' AND unread>0"))
        rows.append([(f"🎧 Destek Kutusu{f' ({unread})' if unread else ''}", "ad:sup")])
    if allowed(user_id, "bc"):
        rows.append([("📣 Reklam / Duyuru Gönder", "ad:bc")])
    if allowed(user_id, "users"):
        rows.append([("🔍 Oyuncu Ara", "ad:find"), ("📊 İstatistik", "ad:stats")])
    if allowed(user_id, "money"):
        rows.append([("🪙 Coin Ver", "ad:give"), ("💎 Elmas Ver", "ad:gems")])
        rows.append([("💵 Gerçek Para Ekle", "ad:money")])
    if allowed(user_id, "ban"):
        rows.append([("🚫 Ban", "ad:ban"), ("✅ Ban Kaldır", "ad:unban")])
    if allowed(user_id, "events"):
        rows.append([("🐉 Canavar Çıkar", "ad:boss"), ("🎟 Çekiliş Yap", "ad:lottery")])
    if role_of(user_id) == "owner":
        rows.append([("👮 Yetkililer", "ad:staff")])
    if allowed(user_id, "logs"):
        rows.append([("📜 Son Hareketler", "ad:logs")])
    rows.append([("🔄 Yenile", "ad:home")])
    return ui.kb(rows)


def stats_text() -> str:
    now = ui.now()
    def n(sql, p=()):
        return int(db.scalar(sql, p))
    users = n("SELECT COUNT(*) FROM users")
    week = n("SELECT COUNT(*) FROM users WHERE last_seen > ?", (now - 7 * 86400,))
    coins = n("SELECT COALESCE(SUM(coins+bank),0) FROM users")
    gems = n("SELECT COALESCE(SUM(gems),0) FROM users")
    tmt = n("SELECT COALESCE(SUM(tmt),0) FROM users")
    paid = n("SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE state='odendi'")
    plays = n("SELECT COALESCE(SUM(games),0) FROM users")
    wagered = n("SELECT COALESCE(SUM(wagered),0) FROM users")
    duels = n("SELECT COUNT(*) FROM duels WHERE state='done'")
    groups = n("SELECT COUNT(*) FROM groups")
    clans = n("SELECT COUNT(*) FROM clans")
    banned = n("SELECT COUNT(*) FROM users WHERE banned=1")
    refs = n("SELECT COUNT(*) FROM users WHERE referrer<>0")
    listings = n("SELECT COUNT(*) FROM bazaar WHERE sold_to=0")
    boss = events.active_boss()
    top = db.all_("SELECT first_name, coins+bank AS v FROM users ORDER BY v DESC LIMIT 3")
    lines = [
        f"📊 <b>İSTATİSTİKLER</b>\n{ui.LINE}",
        "<blockquote><b>Oyuncular</b>\n"
        f"Toplam: {ui.fmt(users)}   •   7 gün aktif: {ui.fmt(week)}\n"
        f"Davetle gelen: {ui.fmt(refs)}   •   Banlı: {ui.fmt(banned)}</blockquote>",
        "<blockquote><b>Ekonomi</b>\n"
        f"Dolaşan coin: {ui.fmt(coins)}\n"
        f"Elmas: {ui.fmt(gems)}\n"
        f"Oyuncularda bekleyen para: {cash.money(tmt)}\n"
        f"Bugüne kadar ödenen: {cash.money(paid)}</blockquote>",
        "<blockquote><b>Oyun</b>\n"
        f"Oynanan: {ui.fmt(plays)}   •   Toplam bahis: {ui.fmt(wagered)}\n"
        f"Biten düello: {ui.fmt(duels)}   •   Pazar ilanı: {ui.fmt(listings)}\n"
        f"Grup: {ui.fmt(groups)}   •   Klan: {ui.fmt(clans)}</blockquote>",
        f"🐉 Aktif canavar: {ui.esc(boss['name']) if boss else '—'}",
    ]
    if top:
        lines.append("\n<b>En zenginler</b>")
        for i, row in enumerate(top, 1):
            lines.append(f"{i}. {ui.esc(row['first_name'])} — {ui.fmt(row['v'])} 🪙")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ÖDEME TALEPLERİ
# ---------------------------------------------------------------------------

def withdrawals_text() -> str:
    rows = db.all_("SELECT * FROM withdrawals WHERE state='bekliyor' ORDER BY id LIMIT 10")
    total = int(db.scalar("SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE state='bekliyor'"))
    paid = int(db.scalar("SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE state='odendi'"))
    lines = [f"💸 <b>ÖDEME TALEPLERİ</b>\n{ui.LINE}",
             f"<blockquote>⏳ Bekleyen: <b>{cash.money(total)}</b> ({len(rows)} talep)\n"
             f"✅ Toplam ödenen: <b>{cash.money(paid)}</b></blockquote>"]
    if not rows:
        lines.append("Bekleyen talep yok 👌")
    for row in rows:
        user = db.get_user(row["user_id"])
        cur = cash.request_display(row)
        lines.append(
            f"\n<b>#{row['id']}</b> — {cur}\n"
            f"👤 {ui.name_of(user)} <code>{row['user_id']}</code> • Sv.{user['level'] if user else '?'}"
            f" • {cash.days_old(user) if user else 0} günlük\n"
            f"{cash.method_name(row['method'], 'tr')}: <code>{ui.esc(row['details'])}</code>")
    return "\n".join(lines)


def withdrawals_kb():
    rows_db = db.all_("SELECT * FROM withdrawals WHERE state='bekliyor' ORDER BY id LIMIT 10")
    rows = [[(f"✅ #{r['id']} ödedim", f"ad:pay:{r['id']}"), ("❌", f"ad:rej:{r['id']}")]
            for r in rows_db]
    rows.append([("🔄 Yenile", "ad:wds"), ("⬅️ Panel", "ad:home")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# YETKİLİLER
# ---------------------------------------------------------------------------

def staff_text() -> str:
    rows = db.all_("SELECT * FROM staff ORDER BY role, user_id")
    lines = [f"👮 <b>YETKİLİLER</b>\n{ui.LINE}",
             "<blockquote>Kurucular .env dosyasındaki ADMIN_IDS listesinden gelir, "
             "buradan silinemez.</blockquote>"]
    for uid in config.ADMIN_IDS:
        user = db.get_user(uid)
        lines.append(f"👑 {ui.name_of(user) if user else uid} <code>{uid}</code>")
    if not rows:
        lines.append("\nBaşka yetkili yok.")
    for row in rows:
        user = db.get_user(row["user_id"])
        lines.append(f"{ROLE_NAMES.get(row['role'], row['role'])} "
                     f"{ui.name_of(user) if user else row['user_id']} <code>{row['user_id']}</code>")
    lines.append("\n<i>Yetkililer sıralamalarda görünmez.</i>")
    return "\n".join(lines)


def staff_kb():
    rows = [[("➕ Yönetici Ekle", "ad:addadmin"), ("➕ Destek Ekle", "ad:addsup")]]
    for row in db.all_("SELECT * FROM staff ORDER BY role LIMIT 10"):
        user = db.get_user(row["user_id"])
        rows.append([(f"🗑 {ui.name_of(user) if user else row['user_id']} sil",
                      f"ad:delstaff:{row['user_id']}")])
    rows.append([("⬅️ Panel", "ad:home")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# OYUNCU KARTI
# ---------------------------------------------------------------------------

def user_card(target_id: int) -> tuple[str, object]:
    user = db.get_user(target_id)
    if not user:
        return "Oyuncu bulunamadı.", ui.kb([[("⬅️ Panel", "ad:home")]])
    txs = db.all_("SELECT delta, reason FROM tx WHERE user_id=? ORDER BY id DESC LIMIT 6", (target_id,))
    wds = db.all_("SELECT amount, state FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 3",
                  (target_id,))
    role = role_of(target_id)
    text = (
        f"👤 <b>{ui.name_of(user)}</b>"
        + (f"  {ROLE_NAMES.get(role, '')}" if role else "") + "\n"
        f"<code>{target_id}</code>"
        + (f"  @{ui.esc(user['username'])}" if user["username"] else "") + f"\n{ui.LINE}\n"
        f"<blockquote>🪙 {ui.fmt(user['coins'])}  🏦 {ui.fmt(user['bank'])}  💎 {user['gems']}\n"
        f"💵 {cash.money(user['tmt'])}  (ödenen {cash.money(user['tmt_paid'])})\n"
        f"🎚 Seviye {user['level']}  •  ⚡ {user['energy']}\n"
        f"📅 {cash.days_old(user)} günlük hesap  •  🔥 {user['streak']} gün seri</blockquote>\n"
        f"🎮 {ui.fmt(user['games'])} oyun  •  ⚔️ {user['pvp_wins']}G/{user['pvp_losses']}Y\n"
        f"💰 Kazanç {ui.fmt(user['earned'])}  •  Bahis {ui.fmt(user['wagered'])}\n"
        f"👥 Davet: {user['refs']}  •  Davet eden: {user['referrer'] or '—'}\n"
        f"🤖 Bot koruması: {'✅' if user['captcha_ok'] else '❌'} ({user['captcha_try']} deneme)\n"
        f"🚫 Ban: {'evet' if user['banned'] else 'hayır'}\n"
    )
    if wds:
        text += "\n<b>Son ödemeler</b>\n" + "\n".join(
            f"• {cash.money(w['amount'])} — {w['state']}" for w in wds)
    if txs:
        text += "\n\n<b>Son hareketler</b>\n" + "\n".join(
            f"• {t['delta']:+} {ui.esc(t['reason'])}" for t in txs)
    kb = ui.kb([
        [("🪙 Coin ver", f"ad:ugive:{target_id}"), ("💎 Elmas ver", f"ad:ugems:{target_id}")],
        [("💵 Para ekle", f"ad:umoney:{target_id}")],
        [("🚫 Banla", f"ad:uban:{target_id}"), ("✅ Ban kaldır", f"ad:uunban:{target_id}")],
        [("💬 Mesaj gönder", f"ad:umsg:{target_id}")],
        [("🔍 Başka oyuncu", "ad:find"), ("⬅️ Panel", "ad:home")],
    ])
    return text, kb


# ---------------------------------------------------------------------------
# REKLAM / DUYURU  (arka planda çalışır, bot durmaz)
# ---------------------------------------------------------------------------

async def broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    bid = data["id"]
    row = db.one("SELECT * FROM broadcasts WHERE id=?", (bid,))
    if not row or row["state"] != "gonderiliyor":
        return
    targets = [r["user_id"] for r in db.all_(
        "SELECT user_id FROM users WHERE banned=0 ORDER BY last_seen DESC")]
    db.run("UPDATE broadcasts SET total=? WHERE id=?", (len(targets), bid))
    sent = failed = 0
    status_chat = row["admin_id"]
    status_msg = data.get("status_msg")
    for i, uid in enumerate(targets, 1):
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=row["src_chat"],
                                           message_id=row["src_msg"])
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            db.run("UPDATE broadcasts SET sent=?, failed=? WHERE id=?", (sent, failed, bid))
            if status_msg:
                try:
                    await context.bot.edit_message_text(
                        f"📣 <b>Gönderiliyor...</b>\n{ui.LINE}\n"
                        f"✅ {sent} / {len(targets)}   ❌ {failed}\n"
                        f"{ui.bar(i, len(targets), 12)}",
                        chat_id=status_chat, message_id=status_msg, parse_mode=ParseMode.HTML)
                except Exception:
                    pass
        await asyncio.sleep(0.045)          # saniyede ~22 mesaj: Telegram sınırının altında
    db.run("UPDATE broadcasts SET sent=?, failed=?, state='bitti' WHERE id=?", (sent, failed, bid))
    try:
        await context.bot.send_message(
            status_chat,
            f"📣 <b>REKLAM BİTTİ</b>\n{ui.LINE}\n"
            f"✅ Ulaşan: <b>{sent}</b>\n❌ Ulaşmayan: {failed}\n"
            f"(engelleyenler ve botu silenler)",
            parse_mode=ParseMode.HTML, reply_markup=ui.kb([[("⬅️ Panel", "ad:home")]]))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

PROMPTS = {
    "give":     ("🪙 <b>COİN VER</b>\n\n<code>kullanıcı_id miktar</code> yaz.\nÖrnek: <code>123456789 50000</code>", "admin_give", "money"),
    "gems":     ("💎 <b>ELMAS VER</b>\n\n<code>kullanıcı_id miktar</code>", "admin_gems", "money"),
    "money":    ("💵 <b>GERÇEK PARA EKLE</b>\n\n<code>kullanıcı_id miktar</code>\n"
                 "<i>Miktar TMT cinsinden, ondalık yazabilirsin: 2.5</i>", "admin_money", "money"),
    "ban":      ("🚫 <b>BAN</b>\n\nKullanıcı ID yaz.", "admin_ban", "ban"),
    "unban":    ("✅ <b>BAN KALDIR</b>\n\nKullanıcı ID yaz.", "admin_unban", "ban"),
    "find":     ("🔍 <b>OYUNCU ARA</b>\n\nID ya da @kullanıcıadı yaz.", "admin_find", "users"),
    "addadmin": ("➕ <b>YÖNETİCİ EKLE</b>\n\nKullanıcı ID yaz.\n"
                 "<i>Yönetici: ödeme onayı, para verme, ban, reklam, destek.</i>", "admin_addadmin", "all"),
    "addsup":   ("➕ <b>DESTEK EKLE</b>\n\nKullanıcı ID yaz.\n"
                 "<i>Destek: sadece destek kutusunu görür.</i>", "admin_addsup", "all"),
}


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_staff(user_id):
        await query.answer("Yetkin yok.", show_alert=True)
        return
    parts = query.data.split(":")
    action = parts[1]
    await query.answer()

    if action == "home":
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
        return
    if action == "stats":
        if not allowed(user_id, "stats"):
            return
        await ui.safe_edit(query, stats_text(), ui.kb([[("🔄", "ad:stats"), ("⬅️ Panel", "ad:home")]]))
        return

    if action in PROMPTS:
        text, kind, perm = PROMPTS[action]
        if perm != "all" and not allowed(user_id, perm):
            await query.answer("Bu işlem için yetkin yok.", show_alert=True)
            return
        if perm == "all" and role_of(user_id) != "owner":
            await query.answer("Sadece kurucu yapabilir.", show_alert=True)
            return
        context.user_data["await"] = {"kind": kind}
        await ui.safe_edit(query, text + "\n\nVazgeçmek için ⬅️", ui.kb([[("⬅️ Panel", "ad:home")]]))
        return

    # --- ödeme talepleri ---
    if action == "wds":
        if not allowed(user_id, "wds"):
            return
        await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
        return
    if action in ("pay", "rej"):
        if not allowed(user_id, "wds"):
            await query.answer("Yetkin yok.", show_alert=True)
            return
        req_id = int(parts[2])
        row = db.one("SELECT * FROM withdrawals WHERE id=?", (req_id,))
        if not row:
            await query.answer("Talep bulunamadı.", show_alert=True)
            return
        if row["state"] != "bekliyor":
            await query.answer(f"Bu talep zaten '{row['state']}'.", show_alert=True)
            await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
            return
        lang = i18n.lang_of(row["user_id"])
        if action == "pay":
            db.run("UPDATE withdrawals SET state='odendi', done_ts=?, note=? WHERE id=?",
                   (ui.now(), f"onay: {user_id}", req_id))
            db.bump(row["user_id"], tmt_paid=row["amount"])
            msg = i18n.t(lang, "m_paid", amount=cash.request_display(row), id=req_id)
            await query.answer(f"#{req_id} ödendi.")
        else:
            db.run("UPDATE withdrawals SET state='reddedildi', done_ts=?, note=? WHERE id=?",
                   (ui.now(), f"ret: {user_id}", req_id))
            db.bump(row["user_id"], tmt=row["amount"])
            msg = i18n.t(lang, "m_rejected", amount=cash.money(row["amount"]), id=req_id)
            await query.answer(f"#{req_id} reddedildi, para iade edildi.")
        db.log_action(user_id, f"wd_{action}", f"#{req_id} {row['user_id']}")
        try:
            await context.bot.send_message(row["user_id"], msg, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
        return

    # --- yetkililer ---
    if action == "staff":
        if role_of(user_id) != "owner":
            await query.answer("Sadece kurucu görebilir.", show_alert=True)
            return
        await ui.safe_edit(query, staff_text(), staff_kb())
        return
    if action == "delstaff":
        if role_of(user_id) != "owner":
            await query.answer("Sadece kurucu silebilir.", show_alert=True)
            return
        db.staff_remove(int(parts[2]))
        db.log_action(user_id, "staff_del", parts[2])
        await query.answer("Yetkili silindi.")
        await ui.safe_edit(query, staff_text(), staff_kb())
        return

    # --- oyuncu kartı işlemleri ---
    if action in ("ugive", "ugems", "umoney", "umsg"):
        target = int(parts[2])
        kinds = {"ugive": "admin_give", "ugems": "admin_gems",
                 "umoney": "admin_money", "umsg": "admin_msg"}
        context.user_data["await"] = {"kind": kinds[action], "target": target}
        labels = {"ugive": "🪙 Kaç coin verilsin?", "ugems": "💎 Kaç elmas?",
                  "umoney": "💵 Kaç TMT? (2.5 gibi yazabilirsin)",
                  "umsg": "💬 Gönderilecek mesajı yaz"}
        await ui.safe_edit(query, f"{labels[action]}\n\nOyuncu: <code>{target}</code>",
                           ui.kb([[("⬅️ Geri", f"ad:card:{target}")]]))
        return
    if action in ("uban", "uunban"):
        target = int(parts[2])
        if not allowed(user_id, "ban"):
            await query.answer("Yetkin yok.", show_alert=True)
            return
        if role_of(target) and action == "uban":
            await query.answer("Yetkiliyi banlayamazsın.", show_alert=True)
            return
        db.upd(target, banned=1 if action == "uban" else 0)
        db.log_action(user_id, action, str(target))
        await query.answer("Banlandı." if action == "uban" else "Ban kaldırıldı.")
        text, kb = user_card(target)
        await ui.safe_edit(query, text, kb)
        return
    if action == "card":
        text, kb = user_card(int(parts[2]))
        await ui.safe_edit(query, text, kb)
        return

    # --- reklam ---
    if action == "bc":
        if not allowed(user_id, "bc"):
            await query.answer("Yetkin yok.", show_alert=True)
            return
        context.user_data["await"] = {"kind": "admin_bc"}
        await ui.safe_edit(query, (
            f"📣 <b>REKLAM / DUYURU</b>\n{ui.LINE}\n"
            "<blockquote>Şimdi göndermek istediğin mesajı bana at.\n"
            "Yazı, fotoğraf, video, ses, GIF, dosya — hepsi olur.\n"
            "Fotoğrafın altına yazı da yazabilirsin.</blockquote>\n"
            "Attıktan sonra önizleme gelecek, onaylayınca gönderilecek.\n"
            "<i>Gönderim arka planda olur, bot çalışmaya devam eder.</i>"
        ), ui.kb([[("⬅️ Panel", "ad:home")]]))
        return
    if action == "bcgo":
        bid = int(parts[2])
        row = db.one("SELECT * FROM broadcasts WHERE id=?", (bid,))
        if not row or row["state"] != "bekliyor":
            await query.answer("Bu duyuru zaten gönderilmiş.", show_alert=True)
            return
        db.run("UPDATE broadcasts SET state='gonderiliyor' WHERE id=?", (bid,))
        total = int(db.scalar("SELECT COUNT(*) FROM users WHERE banned=0"))
        msg = await query.message.chat.send_message(
            f"📣 <b>Gönderiliyor...</b>\n{ui.LINE}\n✅ 0 / {total}", parse_mode=ParseMode.HTML)
        context.job_queue.run_once(broadcast_job, 1, data={"id": bid, "status_msg": msg.message_id})
        db.log_action(user_id, "broadcast", f"#{bid}")
        await ui.safe_edit(query, "📣 Gönderim başladı, arka planda devam ediyor. "
                                  "Botu kullanmaya devam edebilirsin.",
                           ui.kb([[("⬅️ Panel", "ad:home")]]))
        return
    if action == "bccancel":
        db.run("UPDATE broadcasts SET state='iptal' WHERE id=?", (int(parts[2]),))
        await ui.safe_edit(query, "🚫 Duyuru iptal edildi.", ui.kb([[("⬅️ Panel", "ad:home")]]))
        return

    # --- etkinlikler ---
    if action == "boss":
        if not allowed(user_id, "events"):
            return
        boss = events.spawn_boss()
        await ui.safe_edit(query, f"🐉 Canavar çıktı: <b>{ui.esc(boss['name'])}</b> "
                                  f"({ui.fmt(boss['hp'])} HP)", panel_kb(user_id))
        return
    if action == "lottery":
        if not allowed(user_id, "events"):
            return
        db.run("UPDATE lottery SET end_ts=? WHERE done=0", (ui.now() - 1,))
        await events.job_lottery(context)
        await ui.safe_edit(query, "🎟 Çekiliş yapıldı.", panel_kb(user_id))
        return

    # --- kayıtlar ---
    if action == "logs":
        rows = db.all_("SELECT * FROM actions ORDER BY id DESC LIMIT 20")
        lines = [f"📜 <b>SON HAREKETLER</b>\n{ui.LINE}"]
        for row in rows:
            who = db.get_user(row["user_id"])
            lines.append(f"• {ui.name_of(who) if who else row['user_id']} — "
                         f"<code>{ui.esc(row['what'])}</code> {ui.esc(row['detail'])}")
        if not rows:
            lines.append("Kayıt yok.")
        await ui.safe_edit(query, "\n".join(lines), ui.kb([[("🔄", "ad:logs"), ("⬅️ Panel", "ad:home")]]))
        return


# ---------------------------------------------------------------------------
# METİN / MEDYA GİRİŞLERİ
# ---------------------------------------------------------------------------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending or not str(pending.get("kind", "")).startswith("admin_"):
        return False
    user_id = update.effective_user.id
    if not is_staff(user_id):
        context.user_data.pop("await", None)
        return False
    kind = pending["kind"]
    msg = update.message
    text = (msg.text or msg.caption or "").strip()

    # --- reklam: her tür mesajı kabul et ---
    if kind == "admin_bc":
        context.user_data.pop("await", None)
        cur = db.run(
            "INSERT INTO broadcasts (admin_id, src_chat, src_msg, kind, text, created_ts) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, msg.chat_id, msg.message_id, _msg_kind(msg), text[:200], ui.now()))
        bid = int(cur.lastrowid)
        total = int(db.scalar("SELECT COUNT(*) FROM users WHERE banned=0"))
        await ui.send(update, (
            f"📣 <b>ÖNİZLEME HAZIR</b>\n{ui.LINE}\n"
            f"<blockquote>Tür: {_msg_kind(msg)}\n"
            f"Alıcı: <b>{ui.fmt(total)}</b> oyuncu\n"
            f"Tahmini süre: ~{max(1, total // 20 // 60)} dakika</blockquote>\n"
            "Yukarıdaki mesaj aynen gönderilecek. Onaylıyor musun?"
        ), ui.kb([
            [("✅ GÖNDER", f"ad:bcgo:{bid}")],
            [("🚫 Vazgeç", f"ad:bccancel:{bid}")],
        ]))
        return True

    context.user_data.pop("await", None)

    # --- oyuncuya mesaj ---
    if kind == "admin_msg":
        target = pending.get("target")
        try:
            await context.bot.copy_message(chat_id=target, from_chat_id=msg.chat_id,
                                           message_id=msg.message_id)
            await ui.send(update, "✅ Mesaj gönderildi.", ui.kb([[("⬅️ Panel", "ad:home")]]))
        except Exception as exc:
            await ui.send(update, f"❌ Gönderilemedi: {exc}", ui.kb([[("⬅️ Panel", "ad:home")]]))
        return True

    # --- oyuncu ara ---
    if kind == "admin_find":
        user = db.find_user_by_name(text)
        if not user:
            await ui.send(update, "Oyuncu bulunamadı.", ui.kb([[("🔍 Tekrar", "ad:find")]]))
            return True
        card, kb = user_card(user["user_id"])
        await ui.send(update, card, kb)
        return True

    # --- yetkili ekleme ---
    if kind in ("admin_addadmin", "admin_addsup"):
        if role_of(user_id) != "owner":
            return True
        if not text.isdigit():
            await ui.send(update, "Sadece sayısal ID yaz.", ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        target = int(text)
        if db.get_user(target) is None:
            await ui.send(update, "Bu kişi botu hiç kullanmamış. Önce /start yazmalı.",
                          ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        role = "admin" if kind == "admin_addadmin" else "support"
        db.staff_add(target, role, user_id)
        db.log_action(user_id, "staff_add", f"{target} {role}")
        await ui.send(update, f"✅ {ROLE_NAMES[role]} eklendi: <code>{target}</code>",
                      ui.kb([[("👮 Yetkililer", "ad:staff")]]))
        try:
            await context.bot.send_message(
                target, f"🎉 Sana <b>{ROLE_NAMES[role]}</b> yetkisi verildi!\n"
                        f"Paneli açmak için: /admin", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return True

    # --- ban ---
    if kind in ("admin_ban", "admin_unban"):
        if not text.isdigit():
            await ui.send(update, "Sadece ID yaz.", ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        target = int(text)
        if role_of(target) and kind == "admin_ban":
            await ui.send(update, "Yetkiliyi banlayamazsın.", ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        db.upd(target, banned=1 if kind == "admin_ban" else 0)
        db.log_action(user_id, kind, str(target))
        await ui.send(update, f"{'🚫 Banlandı' if kind == 'admin_ban' else '✅ Ban kaldırıldı'}: "
                              f"<code>{target}</code>", ui.kb([[("⬅️ Panel", "ad:home")]]))
        return True

    # --- para/coin/elmas verme ---
    if kind in ("admin_give", "admin_gems", "admin_money"):
        target = pending.get("target")
        amount_raw = text
        if target is None:
            parts = text.split()
            if len(parts) != 2 or not parts[0].isdigit():
                await ui.send(update, "Format: <code>kullanıcı_id miktar</code>",
                              ui.kb([[("⬅️ Panel", "ad:home")]]))
                return True
            target, amount_raw = int(parts[0]), parts[1]
        if db.get_user(target) is None:
            await ui.send(update, "Bu kullanıcı botta kayıtlı değil.",
                          ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        try:
            if kind == "admin_money":
                amount = int(round(float(amount_raw.replace(",", ".")) * 100))
            else:
                amount = int(amount_raw.replace(".", ""))
        except ValueError:
            await ui.send(update, "Miktar sayı olmalı.", ui.kb([[("⬅️ Panel", "ad:home")]]))
            return True
        if kind == "admin_give":
            economy.add_coins(target, amount, f"admin:{user_id}")
            note, notify = f"{ui.fmt(amount)} 🪙", f"🎁 Yönetici sana {ui.fmt(amount)} 🪙 gönderdi!"
        elif kind == "admin_gems":
            economy.add_gems(target, amount, f"admin:{user_id}")
            note, notify = f"{amount} 💎", f"🎁 Yönetici sana {amount} 💎 gönderdi!"
        else:
            db.bump(target, tmt=amount)
            note = cash.money(amount)
            notify = f"💵 Yönetici hesabına <b>{cash.money(amount)}</b> ekledi!"
        db.log_action(user_id, kind, f"{target} {note}")
        await ui.send(update, f"✅ {note} verildi → <code>{target}</code>",
                      ui.kb([[("👤 Oyuncu kartı", f"ad:card:{target}")], [("⬅️ Panel", "ad:home")]]))
        try:
            await context.bot.send_message(target, notify, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return True
    return False


def _msg_kind(msg) -> str:
    if msg.photo:
        return "fotoğraf"
    if msg.video:
        return "video"
    if msg.animation:
        return "gif"
    if msg.document:
        return "dosya"
    if msg.voice or msg.audio:
        return "ses"
    if msg.sticker:
        return "çıkartma"
    return "yazı"


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_staff(user_id):
        return
    await ui.send(update, panel_text(user_id), panel_kb(user_id))
