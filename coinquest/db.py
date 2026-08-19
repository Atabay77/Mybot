# -*- coding: utf-8 -*-
"""SQLite veri katmanı. Şema oluşturma, kullanıcı yönetimi ve yardımcı sorgular."""
import json
import logging
import sqlite3
import time
from typing import Any, Iterable, Optional

import config

log = logging.getLogger(__name__)
_conn: Optional[sqlite3.Connection] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id      INTEGER PRIMARY KEY,
    username     TEXT DEFAULT '',
    first_name   TEXT DEFAULT '',
    coins        INTEGER NOT NULL DEFAULT 0,
    gems         INTEGER NOT NULL DEFAULT 0,
    bank         INTEGER NOT NULL DEFAULT 0,
    xp           INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 1,
    energy       INTEGER NOT NULL DEFAULT 20,
    energy_ts    INTEGER NOT NULL DEFAULT 0,
    created_ts   INTEGER NOT NULL DEFAULT 0,
    last_seen    INTEGER NOT NULL DEFAULT 0,
    last_daily   INTEGER NOT NULL DEFAULT 0,
    last_hourly  INTEGER NOT NULL DEFAULT 0,
    last_work    INTEGER NOT NULL DEFAULT 0,
    last_mine    INTEGER NOT NULL DEFAULT 0,
    last_rob     INTEGER NOT NULL DEFAULT 0,
    last_skill   INTEGER NOT NULL DEFAULT 0,
    last_bank    INTEGER NOT NULL DEFAULT 0,
    streak       INTEGER NOT NULL DEFAULT 0,
    pickaxe      INTEGER NOT NULL DEFAULT 0,
    shield_until INTEGER NOT NULL DEFAULT 0,
    luck_until   INTEGER NOT NULL DEFAULT 0,
    xpboost_until INTEGER NOT NULL DEFAULT 0,
    weapon_id    INTEGER NOT NULL DEFAULT 0,
    armor_id     INTEGER NOT NULL DEFAULT 0,
    pet_id       INTEGER NOT NULL DEFAULT 0,
    clan_id      INTEGER NOT NULL DEFAULT 0,
    business_key TEXT DEFAULT '',
    business_ts  INTEGER NOT NULL DEFAULT 0,
    wins         INTEGER NOT NULL DEFAULT 0,
    losses       INTEGER NOT NULL DEFAULT 0,
    pvp_wins     INTEGER NOT NULL DEFAULT 0,
    pvp_losses   INTEGER NOT NULL DEFAULT 0,
    games        INTEGER NOT NULL DEFAULT 0,
    wagered      INTEGER NOT NULL DEFAULT 0,
    earned       INTEGER NOT NULL DEFAULT 0,
    biggest_win  INTEGER NOT NULL DEFAULT 0,
    boss_kills   INTEGER NOT NULL DEFAULT 0,
    referrer     INTEGER NOT NULL DEFAULT 0,
    refs         INTEGER NOT NULL DEFAULT 0,
    banned       INTEGER NOT NULL DEFAULT 0,
    title        TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inventory (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    item_lvl INTEGER NOT NULL DEFAULT 0,
    qty      INTEGER NOT NULL DEFAULT 1,
    got_ts   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_inv_user ON inventory(user_id);

CREATE TABLE IF NOT EXISTS bazaar (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    item_key  TEXT NOT NULL,
    item_lvl  INTEGER NOT NULL DEFAULT 0,
    qty       INTEGER NOT NULL DEFAULT 1,
    price     INTEGER NOT NULL,
    created_ts INTEGER NOT NULL DEFAULT 0,
    sold_to   INTEGER NOT NULL DEFAULT 0,
    sold_ts   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_bazaar_open ON bazaar(sold_to, price);

CREATE TABLE IF NOT EXISTS clans (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT UNIQUE NOT NULL,
    owner_id  INTEGER NOT NULL,
    treasury  INTEGER NOT NULL DEFAULT 0,
    level     INTEGER NOT NULL DEFAULT 1,
    xp        INTEGER NOT NULL DEFAULT 0,
    motto     TEXT DEFAULT '',
    open_join INTEGER NOT NULL DEFAULT 1,
    created_ts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clan_requests (
    clan_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    ts      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (clan_id, user_id)
);

CREATE TABLE IF NOT EXISTS clan_members (
    clan_id     INTEGER NOT NULL,
    user_id     INTEGER PRIMARY KEY,
    role        TEXT NOT NULL DEFAULT 'uye',
    contributed INTEGER NOT NULL DEFAULT 0,
    joined_ts   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS duels (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game       TEXT NOT NULL,
    chat_id    INTEGER NOT NULL,
    message_id INTEGER NOT NULL DEFAULT 0,
    p1         INTEGER NOT NULL,
    p2         INTEGER NOT NULL DEFAULT 0,
    stake      INTEGER NOT NULL DEFAULT 0,
    state      TEXT NOT NULL DEFAULT 'open',
    data       TEXT NOT NULL DEFAULT '{}',
    created_ts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_duel_state ON duels(state, created_ts);

CREATE TABLE IF NOT EXISTS boss (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    emoji     TEXT NOT NULL DEFAULT '🐉',
    hp        INTEGER NOT NULL,
    max_hp    INTEGER NOT NULL,
    reward    INTEGER NOT NULL DEFAULT 0,
    active    INTEGER NOT NULL DEFAULT 1,
    spawn_ts  INTEGER NOT NULL DEFAULT 0,
    end_ts    INTEGER NOT NULL DEFAULT 0,
    killer_id INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS boss_hits (
    boss_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    damage  INTEGER NOT NULL DEFAULT 0,
    hits    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (boss_id, user_id)
);

CREATE TABLE IF NOT EXISTS lottery (
    round_no INTEGER PRIMARY KEY,
    pot      INTEGER NOT NULL DEFAULT 0,
    end_ts   INTEGER NOT NULL DEFAULT 0,
    done     INTEGER NOT NULL DEFAULT 0,
    winner   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lottery_tickets (
    round_no INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    tickets  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (round_no, user_id)
);

CREATE TABLE IF NOT EXISTS quests (
    user_id  INTEGER NOT NULL,
    day      TEXT NOT NULL,
    qkey     TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    target   INTEGER NOT NULL DEFAULT 1,
    claimed  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day, qkey)
);

CREATE TABLE IF NOT EXISTS achievements (
    user_id INTEGER NOT NULL,
    akey    TEXT NOT NULL,
    ts      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, akey)
);

CREATE TABLE IF NOT EXISTS tx (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    delta   INTEGER NOT NULL,
    reason  TEXT NOT NULL DEFAULT '',
    ts      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tx_user ON tx(user_id, id);

CREATE TABLE IF NOT EXISTS withdrawals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    amount     INTEGER NOT NULL,
    method     TEXT NOT NULL DEFAULT '',
    details    TEXT NOT NULL DEFAULT '',
    state      TEXT NOT NULL DEFAULT 'bekliyor',
    created_ts INTEGER NOT NULL DEFAULT 0,
    done_ts    INTEGER NOT NULL DEFAULT 0,
    note       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_wd_state ON withdrawals(state, id);

CREATE TABLE IF NOT EXISTS staff (
    user_id  INTEGER PRIMARY KEY,
    role     TEXT NOT NULL DEFAULT 'admin',   -- owner | admin | support
    added_by INTEGER NOT NULL DEFAULT 0,
    ts       INTEGER NOT NULL DEFAULT 0,
    note     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tickets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    state      TEXT NOT NULL DEFAULT 'acik',   -- acik | kapali
    staff_id   INTEGER NOT NULL DEFAULT 0,
    created_ts INTEGER NOT NULL DEFAULT 0,
    last_ts    INTEGER NOT NULL DEFAULT 0,
    unread     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ticket_state ON tickets(state, last_ts);

CREATE TABLE IF NOT EXISTS ticket_msgs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    sender    INTEGER NOT NULL,
    is_staff  INTEGER NOT NULL DEFAULT 0,
    kind      TEXT NOT NULL DEFAULT 'text',
    file_id   TEXT NOT NULL DEFAULT '',
    text      TEXT NOT NULL DEFAULT '',
    ts        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tmsg ON ticket_msgs(ticket_id, id);

CREATE TABLE IF NOT EXISTS broadcasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id   INTEGER NOT NULL,
    src_chat   INTEGER NOT NULL DEFAULT 0,
    src_msg    INTEGER NOT NULL DEFAULT 0,
    kind       TEXT NOT NULL DEFAULT 'text',
    file_id    TEXT NOT NULL DEFAULT '',
    text       TEXT NOT NULL DEFAULT '',
    total      INTEGER NOT NULL DEFAULT 0,
    sent       INTEGER NOT NULL DEFAULT 0,
    failed     INTEGER NOT NULL DEFAULT 0,
    state      TEXT NOT NULL DEFAULT 'bekliyor',
    created_ts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    game       TEXT NOT NULL,
    stake      INTEGER NOT NULL,
    created_ts INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, game, stake)
);
CREATE INDEX IF NOT EXISTS idx_queue_game ON queue(game, stake);

CREATE TABLE IF NOT EXISTS miners (
    user_id INTEGER NOT NULL,
    key     TEXT NOT NULL,
    qty     INTEGER NOT NULL DEFAULT 0,
    got_ts  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS actions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    what    TEXT NOT NULL DEFAULT '',
    detail  TEXT NOT NULL DEFAULT '',
    ts      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_actions ON actions(user_id, id);

CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS groups (
    chat_id  INTEGER PRIMARY KEY,
    title    TEXT DEFAULT '',
    added_ts INTEGER NOT NULL DEFAULT 0
);
"""


def connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


# Sonradan eklenen kullanıcı sütunları (eski veritabanları otomatik güncellenir)
EXTRA_USER_COLUMNS = [
    ("tmt", "INTEGER NOT NULL DEFAULT 0"),          # gerçek para bakiyesi (kuruş: 100 = 1 TMT)
    ("tmt_today", "INTEGER NOT NULL DEFAULT 0"),    # bugün çevrilen miktar
    ("tmt_day", "TEXT NOT NULL DEFAULT ''"),        # bugünün tarihi
    ("tmt_paid", "INTEGER NOT NULL DEFAULT 0"),     # bugüne kadar ödenen toplam
    ("lang", "TEXT NOT NULL DEFAULT 'tk'"),         # dil: tk / ru / tr
    ("captcha_ok", "INTEGER NOT NULL DEFAULT 0"),   # bot koruması geçildi mi
    ("captcha_try", "INTEGER NOT NULL DEFAULT 0"),  # kaç denemede geçti
    ("ref_paid", "INTEGER NOT NULL DEFAULT 0"),     # davet ödülü verildi mi
    ("wd_currency", "TEXT NOT NULL DEFAULT 'TMT'"), # tercih ettiği para birimi
    ("energy_unlim", "INTEGER NOT NULL DEFAULT 0"), # 1 = sınırsız enerji
    ("miner_ts", "INTEGER NOT NULL DEFAULT 0"),     # madenlerden son toplama zamanı
    ("miner_notify", "INTEGER NOT NULL DEFAULT 0"), # 'kasan doldu' bildirimi gitti mi
]


EXTRA_TABLE_COLUMNS = {
    "staff": [("perms", "TEXT NOT NULL DEFAULT ''")],
    "clans": [("emblem", "TEXT NOT NULL DEFAULT '🏰'"),
              ("min_level", "INTEGER NOT NULL DEFAULT 1"),
              ("wins", "INTEGER NOT NULL DEFAULT 0")],
    "withdrawals": [("currency", "TEXT NOT NULL DEFAULT 'TMT'")],
    "broadcasts": [("src_chat", "INTEGER NOT NULL DEFAULT 0"),
                   ("src_msg", "INTEGER NOT NULL DEFAULT 0")],
}


def _migrate() -> None:
    # eski tek satırlık kuyruk tablosunu yenisiyle değiştir
    qcols = {row["name"] for row in all_("PRAGMA table_info(queue)")}
    if qcols and "id" not in qcols:
        run("DROP TABLE queue")
        run("""CREATE TABLE queue (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL, game TEXT NOT NULL,
                   stake INTEGER NOT NULL, created_ts INTEGER NOT NULL DEFAULT 0,
                   UNIQUE (user_id, game, stake))""")
        log.info("Kuyruk tablosu yenilendi (çoklu oyun açma)")
    have = {row["name"] for row in all_("PRAGMA table_info(users)")}
    for name, ddl in EXTRA_USER_COLUMNS:
        if name not in have:
            run(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
            log.info("Veritabanı güncellendi: users.%s eklendi", name)
    for table, cols in EXTRA_TABLE_COLUMNS.items():
        existing = {row["name"] for row in all_(f"PRAGMA table_info({table})")}
        if not existing:
            continue
        for name, ddl in cols:
            if name not in existing:
                run(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                log.info("Veritabanı güncellendi: %s.%s eklendi", table, name)


def init() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate()
    log.info("Veritabanı hazır: %s", config.DB_PATH)


# --- temel sorgu yardımcıları ---

def one(sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    return connect().execute(sql, tuple(params)).fetchone()


def all_(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return connect().execute(sql, tuple(params)).fetchall()


def run(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    conn = connect()
    cur = conn.execute(sql, tuple(params))
    conn.commit()
    return cur


def scalar(sql: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    row = one(sql, params)
    if row is None or row[0] is None:
        return default
    return row[0]


# --- kullanıcı işlemleri ---

def get_user(user_id: int) -> Optional[sqlite3.Row]:
    return one("SELECT * FROM users WHERE user_id=?", (user_id,))


def ensure_user(tg_user, referrer: int = 0) -> sqlite3.Row:
    """Kullanıcı yoksa oluşturur, varsa isim bilgilerini günceller."""
    now = int(time.time())
    row = get_user(tg_user.id)
    if row is None:
        run(
            """INSERT INTO users (user_id, username, first_name, coins, gems, energy,
                    energy_ts, created_ts, last_seen, pickaxe, referrer)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tg_user.id,
                (tg_user.username or "")[:64],
                (tg_user.first_name or "Gezgin")[:64],
                config.START_COINS,
                config.START_GEMS,
                config.ENERGY_MAX_BASE,
                now,
                now,
                now,
                50,
                referrer if referrer and referrer != tg_user.id else 0,
            ),
        )
        log_tx(tg_user.id, config.START_COINS, "başlangıç")
        row = get_user(tg_user.id)
    else:
        run(
            "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
            ((tg_user.username or "")[:64], (tg_user.first_name or "Gezgin")[:64], now, tg_user.id),
        )
    return row


def upd(user_id: int, **fields) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    run(f"UPDATE users SET {sets} WHERE user_id=?", (*fields.values(), user_id))


def bump(user_id: int, **fields) -> None:
    """Alanları artırır (yarış koşullarına karşı SQL içinde toplama)."""
    if not fields:
        return
    sets = ", ".join(f"{k}={k}+?" for k in fields)
    run(f"UPDATE users SET {sets} WHERE user_id=?", (*fields.values(), user_id))


def log_tx(user_id: int, delta: int, reason: str) -> None:
    run(
        "INSERT INTO tx (user_id, delta, reason, ts) VALUES (?,?,?,?)",
        (user_id, int(delta), reason[:64], int(time.time())),
    )


def find_user_by_name(name: str) -> Optional[sqlite3.Row]:
    name = name.strip().lstrip("@")
    if name.isdigit():
        return get_user(int(name))
    return one("SELECT * FROM users WHERE lower(username)=lower(?)", (name,))


# --- meta anahtar/değer ---

def meta_get(key: str, default: Any = None) -> Any:
    row = one("SELECT v FROM meta WHERE k=?", (key,))
    if row is None:
        return default
    try:
        return json.loads(row["v"])
    except (ValueError, TypeError):
        return row["v"]


def meta_set(key: str, value: Any) -> None:
    run(
        "INSERT INTO meta (k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (key, json.dumps(value, ensure_ascii=False)),
    )


# --- envanter ---

def inv_list(user_id: int) -> list[sqlite3.Row]:
    return all_("SELECT * FROM inventory WHERE user_id=? ORDER BY id", (user_id,))


def inv_get(inv_id: int, user_id: Optional[int] = None) -> Optional[sqlite3.Row]:
    if user_id is None:
        return one("SELECT * FROM inventory WHERE id=?", (inv_id,))
    return one("SELECT * FROM inventory WHERE id=? AND user_id=?", (inv_id, user_id))


def inv_add(user_id: int, item_key: str, qty: int = 1, item_lvl: int = 0, stackable: bool = False) -> int:
    """Envantere eşya ekler. Yığınlanabilir eşyalar aynı satırda toplanır."""
    now = int(time.time())
    if stackable:
        row = one(
            "SELECT * FROM inventory WHERE user_id=? AND item_key=? AND item_lvl=0 LIMIT 1",
            (user_id, item_key),
        )
        if row:
            run("UPDATE inventory SET qty=qty+? WHERE id=?", (qty, row["id"]))
            return row["id"]
    cur = run(
        "INSERT INTO inventory (user_id, item_key, item_lvl, qty, got_ts) VALUES (?,?,?,?,?)",
        (user_id, item_key, item_lvl, qty, now),
    )
    return int(cur.lastrowid)


def inv_remove(inv_id: int, qty: int = 1) -> None:
    row = inv_get(inv_id)
    if not row:
        return
    if row["qty"] > qty:
        run("UPDATE inventory SET qty=qty-? WHERE id=?", (qty, inv_id))
    else:
        run("DELETE FROM inventory WHERE id=?", (inv_id,))
        run(
            "UPDATE users SET weapon_id=CASE WHEN weapon_id=? THEN 0 ELSE weapon_id END,"
            " armor_id=CASE WHEN armor_id=? THEN 0 ELSE armor_id END,"
            " pet_id=CASE WHEN pet_id=? THEN 0 ELSE pet_id END WHERE user_id=?",
            (inv_id, inv_id, inv_id, row["user_id"]),
        )


def inv_count(user_id: int, item_key: str) -> int:
    return int(scalar(
        "SELECT COALESCE(SUM(qty),0) FROM inventory WHERE user_id=? AND item_key=?",
        (user_id, item_key),
    ))


# ---------------------------------------------------------------------------
# YETKİLİLER (admin / destek)
# ---------------------------------------------------------------------------

def staff_role(user_id: int) -> str:
    """'owner' / 'admin' / 'support' / '' döner."""
    if user_id in config.ADMIN_IDS:
        return "owner"
    row = one("SELECT role FROM staff WHERE user_id=?", (user_id,))
    return row["role"] if row else ""


def staff_ids(*roles: str) -> list[int]:
    if roles:
        marks = ",".join("?" * len(roles))
        rows = all_(f"SELECT user_id FROM staff WHERE role IN ({marks})", roles)
    else:
        rows = all_("SELECT user_id FROM staff")
    out = [r["user_id"] for r in rows]
    for uid in config.ADMIN_IDS:
        if uid not in out:
            out.append(uid)
    return out


def staff_add(user_id: int, role: str, by: int) -> None:
    run("INSERT INTO staff (user_id, role, added_by, ts) VALUES (?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role", (user_id, role, by, int(time.time())))


def staff_remove(user_id: int) -> None:
    run("DELETE FROM staff WHERE user_id=?", (user_id,))


def hidden_ids() -> list[int]:
    """Sıralamalarda görünmeyecek hesaplar (yetkililer)."""
    return staff_ids()


def log_action(user_id: int, what: str, detail: str = "") -> None:
    run("INSERT INTO actions (user_id, what, detail, ts) VALUES (?,?,?,?)",
        (user_id, what[:32], detail[:200], int(time.time())))
