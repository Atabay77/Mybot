# -*- coding: utf-8 -*-
"""Geri çağırma bildirimleri.

Oyuncudan kopmamak için bot kendiliğinden kısa mesajlar atar: serin bozulmak
üzere, hediyen hazır, işletme kasan doldu, boss doğdu...

Kurallar (sahibin isteği): varsayılan AÇIK, oyuncu tek dokunuşla kapatabilir,
günde en fazla 3 mesaj, aralarında en az 4 saat, gece hiç mesaj yok.

Botun gönderdiği TÜM geri çağırma mesajları `send()` fonksiyonundan geçer —
kotanın delinmesi yapısal olarak imkânsız olsun diye.
"""
import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import ui
import war

log = logging.getLogger(__name__)

# tür -> (buton hedefi, mesaj anahtarı, buton anahtarı)
KINDS = {
    "streak": ("s:daily", "nt_streak", "nt_b_streak"),
    "daily":  ("s:daily", "nt_daily", "nt_b_daily"),
    "back7":  ("nt:gift:7", "nt_back7", "nt_b_back"),
    "back3":  ("nt:gift:3", "nt_back3", "nt_b_back"),
    "boss":   ("ev:boss", "nt_boss", "nt_b_boss"),
    "miner":  ("mi:collect", "mn_alert", "mn_collect"),
    "biz":    ("mk:biz", "nt_biz", "nt_b_biz"),
    "energy": ("g:menu", "nt_energy", "nt_b_energy"),
}

# öncelik sırası — seri kaybı en güçlü geri getirici, en tepede
ORDER = ["streak", "daily", "back7", "back3", "boss", "biz", "energy"]

GIFTS = {3: (15_000, 3), 7: (50_000, 10)}


# ---------------------------------------------------------------------------
# KOTA
# ---------------------------------------------------------------------------

def quiet_now(ts: int = None) -> bool:
    """Gece sessizliği (Aşgabat saati)."""
    hour = war.local_hour(ts)
    start, end = config.NOTIFY_QUIET_START, config.NOTIFY_QUIET_END
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end      # gece yarısını aşan aralık


def _roll_day(user, day: str) -> tuple[int, set]:
    """Gün değiştiyse sayacı sıfırlanmış gibi döner (tembel sıfırlama)."""
    if user["notify_day"] != day:
        return 0, set()
    sent = {x for x in (user["notify_sent"] or "").split(",") if x}
    return int(user["notify_count"] or 0), sent


def can_send(user_id: int, kind: str, ts: int = None) -> bool:
    now = ts if ts is not None else ui.now()
    user = db.get_user(user_id)
    if user is None or user["banned"] or user["notify_on"] != 1:
        return False                                    # 0 = kapattı, 2 = botu engelledi
    if quiet_now(now):
        return False
    count, sent = _roll_day(user, war.day_key(now))
    if count >= config.NOTIFY_MAX_PER_DAY:
        return False
    if now - int(user["notify_last"] or 0) < config.NOTIFY_MIN_GAP:
        return False
    if kind in sent:
        return False                                    # aynı tür günde bir kez
    return True


def _mark(user_id: int, kind: str, ts: int) -> None:
    user = db.get_user(user_id)
    if user is None:
        return
    day = war.day_key(ts)
    count, sent = _roll_day(user, day)
    sent.add(kind)
    fields = {"notify_day": day, "notify_count": count + 1, "notify_last": ts,
              "notify_sent": ",".join(sorted(sent))}
    if kind in ("back3", "back7"):
        fields["notify_back"] = ts
    db.upd(user_id, **fields)


async def send(context: ContextTypes.DEFAULT_TYPE, user_id: int, kind: str,
               text: str = "", extra_rows: list = None) -> bool:
    """Tek gerçek gönderim yolu. Kota/sessiz saat/engel kurallarını uygular."""
    if kind not in KINDS or not can_send(user_id, kind):
        return False
    target, msg_key, btn_key = KINDS[kind]
    lang = i18n.lang_of(user_id)
    rows = [[(i18n.t(lang, btn_key), target)]]
    if extra_rows:
        rows += extra_rows
    rows.append([(i18n.t(lang, "nt_b_off"), "nt:off")])     # tek dokunuşla kapatma
    try:
        await context.bot.send_message(user_id, text or i18n.t(lang, msg_key),
                                       parse_mode=ParseMode.HTML, reply_markup=ui.kb(rows))
    except Forbidden:                       # botu engellemiş — bir daha denemeyiz
        db.upd(user_id, notify_on=2)
        return False
    except RetryAfter as exc:               # flood limiti: bu turu atla
        await asyncio.sleep(min(30, exc.retry_after + 1))
        return False
    except (BadRequest, TimedOut, NetworkError):
        return False
    except Exception as exc:
        log.warning("bildirim gönderilemedi (%s): %s", user_id, exc)
        return False
    _mark(user_id, kind, ui.now())
    return True


# ---------------------------------------------------------------------------
# ADAY SEÇİMİ
# ---------------------------------------------------------------------------

_BASE = ("banned=0 AND notify_on=1 AND captcha_ok=1 "
         "AND notify_last < ? AND (notify_day <> ? OR notify_count < ?)")


def _candidates(kind: str, now: int, limit: int) -> list[int]:
    """Tür başına tek SQL. En son görülen oyuncu önce (en kolay geri gelen)."""
    day = war.day_key(now)
    base = [now - config.NOTIFY_MIN_GAP, day, config.NOTIFY_MAX_PER_DAY]
    if kind == "streak":
        sql = _BASE + " AND streak >= 3 AND last_daily BETWEEN ? AND ?"
        args = base + [now - 44 * 3600, now - 20 * 3600]
    elif kind == "daily":
        sql = _BASE + " AND streak < 3 AND last_daily <= ? AND last_seen > ?"
        args = base + [now - 20 * 3600, now - 5 * 86400]
    elif kind == "back7":
        sql = _BASE + " AND last_seen BETWEEN ? AND ? AND notify_gift < ?"
        args = base + [now - 10 * 86400, now - 7 * 86400, now - 14 * 86400]
    elif kind == "back3":
        sql = _BASE + " AND last_seen BETWEEN ? AND ? AND notify_gift < ?"
        args = base + [now - 5 * 86400, now - 3 * 86400, now - 14 * 86400]
    elif kind == "boss":
        sql = _BASE + " AND level >= 5 AND last_seen > ?"
        args = base + [now - 3 * 86400]
    elif kind == "biz":
        sql = _BASE + " AND business_key <> '' AND business_ts <= ? AND last_seen > ?"
        args = base + [now - config.BUSINESS_COLLECT_SEC, now - 3 * 86400]
    elif kind == "energy":
        sql = _BASE + " AND energy_unlim = 0 AND last_seen BETWEEN ? AND ?"
        args = base + [now - 2 * 86400, now - 6 * 3600]
    else:
        return []
    rows = db.all_(f"SELECT user_id FROM users WHERE {sql} ORDER BY last_seen DESC LIMIT ?",
                   args + [limit])
    return [r["user_id"] for r in rows]


def _fields(kind: str, user_id: int) -> dict:
    """Mesajdaki {yer tutucular}."""
    user = db.get_user(user_id)
    if kind == "streak":
        return {"n": user["streak"] if user else 0}
    if kind in ("back3", "back7"):
        coins, gems = GIFTS[7 if kind == "back7" else 3]
        return {"coins": ui.fmt(coins), "gems": gems}
    return {}


def _extra_ok(kind: str, user_id: int, now: int, boss_id: int = 0) -> bool:
    """SQL'in kabaca seçtiği adayı Python tarafında kesinleştirir."""
    user = db.get_user(user_id)
    if user is None:
        return False
    if kind == "energy":
        return economy.sync_energy(user_id) >= economy.max_energy(user["level"])
    if kind == "boss":
        if not boss_id:
            return False
        return not db.one("SELECT 1 FROM boss_hits WHERE boss_id=? AND user_id=?",
                          (boss_id, user_id))
    return True


async def job_scan(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kime bildirim gideceğine karar verir ve yollar."""
    try:
        now = ui.now()
        if quiet_now(now):
            return
        boss_id = 0
        try:
            import events                                # geç import: döngü olmasın
            boss = events.active_boss()
            # boss bildirimi sadece doğumdan sonraki ilk 20 dakikada
            if boss and now - boss["spawn_ts"] < 20 * 60:
                boss_id = boss["id"]
        except Exception:
            boss_id = 0
        budget = config.NOTIFY_MAX_PER_PASS
        served: set = set()
        for kind in ORDER:
            if budget <= 0:
                break
            if kind == "boss" and not boss_id:
                continue
            for user_id in _candidates(kind, now, budget):
                if user_id in served:
                    continue                            # bir turda kişiye tek mesaj
                if not _extra_ok(kind, user_id, now, boss_id):
                    continue
                lang = i18n.lang_of(user_id)
                text = i18n.t(lang, KINDS[kind][1], **_fields(kind, user_id))
                if await send(context, user_id, kind, text):
                    served.add(user_id)
                    budget -= 1
                    await asyncio.sleep(config.NOTIFY_PACE)
                if budget <= 0:
                    break
    except Exception:
        log.exception("bildirim taraması hatası")


# ---------------------------------------------------------------------------
# GERİ DÖNÜŞ HEDİYESİ
# ---------------------------------------------------------------------------

def comeback_gift(user_id: int, tier: int) -> str:
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    now = ui.now()
    if user is None:
        return i18n.t(lang, "nt_gift_none")
    if user["notify_back"] <= user["notify_gift"]:
        return i18n.t(lang, "nt_gift_none")             # bekleyen teklif yok
    if now - user["notify_back"] > 48 * 3600:
        return i18n.t(lang, "nt_gift_late")
    coins, gems = GIFTS.get(tier, GIFTS[3])
    economy.add_coins(user_id, coins, "geri dönüş hediyesi")
    economy.add_gems(user_id, gems, "geri dönüş hediyesi")
    db.upd(user_id, notify_gift=now, energy=economy.max_energy(user["level"]), energy_ts=now)
    return i18n.t(lang, "nt_gift_ok", coins=ui.fmt(coins), gems=gems)


# ---------------------------------------------------------------------------
# AYAR EKRANI
# ---------------------------------------------------------------------------

def settings_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    on = user is not None and user["notify_on"] == 1
    count, _sent = _roll_day(user, war.day_key()) if user else (0, set())
    state = i18n.t(lang, "nt_state_on") if on else i18n.t(lang, "nt_state_off")
    if user is not None and user["notify_on"] == 2:
        state = i18n.t(lang, "nt_state_blocked")
    types = "\n".join(f"• {i18n.t(lang, f'nt_type_{k}')}" for k in ORDER)
    return (f"{i18n.t(lang, 'nt_title')}\n{ui.LINE}\n"
            f"<blockquote>{state}\n"
            f"{i18n.t(lang, 'nt_today')}: <b>{count}</b>/{config.NOTIFY_MAX_PER_DAY}</blockquote>\n\n"
            f"<b>{i18n.t(lang, 'nt_types')}</b>\n<blockquote>{types}</blockquote>\n\n"
            + i18n.t(lang, "nt_limits", max=config.NOTIFY_MAX_PER_DAY,
                     gap=config.NOTIFY_MIN_GAP // 3600,
                     start=config.NOTIFY_QUIET_START, end=config.NOTIFY_QUIET_END))


def settings_kb(user_id: int):
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    on = user is not None and user["notify_on"] == 1
    toggle = (i18n.t(lang, "nt_b_off"), "nt:off") if on else (i18n.t(lang, "nt_b_on"), "nt:on")
    return ui.kb([[toggle], [(i18n.t(lang, "b_home"), "m:main")]])


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    if not ui.is_private(update):
        await ui.answer(query, i18n.t(lang, "only_private"), alert=True)
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    context.user_data["_toast"] = i18n.t(lang, "nt_toast")

    if action == "on":
        db.upd(user_id, notify_on=1)
        await ui.answer(query, i18n.t(lang, "nt_turned_on"), alert=True)
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "off":
        db.upd(user_id, notify_on=0)
        await ui.answer(query, i18n.t(lang, "nt_turned_off"), alert=True)
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    elif action == "gift":
        tier = int(parts[2]) if len(parts) > 2 else 3
        msg = comeback_gift(user_id, tier)
        await ui.answer(query, msg, alert=True)
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))
    else:
        await ui.safe_edit(query, settings_text(user_id), settings_kb(user_id))


async def cmd_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.send(update, settings_text(user_id), settings_kb(user_id))
