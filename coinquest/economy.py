# -*- coding: utf-8 -*-
"""Ekonomi çekirdeği: para hareketleri, seviye/XP, enerji, savaş gücü ve bonuslar."""
import random
import sqlite3
import time
from typing import Optional

import config
import db
import items

LEVEL_TITLES = [
    (1, "Çaylak Gezgin"), (5, "Maden İşçisi"), (10, "Kılıç Ustası"), (15, "Arena Savaşçısı"),
    (20, "Ejder Avcısı"), (25, "Efsane Tüccar"), (30, "Boşluk Lordu"), (40, "Diyar Kralı"),
]


# ---------------- para ----------------

def coins(user_id: int) -> int:
    return int(db.scalar("SELECT coins FROM users WHERE user_id=?", (user_id,)))


def add_coins(user_id: int, amount: int, reason: str = "") -> int:
    amount = int(amount)
    if amount == 0:
        return coins(user_id)
    db.run("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
    if amount > 0:
        db.run("UPDATE users SET earned=earned+? WHERE user_id=?", (amount, user_id))
    db.log_tx(user_id, amount, reason)
    return coins(user_id)


def take_coins(user_id: int, amount: int, reason: str = "") -> bool:
    """Yeterli bakiye varsa düşer ve True döner."""
    amount = int(amount)
    if amount <= 0:
        return True
    cur = db.run(
        "UPDATE users SET coins=coins-? WHERE user_id=? AND coins>=?",
        (amount, user_id, amount),
    )
    if cur.rowcount:
        db.log_tx(user_id, -amount, reason)
        return True
    return False


def add_gems(user_id: int, amount: int, reason: str = "") -> None:
    db.run("UPDATE users SET gems=gems+? WHERE user_id=?", (int(amount), user_id))
    db.log_tx(user_id, 0, f"{reason} ({amount:+d}💎)")


def take_gems(user_id: int, amount: int, reason: str = "") -> bool:
    cur = db.run(
        "UPDATE users SET gems=gems-? WHERE user_id=? AND gems>=?",
        (int(amount), user_id, int(amount)),
    )
    if cur.rowcount:
        db.log_tx(user_id, 0, f"{reason} (-{amount}💎)")
        return True
    return False


# ---------------- seviye / XP ----------------

def xp_needed(level: int) -> int:
    return int(110 + 55 * (level ** 1.42))


def add_xp(user_id: int, amount: int) -> dict:
    """XP ekler, gerekirse seviye atlatır. Sonuç özetini döner."""
    user = db.get_user(user_id)
    if user is None:
        return {"levels": 0}
    amount = int(amount * (1 + xp_bonus(user)))
    xp = user["xp"] + amount
    level = user["level"]
    gained = 0
    coin_reward = 0
    gem_reward = 0
    while xp >= xp_needed(level) and level < 100:
        xp -= xp_needed(level)
        level += 1
        gained += 1
        coin_reward += 900 + level * 260
        if level % 5 == 0:
            gem_reward += 2
    db.upd(user_id, xp=xp, level=level)
    if gained:
        title = title_for(level)
        db.upd(user_id, title=title)
        add_coins(user_id, coin_reward, "seviye ödülü")
        if gem_reward:
            add_gems(user_id, gem_reward, "seviye ödülü")
        db.upd(user_id, energy=max_energy(level), energy_ts=int(time.time()))
    return {
        "levels": gained, "level": level, "xp": xp, "need": xp_needed(level),
        "gained_xp": amount, "coins": coin_reward, "gems": gem_reward,
    }


def title_for(level: int) -> str:
    title = LEVEL_TITLES[0][1]
    for lv, name in LEVEL_TITLES:
        if level >= lv:
            title = name
    return title


# ---------------- enerji ----------------

def max_energy(level: int) -> int:
    return min(120, config.ENERGY_MAX_BASE + level * 2)


def sync_energy(user_id: int) -> int:
    user = db.get_user(user_id)
    if user is None:
        return 0
    mx = max_energy(user["level"])
    if user["energy_unlim"]:
        if user["energy"] < mx:
            db.upd(user_id, energy=mx, energy_ts=int(time.time()))
        return mx
    now = int(time.time())
    if user["energy"] >= mx:
        db.upd(user_id, energy=mx, energy_ts=now)
        return mx
    gain = (now - user["energy_ts"]) // config.ENERGY_REGEN_SEC
    if gain <= 0:
        return user["energy"]
    new = min(mx, user["energy"] + int(gain))
    new_ts = now if new >= mx else user["energy_ts"] + int(gain) * config.ENERGY_REGEN_SEC
    db.upd(user_id, energy=new, energy_ts=new_ts)
    return new


def spend_energy(user_id: int, amount: int) -> bool:
    user = db.get_user(user_id)
    if user and user["energy_unlim"]:
        return True
    sync_energy(user_id)
    cur = db.run(
        "UPDATE users SET energy=energy-? WHERE user_id=? AND energy>=?",
        (amount, user_id, amount),
    )
    return bool(cur.rowcount)


def add_energy(user_id: int, amount: int) -> None:
    user = db.get_user(user_id)
    if not user:
        return
    db.upd(user_id, energy=min(max_energy(user["level"]), user["energy"] + amount))


# ---------------- bonuslar ----------------

def _equipped(user: sqlite3.Row, slot: str) -> Optional[tuple[dict, int]]:
    inv_id = user[slot]
    if not inv_id:
        return None
    row = db.inv_get(inv_id, user["user_id"])
    if not row:
        return None
    item = items.get(row["item_key"])
    if not item:
        return None
    return item, row["item_lvl"]


def pet_bonus(user: sqlite3.Row, field: str) -> float:
    eq = _equipped(user, "pet_id")
    if not eq:
        return 0.0
    return float(eq[0].get("bonus", {}).get(field, 0))


def income_bonus(user: sqlite3.Row) -> float:
    """Oyun kazançlarına eklenen çarpan (0.15 = +%15)."""
    return pet_bonus(user, "income") + min(0.10, user["level"] * 0.002) + clan_bonus(user)


def xp_bonus(user: sqlite3.Row) -> float:
    bonus = pet_bonus(user, "xp")
    if user["xpboost_until"] > time.time():
        bonus += 1.0
    return bonus


def luck(user: sqlite3.Row) -> float:
    val = pet_bonus(user, "luck")
    if user["luck_until"] > time.time():
        val += 0.12
    return min(0.45, val)


def power(user: sqlite3.Row) -> dict:
    """Savaş istatistikleri."""
    atk = 12 + user["level"] * 3
    dfn = 6 + user["level"] * 2
    hp = 110 + user["level"] * 14
    crit = 0.10
    weapon = _equipped(user, "weapon_id")
    if weapon:
        atk += items.stat_at(weapon[0], weapon[1], "atk")
        if weapon[0]["key"] == "w_dagger":
            crit += 0.08
        if weapon[0]["key"] == "w_scythe":
            crit += 0.12
    armor = _equipped(user, "armor_id")
    if armor:
        dfn += items.stat_at(armor[0], armor[1], "dfn")
        hp += items.stat_at(armor[0], armor[1], "dfn") * 2
    atk += int(pet_bonus(user, "atk"))
    crit += luck(user) * 0.25
    return {"atk": atk, "dfn": dfn, "hp": hp, "crit": min(0.6, crit)}


def max_bet(user: sqlite3.Row) -> int:
    return min(config.BET_CAP_MAX, 5_000 + user["level"] * config.BET_CAP_BASE)


def payout(user: sqlite3.Row, amount: int) -> int:
    """Kazanca evcil hayvan/seviye bonusunu uygular."""
    if amount <= 0:
        return 0
    return int(amount * (1 + income_bonus(user)))


def register_game(user_id: int, bet: int, won: int) -> None:
    profit = won - bet
    db.bump(user_id, games=1, wagered=bet)
    if profit > 0:
        db.bump(user_id, wins=1)
        cur_best = int(db.scalar("SELECT biggest_win FROM users WHERE user_id=?", (user_id,)))
        if profit > cur_best:
            db.upd(user_id, biggest_win=profit)
    elif profit < 0:
        db.bump(user_id, losses=1)


# ---------------- klan ----------------

def clan_bonus(user: sqlite3.Row) -> float:
    if not user["clan_id"]:
        return 0.0
    lvl = int(db.scalar("SELECT level FROM clans WHERE id=?", (user["clan_id"],), 1))
    return min(0.20, 0.02 * lvl)


def clan_add_xp(clan_id: int, amount: int) -> None:
    if not clan_id:
        return
    row = db.one("SELECT * FROM clans WHERE id=?", (clan_id,))
    if not row:
        return
    xp = row["xp"] + amount
    level = row["level"]
    while xp >= 5_000 * level and level < 20:
        xp -= 5_000 * level
        level += 1
    db.run("UPDATE clans SET xp=?, level=? WHERE id=?", (xp, level, clan_id))


# ---------------- yardımcılar ----------------

def cooldown_left(last_ts: int, cooldown: int) -> int:
    left = last_ts + cooldown - int(time.time())
    return max(0, left)


def roll(chance: float) -> bool:
    return random.random() < chance
