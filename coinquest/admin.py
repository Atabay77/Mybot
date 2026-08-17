# -*- coding: utf-8 -*-
"""Yönetim paneli — tamamen butonlarla çalışır, hiçbir yere ID/miktar yazılmaz.

Roller:
    owner   -> .env içindeki ADMIN_IDS. Her şeyi yapar, yetkili ekler/siler ve izin verir.
    admin   -> sadece kurucunun açtığı izinleri kullanır.
    support -> sadece destek kutusu (kurucu isterse başka izin de açabilir).
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

# Tek tek açılıp kapatılabilen izinler
PERMS = {
    "wds":     "💸 Ödeme onaylama",
    "money":   "🪙 Coin / 💎 elmas verme",
    "cash":    "💵 Gerçek para ekleme",
    "energy":  "⚡ Enerji verme",
    "ban":     "🚫 Ban atma",
    "bc":      "📣 Reklam gönderme",
    "support": "🎧 Destek kutusu",
    "users":   "🔍 Oyuncu listesi",
    "stats":   "📊 İstatistikler",
    "events":  "🐉 Canavar / çekiliş",
    "logs":    "📜 Kayıtlar",
}
DEFAULT_PERMS = {"admin": ["wds", "support", "users", "stats"], "support": ["support"]}
PAGE = 8


# ---------------------------------------------------------------------------
# YETKİ
# ---------------------------------------------------------------------------

def role_of(user_id: int) -> str:
    return db.staff_role(user_id)


def is_staff(user_id: int) -> bool:
    return bool(role_of(user_id))


def perms_of(user_id: int) -> list[str]:
    if role_of(user_id) == "owner":
        return list(PERMS)
    row = db.one("SELECT perms FROM staff WHERE user_id=?", (user_id,))
    if not row:
        return []
    raw = (row["perms"] or "").strip()
    if raw:
        return [p for p in raw.split(",") if p in PERMS]
    return DEFAULT_PERMS.get(role_of(user_id), [])


def allowed(user_id: int, what: str) -> bool:
    return what in perms_of(user_id)


def toggle_perm(target_id: int, key: str) -> bool:
    perms = perms_of(target_id)
    if key in perms:
        perms.remove(key)
    else:
        perms.append(key)
    db.run("UPDATE staff SET perms=? WHERE user_id=?", (",".join(perms), target_id))
    return key in perms


def guard(user_id: int, what: str) -> bool:
    return role_of(user_id) == "owner" or allowed(user_id, what)


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
        f"<blockquote>{ROLE_NAMES.get(role, role)}\n"
        f"👥 {ui.fmt(users)} oyuncu  •  bugün {ui.fmt(day)} aktif, {ui.fmt(new_day)} yeni</blockquote>\n"
        f"{'🔴' if wd_wait else '🟢'} Bekleyen ödeme: <b>{wd_wait}</b> ({cash.money(wd_sum)})\n"
        f"{'🔴' if tickets else '🟢'} Okunmamış destek: <b>{tickets}</b>"
    )


def panel_kb(user_id: int):
    rows = []
    if guard(user_id, "wds"):
        wait = int(db.scalar("SELECT COUNT(*) FROM withdrawals WHERE state='bekliyor'"))
        rows.append([(f"💸 Ödeme Talepleri{f'  ({wait})' if wait else ''}", "ad:wds")])
    if guard(user_id, "support"):
        unread = int(db.scalar("SELECT COUNT(*) FROM tickets WHERE state='acik' AND unread>0"))
        rows.append([(f"🎧 Destek Kutusu{f'  ({unread})' if unread else ''}", "sup:inbox")])
    if guard(user_id, "bc"):
        rows.append([("📣 Reklam Gönder", "ad:bc")])
    if guard(user_id, "users"):
        rows.append([("👥 Oyuncular", "ad:users:0")])
    if guard(user_id, "stats"):
        rows.append([("📊 İstatistik", "ad:stats")])
    if guard(user_id, "events"):
        rows.append([("🐉 Canavar Çıkar", "ad:boss"), ("🎟 Çekiliş", "ad:lottery")])
    if role_of(user_id) == "owner":
        rows.append([("👮 Yetkililer ve İzinler", "ad:staff")])
    if guard(user_id, "logs"):
        rows.append([("📜 Kayıtlar", "ad:logs")])
    rows.append([("🔄 Yenile", "ad:home"), ("🏠 Oyuna dön", "m:main")])
    return ui.kb(rows)


def stats_text() -> str:
    def n(sql, p=()):
        return int(db.scalar(sql, p))
    now = ui.now()
    boss = events.active_boss()
    return "\n".join([
        f"📊 <b>İSTATİSTİKLER</b>\n{ui.LINE}",
        "<blockquote><b>Oyuncular</b>\n"
        f"Toplam: {ui.fmt(n('SELECT COUNT(*) FROM users'))}\n"
        f"7 gün aktif: {ui.fmt(n('SELECT COUNT(*) FROM users WHERE last_seen>?', (now - 7 * 86400,)))}\n"
        f"Davetle gelen: {ui.fmt(n('SELECT COUNT(*) FROM users WHERE referrer<>0'))}\n"
        f"Banlı: {ui.fmt(n('SELECT COUNT(*) FROM users WHERE banned=1'))}</blockquote>",
        "<blockquote><b>Ekonomi</b>\n"
        f"Dolaşan coin: {ui.fmt(n('SELECT COALESCE(SUM(coins+bank),0) FROM users'))}\n"
        f"Elmas: {ui.fmt(n('SELECT COALESCE(SUM(gems),0) FROM users'))}\n"
        f"Oyuncularda bekleyen para: {cash.money(n('SELECT COALESCE(SUM(tmt),0) FROM users'))}\n"
        f"Ödenen toplam: {cash.money(n(chr(83) + 'ELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE state=' + chr(39) + 'odendi' + chr(39)))}"
        "</blockquote>",
        "<blockquote><b>Oyun</b>\n"
        f"Oynanan: {ui.fmt(n('SELECT COALESCE(SUM(games),0) FROM users'))}\n"
        f"Toplam bahis: {ui.fmt(n('SELECT COALESCE(SUM(wagered),0) FROM users'))}\n"
        f"Biten düello: {ui.fmt(n(chr(83) + 'ELECT COUNT(*) FROM duels WHERE state=' + chr(39) + 'done' + chr(39)))}\n"
        f"Grup: {ui.fmt(n('SELECT COUNT(*) FROM groups'))}  •  "
        f"Klan: {ui.fmt(n('SELECT COUNT(*) FROM clans'))}</blockquote>",
        f"🐉 Aktif canavar: {ui.esc(boss['name']) if boss else '—'}",
    ])


# ---------------------------------------------------------------------------
# OYUNCU LİSTESİ (yazmadan seçme)
# ---------------------------------------------------------------------------
LISTS = {
    "yeni": ("🆕 Son katılanlar", "ORDER BY created_ts DESC"),
    "aktif": ("🕒 Son görülenler", "ORDER BY last_seen DESC"),
    "zengin": ("💰 En zenginler", "ORDER BY coins+bank DESC"),
    "para": ("💵 Parası olanlar", "WHERE tmt>0 ORDER BY tmt DESC"),
    "banli": ("🚫 Banlılar", "WHERE banned=1 ORDER BY last_seen DESC"),
}


def users_text(kind: str, page: int) -> str:
    title, _ = LISTS.get(kind, LISTS["aktif"])
    total = int(db.scalar("SELECT COUNT(*) FROM users"))
    return (f"👥 <b>OYUNCULAR</b>\n{ui.LINE}\n"
            f"<blockquote>{title}  •  toplam {ui.fmt(total)} kayıt</blockquote>\n"
            f"Sayfa {page + 1} — birine basınca kartı açılır 👇")


def users_kb(kind: str, page: int):
    _title, order = LISTS.get(kind, LISTS["aktif"])
    rows_db = db.all_(f"SELECT user_id, first_name, level, coins, tmt FROM users {order} "
                      f"LIMIT {PAGE} OFFSET {page * PAGE}")
    rows = []
    for row in rows_db:
        tag = f" 💵{cash.money(row['tmt'])}" if row["tmt"] else ""
        rows.append([(f"{ui.name_of(row)} • Sv.{row['level']}{tag}", f"ad:card:{row['user_id']}")])
    nav = []
    if page > 0:
        nav.append(("⬅️", f"ad:users:{page - 1}:{kind}"))
    if len(rows_db) == PAGE:
        nav.append(("➡️", f"ad:users:{page + 1}:{kind}"))
    if nav:
        rows.append(nav)
    filt = [(label.split()[0] + " " + label.split()[1] if len(label.split()) > 1 else label,
             f"ad:users:0:{key}") for key, (label, _o) in LISTS.items()]
    rows.append(filt[:3])
    rows.append(filt[3:])
    rows.append([("⬅️ Geri", "ad:home"), ("🏠", "m:main")])
    return ui.kb([r for r in rows if r])


# ---------------------------------------------------------------------------
# OYUNCU KARTI
# ---------------------------------------------------------------------------

def user_card(target_id: int, viewer_id: int) -> tuple[str, object]:
    user = db.get_user(target_id)
    if not user:
        return "Oyuncu bulunamadı.", ui.kb([[("⬅️ Geri", "ad:users:0")]])
    role = role_of(target_id)
    txs = db.all_("SELECT delta, reason FROM tx WHERE user_id=? ORDER BY id DESC LIMIT 5", (target_id,))
    text = (
        f"👤 <b>{ui.name_of(user)}</b>" + (f"  {ROLE_NAMES.get(role, '')}" if role else "") + "\n"
        f"<code>{target_id}</code>" + (f"  @{ui.esc(user['username'])}" if user["username"] else "")
        + f"\n{ui.LINE}\n"
        f"<blockquote>🪙 {ui.fmt(user['coins'])}   🏦 {ui.fmt(user['bank'])}   💎 {user['gems']}\n"
        f"💵 {cash.money(user['tmt'])}  (ödenen {cash.money(user['tmt_paid'])})\n"
        f"🎚 Seviye {user['level']}   ⚡ {user['energy']}"
        + ("  <b>∞</b>" if user["energy_unlim"] else "") + "\n"
        f"📅 {cash.days_old(user)} günlük   🔥 {user['streak']} gün seri</blockquote>\n"
        f"🎮 {ui.fmt(user['games'])} oyun   ⚔️ {user['pvp_wins']}G/{user['pvp_losses']}Y\n"
        f"👥 Davet: {user['refs']}   🤖 Koruma: {'✅' if user['captcha_ok'] else '❌'}\n"
        f"🚫 Ban: {'<b>EVET</b>' if user['banned'] else 'hayır'}"
    )
    if txs:
        text += "\n\n<blockquote><b>Son hareketler</b>\n" + "\n".join(
            f"{t['delta']:+} {ui.esc(t['reason'])}" for t in txs) + "</blockquote>"

    rows = []
    if guard(viewer_id, "money"):
        rows.append([("🪙 Coin ver", f"ad:pick:coin:{target_id}"),
                     ("💎 Elmas ver", f"ad:pick:gem:{target_id}")])
    if guard(viewer_id, "cash"):
        rows.append([("💵 Gerçek para ekle", f"ad:pick:tmt:{target_id}")])
    if guard(viewer_id, "energy"):
        rows.append([("⚡ Enerji ver", f"ad:pick:energy:{target_id}")])
    if guard(viewer_id, "ban"):
        rows.append([("✅ Ban kaldır", f"ad:uunban:{target_id}") if user["banned"]
                     else ("🚫 Banla", f"ad:uban:{target_id}")])
    rows.append([("💬 Mesaj gönder", f"ad:umsg:{target_id}")])
    if role_of(viewer_id) == "owner":
        if role:
            rows.append([("👮 İzinleri düzenle", f"ad:perms:{target_id}"),
                         ("🗑 Yetkiyi al", f"ad:delstaff:{target_id}")])
        else:
            rows.append([("🛠 Yönetici yap", f"ad:mkstaff:{target_id}:admin"),
                         ("🎧 Destek yap", f"ad:mkstaff:{target_id}:support")])
    rows.append([("⬅️ Oyuncular", "ad:users:0"), ("🏠 Panel", "ad:home")])
    return text, ui.kb(rows)


# --- hazır miktar düğmeleri (hiç yazı yok) ---
AMOUNTS = {
    "coin":   ([1_000, 10_000, 100_000, 1_000_000, 10_000_000], "🪙", "coin"),
    "gem":    ([1, 5, 10, 50, 100], "💎", "elmas"),
    "tmt":    ([100, 500, 1_000, 5_000, 10_000], "💵", "gerçek para"),
    "energy": ([10, 50, 100], "⚡", "enerji"),
}


def amount_kb(kind: str, target_id: int):
    values, emoji, _n = AMOUNTS[kind]
    rows = []
    line = []
    for v in values:
        label = (cash.money(v) if kind == "tmt" else
                 f"+{ui.fmt(v)}" if kind != "energy" else f"+{v}")
        line.append((f"{emoji} {label}", f"ad:give:{kind}:{target_id}:{v}"))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    if kind == "coin":
        rows.append([("➖ 100.000 al", f"ad:give:coin:{target_id}:-100000"),
                     ("🧹 Sıfırla", f"ad:give:coin:{target_id}:zero")])
    if kind == "tmt":
        rows.append([("🧹 Sıfırla", f"ad:give:tmt:{target_id}:zero")])
    if kind == "energy":
        user = db.get_user(target_id)
        rows.append([("🔋 Tam doldur", f"ad:give:energy:{target_id}:full")])
        rows.append([("♾ Sınırsız enerji: " + ("AÇIK ✅" if user and user["energy_unlim"] else "kapalı"),
                      f"ad:give:energy:{target_id}:unlim")])
    rows.append([("⬅️ Geri", f"ad:card:{target_id}")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# YETKİLİLER VE İZİNLER
# ---------------------------------------------------------------------------

def staff_text() -> str:
    lines = [f"👮 <b>YETKİLİLER</b>\n{ui.LINE}",
             "<blockquote>Kurucular .env dosyasından gelir, buradan silinemez.\n"
             "Yetkililer sıralamalarda görünmez.</blockquote>"]
    for uid in config.ADMIN_IDS:
        user = db.get_user(uid)
        lines.append(f"👑 {ui.name_of(user) if user else uid}")
    rows = db.all_("SELECT * FROM staff ORDER BY role")
    if not rows:
        lines.append("\n<i>Başka yetkili yok. Oyuncular listesinden birine yetki verebilirsin.</i>")
    for row in rows:
        user = db.get_user(row["user_id"])
        perms = perms_of(row["user_id"])
        lines.append(f"\n{ROLE_NAMES.get(row['role'], row['role'])} "
                     f"<b>{ui.name_of(user) if user else row['user_id']}</b>\n"
                     f"<blockquote>{len(perms)} izin: "
                     + (", ".join(PERMS[p].split(" ", 1)[1] for p in perms) or "yok") + "</blockquote>")
    return "\n".join(lines)


def staff_kb():
    rows = [[("➕ Oyunculardan yetkili seç", "ad:users:0")]]
    for row in db.all_("SELECT * FROM staff ORDER BY role LIMIT 10"):
        user = db.get_user(row["user_id"])
        rows.append([(f"⚙️ {ui.name_of(user) if user else row['user_id']} izinleri",
                      f"ad:perms:{row['user_id']}")])
    rows.append([("⬅️ Geri", "ad:home"), ("🏠", "m:main")])
    return ui.kb(rows)


def perms_text(target_id: int) -> str:
    user = db.get_user(target_id)
    role = role_of(target_id)
    active = perms_of(target_id)
    lines = [f"⚙️ <b>İZİNLER</b>\n{ui.LINE}",
             f"👤 <b>{ui.name_of(user)}</b>  {ROLE_NAMES.get(role, '')}",
             "<blockquote>Her düğmeye basınca o izin açılır/kapanır.\n"
             "✅ = kullanabilir   ❌ = kullanamaz</blockquote>"]
    lines.append(f"\nAçık izin: <b>{len(active)}</b> / {len(PERMS)}")
    return "\n".join(lines)


def perms_kb(target_id: int):
    active = perms_of(target_id)
    rows = [[(f"{'✅' if key in active else '❌'} {label}", f"ad:perm:{target_id}:{key}")]
            for key, label in PERMS.items()]
    rows.append([("✅ Hepsini aç", f"ad:permall:{target_id}:1"),
                 ("❌ Hepsini kapat", f"ad:permall:{target_id}:0")])
    rows.append([("👤 Oyuncu kartı", f"ad:card:{target_id}"), ("⬅️ Geri", "ad:staff")])
    return ui.kb(rows)


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
        lines.append(
            f"\n<b>#{row['id']}</b> — {cash.request_display(row)}\n"
            f"<blockquote>👤 {ui.name_of(user)} <code>{row['user_id']}</code>\n"
            f"🎚 Sv.{user['level'] if user else '?'} • {cash.days_old(user) if user else 0} günlük\n"
            f"{cash.method_name(row['method'], 'tr')}\n"
            f"<code>{ui.esc(row['details'])}</code></blockquote>")
    return "\n".join(lines)


def withdrawals_kb():
    rows_db = db.all_("SELECT * FROM withdrawals WHERE state='bekliyor' ORDER BY id LIMIT 10")
    rows = [[(f"✅ #{r['id']} ödedim", f"ad:pay:{r['id']}"), ("❌ Reddet", f"ad:rej:{r['id']}")]
            for r in rows_db]
    rows.append([("🔄 Yenile", "ad:wds"), ("⬅️ Geri", "ad:home")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# REKLAM (arka planda)
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
                        f"✅ {sent} / {len(targets)}   ❌ {failed}\n{ui.bar(i, len(targets), 12)}",
                        chat_id=row["admin_id"], message_id=status_msg, parse_mode=ParseMode.HTML)
                except Exception:
                    pass
        await asyncio.sleep(0.045)
    db.run("UPDATE broadcasts SET sent=?, failed=?, state='bitti' WHERE id=?", (sent, failed, bid))
    try:
        await context.bot.send_message(
            row["admin_id"],
            f"📣 <b>REKLAM BİTTİ</b>\n{ui.LINE}\n✅ Ulaşan: <b>{sent}</b>\n"
            f"❌ Ulaşmayan: {failed}  <i>(botu engelleyenler)</i>",
            parse_mode=ParseMode.HTML, reply_markup=ui.kb([[("⬅️ Panel", "ad:home")]]))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_staff(user_id):
        await query.answer("⛔ Bu bölüm sadece yöneticilere açık.", show_alert=True)
        return
    parts = query.data.split(":")
    action = parts[1]

    async def deny(what: str) -> bool:
        if guard(user_id, what):
            return False
        await query.answer(f"⛔ Bu işlem için iznin yok.\n\nGereken izin: {PERMS.get(what, what)}\n"
                           f"Kurucudan isteyebilirsin.", show_alert=True)
        return True

    if action == "home":
        await query.answer("🛠 Panel")
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
        return

    if action == "stats":
        if await deny("stats"):
            return
        await query.answer("📊 İstatistikler")
        await ui.safe_edit(query, stats_text(),
                           ui.kb([[("🔄 Yenile", "ad:stats")], [("⬅️ Geri", "ad:home")]]))
        return

    # --- oyuncu listesi ---
    if action == "users":
        if await deny("users"):
            return
        page = int(parts[2]) if len(parts) > 2 else 0
        kind = parts[3] if len(parts) > 3 else "aktif"
        await query.answer("👥 Oyuncular")
        await ui.safe_edit(query, users_text(kind, page), users_kb(kind, page))
        return
    if action == "card":
        target = int(parts[2])
        text, kb = user_card(target, user_id)
        await query.answer()
        await ui.safe_edit(query, text, kb)
        return

    # --- miktar seçimi ---
    if action == "pick":
        kind, target = parts[2], int(parts[3])
        need = {"coin": "money", "gem": "money", "tmt": "cash", "energy": "energy"}[kind]
        if await deny(need):
            return
        user = db.get_user(target)
        _v, emoji, name = AMOUNTS[kind]
        await query.answer()
        await ui.safe_edit(query, (
            f"{emoji} <b>{name.upper()} VER</b>\n{ui.LINE}\n"
            f"👤 {ui.name_of(user)}\n"
            f"<blockquote>Şu an: 🪙 {ui.fmt(user['coins'])}  •  💎 {user['gems']}\n"
            f"💵 {cash.money(user['tmt'])}  •  ⚡ {user['energy']}"
            + ("  ♾" if user["energy_unlim"] else "") + "</blockquote>\n"
            "Miktarı seç 👇"
        ), amount_kb(kind, target))
        return

    if action == "give":
        kind, target, value = parts[2], int(parts[3]), parts[4]
        need = {"coin": "money", "gem": "money", "tmt": "cash", "energy": "energy"}[kind]
        if await deny(need):
            return
        user = db.get_user(target)
        if not user:
            await query.answer("Oyuncu yok.", show_alert=True)
            return
        notify = None
        if kind == "coin":
            if value == "zero":
                db.upd(target, coins=0)
                note = "🪙 coin sıfırlandı"
            else:
                economy.add_coins(target, int(value), f"admin:{user_id}")
                note = f"🪙 {ui.fmt(int(value))}"
                notify = f"🎁 Yönetici sana <b>{ui.fmt(int(value))}</b> 🪙 gönderdi!"
        elif kind == "gem":
            economy.add_gems(target, int(value), f"admin:{user_id}")
            note = f"💎 {value}"
            notify = f"🎁 Yönetici sana <b>{value}</b> 💎 gönderdi!"
        elif kind == "tmt":
            if value == "zero":
                db.upd(target, tmt=0)
                note = "💵 para sıfırlandı"
            else:
                db.bump(target, tmt=int(value))
                note = f"💵 {cash.money(int(value))}"
                notify = f"💵 Yönetici hesabına <b>{cash.money(int(value))}</b> ekledi!"
        else:
            if value == "full":
                db.upd(target, energy=economy.max_energy(user["level"]), energy_ts=ui.now())
                note = "⚡ enerji doldu"
                notify = "⚡ Enerjin yönetici tarafından dolduruldu!"
            elif value == "unlim":
                new = 0 if user["energy_unlim"] else 1
                db.upd(target, energy_unlim=new)
                note = "♾ sınırsız enerji " + ("açıldı" if new else "kapatıldı")
                notify = ("♾ Artık <b>sınırsız enerjin</b> var!" if new
                          else "⚡ Sınırsız enerjin kapatıldı.")
            else:
                economy.add_energy(target, int(value))
                note = f"⚡ +{value}"
                notify = f"⚡ Yönetici sana <b>+{value}</b> enerji verdi!"
        db.log_action(user_id, f"ver_{kind}", f"{target} {note}")
        await query.answer(f"✅ {note} → {ui.name_of(user)}", show_alert=True)
        if notify:
            try:
                await context.bot.send_message(
                    target, notify, parse_mode=ParseMode.HTML,
                    reply_markup=ui.kb([[(i18n.t(i18n.lang_of(target), "b_home"), "m:main")]]))
            except Exception:
                pass
        text, kb = user_card(target, user_id)
        await ui.safe_edit(query, text, kb)
        return

    # --- ban ---
    if action in ("uban", "uunban"):
        if await deny("ban"):
            return
        target = int(parts[2])
        if role_of(target) and action == "uban":
            await query.answer("⛔ Yetkili banlanamaz.", show_alert=True)
            return
        db.upd(target, banned=1 if action == "uban" else 0)
        db.log_action(user_id, action, str(target))
        await query.answer("🚫 Banlandı." if action == "uban" else "✅ Ban kaldırıldı.",
                           show_alert=True)
        text, kb = user_card(target, user_id)
        await ui.safe_edit(query, text, kb)
        return

    # --- ödeme ---
    if action == "wds":
        if await deny("wds"):
            return
        await query.answer("💸 Ödeme talepleri")
        await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
        return
    if action in ("pay", "rej"):
        if await deny("wds"):
            return
        req_id = int(parts[2])
        row = db.one("SELECT * FROM withdrawals WHERE id=?", (req_id,))
        if not row:
            await query.answer("Talep bulunamadı.", show_alert=True)
            return
        if row["state"] != "bekliyor":
            await query.answer(f"⚠️ Bu talep zaten '{row['state']}'.", show_alert=True)
            await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
            return
        lang = i18n.lang_of(row["user_id"])
        if action == "pay":
            db.run("UPDATE withdrawals SET state='odendi', done_ts=?, note=? WHERE id=?",
                   (ui.now(), f"onay:{user_id}", req_id))
            db.bump(row["user_id"], tmt_paid=row["amount"])
            msg = i18n.t(lang, "m_paid", amount=cash.request_display(row), id=req_id)
            await query.answer(f"✅ #{req_id} ödendi olarak işaretlendi.", show_alert=True)
        else:
            db.run("UPDATE withdrawals SET state='reddedildi', done_ts=?, note=? WHERE id=?",
                   (ui.now(), f"ret:{user_id}", req_id))
            db.bump(row["user_id"], tmt=row["amount"])
            msg = i18n.t(lang, "m_rejected", amount=cash.money(row["amount"]), id=req_id)
            await query.answer(f"❌ #{req_id} reddedildi, para iade edildi.", show_alert=True)
        db.log_action(user_id, f"wd_{action}", f"#{req_id}")
        try:
            await context.bot.send_message(
                row["user_id"], msg, parse_mode=ParseMode.HTML,
                reply_markup=ui.kb([[(i18n.t(lang, "sup_write"), "sup:write")],
                                    [(i18n.t(lang, "b_home"), "m:main")]]))
        except Exception:
            pass
        await ui.safe_edit(query, withdrawals_text(), withdrawals_kb())
        return

    # --- yetkililer ---
    if action == "staff":
        if role_of(user_id) != "owner":
            await query.answer("⛔ Sadece kurucu görebilir.", show_alert=True)
            return
        await query.answer("👮 Yetkililer")
        await ui.safe_edit(query, staff_text(), staff_kb())
        return
    if action == "mkstaff":
        if role_of(user_id) != "owner":
            await query.answer("⛔ Sadece kurucu yetki verebilir.", show_alert=True)
            return
        target, role = int(parts[2]), parts[3]
        db.staff_add(target, role, user_id)
        db.run("UPDATE staff SET perms=? WHERE user_id=?",
               (",".join(DEFAULT_PERMS.get(role, [])), target))
        db.log_action(user_id, "staff_add", f"{target} {role}")
        await query.answer(f"✅ {ROLE_NAMES[role]} yapıldı.", show_alert=True)
        try:
            await context.bot.send_message(
                target, f"🎉 Sana <b>{ROLE_NAMES[role]}</b> yetkisi verildi!",
                parse_mode=ParseMode.HTML,
                reply_markup=ui.kb([[("🛠 Paneli aç", "ad:home")]]))
        except Exception:
            pass
        await ui.safe_edit(query, perms_text(target), perms_kb(target))
        return
    if action == "delstaff":
        if role_of(user_id) != "owner":
            await query.answer("⛔ Sadece kurucu silebilir.", show_alert=True)
            return
        target = int(parts[2])
        db.staff_remove(target)
        db.log_action(user_id, "staff_del", str(target))
        await query.answer("🗑 Yetki alındı.", show_alert=True)
        await ui.safe_edit(query, staff_text(), staff_kb())
        return
    if action == "perms":
        if role_of(user_id) != "owner":
            await query.answer("⛔ Sadece kurucu izin verebilir.", show_alert=True)
            return
        target = int(parts[2])
        await query.answer("⚙️ İzinler")
        await ui.safe_edit(query, perms_text(target), perms_kb(target))
        return
    if action == "perm":
        if role_of(user_id) != "owner":
            await query.answer("⛔ Sadece kurucu izin verebilir.", show_alert=True)
            return
        target, key = int(parts[2]), parts[3]
        now_on = toggle_perm(target, key)
        db.log_action(user_id, "perm", f"{target} {key}={int(now_on)}")
        await query.answer(f"{'✅ açıldı' if now_on else '❌ kapatıldı'}: {PERMS[key]}")
        await ui.safe_edit(query, perms_text(target), perms_kb(target))
        return
    if action == "permall":
        if role_of(user_id) != "owner":
            return
        target, on = int(parts[2]), parts[3] == "1"
        db.run("UPDATE staff SET perms=? WHERE user_id=?",
               (",".join(PERMS) if on else "-", target))
        await query.answer("✅ Hepsi açıldı." if on else "❌ Hepsi kapatıldı.", show_alert=True)
        await ui.safe_edit(query, perms_text(target), perms_kb(target))
        return

    # --- reklam ---
    if action == "bc":
        if await deny("bc"):
            return
        context.user_data["await"] = {"kind": "admin_bc"}
        await query.answer("📣 Mesajını gönder")
        await ui.safe_edit(query, (
            f"📣 <b>REKLAM / DUYURU</b>\n{ui.LINE}\n"
            "<blockquote>Göndermek istediğin mesajı şimdi bana at.\n"
            "Yazı, fotoğraf, video, ses, GIF, dosya — hepsi olur.</blockquote>\n"
            "Attıktan sonra önizleme gelecek, onaylayınca gönderilecek.\n"
            "<i>Gönderim arka planda olur, bot çalışmaya devam eder.</i>"
        ), ui.kb([[("⬅️ Vazgeç", "ad:home")]]))
        return
    if action == "bcgo":
        if await deny("bc"):
            return
        bid = int(parts[2])
        row = db.one("SELECT * FROM broadcasts WHERE id=?", (bid,))
        if not row or row["state"] != "bekliyor":
            await query.answer("⚠️ Bu duyuru zaten gönderilmiş.", show_alert=True)
            return
        db.run("UPDATE broadcasts SET state='gonderiliyor' WHERE id=?", (bid,))
        total = int(db.scalar("SELECT COUNT(*) FROM users WHERE banned=0"))
        msg = await query.message.chat.send_message(
            f"📣 <b>Gönderiliyor...</b>\n{ui.LINE}\n✅ 0 / {total}", parse_mode=ParseMode.HTML)
        context.job_queue.run_once(broadcast_job, 1, data={"id": bid, "status_msg": msg.message_id})
        db.log_action(user_id, "broadcast", f"#{bid}")
        await query.answer("📣 Gönderim başladı!", show_alert=True)
        await ui.safe_edit(query, "📣 Arka planda gönderiliyor. Botu kullanmaya devam edebilirsin.",
                           ui.kb([[("⬅️ Panel", "ad:home")]]))
        return
    if action == "bccancel":
        db.run("UPDATE broadcasts SET state='iptal' WHERE id=?", (int(parts[2]),))
        await query.answer("🚫 İptal edildi.")
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
        return

    # --- oyuncuya mesaj ---
    if action == "umsg":
        target = int(parts[2])
        context.user_data["await"] = {"kind": "admin_msg", "target": target}
        user = db.get_user(target)
        await query.answer("💬 Mesajını yaz")
        await ui.safe_edit(query, (
            f"💬 <b>MESAJ GÖNDER</b>\n{ui.LINE}\n"
            f"👤 {ui.name_of(user)}\n"
            "<blockquote>Göndermek istediğin mesajı şimdi yaz.\n"
            "Fotoğraf, video da olur.\n"
            "Oyuncuya mesajın altında <b>✍️ Cevapla</b> düğmesi çıkar.</blockquote>"
        ), ui.kb([[("⬅️ Vazgeç", f"ad:card:{target}")]]))
        return

    # --- etkinlikler ---
    if action == "boss":
        if await deny("events"):
            return
        boss = events.spawn_boss()
        await query.answer(f"🐉 {boss['name']} çıktı!", show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
        return
    if action == "lottery":
        if await deny("events"):
            return
        db.run("UPDATE lottery SET end_ts=? WHERE done=0", (ui.now() - 1,))
        await events.job_lottery(context)
        await query.answer("🎟 Çekiliş yapıldı!", show_alert=True)
        await ui.safe_edit(query, panel_text(user_id), panel_kb(user_id))
        return

    # --- kayıtlar ---
    if action == "logs":
        if await deny("logs"):
            return
        rows = db.all_("SELECT * FROM actions ORDER BY id DESC LIMIT 20")
        lines = [f"📜 <b>KAYITLAR</b>\n{ui.LINE}"]
        for row in rows:
            who = db.get_user(row["user_id"])
            lines.append(f"• <b>{ui.name_of(who) if who else row['user_id']}</b> — "
                         f"{ui.esc(row['what'])} {ui.esc(row['detail'])}")
        if not rows:
            lines.append("Henüz kayıt yok.")
        await query.answer("📜 Kayıtlar")
        await ui.safe_edit(query, "\n".join(lines),
                           ui.kb([[("🔄 Yenile", "ad:logs")], [("⬅️ Geri", "ad:home")]]))
        return

    await query.answer("Bu düğme artık kullanılmıyor.", show_alert=True)


# ---------------------------------------------------------------------------
# MEDYA GİRİŞLERİ (sadece reklam ve oyuncuya mesaj)
# ---------------------------------------------------------------------------

def _msg_kind(msg) -> str:
    for attr, name in (("photo", "fotoğraf"), ("video", "video"), ("animation", "gif"),
                       ("document", "dosya"), ("voice", "ses"), ("audio", "ses"),
                       ("sticker", "çıkartma")):
        if getattr(msg, attr, None):
            return name
    return "yazı"


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending or pending.get("kind") not in ("admin_bc", "admin_msg"):
        return False
    user_id = update.effective_user.id
    if not is_staff(user_id):
        context.user_data.pop("await", None)
        return False
    msg = update.message
    kind = pending["kind"]
    context.user_data.pop("await", None)

    if kind == "admin_bc":
        cur = db.run(
            "INSERT INTO broadcasts (admin_id, src_chat, src_msg, kind, text, created_ts) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, msg.chat_id, msg.message_id, _msg_kind(msg),
             (msg.text or msg.caption or "")[:200], ui.now()))
        bid = int(cur.lastrowid)
        total = int(db.scalar("SELECT COUNT(*) FROM users WHERE banned=0"))
        await ui.send(update, (
            f"📣 <b>ÖNİZLEME</b>\n{ui.LINE}\n"
            f"<blockquote>Tür: {_msg_kind(msg)}\n"
            f"Alıcı: <b>{ui.fmt(total)}</b> oyuncu\n"
            f"Süre: ~{max(1, total // 20 // 60)} dakika</blockquote>\n"
            "Yukarıdaki mesaj aynen gönderilecek. Onaylıyor musun?"
        ), ui.kb([[("✅ GÖNDER", f"ad:bcgo:{bid}")], [("🚫 Vazgeç", f"ad:bccancel:{bid}")]]))
        return True

    target = pending.get("target")
    lang = i18n.lang_of(target)
    try:
        await context.bot.send_message(
            target, "📩 <b>Yöneticiden mesaj:</b>", parse_mode=ParseMode.HTML)
        await context.bot.copy_message(
            chat_id=target, from_chat_id=msg.chat_id, message_id=msg.message_id,
            reply_markup=ui.kb([[(i18n.t(lang, "sup_write"), "sup:write")],
                                [(i18n.t(lang, "b_home"), "m:main")]]))
        db.log_action(user_id, "mesaj", str(target))
        await ui.send(update, "✅ Mesaj gönderildi. Oyuncu <b>✍️ Cevapla</b> ile yanıtlayabilir.",
                      ui.kb([[("👤 Oyuncu kartı", f"ad:card:{target}")], [("⬅️ Panel", "ad:home")]]))
    except Exception as exc:
        await ui.send(update, f"❌ Gönderilemedi: {exc}", ui.kb([[("⬅️ Panel", "ad:home")]]))
    return True


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gizli komut — panele asıl giriş ana menüdeki 🛠 düğmesidir."""
    user_id = update.effective_user.id
    if not is_staff(user_id):
        return
    await ui.send(update, panel_text(user_id), panel_kb(user_id))
