# -*- coding: utf-8 -*-
"""3D Arena — bot tarafı ve savaş motoru.

Oyuncular tarayıcıda 3D arenada gerçek zamanlı dövüşür. Silahı, zırhı, evcil
hayvanı, seviyesi ve ustalıkları BOTTAN gelir — arenada kullandığın ne varsa
bottaki eşyanla aynıdır.

Savaş tamamen SUNUCUDA hesaplanır (Battle sınıfı). Tarayıcı sadece "sağa git",
"vur", "blokla" gibi niyet gönderir; hasarı asla kendisi hesaplamaz. Böylece
hile yapılamaz.

Bu dosya sunucusuz da çalışır (test edilebilir): Battle saf Python'dur.
"""
import logging
import math
import random
import secrets

from telegram import Update
from telegram.ext import ContextTypes

import config
import db
import economy
import i18n
import items
import ui

log = logging.getLogger(__name__)

# --- arena ölçüleri (birim = metre) ---
RADIUS = 12.0             # dairesel arenanın yarıçapı
REACH = 2.6               # vuruş menzili
TICK = 1 / 20             # sunucu 20 kez/saniye hesaplar
MATCH_SECONDS = 90        # süre dolarsa canı çok olan kazanır

BASE_SPEED = 5.2          # m/sn
DASH_SPEED = 13.0
DASH_TIME = 0.18
DASH_COST = 25
ATTACK_COST = 18
ATTACK_WINDUP = 0.22      # vuruş havada geçen süre
ATTACK_RECOVER = 0.30
BLOCK_DRAIN = 22          # blokta saniyede giden dayanıklılık
STAMINA_MAX = 100.0
STAMINA_REGEN = 26.0      # saniyede
BLOCK_CUT = 0.65          # blok hasarın %65'ini keser
BACK_BONUS = 1.35         # arkadan vuruş

STAKES = [0, 1_000, 10_000, 100_000, 1_000_000]


# ---------------------------------------------------------------------------
# GİRİŞ ANAHTARI (tarayıcıda kim olduğunu ispatlar)
# ---------------------------------------------------------------------------

def make_token(user_id: int) -> str:
    """Oyuncuya tek kullanımlık giriş bağlantısı üretir."""
    token = secrets.token_urlsafe(24)
    db.run("DELETE FROM arena_tokens WHERE user_id=?", (user_id,))
    db.run("INSERT INTO arena_tokens (token, user_id, ts) VALUES (?,?,?)",
           (token, user_id, ui.now()))
    return token


def check_token(token: str) -> int:
    """Anahtarı doğrular, kullanıcı numarasını döner. Geçersizse 0."""
    row = db.one("SELECT * FROM arena_tokens WHERE token=?", (token,))
    if not row:
        return 0
    if ui.now() - row["ts"] > config.ARENA_TOKEN_TTL:
        db.run("DELETE FROM arena_tokens WHERE token=?", (token,))
        return 0
    return int(row["user_id"])


def arena_url(user_id: int) -> str:
    base = config.ARENA_URL.rstrip("/")
    return f"{base}/a/{make_token(user_id)}"


# ---------------------------------------------------------------------------
# DÖVÜŞÇÜ
# ---------------------------------------------------------------------------

def loadout(user_id: int) -> dict:
    """Oyuncunun bottaki ekipmanından arena dövüşçüsü üretir."""
    user = db.get_user(user_id)
    if user is None:
        return {}
    stats = economy.power(user)
    weapon = db.inv_get(user["weapon_id"], user_id) if user["weapon_id"] else None
    armor = db.inv_get(user["armor_id"], user_id) if user["armor_id"] else None
    pet = db.inv_get(user["pet_id"], user_id) if user["pet_id"] else None
    w_item = items.get(weapon["item_key"]) if weapon else None
    a_item = items.get(armor["item_key"]) if armor else None
    p_item = items.get(pet["item_key"]) if pet else None
    # Ağır zırh yavaşlatır, hafif zırh hızlandırır (savunma arttıkça hız düşer)
    speed = BASE_SPEED * max(0.72, 1.0 - (stats["dfn"] - 6) * 0.004)
    return {
        "id": user_id,
        "name": (user["first_name"] or "Gezgin")[:16],
        "level": user["level"],
        "hp": float(stats["hp"]),
        "max_hp": float(stats["hp"]),
        "atk": float(stats["atk"]),
        "dfn": float(stats["dfn"]),
        "crit": float(stats["crit"]),
        "speed": speed,
        "weapon": w_item["key"] if w_item else "",
        "weapon_name": (w_item["emoji"] + " " + w_item["name"]) if w_item else "🤜 Yumruk",
        "armor": a_item["key"] if a_item else "",
        "armor_name": (a_item["emoji"] + " " + a_item["name"]) if a_item else "👕 Sade kıyafet",
        "pet": p_item["key"] if p_item else "",
        "pet_name": (p_item["emoji"] + " " + p_item["name"]) if p_item else "",
    }


class Fighter:
    """Arenadaki tek dövüşçünün anlık durumu."""

    def __init__(self, data: dict, angle: float):
        self.d = data
        self.id = data["id"]
        self.x = math.cos(angle) * (RADIUS * 0.55)
        self.z = math.sin(angle) * (RADIUS * 0.55)
        self.yaw = angle + math.pi                 # merkeze bak
        self.hp = data["hp"]
        self.stamina = STAMINA_MAX
        self.state = "idle"                        # idle | attack | block | dash | dead
        self.timer = 0.0                           # mevcut hareketin kalan süresi
        self.did_hit = False                       # bu vuruş hasar verdi mi
        self.dash_x = 0.0
        self.dash_z = 0.0
        self.damage_done = 0.0
        self.hits = 0
        self.blocked = 0
        self.input = {"mx": 0.0, "mz": 0.0, "atk": False, "blk": False, "dash": False}

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def snapshot(self) -> dict:
        return {
            "id": self.id, "x": round(self.x, 2), "z": round(self.z, 2),
            "y": round(self.yaw, 2), "hp": round(max(0.0, self.hp), 1),
            "st": round(self.stamina), "s": self.state,
        }


class Battle:
    """Sunucu tarafı dövüş simülasyonu. Saf Python — testten çağrılabilir."""

    def __init__(self, a: dict, b: dict, stake: int = 0, seed: int | None = None):
        self.rng = random.Random(seed)
        self.a = Fighter(a, 0.0)
        self.b = Fighter(b, math.pi)
        self.stake = stake
        self.time = 0.0
        self.over = False
        self.winner = 0                # 0 = berabere/henüz yok
        self.events: list[dict] = []   # istemciye gidecek efektler (vuruş, blok...)

    def fighters(self):
        return (self.a, self.b)

    def other(self, f: Fighter) -> Fighter:
        return self.b if f is self.a else self.a

    def set_input(self, user_id: int, data: dict) -> None:
        """Tarayıcıdan gelen NİYET. Hasar bilgisi asla kabul edilmez."""
        for f in self.fighters():
            if f.id == user_id:
                mx = float(data.get("mx", 0) or 0)
                mz = float(data.get("mz", 0) or 0)
                length = math.hypot(mx, mz)
                if length > 1.0:                   # hız hilesi engeli
                    mx, mz = mx / length, mz / length
                f.input = {"mx": mx, "mz": mz,
                           "atk": bool(data.get("atk")), "blk": bool(data.get("blk")),
                           "dash": bool(data.get("dash"))}
                return

    # -- simülasyon --------------------------------------------------------
    def step(self, dt: float = TICK) -> None:
        if self.over:
            return
        self.time += dt
        for f in self.fighters():
            self._advance(f, dt)
        for f in self.fighters():
            self._act(f, dt)
        self._separate()
        self._check_end()

    def _advance(self, f: Fighter, dt: float) -> None:
        if not f.alive:
            f.state = "dead"
            return
        if f.timer > 0:
            f.timer -= dt
            if f.timer <= 0:
                f.timer = 0.0
                if f.state in ("attack", "dash"):
                    f.state = "idle"
        # dayanıklılık
        if f.state == "block":
            f.stamina -= BLOCK_DRAIN * dt
            if f.stamina <= 0:
                f.stamina = 0.0
                f.state = "idle"                   # blok kırıldı
        else:
            f.stamina = min(STAMINA_MAX, f.stamina + STAMINA_REGEN * dt)

    def _act(self, f: Fighter, dt: float) -> None:
        if not f.alive:
            return
        inp = f.input
        # atılma
        if f.state == "dash":
            f.x += f.dash_x * DASH_SPEED * dt
            f.z += f.dash_z * DASH_SPEED * dt
            self._clamp(f)
            return
        if f.state == "attack":
            # vuruş anı: hazırlık bittiğinde tek sefer hasar dener
            if not f.did_hit and f.timer <= ATTACK_RECOVER:
                f.did_hit = True
                self._swing(f)
            return
        if inp["dash"] and f.stamina >= DASH_COST and (inp["mx"] or inp["mz"]):
            f.stamina -= DASH_COST
            f.state = "dash"
            f.timer = DASH_TIME
            f.dash_x, f.dash_z = inp["mx"], inp["mz"]
            return
        if inp["atk"] and f.stamina >= ATTACK_COST:
            f.stamina -= ATTACK_COST
            f.state = "attack"
            f.timer = ATTACK_WINDUP + ATTACK_RECOVER
            f.did_hit = False
            self._face_enemy(f)
            return
        if inp["blk"] and f.stamina > 0:
            f.state = "block"
        elif f.state == "block":
            f.state = "idle"
        # yürüme (blokta yavaş)
        if inp["mx"] or inp["mz"]:
            speed = f.d["speed"] * (0.45 if f.state == "block" else 1.0)
            f.x += inp["mx"] * speed * dt
            f.z += inp["mz"] * speed * dt
            f.yaw = math.atan2(inp["mx"], inp["mz"])
            self._clamp(f)

    def _face_enemy(self, f: Fighter) -> None:
        e = self.other(f)
        f.yaw = math.atan2(e.x - f.x, e.z - f.z)

    def _clamp(self, f: Fighter) -> None:
        dist = math.hypot(f.x, f.z)
        if dist > RADIUS - 0.6:
            k = (RADIUS - 0.6) / dist
            f.x *= k
            f.z *= k

    def _separate(self) -> None:
        """İki dövüşçü iç içe geçmesin."""
        dx, dz = self.b.x - self.a.x, self.b.z - self.a.z
        dist = math.hypot(dx, dz)
        min_d = 1.25
        if 0 < dist < min_d:
            push = (min_d - dist) / 2
            ux, uz = dx / dist, dz / dist
            self.a.x -= ux * push
            self.a.z -= uz * push
            self.b.x += ux * push
            self.b.z += uz * push
            self._clamp(self.a)
            self._clamp(self.b)

    def _swing(self, f: Fighter) -> None:
        """Vuruşu çözer. Menzil ve açı tutuyorsa hasar verir."""
        e = self.other(f)
        if not e.alive:
            return
        dx, dz = e.x - f.x, e.z - f.z
        dist = math.hypot(dx, dz)
        if dist > REACH:
            self.events.append({"e": "miss", "id": f.id})
            return
        # önündeki 120 derecelik yayda mı
        aim = math.atan2(dx, dz)
        diff = abs((aim - f.yaw + math.pi) % (2 * math.pi) - math.pi)
        if diff > math.radians(60):
            self.events.append({"e": "miss", "id": f.id})
            return

        atk = f.d["atk"] * self.rng.uniform(0.88, 1.12)
        crit = self.rng.random() < f.d["crit"]
        if crit:
            atk *= 2.0
        # arkadan vuruş
        back = abs((aim - e.yaw + math.pi) % (2 * math.pi) - math.pi) < math.radians(70)
        if back:
            atk *= BACK_BONUS
        # savunma: azalan verim (zırh asla %100 kesmez)
        reduce = e.d["dfn"] / (e.d["dfn"] + 120.0)
        dmg = atk * (1.0 - reduce)
        blocked = False
        if e.state == "block" and not back:
            dmg *= (1.0 - BLOCK_CUT)
            e.stamina = max(0.0, e.stamina - 18)
            blocked = True
            e.blocked += 1
        dmg = max(1.0, dmg)
        e.hp -= dmg
        f.damage_done += dmg
        f.hits += 1
        self.events.append({"e": "hit", "id": f.id, "to": e.id, "d": round(dmg, 1),
                            "crit": crit, "blk": blocked, "back": back})
        if e.hp <= 0:
            e.hp = 0.0
            e.state = "dead"

    def _check_end(self) -> None:
        if not self.a.alive or not self.b.alive:
            self.over = True
            self.winner = self.a.id if self.a.alive else (self.b.id if self.b.alive else 0)
            return
        if self.time >= MATCH_SECONDS:
            self.over = True
            ra = self.a.hp / max(1.0, self.a.d["max_hp"])
            rb = self.b.hp / max(1.0, self.b.d["max_hp"])
            if abs(ra - rb) < 0.02:
                self.winner = 0                     # berabere
            else:
                self.winner = self.a.id if ra > rb else self.b.id

    def snapshot(self) -> dict:
        out = {"t": "s", "tm": round(max(0.0, MATCH_SECONDS - self.time), 1),
               "f": [self.a.snapshot(), self.b.snapshot()]}
        if self.events:
            out["ev"] = self.events[:]
            self.events.clear()
        return out


# ---------------------------------------------------------------------------
# SONUÇ (bot ekonomisine yazar)
# ---------------------------------------------------------------------------

def settle(battle: Battle) -> dict:
    """Dövüş bitince ödülü dağıtır ve istatistikleri yazar."""
    import events as ev_mod
    import war
    a, b = battle.a, battle.b
    stake = battle.stake
    result = {"winner": battle.winner, "stake": stake, "prize": 0}
    if battle.winner == 0:
        for f in (a, b):
            if stake:
                economy.add_coins(f.id, stake, "arena berabere")
        result["draw"] = True
    else:
        loser = b.id if battle.winner == a.id else a.id
        prize = int(stake * 2 * (1 - config.PVP_RAKE)) if stake else 0
        if prize:
            economy.add_coins(battle.winner, prize, "arena kazanç")
        db.bump(battle.winner, pvp_wins=1)
        db.bump(loser, pvp_losses=1)
        economy.add_xp(battle.winner, 90)
        economy.add_xp(loser, 30)
        ev_mod.track(battle.winner, "pvp")
        war.add(battle.winner, "pvp")
        result["prize"] = prize
        result["loser"] = loser
    db.run("INSERT INTO arena_matches (p1, p2, stake, winner, dmg1, dmg2, hits1, hits2, "
           "dur, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
           (a.id, b.id, stake, battle.winner, int(a.damage_done), int(b.damage_done),
            a.hits, b.hits, int(battle.time), ui.now()))
    return result


def take_stake(user_id: int, stake: int) -> bool:
    """Bahsi dövüş BAŞLARKEN alır (eşleşme olmazsa kimseden para gitmez)."""
    if stake <= 0:
        return True
    return economy.take_coins(user_id, stake, "arena bahsi")


def refund(user_id: int, stake: int) -> None:
    if stake > 0:
        economy.add_coins(user_id, stake, "arena iadesi")


def my_stats(user_id: int) -> dict:
    row = db.one(
        "SELECT COUNT(*) AS n, "
        "  SUM(CASE WHEN winner=? THEN 1 ELSE 0 END) AS w, "
        "  SUM(CASE WHEN p1=? THEN dmg1 ELSE dmg2 END) AS dmg "
        "FROM arena_matches WHERE p1=? OR p2=?", (user_id, user_id, user_id, user_id))
    n = int(row["n"] or 0) if row else 0
    w = int(row["w"] or 0) if row else 0
    return {"matches": n, "wins": w, "losses": n - w, "damage": int(row["dmg"] or 0) if row else 0}


# ---------------------------------------------------------------------------
# BOT EKRANI
# ---------------------------------------------------------------------------

def panel_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    user = db.get_user(user_id)
    kit = loadout(user_id)
    st = my_stats(user_id)
    if not config.ARENA_URL:
        return (f"{i18n.t(lang, 'ar_title')}\n{ui.LINE}\n"
                + i18n.t(lang, "ar_offline"))
    return (
        f"{i18n.t(lang, 'ar_title')}\n{ui.LINE}\n"
        f"{ui.header(user)}\n"
        + i18n.t(lang, "ar_intro") + "\n\n"
        f"<blockquote>⚔️ {i18n.t(lang, 'ar_atk')}: <b>{int(kit['atk'])}</b>   "
        f"🛡 {i18n.t(lang, 'ar_dfn')}: <b>{int(kit['dfn'])}</b>\n"
        f"❤️ {i18n.t(lang, 'ar_hp')}: <b>{int(kit['hp'])}</b>   "
        f"💥 {i18n.t(lang, 'ar_crit')}: <b>%{kit['crit'] * 100:.0f}</b>\n"
        f"🏃 {i18n.t(lang, 'ar_speed')}: <b>{kit['speed']:.1f}</b> m/sn</blockquote>\n"
        f"<blockquote>{kit['weapon_name']}\n{kit['armor_name']}"
        + (f"\n{kit['pet_name']}" if kit["pet_name"] else "") + "</blockquote>\n"
        f"<blockquote>🏟 {i18n.t(lang, 'ar_record')}: "
        f"<b>{st['wins']}W</b> / {st['losses']}L  •  "
        f"💢 {ui.fmt(st['damage'])} {i18n.t(lang, 'ar_damage')}</blockquote>"
    )


def panel_kb(user_id: int):
    lang = i18n.lang_of(user_id)
    if not config.ARENA_URL:
        return ui.kb([[(i18n.t(lang, "b_home"), "m:main")]])
    rows = [[(i18n.t(lang, "ar_b_play"), f"url:{arena_url(user_id)}")],
            [(i18n.t(lang, "ar_b_how"), "ar:how"), (i18n.t(lang, "ar_b_top"), "ar:top")],
            [(i18n.t(lang, "b_shop"), "mk:menu"), (i18n.t(lang, "b_items"), "mk:inv")],
            [(i18n.t(lang, "b_home"), "m:main")]]
    return ui.kb(rows)


def how_text(lang: str) -> str:
    return (f"{i18n.t(lang, 'ar_how_title')}\n{ui.LINE}\n"
            + i18n.t(lang, "ar_how_body", secs=MATCH_SECONDS))


def top_text(user_id: int) -> str:
    lang = i18n.lang_of(user_id)
    hidden = db.hidden_ids()
    marks = ",".join("?" * len(hidden)) if hidden else "0"
    rows = db.all_(
        f"SELECT winner AS uid, COUNT(*) AS n FROM arena_matches "
        f"WHERE winner<>0 AND winner NOT IN ({marks}) "
        f"GROUP BY winner ORDER BY n DESC LIMIT 10", hidden)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{i18n.t(lang, 'ar_top_title')}\n{ui.LINE}"]
    for i, row in enumerate(rows):
        u = db.get_user(row["uid"])
        lines.append(f"{medals[i]} {ui.name_of(u)} — <b>{row['n']}</b>W")
    if not rows:
        lines.append(i18n.t(lang, "ar_top_empty"))
    return "\n".join(lines)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    lang = i18n.lang_of(user_id)
    if not ui.is_private(update):
        await ui.answer(query, i18n.t(lang, "only_private"), alert=True)
        return
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "menu"
    context.user_data["_toast"] = i18n.t(lang, "ar_toast")

    if action == "how":
        await ui.nav(query, "", how_text(lang), ui.back_kb("ar:menu", i18n.t(lang, "ar_b_back"), lang))
    elif action == "top":
        await ui.nav(query, "", top_text(user_id),
                     ui.back_kb("ar:menu", i18n.t(lang, "ar_b_back"), lang))
    else:
        await ui.nav(query, "arena", panel_text(user_id), panel_kb(user_id))


async def cmd_arena(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not ui.is_private(update):
        await ui.send(update, i18n.t(i18n.lang_of(user_id), "only_private"), ui.pm_link())
        return
    await ui.screen(update, "arena", panel_text(user_id), panel_kb(user_id))
