# -*- coding: utf-8 -*-
"""Klan Savaşı ve haftalık sezon.

Oyuncular zaten yaptıkları işlerden (oyun, PVP, boss, görev, bağış...) sezon
puanı kazanır. Puan hem kişisel haftalık sıralamayı hem de klanının savaş
puanını besler. Pazartesi 00:00'da (Aşgabat saati) hafta kapanır, ilk 3 oyuncu
ve ilk 3 klan ödül alır.

Bu modül `social` veya `events` modüllerini üst seviyede import ETMEZ
(events -> war zinciri var, döngü olur). Klan tablolarını doğrudan okur.
"""
import asyncio
import datetime as dt
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import ui

log = logging.getLogger(__name__)

# Aşgabat: 1991'den beri sabit +05, yaz saati yok. zoneinfo/tzdata gerektirmez.
TZ = dt.timezone(dt.timedelta(hours=5))

STAR = "⭐"


# ---------------------------------------------------------------------------
# ZAMAN
# ---------------------------------------------------------------------------

def week_key(ts: int = None) -> str:
    """Haftanın kimliği: '2026-W34'. ISO hafta, pazartesi başlar, UTC+5."""
    moment = dt.datetime.fromtimestamp(ts if ts is not None else ui.now(), TZ)
    year, week, _day = moment.isocalendar()
    return f"{year}-W{week:02d}"        # sıfır dolgusu: sözlük sırası = kronolojik sıra


def day_key(ts: int = None) -> str:
    """Günün kimliği: '2026-08-19' (UTC+5)."""
    return dt.datetime.fromtimestamp(ts if ts is not None else ui.now(), TZ).strftime("%Y-%m-%d")


def local_hour(ts: int = None) -> int:
    return dt.datetime.fromtimestamp(ts if ts is not None else ui.now(), TZ).hour


def week_bounds(week: str) -> tuple[int, int]:
    """Haftanın başlangıç/bitiş zaman damgası. Bozuk anahtarda (0, 0)."""
    try:
        year, num = week.split("-W")
        start = dt.datetime.fromisocalendar(int(year), int(num), 1).replace(tzinfo=TZ)
        return int(start.timestamp()), int((start + dt.timedelta(days=7)).timestamp())
    except (ValueError, TypeError):
        return 0, 0


def seconds_left(ts: int = None) -> int:
    """Sezonun bitmesine kaç saniye kaldı."""
    now = ts if ts is not None else ui.now()
    _start, end = week_bounds(week_key(now))
    return max(0, end - now) if end else 0


# ---------------------------------------------------------------------------
# PUAN KAYNAKLARI
# ---------------------------------------------------------------------------
# src -> (puan, bölen, günlük tavan)
#   bölen 0  -> her olay için sabit puan
#   bölen >0 -> puan = miktar // bölen   (bahis, bağış)
SRC = {
    "play":    (2, 0, 120),
    "win":     (3, 0, 90),
    "wager":   (1, 10_000, 60),
    "pvp":     (15, 0, 90),
    "boss":    (6, 0, 90),
    "work":    (5, 0, 50),
    "mine":    (5, 0, 50),
    "skill":   (4, 0, 60),
    "arena":   (4, 0, 60),
    "buy":     (3, 0, 15),
    "upgrade": (5, 0, 25),
    "quest":   (15, 0, 45),
    "daily":   (40, 0, 40),
    "miner":   (10, 0, 40),
    "biz":     (8, 0, 32),
    "donate":  (1, 100_000, 100),
    "ref":     (50, 0, 150),
}

# Ekranda gösterim sırası ve adı
SRC_NAMES = [
    ("play", "🎮"), ("win", "🏅"), ("wager", "💰"), ("pvp", "⚔️"), ("boss", "🐉"),
    ("work", "💼"), ("mine", "⛏"), ("skill", "🧠"), ("arena", "🗡"), ("buy", "🏪"),
    ("upgrade", "🔨"), ("quest", "📜"), ("daily", "🎁"), ("miner", "🏭"), ("biz", "🏬"),
    ("donate", "💝"), ("ref", "👥"),
]


def add(user_id: int, src: str, amount: int = 1) -> int:
    """Sezon puanı ekler, günlük tavanı uygular. Eklenen puanı döner.

    Asla hata fırlatmaz — savaş muhasebesi bir oyun turunu bozmamalı.
    """
    try:
        spec = SRC.get(src)
        if not spec or user_id <= 0 or amount <= 0:
            return 0
        points, divisor, cap = spec
        raw = amount // divisor if divisor else points * amount
        if raw <= 0:
            return 0
        user = db.get_user(user_id)
        if user is None or user["banned"]:
            return 0
        day = day_key()
        spent = int(db.scalar("SELECT points FROM war_daily WHERE day=? AND user_id=? AND src=?",
                              (day, user_id, src), 0))
        gained = min(raw, cap - spent)
        if gained <= 0:
            return 0
        week = week_key()
        db.run("INSERT INTO war_daily (day, user_id, src, points) VALUES (?,?,?,?) "
               "ON CONFLICT(day, user_id, src) DO UPDATE SET points=points+?",
               (day, user_id, src, gained, gained))
        db.run("INSERT INTO war_points (week, user_id, points) VALUES (?,?,?) "
               "ON CONFLICT(week, user_id) DO UPDATE SET points=points+?",
               (week, user_id, gained, gained))
        clan_id = user["clan_id"]
        if clan_id:
            db.run("INSERT INTO war_clan (week, clan_id, user_id, points) VALUES (?,?,?,?) "
                   "ON CONFLICT(week, clan_id, user_id) DO UPDATE SET points=points+?",
                   (week, clan_id, user_id, gained, gained))
        return gained
    except Exception as exc:            # savaş puanı asla oyunu bozmamalı
        log.warning("savaş puanı hatası (%s/%s): %s", user_id, src, exc)
        return 0


# ---------------------------------------------------------------------------
# OKUMA
# ---------------------------------------------------------------------------

def _week(week: str = "") -> str:
    return week or week_key()


def my_points(user_id: int, week: str = "") -> int:
    return int(db.scalar("SELECT points FROM war_points WHERE week=? AND user_id=?",
                         (_week(week), user_id), 0))


def my_rank(user_id: int, week: str = "") -> int:
    """1'den başlayan sıra. Puanı yoksa 0."""
    mine = my_points(user_id, week)
    if mine <= 0:
        return 0
    hidden = db.hidden_ids()
    marks = ",".join("?" * len(hidden)) if hidden else "0"
    return int(db.scalar(
        f"SELECT COUNT(*)+1 FROM war_points WHERE week=? AND points>? AND user_id NOT IN ({marks})",
        [_week(week), mine] + hidden, 1))


def my_breakdown(user_id: int, day: str = "") -> list[tuple[str, str, int, int]]:
    """(kaynak, emoji, bugün kazanılan, günlük tavan) listesi."""
    day = day or day_key()
    rows = {r["src"]: r["points"] for r in
            db.all_("SELECT src, points FROM war_daily WHERE day=? AND user_id=?", (day, user_id))}
    return [(src, emoji, rows.get(src, 0), SRC[src][2]) for src, emoji in SRC_NAMES]


def clan_points(clan_id: int, week: str = "") -> int:
    return int(db.scalar("SELECT COALESCE(SUM(points),0) FROM war_clan WHERE week=? AND clan_id=?",
                         (_week(week), clan_id), 0))


def clan_board(week: str = "", limit: int = 10, offset: int = 0) -> list[dict]:
    rows = db.all_(
        "SELECT w.clan_id AS clan_id, SUM(w.points) AS pts, c.name AS name, "
        "       c.emblem AS emblem, c.level AS level, c.wins AS wins "
        "  FROM war_clan w JOIN clans c ON c.id = w.clan_id "
        " WHERE w.week=? GROUP BY w.clan_id HAVING pts > 0 "
        " ORDER BY pts DESC, c.level DESC LIMIT ? OFFSET ?",
        (_week(week), limit, offset))
    return [dict(r) for r in rows]


def clan_rank(clan_id: int, week: str = "") -> int:
    mine = clan_points(clan_id, week)
    if mine <= 0:
        return 0
    return int(db.scalar(
        "SELECT COUNT(*)+1 FROM (SELECT clan_id, SUM(points) p FROM war_clan "
        "WHERE week=? GROUP BY clan_id HAVING p > ?)", (_week(week), mine), 1))


def clan_count(week: str = "") -> int:
    return int(db.scalar("SELECT COUNT(*) FROM (SELECT clan_id FROM war_clan WHERE week=? "
                         "GROUP BY clan_id HAVING SUM(points) > 0)", (_week(week),), 0))


def player_board(week: str = "", limit: int = 10, offset: int = 0) -> list[dict]:
    """Kişisel sıralama. Yetkililer gizlidir (ödeme de buradan yapılır)."""
    hidden = db.hidden_ids()
    marks = ",".join("?" * len(hidden)) if hidden else "0"
    rows = db.all_(
        f"SELECT w.user_id AS user_id, w.points AS pts, u.first_name AS name, "
        f"       u.level AS level, u.clan_id AS clan_id "
        f"  FROM war_points w JOIN users u ON u.user_id = w.user_id "
        f" WHERE w.week=? AND w.points>0 AND u.banned=0 AND w.user_id NOT IN ({marks}) "
        f" ORDER BY w.points DESC, u.level DESC LIMIT ? OFFSET ?",
        [_week(week)] + hidden + [limit, offset])
    return [dict(r) for r in rows]


def contributors(clan_id: int, week: str = "", limit: int = 5) -> list[dict]:
    rows = db.all_(
        "SELECT w.user_id AS user_id, w.points AS pts, u.first_name AS name "
        "  FROM war_clan w LEFT JOIN users u ON u.user_id = w.user_id "
        " WHERE w.week=? AND w.clan_id=? AND w.points>0 "
        " ORDER BY w.points DESC LIMIT ?", (_week(week), clan_id, limit))
    return [dict(r) for r in rows]


def rival_above(clan_id: int, week: str = "") -> dict | None:
    """Bir üst sıradaki klan ve aradaki fark. Birinciysen None."""
    mine = clan_points(clan_id, week)
    row = db.one(
        "SELECT w.clan_id AS clan_id, SUM(w.points) AS pts, c.name AS name, c.emblem AS emblem "
        "  FROM war_clan w JOIN clans c ON c.id = w.clan_id "
        " WHERE w.week=? AND w.clan_id<>? GROUP BY w.clan_id HAVING pts > ? "
        " ORDER BY pts ASC LIMIT 1", (_week(week), clan_id, mine))
    if row is None:
        return None
    out = dict(row)
    out["gap"] = out["pts"] - mine
    return out


def rival_below(clan_id: int, week: str = "") -> dict | None:
    """Birinci isen: arkandaki takipçi."""
    mine = clan_points(clan_id, week)
    row = db.one(
        "SELECT w.clan_id AS clan_id, SUM(w.points) AS pts, c.name AS name, c.emblem AS emblem "
        "  FROM war_clan w JOIN clans c ON c.id = w.clan_id "
        " WHERE w.week=? AND w.clan_id<>? GROUP BY w.clan_id HAVING pts <= ? "
        " ORDER BY pts DESC LIMIT 1", (_week(week), clan_id, mine))
    if row is None:
        return None
    out = dict(row)
    out["gap"] = mine - out["pts"]
    return out


def _clan_of(user_id: int):
    """social.clan_of'un import etmeden çalışan kopyası (döngü olmasın)."""
    user = db.get_user(user_id)
    if user is None or not user["clan_id"]:
        return None
    return db.one("SELECT * FROM clans WHERE id=?", (user["clan_id"],))


# ---------------------------------------------------------------------------
# ÖDÜLLER
# ---------------------------------------------------------------------------
# (coin, elmas, TMT kuruş)
# Sadece ilk 3 ödül alır. Ödül az sayıda kişiye gitsin ki değerli olsun.
PLAYER_REWARDS = [
    (120_000, 12, config.WAR_TMT_1),
    (60_000, 6, config.WAR_TMT_2),
    (30_000, 3, config.WAR_TMT_3),
]
PLAYER_MIN = 300                # ödül için en az bu kadar puan gerekir
PARTICIPATION_MIN = 0           # katılım ödülü yok
PARTICIPATION_COINS = 0

# (klan kasası, üyelere dağıtılacak havuz, ilk 3 katkıcıya elmas)
CLAN_REWARDS = [
    (80_000, 100_000, (10, 6, 3)),
    (40_000, 50_000, (6, 3, 2)),
    (20_000, 25_000, (3, 2, 1)),
]


# ---------------------------------------------------------------------------
# EKRANLAR
# ---------------------------------------------------------------------------

def war_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    week = week_key()
    clan = _clan_of(user_id)
    left = ui.dur(seconds_left())
    head = f"{i18n.t(lang, 'w_title')}\n{ui.LINE}\n"
    if clan is None:
        return (head
                + i18n.t(lang, "w_noclan") + "\n\n"
                + f"<blockquote>{i18n.t(lang, 'w_my_points')}: <b>{ui.fmt(my_points(user_id))}</b> {STAR}"
                  f"\n{i18n.t(lang, 'w_left')}: <b>{left}</b></blockquote>\n\n"
                + i18n.t(lang, "w_join_first"))
    cid = clan["id"]
    pts = clan_points(cid)
    rank = clan_rank(cid)
    total = clan_count()
    top = clan_board(limit=1)
    best = top[0]["pts"] if top else 0
    lines = [head,
             f"{clan['emblem']} <b>{ui.esc(clan['name'])}</b>"
             + (f"   🏆×{clan['wins']}" if clan["wins"] else "") + "\n",
             f"<blockquote>{i18n.t(lang, 'w_rank')}: <b>#{rank or '-'}</b> / {total} "
             f"{i18n.t(lang, 'w_clans')}\n"
             f"{STAR} <b>{ui.fmt(pts)}</b>  {ui.bar(pts, best or 1)}\n"
             f"⏳ {i18n.t(lang, 'w_left')}: <b>{left}</b></blockquote>"]
    rival = rival_above(cid)
    if rival:
        lines.append(f"🔺 {rival['emblem']} <b>{ui.esc(rival['name'])}</b>: "
                     f"{ui.fmt(rival['pts'])} {STAR}\n"
                     + i18n.t(lang, "w_rival_ahead", gap=ui.fmt(rival["gap"])))
    else:
        back = rival_below(cid)
        lines.append(i18n.t(lang, "w_leader")
                     + (f"\n🔻 {back['emblem']} {ui.esc(back['name'])}: "
                        + i18n.t(lang, "w_rival_behind", gap=ui.fmt(back["gap"])) if back else ""))
    tops = contributors(cid, limit=5)
    if tops:
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        rows = "\n".join(
            f"{medals[i]} {ui.esc(row['name'] or '?')} — <b>{ui.fmt(row['pts'])}</b>"
            for i, row in enumerate(tops))
        lines.append(f"👑 <b>{i18n.t(lang, 'w_top_contrib')}</b>\n<blockquote>{rows}</blockquote>")
    mine = my_points(user_id)
    lines.append(i18n.t(lang, "w_my_share", points=ui.fmt(mine)))
    lines.append(i18n.t(lang, "w_prize_teaser"))
    return "\n\n".join(x for x in lines if x)


def war_kb(user_id: int):
    lang = i18n.lang_of(user_id)
    clan = _clan_of(user_id)
    rows = [[(i18n.t(lang, "w_b_board_c"), "w:top:c:0")],
            [(i18n.t(lang, "w_b_board_p"), "w:top:p:0")],
            [(i18n.t(lang, "w_b_me"), "w:me"), (i18n.t(lang, "w_b_rules"), "w:rules")],
            [(i18n.t(lang, "w_b_rewards"), "w:rewards"), (i18n.t(lang, "w_b_last"), "w:last")]]
    if clan is None:
        rows.append([(i18n.t(lang, "w_b_join"), "s:clist:0")])
    else:
        rows.append([(i18n.t(lang, "b_clan"), "s:clan")])
    rows.append([(i18n.t(lang, "b_home"), "m:main")])
    return ui.kb(rows)


PAGE = 10


def board_text(kind: str, page: int = 0, user_id: int = 0) -> str:
    """kind: 'c' klan ligi, 'p' kişisel sıralama."""
    lang = i18n.lang_of(user_id) if user_id else i18n.DEFAULT
    offset = page * PAGE
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    if kind == "c":
        rows = clan_board(limit=PAGE, offset=offset)
        title = i18n.t(lang, "w_board_clan")
        body = [f"{medals[i]} {r['emblem']} <b>{ui.esc(r['name'])}</b> — "
                f"<b>{ui.fmt(r['pts'])}</b> {STAR}" for i, r in enumerate(rows)]
    else:
        rows = player_board(limit=PAGE, offset=offset)
        title = i18n.t(lang, "w_board_player")
        body = [f"{medals[i]} {ui.esc(r['name'] or '?')} — <b>{ui.fmt(r['pts'])}</b> {STAR}"
                for i, r in enumerate(rows)]
    out = [f"{title}\n{ui.LINE}"]
    out.append("\n".join(body) if body else i18n.t(lang, "w_board_empty"))
    out.append(f"<blockquote>⏳ {i18n.t(lang, 'w_left')}: <b>{ui.dur(seconds_left())}</b></blockquote>")
    if user_id:
        if kind == "p":
            rank = my_rank(user_id)
            out.append(i18n.t(lang, "w_you_are", rank=rank or "-", points=ui.fmt(my_points(user_id))))
        else:
            clan = _clan_of(user_id)
            if clan:
                out.append(i18n.t(lang, "w_you_are", rank=clan_rank(clan["id"]) or "-",
                                  points=ui.fmt(clan_points(clan["id"]))))
    return "\n\n".join(out)


def board_kb(kind: str, page: int = 0, user_id: int = 0):
    lang = i18n.lang_of(user_id) if user_id else i18n.DEFAULT
    rows = []
    if kind == "p":                     # oyuncu isimleri profil butonu olur
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        line = []
        for i, r in enumerate(player_board(limit=PAGE, offset=page * PAGE)):
            line.append((f"{medals[i]} {(r['name'] or '?')[:12]}", f"s:pf:{r['user_id']}"))
            if len(line) == 2:
                rows.append(line); line = []
        if line:
            rows.append(line)
    other = "p" if kind == "c" else "c"
    other_label = i18n.t(lang, "w_b_board_p" if other == "p" else "w_b_board_c")
    nav = []
    if page > 0:
        nav.append(("⬅️", f"w:top:{kind}:{page - 1}"))
    nav.append((f"{page + 1}", "w:noop"))
    count = clan_count() if kind == "c" else int(db.scalar(
        "SELECT COUNT(*) FROM war_points WHERE week=? AND points>0", (week_key(),), 0))
    if (page + 1) * PAGE < count:
        nav.append(("➡️", f"w:top:{kind}:{page + 1}"))
    rows += [nav,
             [(other_label, f"w:top:{other}:0")],
             [(i18n.t(lang, "w_b_war"), "w:menu"), (i18n.t(lang, "b_home"), "m:main")]]
    return ui.kb(rows)


def rules_text(lang: str) -> str:
    rows = []
    for src, emoji in SRC_NAMES:
        points, divisor, cap = SRC[src]
        label = i18n.t(lang, f"w_src_{src}")
        value = f"{points} {STAR}" if not divisor else f"{ui.fmt(divisor)} → 1 {STAR}"
        rows.append(f"{emoji} {label} — <b>{value}</b>  <i>({i18n.t(lang, 'w_cap')} {cap})</i>")
    return (f"{i18n.t(lang, 'w_rules_title')}\n{ui.LINE}\n"
            + i18n.t(lang, "w_rules_intro") + "\n\n"
            + "<blockquote>" + "\n".join(rows) + "</blockquote>\n\n"
            + i18n.t(lang, "w_rules_cap"))


def rewards_text(lang: str) -> str:
    lines = [f"{i18n.t(lang, 'w_rewards_title')}\n{ui.LINE}",
             f"<b>{i18n.t(lang, 'w_rewards_player')}</b>"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (coins, gems, tmt) in enumerate(PLAYER_REWARDS):
        extra = f" + <b>{ui.money(tmt)}</b>" if tmt else ""
        lines.append(f"{medals[i]} {ui.fmt(coins)} 🪙 + {gems} 💎{extra}")
    lines.append(i18n.t(lang, "w_rewards_min", points=PLAYER_MIN))
    lines.append(i18n.t(lang, "w_rewards_join", points=PARTICIPATION_MIN,
                        coins=ui.fmt(PARTICIPATION_COINS)))
    lines.append(f"<b>{i18n.t(lang, 'w_rewards_clan')}</b>")
    for i, (treasury, pool, gems) in enumerate(CLAN_REWARDS):
        extra = f" + {i18n.t(lang, 'w_leader_prize', money=ui.money(config.WAR_TMT_CLAN))}" \
            if i == 0 and config.WAR_TMT_CLAN else ""
        lines.append(f"{medals[i]} {i18n.t(lang, 'w_treasury')} {ui.fmt(treasury)} 🪙 • "
                     f"{i18n.t(lang, 'w_pool')} {ui.fmt(pool)} 🪙 • 💎 {'/'.join(map(str, gems))}{extra}")
    return "\n".join(lines)


def me_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    rows = []
    for src, emoji, got, cap in my_breakdown(user_id):
        if got:
            rows.append(f"{emoji} {i18n.t(lang, f'w_src_{src}')} — <b>{got}</b>/{cap}")
    body = "\n".join(rows) if rows else i18n.t(lang, "w_me_none")
    clan = _clan_of(user_id)
    extra = ""
    if clan:
        extra = (f"\n{clan['emblem']} {ui.esc(clan['name'])}: "
                 f"<b>{ui.fmt(clan_points(clan['id']))}</b> {STAR} (#{clan_rank(clan['id']) or '-'})")
    return (f"{i18n.t(lang, 'w_me_title')}\n{ui.LINE}\n"
            f"<blockquote>{i18n.t(lang, 'w_my_points')}: <b>{ui.fmt(my_points(user_id))}</b> {STAR}"
            f"   (#{my_rank(user_id) or '-'}){extra}</blockquote>\n\n"
            f"<b>{i18n.t(lang, 'w_me_today')}</b>\n<blockquote>{body}</blockquote>\n\n"
            + i18n.t(lang, "w_me_hint"))


def last_text(user_id: int = 0) -> str:
    lang = i18n.lang_of(user_id) if user_id else i18n.DEFAULT
    row = db.one("SELECT * FROM war_season WHERE settled=1 AND summary<>'' "
                 "ORDER BY ended_ts DESC LIMIT 1")
    if row is None:
        return f"{i18n.t(lang, 'w_last_title')}\n{ui.LINE}\n{i18n.t(lang, 'w_last_none')}"
    return row["summary"]


# ---------------------------------------------------------------------------
# SEZON KAPANIŞI
# ---------------------------------------------------------------------------

def _summary_html(week: str, players: list[dict], clans: list[dict]) -> str:
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    out = [f"🏁 <b>SEZON BİTTİ — {week}</b>\n{ui.LINE}"]
    if players:
        out.append("🔥 <b>EN İYİ OYUNCULAR</b>\n" + "\n".join(
            f"{medals[i]} {ui.esc(p['name'] or '?')} — <b>{ui.fmt(p['pts'])}</b> {STAR}"
            for i, p in enumerate(players[:5])))
    if clans:
        out.append("⚔️ <b>KLAN SAVAŞI</b>\n" + "\n".join(
            f"{medals[i]} {c['emblem']} {ui.esc(c['name'])} — <b>{ui.fmt(c['pts'])}</b> {STAR}"
            for i, c in enumerate(clans[:3])))
    out.append("🎁 Ödüller dağıtıldı. Yeni sezon başladı — bu hafta sıra sende!")
    return "\n\n".join(out)


def settle(week: str) -> dict:
    """Bir haftayı kapatır ve ödülleri dağıtır. Senkron — testten çağrılabilir.

    Önce 'settled=1' yazılır, ÖNDEN mühürleme sayesinde çift ödeme imkânsızdır.
    Ödeme bloğunda hiç 'await' yoktur; yarıda kesilemez.
    """
    done = db.one("SELECT settled FROM war_season WHERE week=?", (week,))
    if done and done["settled"]:
        return {"skipped": "zaten kapandı", "payout": 0, "winners": []}

    _start, end = week_bounds(week)
    stale = end and (ui.now() - end) > config.WAR_STALE_DAYS * 86400
    players = [] if stale else [p for p in player_board(week, limit=len(PLAYER_REWARDS))
                                if p["pts"] >= PLAYER_MIN]
    clans = [] if stale else clan_board(week, limit=len(CLAN_REWARDS))
    total_players = int(db.scalar("SELECT COUNT(*) FROM war_points WHERE week=? AND points>0",
                                  (week,), 0))
    summary = "" if stale else _summary_html(week, players, clans)

    # 1) ÖNCE MÜHÜRLE
    db.run("INSERT INTO war_season (week, settled, ended_ts, players, top_user, top_clan, summary) "
           "VALUES (?,1,?,?,?,?,?) "
           "ON CONFLICT(week) DO UPDATE SET settled=1, ended_ts=excluded.ended_ts, "
           "players=excluded.players, top_user=excluded.top_user, top_clan=excluded.top_clan, "
           "summary=excluded.summary",
           (week, ui.now(), total_players,
            players[0]["user_id"] if players else 0,
            clans[0]["clan_id"] if clans else 0, summary))
    if stale:
        log.info("sezon %s bayat (%d günden eski) — ödemesiz kapatıldı", week, config.WAR_STALE_DAYS)
        return {"skipped": "bayat", "payout": 0, "winners": []}

    # 2) SONRA ÖDE  (bu blokta await yok!)
    paid = 0
    winners: list[int] = []
    for i, row in enumerate(players):
        coins, gems, tmt = PLAYER_REWARDS[i]
        uid = row["user_id"]
        economy.add_coins(uid, coins, f"haftalık ödül #{i + 1}")
        if gems:
            economy.add_gems(uid, gems, f"haftalık ödül #{i + 1}")
        if tmt:
            _pay_tmt(uid, tmt, f"sezon ödülü #{i + 1}")
        paid += coins
        winners.append(uid)

    if PARTICIPATION_COINS:
        joiners = db.all_("SELECT user_id FROM war_points WHERE week=? AND points>=?",
                          (week, PARTICIPATION_MIN))
        top_ids = {p["user_id"] for p in players}
        for row in joiners:
            uid = row["user_id"]
            if uid in top_ids:
                continue
            economy.add_coins(uid, PARTICIPATION_COINS, "haftalık katılım ödülü")
            paid += PARTICIPATION_COINS

    for i, clan in enumerate(clans):
        treasury, pool, gem_tiers = CLAN_REWARDS[i]
        cid = clan["clan_id"]
        db.run("UPDATE clans SET treasury=treasury+? WHERE id=?", (treasury, cid))
        if i == 0:
            db.run("UPDATE clans SET wins=wins+1 WHERE id=?", (cid,))
        economy.clan_add_xp(cid, treasury // 100)
        members = contributors(cid, week, limit=999)
        total = sum(m["pts"] for m in members) or 1
        for j, member in enumerate(members):
            share = int(pool * member["pts"] / total)
            if share > 0:
                economy.add_coins(member["user_id"], share, f"klan savaşı #{i + 1}")
                paid += share
            if j < 3 and gem_tiers[j]:
                economy.add_gems(member["user_id"], gem_tiers[j], f"klan savaşı #{i + 1}")
            if member["user_id"] not in winners:
                winners.append(member["user_id"])
        if i == 0 and config.WAR_TMT_CLAN:
            leader = db.one("SELECT owner_id FROM clans WHERE id=?", (cid,))
            if leader:
                _pay_tmt(leader["owner_id"], config.WAR_TMT_CLAN, "klan savaşı şampiyonu")

    db.run("UPDATE war_season SET payout=? WHERE week=?", (paid, week))
    log.info("sezon %s kapandı: %d oyuncu, %d altın dağıtıldı", week, total_players, paid)
    return {"payout": paid, "winners": winners, "players": players, "clans": clans,
            "summary": summary}


def _pay_tmt(user_id: int, amount: int, reason: str) -> None:
    """Gerçek para ödülü. Günlük çevirme hakkına (tmt_today) DOKUNMAZ."""
    db.bump(user_id, tmt=amount)
    db.log_tx(user_id, 0, f"{reason} (+{amount / 100:.2f} {config.MONEY_NAME})")


def _cleanup(now: int) -> None:
    db.run("DELETE FROM war_daily WHERE day < ?", (day_key(now - 10 * 86400),))
    db.run("DELETE FROM war_clan WHERE clan_id NOT IN (SELECT id FROM clans)")


async def job_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hafta devrini bekler; devrildiğinde kapanmamış tüm haftaları kapatır."""
    try:
        now = ui.now()
        current = week_key(now)
        seen = db.meta_get("war_week", "")
        if not seen:                                    # ilk çalıştırma: ödül dağıtma
            db.meta_set("war_week", current)
            return
        if seen == current:
            return                                      # tiklerin %99.9'u buradan çıkar
        if local_hour(now) < config.WAR_SETTLE_HOUR:
            return                                      # gece yarısı DM yağdırma
        lock = int(db.meta_get("war_lock", 0) or 0)
        if lock and now - lock < 900:
            return
        db.meta_set("war_lock", now)
        try:
            pending = db.all_(
                "SELECT DISTINCT p.week AS week FROM war_points p "
                "LEFT JOIN war_season s ON s.week = p.week "
                "WHERE p.week <> ? AND COALESCE(s.settled,0)=0 ORDER BY p.week", (current,))
            for row in pending:
                result = settle(row["week"])
                await _announce(context, result)
            db.meta_set("war_week", current)
            _cleanup(now)
        finally:
            db.meta_set("war_lock", 0)
    except Exception:
        log.exception("sezon kapanış hatası")


async def _announce(context: ContextTypes.DEFAULT_TYPE, result: dict) -> None:
    """Kazananlara DM, gruplara özet. Kota dışıdır: haftada bir, sadece kazanana."""
    summary = result.get("summary")
    if not summary:
        return
    for uid in result.get("winners", []):
        try:
            lang = i18n.lang_of(uid)
            await context.bot.send_message(
                uid, summary, parse_mode=ParseMode.HTML,
                reply_markup=ui.kb([[(i18n.t(lang, "w_b_war"), "w:menu")],
                                    [(i18n.t(lang, "b_home"), "m:main")]]))
        except Forbidden:
            db.upd(uid, notify_on=2)
        except Exception:
            pass
        await asyncio.sleep(0.05)
    # Gruplara duyuru YOK: sahibin isteğiyle gruplara sadece boss bildirimi gidiyor.
    # Sezon sonucu kazananlara yukarıda özelden iletildi.


# ---------------------------------------------------------------------------
# BUTONLAR
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
    context.user_data["_toast"] = i18n.t(lang, "w_toast")

    if action == "menu":
        await ui.nav(query, "war", war_text(user_id), war_kb(user_id))
    elif action == "noop":
        await ui.answer(query)
    elif action == "top":
        kind = parts[2] if len(parts) > 2 else "c"
        page = int(parts[3]) if len(parts) > 3 else 0
        await ui.nav(query, "", board_text(kind, page, user_id), board_kb(kind, page, user_id))
    elif action == "me":
        await ui.nav(query, "", me_text(user_id), ui.back_kb("w:menu", i18n.t(lang, "w_b_war"), lang))
    elif action == "rules":
        await ui.nav(query, "", rules_text(lang), ui.back_kb("w:menu", i18n.t(lang, "w_b_war"), lang))
    elif action == "rewards":
        await ui.nav(query, "", rewards_text(lang),
                     ui.back_kb("w:menu", i18n.t(lang, "w_b_war"), lang))
    elif action == "last":
        await ui.nav(query, "", last_text(user_id),
                     ui.back_kb("w:menu", i18n.t(lang, "w_b_war"), lang))
    else:
        await ui.nav(query, "war", war_text(user_id), war_kb(user_id))


async def cmd_war(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.screen(update, "war", war_text(user_id), war_kb(user_id))
