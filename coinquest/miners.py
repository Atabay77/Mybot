# -*- coding: utf-8 -*-
"""Madenci sistemi.

Oyuncu coin ile madenci satın alır. Her madencinin bir GÜCÜ vardır ve
gücü kadar 4 saatte bir coin üretir. Kasa en fazla 20 döngü (80 saat) biriktirir,
yani düzenli toplamak gerekir.

Yeni madenci eklemek için MINERS listesine satır eklemen yeterli.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import notify
import ui
import war

log = logging.getLogger(__name__)

CYCLE = config.BUSINESS_COLLECT_SEC       # 4 saat
MAX_CYCLES = 20                           # en fazla 20 döngü (80 saat) birikir
PAGE = 5

#            anahtar  ad                      emoji  fiyat            güç (4 saatte coin)  seviye
MINERS = [
    ("m01", "El Kazması",            "⛏",  5_000,             900,           1),
    ("m02", "Kömür Ocağı",           "🪨", 15_000,          2_700,           2),
    ("m03", "Demir Vagonu",          "🛒", 45_000,          8_100,           4),
    ("m04", "Buhar Matkabı",         "⚙️", 120_000,        21_000,           6),
    ("m05", "Elmas Delici",          "💠", 350_000,        62_000,           8),
    ("m06", "Altın Eleği",           "🥇", 900_000,       160_000,          10),
    ("m07", "Lazer Kesici",          "🔦", 2_400_000,     430_000,          13),
    ("m08", "Robot Madenci",         "🤖", 6_000_000,   1_080_000,          16),
    ("m09", "Dev Ekskavatör",        "🚜", 15_000_000,  2_700_000,          19),
    ("m10", "Yeraltı Fabrikası",     "🏭", 40_000_000,  7_200_000,          22),
    ("m11", "Sismik Sondaj",         "🌋", 100_000_000, 18_000_000,         25),
    ("m12", "Kuantum Delici",        "⚛️", 260_000_000, 47_000_000,         28),
    ("m13", "Asteroit Madeni",       "☄️", 700_000_000, 126_000_000,        32),
    ("m14", "Kara Delik Toplayıcı",  "🕳", 1_800_000_000, 325_000_000,      36),
    ("m15", "Yıldız Fabrikası",      "🌟", 5_000_000_000, 900_000_000,      40),
]
BY_KEY = {m[0]: m for m in MINERS}

# Görsellerdeki boy ile aynı olmalı (images/PROMPTLAR.md).
# Güç farkı oyuncuya "boy farkı" olarak da gösteriliyor.
SIZES = {
    "m01": (1, "🧍"), "m02": (2, "🧍"), "m03": (3, "🧍"), "m04": (5, "🏠"),
    "m05": (8, "🏠"), "m06": (12, "🏢"), "m07": (18, "🏢"), "m08": (25, "🏢"),
    "m09": (40, "🏗"), "m10": (70, "🏙"), "m11": (120, "🗼"), "m12": (200, "🗼"),
    "m13": (400, "🚀"), "m14": (1000, "🌌"), "m15": (10000, "⭐"),
}


def size_of(key: str) -> str:
    """1 -> '1 m 🧍',  1000 -> '1 km 🌌'"""
    meters, icon = SIZES.get(key, (1, "🧍"))
    label = f"{meters // 1000} km" if meters >= 1000 else f"{meters} m"
    return f"{label} {icon}"


def size_bar(key: str) -> str:
    """Boyu çubukla gösterir. Logaritmik: 1 m = 1 çubuk, 10 km = 15 çubuk."""
    import math
    meters = SIZES.get(key, (1, ""))[0]
    length = max(1, min(15, int(round(math.log10(max(1, meters)) * 3.5)) + 1))
    return "▮" * length + "▫" * (15 - length)


def power_vs_prev(key: str) -> float:
    """Bir önceki madenciye göre kaç kat güçlü."""
    keys = [m[0] for m in MINERS]
    idx = keys.index(key)
    if idx == 0:
        return 0.0
    return MINERS[idx][4] / MINERS[idx - 1][4]


def get(key: str):
    return BY_KEY.get(key)


def owned(user_id: int) -> dict[str, int]:
    return {r["key"]: r["qty"] for r in
            db.all_("SELECT key, qty FROM miners WHERE user_id=? AND qty>0", (user_id,))}


def total_power(user_id: int) -> int:
    """Sahip olunan tüm madencilerin toplam gücü (4 saatlik üretim)."""
    total = 0
    for key, qty in owned(user_id).items():
        miner = get(key)
        if miner:
            total += miner[4] * qty
    return total


def pending(user_id: int) -> tuple[float, int, int]:
    """Kasa saniye saniye dolar.

    (birikmiş coin [ondalıklı], tamamlanan döngü, sonraki döngüye kalan saniye)
    """
    user = db.get_user(user_id)
    power = total_power(user_id)
    if not power:
        return 0.0, 0, 0
    last = user["miner_ts"] or ui.now()
    elapsed = max(0, ui.now() - last)
    capped = min(elapsed, MAX_CYCLES * CYCLE)     # üst sınır
    amount = power * capped / CYCLE               # sürekli birikim
    cycles = int(capped // CYCLE)
    left = CYCLE - (elapsed % CYCLE) if capped < MAX_CYCLES * CYCLE else 0
    return amount, cycles, int(left)


def counter(amount: float) -> str:
    """Sayaç görünümü: 003722.4 — gözle artışı takip edebilmek için."""
    return f"{amount:08.1f}"


def collect(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    amount, cycles, left = pending(user_id)
    if total_power(user_id) == 0:
        return i18n.t(lang, "mn_none")
    if cycles <= 0:
        return i18n.t(lang, "mn_wait", time=ui.dur(left))
    user = db.get_user(user_id)
    amount = economy.payout(user, int(amount))
    db.upd(user_id, miner_ts=ui.now(), miner_notify=0)
    economy.add_coins(user_id, amount, "madenci geliri")
    economy.add_xp(user_id, 15 * cycles)
    war.add(user_id, "miner")
    return i18n.t(lang, "mn_got", amount=ui.fmt(amount), cycles=cycles)


def buy(user_id: int, key: str) -> tuple[bool, str]:
    miner = get(key)
    lang = i18n.lang_of(user_id)
    if not miner:
        return False, "?"
    _k, name, emoji, price, power, min_level = miner
    user = db.get_user(user_id)
    if user["level"] < min_level:
        return False, i18n.t(lang, "mn_level", lvl=min_level)
    if user["coins"] < price:
        return False, i18n.t(lang, "no_money", need=ui.fmt(price), have=ui.fmt(user["coins"]))
    # ilk madenciyi alırken sayacı başlat
    if total_power(user_id) == 0:
        db.upd(user_id, miner_ts=ui.now())
    if not economy.take_coins(user_id, price, f"madenci: {key}"):
        return False, i18n.t(lang, "no_money", need=ui.fmt(price), have=ui.fmt(user["coins"]))
    db.run("INSERT INTO miners (user_id, key, qty, got_ts) VALUES (?,?,1,?) "
           "ON CONFLICT(user_id, key) DO UPDATE SET qty=qty+1", (user_id, key, ui.now()))
    have = owned(user_id).get(key, 1)
    return True, i18n.t(lang, "mn_bought", name=f"{emoji} {name}", qty=have,
                        power=ui.fmt(power))


# ---------------------------------------------------------------------------
# EKRANLAR
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    mine = owned(user_id)
    power = total_power(user_id)
    amount, cycles, left = pending(user_id)
    lines = [f"{i18n.t(lang, 'mn_title')}\n{ui.LINE}", ui.header(user)]
    if mine:
        listed = "\n".join(
            f"{get(k)[2]} {get(k)[1]} ×{q}  ({size_of(k)})\n"
            f"    {ui.fmt(get(k)[4] * q)} 🪙"
            for k, q in sorted(mine.items()) if get(k))
        lines.append(f"<blockquote>{listed}</blockquote>")
        lines.append(i18n.t(lang, "mn_power", power=ui.fmt(power)))
        lines.append(f"<blockquote>{i18n.t(lang, 'mn_case')}\n"
                     f"<code>{counter(amount)}</code> 🪙\n"
                     f"<i>+{power / CYCLE:.2f} 🪙/sn</i></blockquote>")
        if cycles > 0:
            lines.append(i18n.t(lang, "mn_ready_c", cycles=cycles, max=MAX_CYCLES))
        else:
            lines.append(i18n.t(lang, "mn_next", time=ui.dur(left)))
        if cycles >= MAX_CYCLES:
            lines.append(i18n.t(lang, "mn_full"))
    else:
        lines.append(i18n.t(lang, "mn_empty"))
    lines.append("\n" + i18n.t(lang, "mn_how", hours=CYCLE // 3600, max=MAX_CYCLES))
    return "\n".join(lines)


def panel_kb(user_id: int, page: int = 0):
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    mine = owned(user_id)
    _amount, cycles, _left = pending(user_id)
    rows = []
    if total_power(user_id):
        label = i18n.t(lang, "mn_collect")
        if cycles > 0:
            label += f"  ({ui.fmt(int(pending(user_id)[0]))} 🪙)"
        rows.append([(label, "mi:collect")])
    pages = max(1, (len(MINERS) + PAGE - 1) // PAGE)
    page = max(0, min(page, pages - 1))
    for key, name, emoji, price, power, min_level in MINERS[page * PAGE:(page + 1) * PAGE]:
        have = mine.get(key, 0)
        if user["level"] < min_level:
            label = f"🔒 {emoji} {name} — Sv.{min_level}"
        else:
            tag = f" ×{have}" if have else ""
            label = f"{emoji} {name}{tag} • {size_of(key)} — {ui.fmt(price)} 🪙"
        rows.append([(label, f"mi:info:{key}")])
    nav = []
    if page > 0:
        nav.append(("⬅️", f"mi:menu:{page - 1}"))
    nav.append((f"{page + 1}/{pages}", "mi:noop"))
    if page < pages - 1:
        nav.append(("➡️", f"mi:menu:{page + 1}"))
    rows.append(nav)
    rows.append([(i18n.t(lang, "b_refresh"), f"mi:menu:{page}"),
                 (i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


def info_text(user_id: int, key: str) -> str:
    lang = i18n.lang_of(user_id)
    miner = get(key)
    if not miner:
        return "?"
    _k, name, emoji, price, power, min_level = miner
    user = db.get_user(user_id)
    have = owned(user_id).get(key, 0)
    roi = price / power * (CYCLE / 3600)
    idx = [m[0] for m in MINERS].index(key) + 1
    return (
        f"{emoji} <b>{name}</b>   <i>{idx}/{len(MINERS)}</i>\n{ui.LINE}\n"
        f"<blockquote>📏 {i18n.t(lang, 'mn_size')}: <b>{size_of(key)}</b>\n"
        f"{size_bar(key)}\n"
        f"💰 {i18n.t(lang, 'mn_price')}: <b>{ui.fmt(price)}</b> 🪙\n"
        f"⚡ {i18n.t(lang, 'mn_power_s')}: <b>{ui.fmt(power)}</b> 🪙 / {CYCLE // 3600}s\n"
        f"📦 {i18n.t(lang, 'mn_have')}: <b>{have}</b>\n"
        f"⏱ {i18n.t(lang, 'mn_roi', hours=int(roi))}</blockquote>\n"
        + (f"🔺 {i18n.t(lang, 'mn_stronger', x=f'{power_vs_prev(key):.1f}')}\n"
           if power_vs_prev(key) else "")
        + (f"🔒 Seviye {min_level} gerekli\n" if user["level"] < min_level else "")
        + f"🪙 {ui.fmt(user['coins'])}"
    )


def info_kb(user_id: int, key: str):
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    miner = get(key)
    rows = []
    if user["level"] >= miner[5]:
        rows.append([(i18n.t(lang, "mn_buy"), f"mi:buy:{key}")])
    rows.append([(i18n.t(lang, "b_back"), "mi:menu:0")])
    return ui.kb(rows)


# ---------------------------------------------------------------------------
# CALLBACK
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    if not ui.is_private(update):
        await ui.answer(query, i18n.t(lang, "only_private"), alert=True)
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    context.user_data["_toast"] = i18n.t(lang, "mn_title_s")

    if action == "menu":
        page = int(parts[2]) if len(parts) > 2 else 0
        msg = await ui.nav(query, "miners", panel_text(user_id), panel_kb(user_id, page))
        if msg and page == 0:
            start_ticker(context, msg.chat_id, msg.message_id, user_id)
    elif action == "noop":
        await ui.answer(query)
    elif action == "info":
        key = parts[2]
        await ui.nav(query, f"miner_{key}", info_text(user_id, key), info_kb(user_id, key))
    elif action == "buy":
        ok, msg = buy(user_id, parts[2])
        await ui.answer(query, msg.replace("<b>", "").replace("</b>", ""), alert=True)
        await ui.nav(query, f"miner_{parts[2]}", info_text(user_id, parts[2]),
                     info_kb(user_id, parts[2]))
    elif action == "collect":
        msg = collect(user_id)
        await ui.answer(query, msg.replace("<b>", "").replace("</b>", ""), alert=True)
        new = await ui.nav(query, "miners", panel_text(user_id), panel_kb(user_id))
        if new:
            start_ticker(context, new.chat_id, new.message_id, user_id)


# ---------------------------------------------------------------------------
# CANLI SAYAÇ  (ekran açıkken kasa gözle görülür şekilde artar)
# ---------------------------------------------------------------------------
TICK_SECONDS = 12          # kaç saniyede bir güncellensin
TICK_COUNT = 15            # kaç kez güncellensin (12 x 15 = 3 dakika)


def start_ticker(context, chat_id: int, message_id: int, user_id: int) -> None:
    """Madenci ekranı açıkken sayacı canlı günceller."""
    queue = getattr(context, "job_queue", None)
    if queue is None:
        return
    name = f"miner_tick_{user_id}"
    for job in queue.get_jobs_by_name(name):
        job.schedule_removal()
    queue.run_repeating(
        _tick, interval=TICK_SECONDS, first=TICK_SECONDS, name=name,
        data={"chat": chat_id, "msg": message_id, "user": user_id, "n": 0})


async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    data["n"] += 1
    if data["n"] > TICK_COUNT or total_power(data["user"]) == 0:
        context.job.schedule_removal()
        return
    try:
        await context.bot.edit_message_text(
            panel_text(data["user"]), chat_id=data["chat"], message_id=data["msg"],
            parse_mode="HTML", reply_markup=panel_kb(data["user"]))
    except Exception:
        context.job.schedule_removal()      # mesaj silinmiş ya da değişmiş


async def job_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kasada en az 1 döngü birikince 'toplama zamanı' bildirimi gönderir."""
    rows = db.all_("SELECT DISTINCT user_id FROM miners WHERE qty>0")
    for row in rows:
        uid = row["user_id"]
        user = db.get_user(uid)
        if not user or user["banned"] or user["miner_notify"]:
            continue
        amount, cycles, _left = pending(uid)
        if cycles < 1:
            continue
        lang = i18n.lang_of(uid)
        # Ortak bildirim kapısından geçer: günlük kota, sessiz saat ve
        # 'botu engelledi' kuralları madenci bildirimine de uygulanır.
        # Bayrak SADECE mesaj gerçekten gittiyse yakılır.
        sent = await notify.send(
            context, uid, "miner",
            i18n.t(lang, "mn_alert", amount=ui.fmt(int(amount))),
            extra_rows=[[(i18n.t(lang, "b_miners"), "mi:menu:0")]])
        if sent:
            db.upd(uid, miner_notify=1)


async def cmd_miners(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    msg = await ui.screen(update, "miners", panel_text(user_id), panel_kb(user_id))
    if msg:
        start_ticker(context, msg.chat_id, msg.message_id, user_id)
