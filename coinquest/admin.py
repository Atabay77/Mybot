# -*- coding: utf-8 -*-
"""Yönetici paneli: istatistik, para/elmas verme, ban, duyuru, boss/piyango tetikleme."""
import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import db
import economy
import events
import ui

log = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def stats_text() -> str:
    now = ui.now()
    total = int(db.scalar("SELECT COUNT(*) FROM users"))
    day = int(db.scalar("SELECT COUNT(*) FROM users WHERE last_seen > ?", (now - 86400,)))
    week = int(db.scalar("SELECT COUNT(*) FROM users WHERE last_seen > ?", (now - 7 * 86400,)))
    new_day = int(db.scalar("SELECT COUNT(*) FROM users WHERE created_ts > ?", (now - 86400,)))
    coins = int(db.scalar("SELECT COALESCE(SUM(coins+bank),0) FROM users"))
    gems = int(db.scalar("SELECT COALESCE(SUM(gems),0) FROM users"))
    plays = int(db.scalar("SELECT COALESCE(SUM(games),0) FROM users"))
    wagered = int(db.scalar("SELECT COALESCE(SUM(wagered),0) FROM users"))
    clans = int(db.scalar("SELECT COUNT(*) FROM clans"))
    groups = int(db.scalar("SELECT COUNT(*) FROM groups"))
    duels = int(db.scalar("SELECT COUNT(*) FROM duels WHERE state='done'"))
    listings = int(db.scalar("SELECT COUNT(*) FROM bazaar WHERE sold_to=0"))
    banned = int(db.scalar("SELECT COUNT(*) FROM users WHERE banned=1"))
    boss = events.active_boss()
    return (
        "🛠 <b>YÖNETİCİ PANELİ</b>\n\n"
        f"👥 Oyuncu: <b>{ui.fmt(total)}</b>  (24s aktif: {ui.fmt(day)}, 7g: {ui.fmt(week)})\n"
        f"🆕 Bugün katılan: {ui.fmt(new_day)}\n"
        f"💬 Grup: {ui.fmt(groups)}  •  🏰 Klan: {ui.fmt(clans)}\n\n"
        f"🪙 Dolaşımdaki altın: <b>{ui.fmt(coins)}</b>\n"
        f"💎 Toplam elmas: {ui.fmt(gems)}\n"
        f"🎮 Oynanan oyun: {ui.fmt(plays)}  •  Toplam bahis: {ui.fmt(wagered)}\n"
        f"⚔️ Tamamlanan düello: {ui.fmt(duels)}\n"
        f"🛒 Açık pazar ilanı: {ui.fmt(listings)}\n"
        f"🚫 Banlı: {ui.fmt(banned)}\n"
        f"🐉 Aktif boss: {ui.esc(boss['name']) if boss else 'yok'}"
    )


def panel_kb():
    return ui.kb([
        [("📊 İstatistik", "ad:stats")],
        [("🪙 Altın Ver", "ad:give"), ("💎 Elmas Ver", "ad:gems")],
        [("🚫 Ban", "ad:ban"), ("✅ Ban Kaldır", "ad:unban")],
        [("📣 Duyuru", "ad:bc")],
        [("🐉 Boss Doğur", "ad:boss"), ("🎟 Piyango Çek", "ad:lottery")],
        [("👤 Oyuncu Sorgula", "ad:query")],
    ])


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await ui.send(update, stats_text(), panel_kb())


PROMPTS = {
    "give": ("🪙 <b>ALTIN VER</b>\n\n<code>kullanıcı_id miktar</code> şeklinde yaz.\n"
             "Örnek: <code>123456789 50000</code>", "admin_give"),
    "gems": ("💎 <b>ELMAS VER</b>\n\n<code>kullanıcı_id miktar</code>", "admin_gems"),
    "ban": ("🚫 <b>BAN</b>\n\nKullanıcı ID yaz.", "admin_ban"),
    "unban": ("✅ <b>BAN KALDIR</b>\n\nKullanıcı ID yaz.", "admin_unban"),
    "bc": ("📣 <b>DUYURU</b>\n\nGönderilecek mesajı yaz. Tüm oyunculara iletilir.", "admin_bc"),
    "query": ("👤 <b>OYUNCU SORGULA</b>\n\nKullanıcı ID veya @kullanıcıadı yaz.", "admin_query"),
}


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.answer("Yetkin yok.", show_alert=True)
        return
    await query.answer()
    action = query.data.split(":")[1]

    if action == "stats":
        await ui.safe_edit(query, stats_text(), panel_kb())
    elif action in PROMPTS:
        text, kind = PROMPTS[action]
        context.user_data["await"] = {"kind": kind}
        await ui.safe_edit(query, text + "\n\nİptal: /iptal", ui.back_kb("ad:stats"))
    elif action == "boss":
        boss = events.spawn_boss()
        await ui.safe_edit(query, f"🐉 Boss doğdu: <b>{ui.esc(boss['name'])}</b> "
                                  f"({ui.fmt(boss['hp'])} HP)", panel_kb())
    elif action == "lottery":
        db.run("UPDATE lottery SET end_ts=? WHERE done=0", (ui.now() - 1,))
        await events.job_lottery(context)
        await ui.safe_edit(query, "🎟 Piyango çekilişi yapıldı.", panel_kb())


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get("await")
    if not pending or not str(pending.get("kind", "")).startswith("admin_"):
        return False
    if not is_admin(update.effective_user.id):
        context.user_data.pop("await", None)
        return False
    kind = pending["kind"]
    text = (update.message.text or "").strip()
    context.user_data.pop("await", None)

    if kind in ("admin_give", "admin_gems"):
        parts = text.split()
        if len(parts) != 2 or not parts[0].isdigit():
            await ui.send(update, "Format: <code>kullanıcı_id miktar</code>")
            return True
        target = int(parts[0])
        try:
            amount = int(parts[1].replace(".", ""))
        except ValueError:
            await ui.send(update, "Miktar sayı olmalı.")
            return True
        if db.get_user(target) is None:
            await ui.send(update, "Bu kullanıcı botta kayıtlı değil.")
            return True
        if kind == "admin_give":
            economy.add_coins(target, amount, "admin")
            await ui.send(update, f"✅ {ui.fmt(amount)} 🪙 verildi → <code>{target}</code>", panel_kb())
            try:
                await context.bot.send_message(target, f"🎁 Yönetici sana {ui.fmt(amount)} 🪙 gönderdi!",
                                               parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            economy.add_gems(target, amount, "admin")
            await ui.send(update, f"✅ {amount} 💎 verildi → <code>{target}</code>", panel_kb())
        return True

    if kind in ("admin_ban", "admin_unban"):
        if not text.isdigit():
            await ui.send(update, "Sadece kullanıcı ID yaz.")
            return True
        target = int(text)
        db.upd(target, banned=1 if kind == "admin_ban" else 0)
        await ui.send(update, f"{'🚫 Banlandı' if kind == 'admin_ban' else '✅ Ban kaldırıldı'}: "
                              f"<code>{target}</code>", panel_kb())
        return True

    if kind == "admin_query":
        user = db.find_user_by_name(text)
        if not user:
            await ui.send(update, "Oyuncu bulunamadı.")
            return True
        txs = db.all_("SELECT delta, reason, ts FROM tx WHERE user_id=? ORDER BY id DESC LIMIT 8",
                      (user["user_id"],))
        lines = [
            f"👤 <b>{ui.name_of(user)}</b>  <code>{user['user_id']}</code>",
            f"@{ui.esc(user['username']) if user['username'] else '—'}",
            f"🪙 {ui.fmt(user['coins'])} + 🏦 {ui.fmt(user['bank'])} • 💎 {user['gems']}",
            f"🎚 Sv.{user['level']} • 🎮 {user['games']} oyun • ⚔️ {user['pvp_wins']}G/{user['pvp_losses']}Y",
            f"💰 Toplam kazanç: {ui.fmt(user['earned'])} • bahis: {ui.fmt(user['wagered'])}",
            f"🚫 Banlı: {'evet' if user['banned'] else 'hayır'}",
            "\n<b>Son hareketler</b>",
        ]
        for tx in txs:
            lines.append(f"{tx['delta']:+} — {ui.esc(tx['reason'])}")
        await ui.send(update, "\n".join(lines), panel_kb())
        return True

    if kind == "admin_bc":
        rows = db.all_("SELECT user_id FROM users WHERE banned=0")
        sent = failed = 0
        status = await ui.send(update, f"📣 Duyuru gönderiliyor... 0/{len(rows)}")
        for i, row in enumerate(rows, 1):
            try:
                await context.bot.send_message(row["user_id"], text, parse_mode=ParseMode.HTML)
                sent += 1
            except Exception:
                failed += 1
            if i % 25 == 0:
                try:
                    await status.edit_text(f"📣 Gönderiliyor... {i}/{len(rows)}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)
        await ui.send(update, f"📣 Duyuru bitti.\n✅ {sent} kişi  ❌ {failed} hata", panel_kb())
        return True
    return False
