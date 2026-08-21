# -*- coding: utf-8 -*-
"""Kalıcı yükseltmeler ("Ustalık").

Oyuncunun biriktirdiği coini harcayacağı KALICI faydalar. Eşya gibi kaybolmaz,
kırılmaz — bir kez alınca sonsuza kadar senindir. Coin için gerçek bir "harcama
yeri" olsun diye var: para biriktirmenin bir anlamı olur.

Yeni yükseltme eklemek için PERKS listesine satır eklemek yeterli.
Bu modül SADECE db/ui/i18n kullanır (economy buradan okur, tersi olmaz).
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import db
import i18n
import ui

log = logging.getLogger(__name__)

#         anahtar     emoji  ad                     max sv  taban fiyat  artış   basamak
PERKS = [
    ("pk_income", "💰", "Kazanç Ustalığı",      10, 50_000,     2.1, "+%2 tüm kazanç"),
    ("pk_miner",  "⛏", "Madenci Deposu",        5, 150_000,    3.0, "+1 döngü (4 saat) depo"),
    ("pk_energy", "⚡", "Enerji Deposu",         8, 40_000,     2.0, "+5 azami enerji"),
    ("pk_regen",  "🔋", "Hızlı Dinlenme",       10, 60_000,     2.2, "enerji 8 sn hızlı dolar"),
    ("pk_bet",    "🎰", "Yüksek Bahis",         10, 80_000,     2.3, "+25.000 bahis limiti"),
    ("pk_bank",   "🏦", "Kasa Genişletme",      10, 45_000,     2.0, "+100.000 banka limiti"),
    ("pk_luck",   "🍀", "Şans Tılsımı",          8, 120_000,    2.6, "+%1 şans"),
    ("pk_xp",     "📘", "Tecrübe Kitabı",       10, 55_000,     2.1, "+%5 tecrübe"),
]
BY_KEY = {p[0]: p for p in PERKS}


def price(key: str, current_lvl: int) -> int:
    """Bir sonraki seviyenin fiyatı. Her seviyede katlanarak artar."""
    spec = BY_KEY.get(key)
    if not spec:
        return 0
    base, growth = spec[4], spec[5]
    return int(base * (growth ** current_lvl))


def level(user_id: int, key: str) -> int:
    return int(db.scalar("SELECT lvl FROM perks WHERE user_id=? AND key=?", (user_id, key), 0))


def levels(user_id: int) -> dict[str, int]:
    return {r["key"]: r["lvl"] for r in
            db.all_("SELECT key, lvl FROM perks WHERE user_id=? AND lvl>0", (user_id,))}


def buy(user_id: int, key: str) -> tuple[bool, str]:
    spec = BY_KEY.get(key)
    lang = i18n.lang_of(user_id)
    if not spec:
        return False, "?"
    _k, emoji, name, max_lvl, _b, _g, effect = spec
    cur = level(user_id, key)
    if cur >= max_lvl:
        return False, i18n.t(lang, "pk_maxed", name=f"{emoji} {name}")
    cost = price(key, cur)
    user = db.get_user(user_id)
    if user is None or user["coins"] < cost:
        return False, i18n.t(lang, "no_money", need=ui.fmt(cost),
                             have=ui.fmt(user["coins"] if user else 0))
    import economy                                   # geç import: döngü olmasın
    if not economy.take_coins(user_id, cost, f"ustalık: {key}"):
        return False, i18n.t(lang, "no_money", need=ui.fmt(cost), have=ui.fmt(user["coins"]))
    db.run("INSERT INTO perks (user_id, key, lvl) VALUES (?,?,1) "
           "ON CONFLICT(user_id, key) DO UPDATE SET lvl=lvl+1", (user_id, key))
    return True, i18n.t(lang, "pk_bought", name=f"{emoji} {name}", lvl=cur + 1, effect=effect)


# ---------------------------------------------------------------------------
# EKRANLAR
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    mine = levels(user_id)
    lines = [f"{i18n.t(lang, 'pk_title')}\n{ui.LINE}", ui.header(user),
             i18n.t(lang, "pk_intro")]
    rows = []
    for key, emoji, name, max_lvl, _b, _g, effect in PERKS:
        lvl = mine.get(key, 0)
        bar = "▮" * lvl + "▫" * (max_lvl - lvl)
        rows.append(f"{emoji} <b>{name}</b>  {bar} {lvl}/{max_lvl}\n    <i>{effect}</i>")
    lines.append("<blockquote>" + "\n".join(rows) + "</blockquote>")
    return "\n\n".join(lines)


def panel_kb(user_id: int):
    lang = i18n.lang_of(user_id)
    mine = levels(user_id)
    rows = []
    for key, emoji, name, max_lvl, _b, _g, _e in PERKS:
        lvl = mine.get(key, 0)
        if lvl >= max_lvl:
            rows.append([(f"{emoji} {name} — MAKS ✅", "pk:noop")])
        else:
            rows.append([(f"{emoji} {name} {lvl}→{lvl + 1}  ({ui.fmt(price(key, lvl))} 🪙)",
                          f"pk:info:{key}")])
    rows.append([(i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


def info_text(user_id: int, key: str) -> str:
    lang = i18n.lang_of(user_id)
    spec = BY_KEY.get(key)
    if not spec:
        return "?"
    _k, emoji, name, max_lvl, _b, _g, effect = spec
    lvl = level(user_id, key)
    user = db.get_user(user_id)
    cost = price(key, lvl)
    toplam = effect_total(key, lvl)
    sonraki = effect_total(key, min(lvl + 1, max_lvl))
    body = (f"<blockquote>{i18n.t(lang, 'pk_level')}: <b>{lvl}</b> / {max_lvl}\n"
            f"{i18n.t(lang, 'pk_now')}: <b>{toplam}</b></blockquote>")
    if lvl >= max_lvl:
        return (f"{emoji} <b>{name}</b>\n{ui.LINE}\n{body}\n\n"
                + i18n.t(lang, "pk_maxed", name=name))
    return (f"{emoji} <b>{name}</b>\n{ui.LINE}\n"
            f"<i>{effect}</i>\n\n{body}\n"
            f"<blockquote>{i18n.t(lang, 'pk_next')}: <b>{sonraki}</b>\n"
            f"{i18n.t(lang, 'pk_cost')}: <b>{ui.fmt(cost)}</b> 🪙\n"
            f"{i18n.t(lang, 'pk_have')}: {ui.fmt(user['coins'])} 🪙</blockquote>")


def effect_total(key: str, lvl: int) -> str:
    """Seviyedeki toplam etkiyi okunur yazıya çevirir."""
    if key == "pk_income":
        return f"+%{lvl * 2} kazanç"
    if key == "pk_miner":
        return f"{1 + lvl} döngü ({(1 + lvl) * 4} saat) depo"
    if key == "pk_energy":
        return f"+{lvl * 5} enerji"
    if key == "pk_regen":
        return f"{max(60, 200 - lvl * 8)} sn'de 1 enerji"
    if key == "pk_bet":
        return f"+{ui.fmt(lvl * 25_000)} bahis limiti"
    if key == "pk_bank":
        return f"+{ui.fmt(lvl * 100_000)} kasa limiti"
    if key == "pk_luck":
        return f"+%{lvl} şans"
    if key == "pk_xp":
        return f"+%{lvl * 5} tecrübe"
    return "—"


def info_kb(user_id: int, key: str):
    lang = i18n.lang_of(user_id)
    spec = BY_KEY.get(key)
    lvl = level(user_id, key)
    rows = []
    if spec and lvl < spec[3]:
        rows.append([(i18n.t(lang, "pk_b_buy", price=ui.fmt(price(key, lvl))), f"pk:buy:{key}")])
    rows.append([(i18n.t(lang, "pk_b_back"), "pk:menu"), (i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    if not ui.is_private(update):
        await ui.answer(query, i18n.t(lang, "only_private"), alert=True)
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    context.user_data["_toast"] = i18n.t(lang, "pk_toast")

    if action == "menu":
        await ui.nav(query, "perks", panel_text(user_id), panel_kb(user_id))
    elif action == "noop":
        await ui.answer(query, i18n.t(lang, "pk_is_max"), alert=True)
    elif action == "info":
        key = parts[2]
        await ui.nav(query, "", info_text(user_id, key), info_kb(user_id, key))
    elif action == "buy":
        key = parts[2]
        # kritik işlem: önce onay ekranı
        spec = BY_KEY.get(key)
        lvl = level(user_id, key)
        if not spec or lvl >= spec[3]:
            await ui.answer(query, i18n.t(lang, "pk_is_max"), alert=True)
            return
        cost = price(key, lvl)
        await ui.answer(query)
        await ui.safe_edit(query, (
            f"⚠️ <b>{i18n.t(lang, 'pk_confirm_title')}</b>\n{ui.LINE}\n"
            f"{spec[1]} <b>{spec[2]}</b>  {lvl} ➜ {lvl + 1}\n"
            f"<blockquote>{i18n.t(lang, 'pk_now')}: {effect_total(key, lvl)}\n"
            f"{i18n.t(lang, 'pk_next')}: <b>{effect_total(key, lvl + 1)}</b>\n"
            f"{i18n.t(lang, 'pk_cost')}: <b>{ui.fmt(cost)}</b> 🪙</blockquote>"
        ), ui.kb([[(i18n.t(lang, "pk_b_yes"), f"pk:ok:{key}")],
                  [(i18n.t(lang, "pk_b_no"), f"pk:info:{key}")]]))
    elif action == "ok":
        key = parts[2]
        done, msg = buy(user_id, key)
        await ui.answer(query, msg.replace("<b>", "").replace("</b>", ""), alert=True)
        await ui.nav(query, "", info_text(user_id, key), info_kb(user_id, key))
    else:
        await ui.nav(query, "perks", panel_text(user_id), panel_kb(user_id))


async def cmd_perks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.screen(update, "perks", panel_text(user_id), panel_kb(user_id))
