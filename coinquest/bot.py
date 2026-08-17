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
import i18n
import items
import market
import media
import party
import pvp
import social
import support
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
    lang = i18n.lang_of(user["user_id"])
    extra = ""
    boss = events.active_boss()
    if boss:
        extra += "\n" + i18n.t(lang, "menu_boss", name=ui.esc(boss["name"]))
    ready = sum(1 for q in events.daily_quests(user["user_id"])
                if not q["claimed"] and q["progress"] >= q["target"])
    if ready:
        extra += "\n" + i18n.t(lang, "menu_quest", n=ready)
    return (
        f"🏰 <b>COINQUEST</b>\n{ui.LINE}\n"
        f"{i18n.t(lang, 'menu_hi', name=ui.name_of(user))}\n"
        f"{ui.header(user, with_money=True)}"
        f"{extra}\n\n{i18n.t(lang, 'menu_ask')} 👇"
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
        # davet ödülü bot koruması geçilince verilir (bkz. on_captcha)
        user = db.get_user(tg_user.id)
        # yeni oyuncu: önce dil seçsin, gerisi dil seçilince gelir
        await update.effective_chat.send_message(
            "🌐 <b>Dil / Язык / Dil</b>\n\nSaýla — Выбери — Seç 👇",
            parse_mode=ParseMode.HTML, reply_markup=ui.lang_kb())
        return

    if not ui.is_private(update):
        await ui.send(update, (
            "🏰 <b>CoinQuest</b>\n\n"
            "⚔️ /duello — teňňe üçin ýaryş / дуэль на монеты\n"
            "🎉 /parti — mugt topar oýunlary / игры для группы\n"
            "🐉 /boss — aždarha / босс"
        ), ui.pm_link())
        return
    lang = i18n.lang_of(tg_user.id)
    user_id = tg_user.id
    try:                                   # eski alt klavyesi kalanlarda temizle
        msg = await update.effective_chat.send_message("🏰", reply_markup=ui.remove_bottom())
        await msg.delete()
    except Exception:
        pass
    if not user["captcha_ok"]:
        await show_captcha(update.effective_chat, context, tg_user.id)
        return
    await ui.screen(update, "menu", main_menu_text(user), ui.main_menu_kb(lang, user_id))


# ---------------------------------------------------------------------------
# BOT KORUMASI (captcha)
# ---------------------------------------------------------------------------

def _captcha_question():
    import random
    a, b = random.randint(2, 19), random.randint(2, 19)
    op = random.choice(["+", "-"])
    if op == "-" and b > a:
        a, b = b, a
    answer = a + b if op == "+" else a - b
    options = {answer}
    while len(options) < 4:
        options.add(answer + random.choice([-5, -3, -2, -1, 1, 2, 3, 4, 6]))
    options = list(options)
    random.shuffle(options)
    return f"{a} {op} {b} = ?", options, options.index(answer)


async def show_captcha(chat, context, user_id: int, first: bool = True) -> None:
    lang = i18n.lang_of(user_id)
    question, options, correct = _captcha_question()
    context.user_data["captcha"] = correct
    rows = [[(str(v), f"cap:{i}") for i, v in enumerate(options)]]
    text = (f"{i18n.t(lang, 'cap_title')}\n{ui.LINE}\n"
            f"{i18n.t(lang, 'cap_ask')}\n\n<code>   {question}   </code>")
    await chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=ui.kb(rows))


async def on_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    if user is None:
        await query.answer()
        return
    correct = context.user_data.get("captcha")
    picked = int(query.data.split(":")[1])
    tries = user["captcha_try"] + 1
    db.upd(user_id, captcha_try=tries)

    if correct is None or picked != correct:
        await query.answer(i18n.t(lang, "cap_wrong", n=tries, max=config.CAPTCHA_MAX_TRIES),
                           show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        await show_captcha(query.message.chat, context, user_id, first=False)
        return

    db.upd(user_id, captcha_ok=1)
    context.user_data.pop("captcha", None)
    await query.answer(i18n.t(lang, "cap_ok"))
    # davet ödülü: ilk denemede tam, 2-3. denemede yarım, sonrası yok
    if user["referrer"] and not user["ref_paid"]:
        if tries == 1:
            factor = 1.0
        elif tries <= config.CAPTCHA_MAX_TRIES:
            factor = 0.5
        else:
            factor = 0.0
        social.grant_referral(user_id, user["referrer"], factor)
        db.upd(user_id, ref_paid=1)
        if factor > 0:
            try:
                inviter_lang = i18n.lang_of(user["referrer"])
                await context.bot.send_message(
                    user["referrer"],
                    f"👥 <b>{ui.name_of(db.get_user(user_id))}</b> +"
                    f"{ui.fmt(int(config.REF_REWARD_COINS * factor))} 🪙"
                    + ("" if factor == 1 else "  <i>(bot koruması 1. denemede geçilmedi, yarım ödül)</i>"),
                    parse_mode=ParseMode.HTML)
            except Exception:
                pass
    try:
        await query.message.delete()
    except Exception:
        pass
    if not user["last_daily"] and user["games"] == 0:
        await query.message.chat.send_message(
            i18n.t(lang, "welcome", coins=ui.fmt(config.START_COINS), gems=config.START_GEMS),
            parse_mode=ParseMode.HTML)
    user = db.get_user(user_id)
    await ui.screen(update, "menu", main_menu_text(user), ui.main_menu_kb(lang, user_id))


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ui.is_private(update):
        await ui.send(update, "Menü bana özelden yazınca açılır 🙂", ui.pm_link())
        return
    user = db.get_user(update.effective_user.id)
    await ui.screen(update, "menu", main_menu_text(user),
                    ui.main_menu_kb(i18n.lang_of(user["user_id"]), user["user_id"]))


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await", None)
    games.clear_sessions(context)
    await ui.send(update, "✅ İşlem iptal edildi.", ui.main_menu_kb(i18n.lang_of(update.effective_user.id), update.effective_user.id)
                     if ui.is_private(update) else None)


async def on_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[1]
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)

    if action == "setlang":
        i18n.set_lang(user_id, parts[2])
        lang = parts[2]
        user = db.get_user(user_id)
        await query.answer(i18n.t(lang, "lang_ok"))
        if not user["captcha_ok"]:
            try:
                await query.message.delete()
            except Exception:
                pass
            await show_captcha(query.message.chat, context, user_id)
            return
        await ui.nav(query, "menu", main_menu_text(user), ui.main_menu_kb(lang, user_id))
        return

    if not ui.is_private(update):
        await query.answer(i18n.t(lang, "only_private"), show_alert=True)
        return

    if action == "main":
        games.clear_sessions(context)
        user = db.get_user(user_id)
        await ui.nav(query, "menu", main_menu_text(user), ui.main_menu_kb(lang, user_id))
    elif action == "more":
        user = db.get_user(user_id)
        await ui.safe_edit(query, (
            f"{i18n.t(lang, 'more_title')}\n{ui.LINE}\n{ui.header(user, with_money=True)}"
        ), ui.more_menu_kb(lang))
    elif action == "lang":
        await ui.safe_edit(query, i18n.t(lang, "lang_title"), ui.lang_kb())


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
    key = i18n.all_button_labels().get(text)
    if key is None:
        return False
    context.user_data.pop("await", None)      # yarım kalan yazma işlemi varsa iptal
    games.clear_sessions(context)
    await BOTTOM_ACTIONS[key](update, context)
    return True


async def _open_menu(update, context):
    user = db.get_user(update.effective_user.id)
    lang = i18n.lang_of(user["user_id"])
    await ui.screen(update, "menu", main_menu_text(user), ui.main_menu_kb(lang, user["user_id"]))


BOTTOM_ACTIONS = {
    "b_play":    lambda u, c: games.cmd_games(u, c),
    "b_money":   lambda u, c: cash.cmd_cash(u, c),
    "b_gift":    lambda u, c: social.cmd_daily(u, c),
    "b_shop":    lambda u, c: market.cmd_market(u, c),
    "b_items":   lambda u, c: market.cmd_inventory(u, c),
    "b_friends": lambda u, c: social.cmd_ref(u, c),
    "b_menu":    lambda u, c: _open_menu(u, c),
}


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yazı ve medya mesajlarını ilgili bölüme yönlendirir."""
    msg = update.message
    if msg is None:
        return
    if ui.is_private(update):
        # destek ve reklam her tür medyayı kabul eder
        for handler in (support.on_message, admin.on_text):
            try:
                if await handler(update, context):
                    return
            except Exception:
                log.exception("işleyici hatası: %s", handler.__name__)
        if not msg.text:
            return
        if await on_bottom_button(update, context):
            return
        for handler in (cash.on_text, market.on_text, social.on_text, games.on_text_answer):
            try:
                if await handler(update, context):
                    return
            except Exception:
                log.exception("metin işleyici hatası: %s", handler.__name__)
        return
    if msg.text:
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


async def on_unknown_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiçbir kalıba uymayan buton — kullanıcı boşluğa basmasın."""
    query = update.callback_query
    log.warning("bilinmeyen buton: %s (user %s)", query.data, update.effective_user.id)
    await query.answer("Bu buton eskimiş, menüyü yeniliyorum 🙂", show_alert=False)
    user = db.get_user(update.effective_user.id)
    if user and ui.is_private(update):
        await ui.nav(query, "menu", main_menu_text(user),
                     ui.main_menu_kb(i18n.lang_of(user["user_id"]), user["user_id"]))


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
    app.add_handler(CommandHandler(["destek", "support", "komek"], support.cmd_support))
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
    app.add_handler(CallbackQueryHandler(support.on_callback, pattern=r"^sup:"))
    app.add_handler(CallbackQueryHandler(on_captcha, pattern=r"^cap:"))
    app.add_handler(CallbackQueryHandler(admin.on_callback, pattern=r"^ad:"))

    # yazı + medya (destek ve reklam için)
    media_filter = (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION
                    | filters.Document.ALL | filters.VOICE | filters.AUDIO
                    | filters.Sticker.ALL | filters.VIDEO_NOTE)
    app.add_handler(MessageHandler(media_filter & ~filters.COMMAND, on_message))
    # tanınmayan buton: sessiz kalmasın
    app.add_handler(CallbackQueryHandler(on_unknown_button))

    app.add_error_handler(on_error)

    jq = app.job_queue
    if jq is not None:
        jq.run_repeating(events.job_boss, interval=config.BOSS_INTERVAL_MIN * 60, first=60)
        jq.run_repeating(events.job_lottery, interval=300, first=90)
        jq.run_repeating(events.job_interest, interval=3600, first=300)
        jq.run_repeating(pvp.job_cleanup, interval=300, first=120)
        jq.run_repeating(pvp.job_queue_clean, interval=120, first=60)
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
    log.info("%d eşya, %d dil, resimler: %s", len(items.ITEMS), len(i18n.LANGS),
             ", ".join(media.available()) or "yok")
    app = build_app()
    log.info("CoinQuest başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
