# -*- coding: utf-8 -*-
"""3D Arena web sunucusu (aiohttp).

Botla AYNI süreçte çalışır, aynı veritabanını kullanır. Yaptığı işler:
  • Tarayıcıya oyunu (HTML/JS) servis eder
  • Giriş anahtarını doğrular — kimin oynadığı bottan gelir
  • Oyuncuları eşleştirir
  • Dövüşü 20 kez/saniye SUNUCUDA hesaplar ve iki tarafa da yayınlar

Hile koruması: tarayıcı sadece "ileri git / vur / blokla" gönderir. Konum ve
hasar sunucuda hesaplanır; istemciden gelen hiçbir sayı doğrudan kullanılmaz.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import pathlib
import time
from urllib.parse import parse_qsl

import arena
import config
import db
import ui

log = logging.getLogger(__name__)

try:
    from aiohttp import WSMsgType, web
    HAVE_AIOHTTP = True
except ImportError:                                  # aiohttp kurulu değilse bot yine çalışır
    HAVE_AIOHTTP = False
    web = None
    WSMsgType = None

STATIC = pathlib.Path(__file__).resolve().parent / "webapp"

# oturumlar: sid -> (user_id, son görülme)
_sessions: dict[str, tuple[int, float]] = {}
# eşleşme bekleyenler: stake -> [oyuncu]
_queue: dict[int, list] = {}
# canlı dövüşler: match_id -> Match
_matches: dict[int, "Match"] = {}
_next_match = [1]
# hangi oyuncu hangi maçta: user_id -> Match  (yeniden bağlanma için)
_in_match: dict[int, "Match"] = {}

RECONNECT_GRACE = 20.0   # bağlantı koparsa kaç saniye beklenir (telefonda uygulama
                         # değiştirince soket kapanıyor — hemen kaybetmesin)


# ---------------------------------------------------------------------------
# OTURUM
# ---------------------------------------------------------------------------

def _new_session(user_id: int) -> str:
    import secrets
    sid = secrets.token_urlsafe(24)
    _sessions[sid] = (user_id, time.time())
    if len(_sessions) > 5000:                        # eskileri temizle
        cut = time.time() - 12 * 3600
        for key in [k for k, v in _sessions.items() if v[1] < cut]:
            _sessions.pop(key, None)
    return sid


def _session_user(request) -> int:
    sid = request.cookies.get("cq_sid", "")
    row = _sessions.get(sid)
    if not row:
        return 0
    user_id, _ts = row
    _sessions[sid] = (user_id, time.time())
    return user_id


def check_webapp_data(init_data: str, bot_token: str) -> int:
    """Telegram Mini App imzasını doğrular. Geçerliyse kullanıcı numarası."""
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
        got = pairs.pop("hash", "")
        if not got:
            return 0
        check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        want = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, got):
            return 0
        if time.time() - int(pairs.get("auth_date", 0)) > 86400:
            return 0
        return int(json.loads(pairs.get("user", "{}")).get("id", 0))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# HTTP UÇLARI
# ---------------------------------------------------------------------------

async def h_login(request):
    """Bottan gelen tek kullanımlık bağlantı: /a/<token>"""
    token = request.match_info.get("token", "")
    user_id = arena.check_token(token)
    if not user_id:
        return web.Response(text=_page("Bağlantının süresi dolmuş",
                                       "Bota dön ve 🏟 ARENA düğmesine tekrar bas."),
                            content_type="text/html", status=403)
    resp = web.HTTPFound("/")
    resp.set_cookie("cq_sid", _new_session(user_id), max_age=12 * 3600,
                    httponly=True, samesite="Lax")
    raise resp


async def h_index(request):
    if not _session_user(request):
        return web.Response(text=_page("Giriş yapılmadı",
                                       "Bota git, 🏟 ARENA düğmesine bas ve açılan bağlantıyı kullan."),
                            content_type="text/html", status=403)
    return web.FileResponse(STATIC / "index.html")


async def h_tg_login(request):
    """Telegram Mini App içinden giriş (initData ile)."""
    data = await request.json()
    user_id = check_webapp_data(data.get("initData", ""), config.BOT_TOKEN)
    if not user_id or db.get_user(user_id) is None:
        return web.json_response({"ok": False}, status=403)
    resp = web.json_response({"ok": True})
    resp.set_cookie("cq_sid", _new_session(user_id), max_age=12 * 3600,
                    httponly=True, samesite="Lax")
    return resp


async def h_me(request):
    user_id = _session_user(request)
    if not user_id:
        return web.json_response({"ok": False}, status=403)
    user = db.get_user(user_id)
    kit = arena.loadout(user_id)
    st = arena.my_stats(user_id)
    return web.json_response({
        "ok": True, "me": kit, "coins": user["coins"], "level": user["level"],
        "stats": st, "stakes": [s for s in arena.STAKES if s <= user["coins"]] or [0],
        "waiting": {str(k): len(v) for k, v in _queue.items() if v},
    })


def _page(title: str, body: str) -> str:
    return (f"<!doctype html><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<style>body{{background:#0b1020;color:#e8ecf8;font:16px system-ui;"
            f"display:grid;place-items:center;height:100vh;margin:0;text-align:center;padding:20px}}"
            f"h1{{font-size:20px}}</style><h1>{title}</h1><p>{body}</p>")


# ---------------------------------------------------------------------------
# EŞLEŞME VE DÖVÜŞ
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, user_id: int, ws):
        self.id = user_id
        self.ws = ws
        self.match = None
        self.stake = 0
        self.gone_at = 0.0          # bağlantı koptuysa ne zaman koptu

    async def send(self, obj) -> bool:
        if self.ws is None:
            return False
        try:
            await self.ws.send_json(obj)
            return True
        except Exception:
            return False


class BotPlayer:
    """Antrenman rakibi — soketi yoktur, mesajları yutar."""

    def __init__(self):
        self.id = arena.BOT_ID
        self.ws = None
        self.match = None
        self.stake = 0
        self.gone_at = 0.0

    async def send(self, obj) -> bool:
        return True


class Match:
    def __init__(self, p1: Player, p2, stake: int, training: bool = False,
                 difficulty: str = "orta"):
        self.id = _next_match[0]
        _next_match[0] += 1
        self.players = [p1, p2]
        self.training = training
        if training:
            level = (db.get_user(p1.id) or {"level": 1})["level"]
            foe = arena.bot_loadout(level, difficulty)
            self.battle = arena.Battle(arena.loadout(p1.id), foe, 0, training=True)
            self.brain = arena.BotBrain(self.battle, difficulty)
        else:
            self.battle = arena.Battle(arena.loadout(p1.id), arena.loadout(p2.id), stake)
            self.brain = None
        self.task = None
        self.done = False
        for p in self.players:
            if p.id > 0:
                _in_match[p.id] = self

    def player_of(self, user_id: int):
        return next((p for p in self.players if p.id == user_id), None)

    def attach(self, player: Player) -> bool:
        """Kopan oyuncu geri döndü: yeni soketi maça bağla."""
        for i, p in enumerate(self.players):
            if p.id == player.id:
                self.players[i] = player
                player.match = self
                player.gone_at = 0.0
                return True
        return False

    async def send_start(self, only=None) -> None:
        b = self.battle
        for p in self.players:
            if only is not None and p is not only:
                continue
            await p.send({
                "t": "start", "mid": self.id, "stake": b.stake, "you": p.id,
                "training": self.training,
                "arena": {"r": arena.RADIUS, "reach": arena.REACH},
                "f": [b.a.d, b.b.d],
            })

    async def broadcast(self, obj) -> None:
        for p in self.players:
            await p.send(obj)

    async def run(self) -> None:
        b = self.battle
        await self.send_start()
        try:
            next_tick = time.monotonic()
            while not b.over:
                if self.brain:
                    self.brain.think(arena.TICK)
                b.step(arena.TICK)
                await self.broadcast(b.snapshot())
                kacan = self._check_gone()
                if kacan:
                    await self.finish(forfeit=kacan)
                    return
                next_tick += arena.TICK
                delay = next_tick - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                else:                                # sunucu geride kaldıysa toparla
                    next_tick = time.monotonic()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("arena dövüş hatası")
        await self.finish()

    def _check_gone(self) -> int:
        """Süresi içinde dönmeyen oyuncuyu bildirir (0 = herkes bağlı)."""
        now = time.monotonic()
        for p in self.players:
            if p.gone_at and now - p.gone_at > RECONNECT_GRACE:
                return p.id
        return 0

    async def finish(self, forfeit: int = 0) -> None:
        if self.done:
            return
        self.done = True
        b = self.battle
        if forfeit:                                  # bağlantısı kopan kaybeder
            b.over = True
            b.winner = b.b.id if forfeit == b.a.id else b.a.id
        result = arena.settle(b)
        for p in self.players:
            p.match = None
            _in_match.pop(p.id, None)
            me = b.a if b.a.id == p.id else b.b
            foe = b.b if b.a.id == p.id else b.a
            if p.id <= 0:
                continue
            user = db.get_user(p.id)
            await p.send({
                "t": "end", "win": (b.winner == p.id), "draw": b.winner == 0,
                "prize": result.get("prize", 0), "stake": b.stake,
                "training": self.training,
                "dmg": int(me.damage_done), "taken": int(foe.damage_done),
                "hits": me.hits, "coins": user["coins"] if user else 0,
            })
        _matches.pop(self.id, None)


def _leave_queue(player: Player) -> None:
    for stake, waiting in _queue.items():
        if player in waiting:
            waiting.remove(player)


async def _try_match(player: Player, stake: int) -> None:
    waiting = _queue.setdefault(stake, [])
    # kendisiyle eşleşmesin
    rival = next((p for p in waiting if p.id != player.id), None)
    if rival is None:
        if player not in waiting:
            waiting.append(player)
        await player.send({"t": "queued", "stake": stake, "n": len(waiting)})
        return
    waiting.remove(rival)
    # bahisleri şimdi al — eşleşme kesinleşti
    if not arena.take_stake(player.id, stake):
        await player.send({"t": "err", "m": "Bahis için coinin yetmiyor."})
        await _try_match(rival, stake)               # rakip sıraya geri dönsün
        return
    if not arena.take_stake(rival.id, stake):
        arena.refund(player.id, stake)
        await rival.send({"t": "err", "m": "Bahis için coinin yetmiyor."})
        await _try_match(player, stake)
        return
    match = Match(player, rival, stake)
    _matches[match.id] = match
    player.match = rival.match = match
    match.task = asyncio.create_task(match.run())


async def _start_training(player: Player, difficulty: str = "orta") -> None:
    match = Match(player, BotPlayer(), 0, training=True, difficulty=difficulty)
    _matches[match.id] = match
    player.match = match
    match.task = asyncio.create_task(match.run())


async def h_ws(request):
    user_id = _session_user(request)
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    if not user_id or db.get_user(user_id) is None:
        await ws.send_json({"t": "err", "m": "Giriş geçersiz. Bota dönüp tekrar gir."})
        await ws.close()
        return ws
    player = Player(user_id, ws)
    log.info("arena: %s bağlandı", user_id)
    # Kopan bir maçı varsa geri bağla (telefonda uygulama değiştirince soket kapanıyor)
    live = _in_match.get(user_id)
    if live and not live.done:
        live.attach(player)
        await live.send_start(only=player)
        log.info("arena: %s maça geri döndü (#%s)", user_id, live.id)
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
            except Exception:
                continue
            kind = data.get("t")
            if kind == "train":
                if player.match:
                    continue
                _leave_queue(player)
                zorluk = str(data.get("level", "orta"))
                if zorluk not in ("kolay", "orta", "zor"):
                    zorluk = "orta"
                await _start_training(player, zorluk)
            elif kind == "find":
                stake = int(data.get("stake", 0) or 0)
                if stake not in arena.STAKES:
                    stake = 0
                user = db.get_user(user_id)
                if stake and user["coins"] < stake:
                    await player.send({"t": "err", "m": "Bu bahis için coinin yetmiyor."})
                    continue
                if player.match:
                    continue
                _leave_queue(player)
                player.stake = stake
                await _try_match(player, stake)
            elif kind == "cancel":
                _leave_queue(player)
                await player.send({"t": "idle"})
            elif kind == "in" and player.match:
                player.match.battle.set_input(user_id, data)
            elif kind == "ping":
                await player.send({"t": "pong"})
    except Exception:
        log.exception("arena websocket hatası")
    finally:
        _leave_queue(player)
        match = player.match
        if match and not match.done and match.player_of(user_id) is player:
            if match.training:
                # antrenman maçı: kimse beklemesin, sessizce kapat
                match.done = True
                for p in match.players:
                    p.match = None
                    _in_match.pop(p.id, None)
                _matches.pop(match.id, None)
                if match.task:
                    match.task.cancel()
            else:
                # HEMEN kaybettirme: geri dönmesi için süre tanı
                player.gone_at = time.monotonic()
                log.info("arena: %s koptu, %ssn bekleniyor", user_id, int(RECONNECT_GRACE))
        log.info("arena: %s ayrıldı", user_id)
    return ws


# ---------------------------------------------------------------------------
# BAŞLATMA
# ---------------------------------------------------------------------------

def build_app():
    app = web.Application()
    app.router.add_get("/a/{token}", h_login)
    app.router.add_get("/", h_index)
    app.router.add_post("/api/tglogin", h_tg_login)
    app.router.add_get("/api/me", h_me)
    app.router.add_get("/ws", h_ws)
    app.router.add_static("/static/", STATIC, show_index=False)
    return app


async def start(bot_app=None) -> None:
    """Botla aynı olay döngüsünde web sunucusunu açar."""
    if not config.ARENA_ENABLED:
        log.info("Arena kapalı (ARENA_ENABLED=0)")
        return
    if not HAVE_AIOHTTP:
        log.warning("Arena açılamadı: aiohttp kurulu değil (pip install aiohttp)")
        return
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.ARENA_PORT)
    await site.start()
    log.info("🏟 Arena sunucusu açık: port %s  (dış adres: %s)",
             config.ARENA_PORT, config.ARENA_URL or "AYARLANMADI")
