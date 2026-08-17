# -*- coding: utf-8 -*-
"""CoinQuest — Telegram oyun & ekonomi botu.  Çalıştırma:  python3 bot.py"""
import logging
import sys
import traceback

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, ApplicationHandlerStop, CallbackQueryHandler,
    CommandHandler, ContextTypes, MessageHandler, TypeHandler, filters,
)

import admin
import cash
import config
import db
import economy
import events
import games
import items
import market
import party
import pvp
import social
import ui

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("coinquest")


# ---------------------------------------------------------------------------
# GİRİŞ / ANA MENÜ
# ---------------------------------------------------------------------------

def main_menu_text(user) -> str:
    boss = events.active_boss()
    boss_line = ""
    if boss:
        boss_line = (f"\n🐉 <b>{ui.esc(boss['name'])}</b> saldırıda! "
                     f"({ui.fmt(boss['hp'])} HP kaldı) → /boss\n")
    ready = sum(1 for q in events.daily_quests(user["user_id"])
                if not q["claimed"] and q["progress"] >= q["target"])
    quest_line = f"\n🎁 <b>{ready} görevin bitti, ödülünü al!</b>\n" if ready else ""
    return (
        f"🏰 <b>COINQUEST</b>\n"
        f"Merhaba <b>{ui.name_of(user)}</b> 👋\n\n"
        f"{ui.header(user)}\n"
        f"💵 Gerçek para: <b>{cash.money(user['tmt'])}</b>\n"
        f"{boss_line}{quest_line}\n"
        "Ne yapmak istersin? 👇"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    args = context.args or []
    referrer = 0
    if args and args[0].startswith("ref"):
        raw = args[0][3:]
        if raw.isdigit():
            referrer = int(raw)

    existed = db.get_user(tg_user.id) is not None
    user = db.ensure_user(tg_user, referrer)
    if not existed:
        db.upd(tg_user.id, title=economy.title_for(1))
        if referrer and referrer != tg_user.id and db.get_user(referrer):
            social.grant_referral(tg_user.id, referrer)
            try:
                await context.bot.send_message(
                    referrer,
                    f"👥 <b>{ui.name_of(db.get_user(tg_user.id))}</b> davetinle katıldı!\n"
                    f"+10.000 🪙 ve +2 💎 kazandın.",
                    parse_mode=ParseMode.HTML)
            except Exception:
                pass
        user = db.get_user(tg_user.id)
        welcome = (
            "🏰 <b>HOŞ GELDİN!</b>\n\n"
            f"Sana hediye: <b>{ui.fmt(config.START_COINS)}</b> 🪙 coin ve "
            f"<b>{config.START_GEMS}</b> 💎 elmas.\n\n"
            "<b>Burada ne yapılır?</b>\n"
            "🎮 Oyun oynarsın, coin kazanırsın\n"
            "⚔️ Arkadaşınla yarışırsın, onun coinini alırsın\n"
            "🏪 Kazandığınla eşya alırsın, güçlenirsin\n"
            f"💵 Coini <b>gerçek paraya</b> çevirirsin ({cash.money(config.MIN_WITHDRAW)} olunca çekersin)\n\n"
            "👇 Aşağıdaki butonları kullan, hiçbir şey yazmana gerek yok."
        )
        await update.effective_chat.send_message(welcome, parse_mode=ParseMode.HTML,
                                                 reply_markup=ui.bottom_kb())
        await ui.send(update, main_menu_text(user), ui.main_menu_kb())
        return

    if not ui.is_private(update):
        await ui.send(update, (
            "🏰 <b>CoinQuest</b> burada da hazır!\n\n"
            "Grupta: /duello (altınla 1v1), /parti (bedava grup oyunları), /boss, /siralama\n"
            "Özelde: tüm oyun salonu, market, envanter ve daha fazlası."
        ), ui.pm_link())
        return
    await update.effective_chat.send_message("👇 Butonlar hazır.", reply_markup=ui.bottom_kb())
    await ui.send(update, main_menu_text(user), ui.main_menu_kb())


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "Menü bana özelden yazınca açılır 🙂", ui.pm_link())
        return
    user = db.get_user(update.effective_user.id)
    await ui.send(update, main_menu_text(user), ui.main_menu_kb())


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await", None)
    games.clear_sessions(context)
    await ui.send(update, "✅ İşlem iptal edildi.", ui.main_menu_kb() if ui.is_private(update) else None)


async def on_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    if parts[1] == "main":
        if not ui.is_private(update):
            await query.answer("Menü özel sohbette açılır.", show_alert=True)
            return
        games.clear_sessions(context)
        user = db.get_user(update.effective_user.id)
        await ui.safe_edit(query, main_menu_text(user), ui.main_menu_kb())


async def on_custom_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """bet:custom:<callback_prefix> — kullanıcıdan özel bahis tutarı ister."""
    query = update.callback_query
    await query.answer()
    prefix = query.data.split(":", 2)[2]
    user = db.get_user(update.effective_user.id)
    context.user_data["await"] = {"kind": "custom_bet", "prefix": prefix}
    await ui.safe_edit(query, (
        "✏️ <b>ÖZEL BAHİS</b>\n\n"
        f"Bakiyen: {ui.fmt(user['coins'])} 🪙\n"
        f"Limit: {ui.fmt(config.MIN_BET)} – {ui.fmt(economy.max_bet(user))} 🪙\n\n"
        "Bahis tutarını yaz (sadece sayı). İptal: /iptal"
    ), ui.kb([[("🎮 Oyunlar", "g:menu")]]))


# ---------------------------------------------------------------------------
# METİN YÖNLENDİRİCİ
# ---------------------------------------------------------------------------

async def on_bottom_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ekranın altındaki sabit butonlara basıldığında ilgili ekranı açar."""
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    if text not in BOTTOM_ACTIONS:
        return False
    context.user_data.pop("await", None)      # yarım kalan yazma işlemi varsa iptal
    games.clear_sessions(context)
    await BOTTOM_ACTIONS[text](update, context)
    return True


async def _open_menu(update, context):
    user = db.get_user(update.effective_user.id)
    await ui.send(update, main_menu_text(user), ui.main_menu_kb())


BOTTOM_ACTIONS = {
    "🎮 Oyunlar": lambda u, c: games.cmd_games(u, c),
    "💰 Cüzdanım": lambda u, c: social.cmd_profile(u, c),
    "🎁 Günlük Hediye": lambda u, c: social.cmd_daily(u, c),
    "💵 Para Çek": lambda u, c: cash.cmd_cash(u, c),
    "🏪 Market": lambda u, c: market.cmd_market(u, c),
    "🎒 Eşyalarım": lambda u, c: market.cmd_inventory(u, c),
    "👥 Arkadaş Çağır": lambda u, c: social.cmd_ref(u, c),
    "📖 Menü": _open_menu,
}


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return
    if ui.is_private(update):
        if await on_bottom_button(update, context):
            return
        for handler in (admin.on_text, cash.on_text, market.on_text, social.on_text,
                        games.on_text_answer):
            try:
                if await handler(update, context):
                    return
            except Exception:
                log.exception("metin işleyici hatası: %s", handler.__name__)
        return
    try:
        await party.on_text(update, context)
    except Exception:
        log.exception("parti metin işleyici hatası")


# ---------------------------------------------------------------------------
# ÖN İŞLEM (kayıt / ban / grup takibi)
# ---------------------------------------------------------------------------

async def pre_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    if tg_user is None or tg_user.is_bot:
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        db.run(
            "INSERT INTO groups (chat_id, title, added_ts) VALUES (?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title",
            (chat.id, (chat.title or "")[:80], ui.now()),
        )
    row = db.get_user(tg_user.id)
    if row is None:
        # /start dışındaki ilk temaslarda da hesap açılır (grup oyunları için)
        db.ensure_user(tg_user)
        return
    db.upd(tg_user.id, last_seen=ui.now(), username=(tg_user.username or "")[:64],
           first_name=(tg_user.first_name or "Gezgin")[:64])
    if row["banned"]:
        if update.callback_query:
            await update.callback_query.answer("🚫 Bu bottan yasaklandın.", show_alert=True)
        raise ApplicationHandlerStop


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Hata: %s", context.error)
    log.error("".join(traceback.format_exception(None, context.error, context.error.__traceback__))[-1500:])


async def post_init(app: Application) -> None:
    # Kısa liste: normalde kimse komut yazmaz, her şey butonlarla yapılır.
    await app.bot.set_my_commands([
        BotCommand("start", "🏰 Başla / menü"),
        BotCommand("para", "💵 Gerçek para ekranı"),
        BotCommand("duello", "⚔️ Grupta düello kur"),
        BotCommand("parti", "🎉 Grup oyunları"),
        BotCommand("yardim", "❓ Nasıl oynanır"),
    ])
    me = await app.bot.get_me()
    if not config.BOT_USERNAME:
        config.BOT_USERNAME = me.username or ""
    log.info("Bot hazır: @%s (%s)", me.username, me.id)


def build_app() -> Application:
    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(TypeHandler(Update, pre_process), group=-1)

    # komutlar
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["menu", "anamenu"], cmd_menu))
    app.add_handler(CommandHandler(["iptal", "cancel"], cmd_cancel))
    app.add_handler(CommandHandler(["oyunlar", "oyun", "games"], games.cmd_games))
    app.add_handler(CommandHandler(["duello", "duel", "pvp"], pvp.cmd_duel))
    app.add_handler(CommandHandler(["kabul", "katil"], pvp.cmd_accept))
    app.add_handler(CommandHandler(["parti", "grupoyun"], party.cmd_party))
    app.add_handler(CommandHandler(["sandik", "hazine"], party.cmd_chest))
    app.add_handler(CommandHandler(["profil", "profile", "p"], social.cmd_profile))
    app.add_handler(CommandHandler(["bakiye", "cuzdan", "balance"], social.cmd_balance))
    app.add_handler(CommandHandler(["gunluk", "daily"], social.cmd_daily))
    app.add_handler(CommandHandler(["saatlik", "bonus"], social.cmd_hourly))
    app.add_handler(CommandHandler(["market", "dukkan"], market.cmd_market))
    app.add_handler(CommandHandler(["envanter", "inv"], market.cmd_inventory))
    app.add_handler(CommandHandler(["pazar", "bazaar"], market.cmd_bazaar))
    app.add_handler(CommandHandler(["isletme", "biz"], market_biz_cmd))
    app.add_handler(CommandHandler(["banka", "bank"], social.cmd_bank))
    app.add_handler(CommandHandler(["transfer", "gonder"], social.cmd_transfer))
    app.add_handler(CommandHandler(["soy", "soygun", "rob"], social.cmd_rob))
    app.add_handler(CommandHandler(["klan", "clan"], social.cmd_clan))
    app.add_handler(CommandHandler(["gorevler", "quests"], events.cmd_quests))
    app.add_handler(CommandHandler(["siralama", "top"], social.cmd_top))
    app.add_handler(CommandHandler(["boss", "raid"], events.cmd_boss))
    app.add_handler(CommandHandler(["piyango", "lottery"], events.cmd_lottery))
    app.add_handler(CommandHandler(["davet", "ref"], social.cmd_ref))
    app.add_handler(CommandHandler(["yardim", "help"], social.cmd_help))
    app.add_handler(CommandHandler(["para", "cek", "cash"], cash.cmd_cash))
    app.add_handler(CommandHandler("admin", admin.cmd_admin))

    # callback yönlendirmeleri
    app.add_handler(CallbackQueryHandler(on_menu_callback, pattern=r"^m:"))
    app.add_handler(CallbackQueryHandler(on_custom_bet, pattern=r"^bet:custom:"))
    app.add_handler(CallbackQueryHandler(games.on_callback, pattern=r"^g:"))
    app.add_handler(CallbackQueryHandler(pvp.on_callback, pattern=r"^pvp:"))
    app.add_handler(CallbackQueryHandler(party.on_callback, pattern=r"^pt:"))
    app.add_handler(CallbackQueryHandler(market.on_callback, pattern=r"^mk:"))
    app.add_handler(CallbackQueryHandler(social.on_callback, pattern=r"^s:"))
    app.add_handler(CallbackQueryHandler(events.on_callback, pattern=r"^ev:"))
    app.add_handler(CallbackQueryHandler(cash.on_callback, pattern=r"^cash:"))
    app.add_handler(CallbackQueryHandler(admin.on_callback, pattern=r"^ad:"))

    # düz metin
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.add_error_handler(on_error)

    jq = app.job_queue
    if jq is not None:
        jq.run_repeating(events.job_boss, interval=config.BOSS_INTERVAL_MIN * 60, first=60)
        jq.run_repeating(events.job_lottery, interval=300, first=90)
        jq.run_repeating(events.job_interest, interval=3600, first=300)
        jq.run_repeating(pvp.job_cleanup, interval=300, first=120)
    else:
        log.warning("JobQueue yok: pip install 'python-telegram-bot[job-queue]'")
    return app


async def market_biz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "🏭 İşletme paneli özel sohbette açılır.", ui.pm_link())
        return
    user = db.get_user(update.effective_user.id)
    await ui.send(update, market.biz_text(user), market.biz_kb(user))


def main() -> None:
    if not config.BOT_TOKEN:
        print(
            "\n❌ BOT_TOKEN bulunamadı!\n\n"
            "1) coinquest/.env.example dosyasını .env olarak kopyala\n"
            "2) İçine @BotFather'dan aldığın tokenı yaz:\n"
            "   BOT_TOKEN=123456:ABC...\n"
            "   ADMIN_IDS=senin_telegram_id\n\n"
            "Sonra tekrar çalıştır: python3 bot.py\n"
        )
        sys.exit(1)
    db.init()
    log.info("%d eşya yüklendi", len(items.ITEMS))
    app = build_app()
    log.info("CoinQuest başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
