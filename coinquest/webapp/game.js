/* CoinQuest 3D Arena — istemci
 *
 * Kendi WebGL motoru: hiçbir dış kütüphane yok, tek dosya, hızlı açılır.
 * (Yavaş internette CDN beklemesin diye üç.js gibi kütüphane kullanmadık.)
 *
 * ÖNEMLİ: burada hasar/konum HESAPLANMAZ. Sunucu ne derse o çizilir.
 * Bu dosya sadece "ileri git / vur / blokla" niyetini gönderir ve sonucu gösterir.
 */
'use strict';

// ===========================================================================
// 1) MATEMATİK (4x4 matrisler)
// ===========================================================================
const M4 = {
  ident: () => new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]),
  mul(a, b) {
    const o = new Float32Array(16);
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
      o[r*4+c] = a[r*4]*b[c] + a[r*4+1]*b[4+c] + a[r*4+2]*b[8+c] + a[r*4+3]*b[12+c];
    }
    return o;
  },
  persp(fov, asp, near, far) {
    const f = 1 / Math.tan(fov / 2), d = near - far;
    return new Float32Array([f/asp,0,0,0, 0,f,0,0, 0,0,(far+near)/d,-1, 0,0,2*far*near/d,0]);
  },
  look(eye, at, up) {
    const z = norm(sub(eye, at)), x = norm(cross(up, z)), y = cross(z, x);
    return new Float32Array([
      x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
      -dot(x,eye), -dot(y,eye), -dot(z,eye), 1]);
  },
  trans(x, y, z) { const m = M4.ident(); m[12]=x; m[13]=y; m[14]=z; return m; },
  scale(x, y, z) { const m = M4.ident(); m[0]=x; m[5]=y; m[10]=z; return m; },
  rotY(a) { const m = M4.ident(), c = Math.cos(a), s = Math.sin(a);
    m[0]=c; m[2]=-s; m[8]=s; m[10]=c; return m; },
  rotX(a) { const m = M4.ident(), c = Math.cos(a), s = Math.sin(a);
    m[5]=c; m[6]=s; m[9]=-s; m[10]=c; return m; },
  rotZ(a) { const m = M4.ident(), c = Math.cos(a), s = Math.sin(a);
    m[0]=c; m[1]=s; m[4]=-s; m[5]=c; return m; },
};
const sub = (a,b) => [a[0]-b[0], a[1]-b[1], a[2]-b[2]];
const dot = (a,b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const norm = (a) => { const l = Math.hypot(a[0],a[1],a[2]) || 1; return [a[0]/l,a[1]/l,a[2]/l]; };
const lerp = (a,b,t) => a + (b-a) * t;
const angLerp = (a,b,t) => { let d = ((b-a+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
  return a + d*t; };

// ===========================================================================
// 2) WEBGL MOTORU
// ===========================================================================
const cv = document.getElementById('cv');
const gl = cv.getContext('webgl', {antialias:true, alpha:false}) ||
           cv.getContext('experimental-webgl');
if (!gl) {
  document.body.innerHTML = '<div style="display:grid;place-items:center;height:100vh;' +
    'padding:24px;text-align:center;color:#e8ecf8;font:16px system-ui">' +
    'Bu cihaz 3D desteklemiyor 😔<br><br>Telefonun tarayıcısını güncelle ya da ' +
    'Chrome ile aç.</div>';
  throw new Error('no webgl');
}

const VS = `
attribute vec3 aPos; attribute vec3 aNrm;
uniform mat4 uMVP, uModel; uniform mat3 uNM;
varying vec3 vN; varying vec3 vW;
void main(){ vN = uNM * aNrm; vW = (uModel * vec4(aPos,1.0)).xyz;
  gl_Position = uMVP * vec4(aPos,1.0); }`;

const FS = `
precision mediump float;
varying vec3 vN; varying vec3 vW;
uniform vec3 uColor; uniform float uEmit;
void main(){
  vec3 n = normalize(vN);
  vec3 L = normalize(vec3(0.45, 0.9, 0.35));
  float d = max(dot(n, L), 0.0);
  float rim = pow(1.0 - max(dot(n, normalize(vec3(0.0,0.35,1.0))), 0.0), 3.0);
  vec3 col = uColor * (0.34 + 0.66*d) + vec3(0.35,0.5,0.9)*rim*0.28;
  col += uColor * uEmit;
  float fog = clamp((length(vW.xz) - 13.0) / 16.0, 0.0, 0.75);
  col = mix(col, vec3(0.035,0.05,0.10), fog);
  gl_FragColor = vec4(col, 1.0);
}`;

function shader(type, src) {
  const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
const prog = gl.createProgram();
gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS));
gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS));
gl.linkProgram(prog);
gl.useProgram(prog);
const A = {pos: gl.getAttribLocation(prog,'aPos'), nrm: gl.getAttribLocation(prog,'aNrm')};
const U = {mvp: gl.getUniformLocation(prog,'uMVP'), model: gl.getUniformLocation(prog,'uModel'),
           nm: gl.getUniformLocation(prog,'uNM'), color: gl.getUniformLocation(prog,'uColor'),
           emit: gl.getUniformLocation(prog,'uEmit')};
gl.enable(gl.DEPTH_TEST);
gl.enable(gl.CULL_FACE);

function mesh(verts, norms, idx) {
  const m = {vb: gl.createBuffer(), nb: gl.createBuffer(), ib: gl.createBuffer(), n: idx.length};
  gl.bindBuffer(gl.ARRAY_BUFFER, m.vb);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, m.nb);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(norms), gl.STATIC_DRAW);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, m.ib);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
  return m;
}

function boxMesh() {
  const v = [], n = [], i = [];
  const faces = [
    [[ .5,-.5,-.5],[ .5, .5,-.5],[ .5, .5, .5],[ .5,-.5, .5],[1,0,0]],
    [[-.5,-.5, .5],[-.5, .5, .5],[-.5, .5,-.5],[-.5,-.5,-.5],[-1,0,0]],
    [[-.5, .5,-.5],[-.5, .5, .5],[ .5, .5, .5],[ .5, .5,-.5],[0,1,0]],
    [[-.5,-.5, .5],[-.5,-.5,-.5],[ .5,-.5,-.5],[ .5,-.5, .5],[0,-1,0]],
    [[-.5,-.5, .5],[ .5,-.5, .5],[ .5, .5, .5],[-.5, .5, .5],[0,0,1]],
    [[ .5,-.5,-.5],[-.5,-.5,-.5],[-.5, .5,-.5],[ .5, .5,-.5],[0,0,-1]],
  ];
  faces.forEach((f, k) => {
    for (let j = 0; j < 4; j++) { v.push(...f[j]); n.push(...f[4]); }
    const b = k * 4; i.push(b, b+1, b+2, b, b+2, b+3);
  });
  return mesh(v, n, i);
}

function cylMesh(seg, capTop) {
  const v = [], n = [], i = [];
  for (let s = 0; s < seg; s++) {
    const a0 = s/seg*2*Math.PI, a1 = (s+1)/seg*2*Math.PI;
    const x0 = Math.cos(a0)*.5, z0 = Math.sin(a0)*.5;
    const x1 = Math.cos(a1)*.5, z1 = Math.sin(a1)*.5;
    const b = v.length/3;
    v.push(x0,-.5,z0, x1,-.5,z1, x1,.5,z1, x0,.5,z0);
    n.push(x0*2,0,z0*2, x1*2,0,z1*2, x1*2,0,z1*2, x0*2,0,z0*2);
    i.push(b,b+1,b+2, b,b+2,b+3);
    if (capTop) {
      const c = v.length/3;
      v.push(0,.5,0, x0,.5,z0, x1,.5,z1);
      n.push(0,1,0, 0,1,0, 0,1,0);
      i.push(c, c+1, c+2);
      const d = v.length/3;
      v.push(0,-.5,0, x1,-.5,z1, x0,-.5,z0);
      n.push(0,-1,0, 0,-1,0, 0,-1,0);
      i.push(d, d+1, d+2);
    }
  }
  return mesh(v, n, i);
}

const MESH = {box: boxMesh(), cyl: cylMesh(16, true), disc: cylMesh(48, true)};
let VIEWPROJ = M4.ident();

function draw(m, model, color, emit) {
  gl.bindBuffer(gl.ARRAY_BUFFER, m.vb);
  gl.enableVertexAttribArray(A.pos); gl.vertexAttribPointer(A.pos, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ARRAY_BUFFER, m.nb);
  gl.enableVertexAttribArray(A.nrm); gl.vertexAttribPointer(A.nrm, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, m.ib);
  gl.uniformMatrix4fv(U.mvp, false, M4.mul(model, VIEWPROJ));
  gl.uniformMatrix4fv(U.model, false, model);
  gl.uniformMatrix3fv(U.nm, false, new Float32Array([
    model[0],model[1],model[2], model[4],model[5],model[6], model[8],model[9],model[10]]));
  gl.uniform3fv(U.color, color);
  gl.uniform1f(U.emit, emit || 0);
  gl.drawElements(gl.TRIANGLES, m.n, gl.UNSIGNED_SHORT, 0);
}

/** Kutu çizer: konum, boyut, döndürme (yaw/pitch/roll) */
function box(pos, size, color, rot) {
  let m = M4.scale(size[0], size[1], size[2]);
  if (rot) {
    if (rot[2]) m = M4.mul(m, M4.rotZ(rot[2]));
    if (rot[0]) m = M4.mul(m, M4.rotX(rot[0]));
    if (rot[1]) m = M4.mul(m, M4.rotY(rot[1]));
  }
  draw(MESH.box, M4.mul(m, M4.trans(pos[0], pos[1], pos[2])), color);
}

// ===========================================================================
// 3) ARENA VE KARAKTER ÇİZİMİ
// ===========================================================================
const COL = {
  ground: [0.13,0.11,0.09], ring: [0.35,0.27,0.16], wall: [0.16,0.14,0.20],
  pillar: [0.22,0.20,0.26], torch: [1.0,0.62,0.22],
  skinA: [0.86,0.66,0.48], skinB: [0.78,0.58,0.42],
  p1: [0.86,0.30,0.34], p2: [0.30,0.55,0.92],
  steel: [0.72,0.74,0.80], wood: [0.42,0.28,0.16], gold: [0.95,0.78,0.30],
  dark: [0.15,0.16,0.22],
};

let R = 12;                   // sunucudan gelir

function drawArena(t) {
  // zemin
  draw(MESH.disc, M4.mul(M4.scale(R*2, 0.5, R*2), M4.trans(0,-0.25,0)), COL.ground);
  // dış halka
  draw(MESH.disc, M4.mul(M4.scale(R*2.13, 0.34, R*2.13), M4.trans(0,-0.32,0)), COL.ring);
  // duvar sütunları + meşaleler
  const N = 16;
  for (let i = 0; i < N; i++) {
    const a = i/N*2*Math.PI, x = Math.cos(a)*(R+0.9), z = Math.sin(a)*(R+0.9);
    box([x, 1.5, z], [1.0, 3.0, 1.0], COL.pillar);
    const fl = 0.16 + Math.sin(t*7 + i)*0.05;
    box([x, 3.25 + fl*0.4, z], [0.42+fl, 0.7+fl*2, 0.42+fl], COL.torch);
  }
  // merkez göbek
  draw(MESH.disc, M4.mul(M4.scale(4.2, 0.06, 4.2), M4.trans(0,0.03,0)), [0.19,0.16,0.13]);
}

const WEAPONS = {
  w_stick:  {len:1.1, w:0.13, col:COL.wood,  blade:false},
  w_axe:    {len:1.0, w:0.12, col:COL.wood,  blade:true, head:[0.5,0.42,0.14]},
  w_hammer: {len:1.1, w:0.15, col:COL.wood,  blade:true, head:[0.44,0.44,0.42]},
  w_dagger: {len:0.65,w:0.10, col:COL.steel, blade:true, head:[0.13,0.5,0.05]},
  w_blade:  {len:1.5, w:0.11, col:COL.steel, blade:true, head:[0.16,1.0,0.05]},
  w_scythe: {len:1.7, w:0.12, col:COL.dark,  blade:true, head:[0.9,0.16,0.08]},
  _def:     {len:1.25,w:0.12, col:COL.steel, blade:true, head:[0.15,0.75,0.05]},
};

/** Tek dövüşçüyü çizer. anim: yürüme fazı, vuruş açısı, blok, ölü */
function drawFighter(f, col, anim) {
  const {x, z, yaw} = f;
  const walk = anim.walk, sw = Math.sin(walk) * anim.moving;
  const dead = anim.dead;
  const lean = dead ? Math.PI/2 * anim.deadT : (anim.attack > 0 ? 0.15 : 0);
  const yBase = dead ? 0.45 * (1 - anim.deadT) + 0.3 : 0;

  const P = (lx, ly, lz) => {            // yerel -> dünya
    const c = Math.cos(yaw), s = Math.sin(yaw);
    return [x + lx*c + lz*s, ly + yBase, z - lx*s + lz*c];
  };
  const rot = (extraX, extraZ) => [ (extraX||0) + lean, yaw, extraZ||0 ];

  // gölge
  draw(MESH.disc, M4.mul(M4.scale(1.5, 0.02, 1.5), M4.trans(x, 0.02, z)), [0.04,0.05,0.09]);

  // bacaklar
  box(P(-0.22, 0.42 - Math.abs(sw)*0.05, sw*0.28), [0.26, 0.85, 0.26], COL.dark, rot(sw*0.7));
  box(P( 0.22, 0.42 - Math.abs(sw)*0.05, -sw*0.28), [0.26, 0.85, 0.26], COL.dark, rot(-sw*0.7));
  // gövde
  box(P(0, 1.28, 0), [0.72, 0.92, 0.44], col, rot());
  // omuz zırhı
  box(P(-0.46, 1.60, 0), [0.28, 0.28, 0.46], col, rot());
  box(P( 0.46, 1.60, 0), [0.28, 0.28, 0.46], col, rot());
  // kafa
  box(P(0, 1.94, 0), [0.42, 0.42, 0.42], COL.skinA, rot());
  // miğfer
  box(P(0, 2.10, 0), [0.48, 0.20, 0.48], col, rot());

  // kollar
  const atkA = anim.attack;                        // 0..1 vuruş ilerlemesi
  const swing = atkA > 0 ? Math.sin(atkA * Math.PI) : 0;
  const blockPose = anim.block;
  // sol kol (kalkan tarafı)
  const lArmX = blockPose ? -0.30 : -0.48;
  const lArmY = blockPose ? 1.42 : 1.25;
  const lArmZ = blockPose ? 0.34 : 0;
  box(P(lArmX, lArmY, lArmZ + sw*0.18), [0.22, 0.7, 0.22], COL.skinB,
      rot(blockPose ? -1.1 : -sw*0.6));
  if (blockPose) {                                  // kalkan
    box(P(-0.26, 1.42, 0.62), [0.9, 1.0, 0.12], COL.steel, rot(0.1));
    box(P(-0.26, 1.42, 0.70), [0.34, 0.34, 0.06], COL.gold, rot(0.1));
  }
  // sağ kol + silah
  const rSwing = swing * 1.9 - (atkA > 0 ? 0.5 : 0);
  box(P(0.48, 1.28 + swing*0.25, sw*-0.18 + swing*0.42), [0.22, 0.7, 0.22], COL.skinB,
      rot(-rSwing + (sw*0.6)));

  const wp = WEAPONS[anim.weapon] || WEAPONS._def;
  const wx = 0.52, wy = 1.15 + swing*0.5, wz = 0.30 + swing*0.85;
  const tilt = -0.9 - rSwing;
  box(P(wx, wy, wz), [wp.w, wp.len, wp.w], wp.col, rot(tilt));
  if (wp.blade) {
    const h = wp.head || [0.15,0.7,0.05];
    box(P(wx, wy + Math.cos(tilt)*wp.len*0.52, wz + Math.sin(tilt)*wp.len*0.52),
        h, COL.steel, rot(tilt));
  }
}

// ===========================================================================
// 4) DURUM VE AĞ
// ===========================================================================
const S = {
  me: 0, my: null, foe: null, stake: 0, sel: 0,
  prev: null, cur: null, prevT: 0, curT: 0,
  running: false, walk: [0,0], anim: {}, ws: null, coins: 0,
  camYaw: 0, shake: 0,
};
const el = (id) => document.getElementById(id);
const fmt = (n) => (n|0).toLocaleString('tr-TR');

function show(which) {
  ['lobby','waiting','result','how'].forEach(id => el(id).style.display = 'none');
  el('hud').style.display = which === 'game' ? 'block' : 'none';
  if (which !== 'game') el(which).style.display = 'grid';
}

async function loadMe() {
  const r = await fetch('/api/me');
  if (!r.ok) { el('who').textContent = 'Giriş geçersiz — bota dönüp tekrar gir.'; return; }
  const d = await r.json();
  S.me = d.me.id; S.my = d.me; S.coins = d.coins;
  el('who').innerHTML = `<b>${d.me.name}</b> · Sv.${d.level} · 🪙 ${fmt(d.coins)}`;
  el('kit').innerHTML =
    `<div class="stat"><span>⚔️ Saldırı</span><b>${d.me.atk|0}</b></div>` +
    `<div class="stat"><span>🛡 Savunma</span><b>${d.me.dfn|0}</b></div>` +
    `<div class="stat"><span>❤️ Can</span><b>${d.me.hp|0}</b></div>` +
    `<div class="stat"><span>💥 Kritik</span><b>%${(d.me.crit*100)|0}</b></div>` +
    `<div class="stat"><span>🏃 Hız</span><b>${d.me.speed.toFixed(1)} m/sn</b></div>` +
    `<div class="gear">${d.me.weapon_name}</div>` +
    `<div class="gear">${d.me.armor_name}</div>` +
    (d.me.pet_name ? `<div class="gear">${d.me.pet_name}</div>` : '') +
    `<div class="stat" style="margin-top:8px"><span>🏟 Arena</span>` +
    `<b>${d.stats.wins}W / ${d.stats.losses}L</b></div>`;
  const box = el('stakes'); box.innerHTML = '';
  d.stakes.forEach((v, i) => {
    const b = document.createElement('button');
    b.textContent = v === 0 ? 'Bedava' : (v >= 1e6 ? (v/1e6)+'M' : (v/1000)+'K');
    b.className = i === 0 ? 'on' : '';
    b.onclick = () => { S.sel = v; [...box.children].forEach(c => c.className = '');
                        b.className = 'on'; };
    box.appendChild(b);
  });
  S.sel = d.stakes[0] || 0;
  el('hint').textContent = 'Gücün bottaki eşyalarından geliyor. Daha iyi silah al, daha güçlü ol.';
}

let reconnectTimer = null;

function setConn(txt) { const c = el('conn'); if (c) c.textContent = txt; }

function connect(onOpen) {
  // Zaten bağlıysa ya da bağlanıyorsa YENİ soket açma (iki soket = maç karışması)
  if (S.ws && (S.ws.readyState === 0 || S.ws.readyState === 1)) {
    if (S.ws.readyState === 1 && onOpen) onOpen();
    else if (onOpen) S.pending = onOpen;
    return;
  }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  setConn('Bağlanıyor…');
  S.ws = new WebSocket(`${proto}://${location.host}/ws`);
  S.ws.onopen = () => {
    setConn('');
    const f = onOpen || S.pending; S.pending = null;
    if (f) f();
  };
  S.ws.onmessage = (e) => onMsg(JSON.parse(e.data));
  S.ws.onerror = () => setConn('Bağlantı hatası');
  S.ws.onclose = () => {
    setConn('Bağlantı koptu — yeniden bağlanılıyor…');
    if (S.running) {
      flash('BAĞLANTI KOPTU\nyeniden bağlanılıyor…', '#ffd66b');
    }
    // Telefonda uygulama değiştirince soket kapanıyor; sunucu 20 saniye bekliyor.
    // O yüzden hemen geri bağlanmayı deniyoruz — maç kaldığı yerden devam eder.
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => connect(), 1200);
  };
}
const send = (o) => { if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify(o)); };

// Sayfa geri gelince (uygulama değişimi) bağlantıyı tazele
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && (!S.ws || S.ws.readyState > 1)) connect();
});

function onMsg(m) {
  if (m.t === 'queued') {
    show('waiting');
    el('waitInfo').textContent = m.stake ? `Bahis: ${fmt(m.stake)} 🪙` : 'Bedava maç';
  } else if (m.t === 'start') {
    startMatch(m);
  } else if (m.t === 's') {
    S.prev = S.cur; S.prevT = S.curT;
    S.cur = m; S.curT = performance.now();
    if (m.ev) m.ev.forEach(handleEvent);
    updateHud(m);
  } else if (m.t === 'end') {
    endMatch(m);
  } else if (m.t === 'err') {
    show('lobby'); el('hint').textContent = m.m;
  } else if (m.t === 'idle') {
    show('lobby');
  }
}

function startMatch(m) {
  R = m.arena.r;
  const [a, b] = m.f;
  // Sunucu hangi dövüşçünün bize ait olduğunu söylüyor — /api/me gecikse bile şaşmaz
  if (m.you) S.me = m.you;
  S.my = a.id === S.me ? a : b;
  S.foe = a.id === S.me ? b : a;
  S.training = !!m.training;
  S.stake = m.stake;
  S.prev = S.cur = null;
  S.anim = {};
  [S.my, S.foe].forEach(f => S.anim[f.id] = {walk:0, attack:0, deadT:0, hitT:0});
  el('n1').textContent = S.my.name + ' (sen)';
  el('n2').textContent = S.foe.name;
  el('h1').style.width = '100%'; el('h2').style.width = '100%';
  S.running = true;
  show('game');
  flash(S.training ? 'ANTRENMAN!' : 'DÖVÜŞ!', '#ffd66b');
}

function updateHud(m) {
  const me = m.f.find(f => f.id === S.me), fo = m.f.find(f => f.id !== S.me);
  if (!me || !fo) return;
  el('h1').style.width = Math.max(0, me.hp / S.my.max_hp * 100) + '%';
  el('h2').style.width = Math.max(0, fo.hp / S.foe.max_hp * 100) + '%';
  el('stam').style.width = me.st + '%';
  el('clock').textContent = Math.ceil(m.tm);
}

function handleEvent(ev) {
  if (ev.e !== 'hit') return;
  const victim = ev.to;
  const a = S.anim[victim]; if (a) a.hitT = 1;
  if (victim === S.me) S.shake = ev.crit ? 1.0 : 0.5;
  const pos = S.cur ? S.cur.f.find(f => f.id === victim) : null;
  popDamage(ev, pos);
}

function popDamage(ev, fpos) {
  const d = document.createElement('div');
  d.className = 'pop';
  const mine = ev.id === S.me;
  d.textContent = (ev.crit ? '💥' : '') + (ev.blk ? '🛡' : '') + '-' + Math.round(ev.d);
  d.style.color = mine ? '#8ef08e' : '#ff8a8a';
  d.style.fontSize = ev.crit ? '26px' : '19px';
  const p = fpos ? project(fpos.x, 2.4, fpos.z) : {x: innerWidth/2, y: innerHeight/2};
  d.style.left = (p.x - 20) + 'px'; d.style.top = p.y + 'px';
  el('hud').appendChild(d);
  requestAnimationFrame(() => {
    d.style.transform = 'translateY(-70px)'; d.style.opacity = '0';
  });
  setTimeout(() => d.remove(), 750);
}

function flash(text, color) {
  const m = el('msg');
  m.textContent = text; m.style.color = color || '#fff'; m.style.opacity = '1';
  setTimeout(() => m.style.opacity = '0', 900);
}

function endMatch(m) {
  S.running = false;
  show('result');
  const win = m.win, draw = m.draw;
  el('resTitle').textContent = draw ? '🤝 BERABERE' : (win ? '🏆 KAZANDIN!' : '☠️ KAYBETTİN');
  el('resTitle').style.color = draw ? '#ffd66b' : (win ? '#8ef08e' : '#ff8a8a');
  el('resBody').innerHTML =
    (m.training ? '<div class="sub">🥊 Antrenman maçı — coin ve istatistik yok.</div>' : '') +
    (m.prize ? `<div class="stat"><span>💰 Ödül</span><b>+${fmt(m.prize)} 🪙</b></div>` :
     (m.stake && !draw && !win ? `<div class="stat"><span>💸 Kaybettiğin</span>` +
        `<b>${fmt(m.stake)} 🪙</b></div>` : '')) +
    `<div class="stat"><span>💢 Verdiğin hasar</span><b>${fmt(m.dmg)}</b></div>` +
    `<div class="stat"><span>🩸 Yediğin hasar</span><b>${fmt(m.taken)}</b></div>` +
    `<div class="stat"><span>👊 İsabetli vuruş</span><b>${m.hits}</b></div>` +
    `<div class="stat"><span>🪙 Bakiyen</span><b>${fmt(m.coins)}</b></div>`;
  S.coins = m.coins;
}

// ===========================================================================
// 5) KAMERA VE ÇİZİM DÖNGÜSÜ
// ===========================================================================
let camEye = [0, 9, 14], camAt = [0, 1.2, 0];

function project(wx, wy, wz) {              // dünya -> ekran (hasar yazıları için)
  const v = M4.mul(M4.trans(wx, wy, wz), VIEWPROJ);
  const w = v[15] || 1;
  return {x: (v[12]/w * 0.5 + 0.5) * innerWidth, y: (-v[13]/w * 0.5 + 0.5) * innerHeight};
}

function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  cv.width = innerWidth * dpr; cv.height = innerHeight * dpr;
  gl.viewport(0, 0, cv.width, cv.height);
}
addEventListener('resize', resize); resize();

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  const t = now / 1000;

  gl.clearColor(0.027, 0.039, 0.086, 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

  // sunucu 20 Hz gönderiyor, biz 60 Hz çiziyoruz -> aradaki kareleri yumuşat
  let fighters = [];
  if (S.cur) {
    const span = Math.max(1, S.curT - S.prevT);
    const k = Math.min(1, (now - S.curT) / span + 1);
    fighters = S.cur.f.map(f => {
      const p = S.prev ? S.prev.f.find(q => q.id === f.id) : null;
      if (!p) return {...f, yaw: f.y};
      return {id: f.id, hp: f.hp, s: f.s,
              x: lerp(p.x, f.x, k), z: lerp(p.z, f.z, k),
              yaw: angLerp(p.y, f.y, Math.min(1, k * 1.6))};
    });
  }

  const me = fighters.find(f => f.id === S.me);
  const fo = fighters.find(f => f.id !== S.me);

  // kamera: iki dövüşçüyü de kadraja alan omuz üstü görüş
  if (me && fo) {
    const mx = (me.x + fo.x) / 2, mz = (me.z + fo.z) / 2;
    const d = Math.hypot(fo.x - me.x, fo.z - me.z);
    const want = Math.atan2(me.x - fo.x, me.z - fo.z);
    S.camYaw = angLerp(S.camYaw, want, 1 - Math.pow(0.001, dt));
    const dist = 9.5 + d * 0.55, h = 5.4 + d * 0.22;
    const ex = mx + Math.sin(S.camYaw) * dist, ez = mz + Math.cos(S.camYaw) * dist;
    camEye = [lerp(camEye[0], ex, 1 - Math.pow(0.002, dt)), lerp(camEye[1], h, 0.08),
              lerp(camEye[2], ez, 1 - Math.pow(0.002, dt))];
    camAt = [lerp(camAt[0], mx, 0.15), 1.3, lerp(camAt[2], mz, 0.15)];
  }
  if (S.shake > 0) {
    S.shake = Math.max(0, S.shake - dt * 3.4);
    camEye = [camEye[0] + (Math.random()-.5) * S.shake * 0.7, camEye[1],
              camEye[2] + (Math.random()-.5) * S.shake * 0.7];
  }
  const proj = M4.persp(1.05, cv.width / cv.height, 0.1, 220);
  VIEWPROJ = M4.mul(M4.look(camEye, camAt, [0,1,0]), proj);

  drawArena(t);

  fighters.forEach(f => {
    const a = S.anim[f.id] || (S.anim[f.id] = {walk:0, attack:0, deadT:0, hitT:0});
    const src = f.id === S.me ? S.my : S.foe;
    const moving = (f.s === 'idle' || f.s === 'block' || f.s === 'dash') ? 1 : 0;
    a.walk += dt * 9 * moving;
    a.attack = f.s === 'attack' ? Math.min(1, a.attack + dt * 4.4) : 0;
    a.deadT = f.s === 'dead' ? Math.min(1, a.deadT + dt * 3) : 0;
    a.hitT = Math.max(0, a.hitT - dt * 3.5);
    let col = f.id === S.me ? COL.p1.slice() : COL.p2.slice();
    if (a.hitT > 0) col = col.map(c => Math.min(1, c + a.hitT * 0.9));   // vurulunca parla
    drawFighter(f, col, {
      walk: a.walk, moving: moving * (f.s === 'dash' ? 1.7 : 1),
      attack: a.attack, block: f.s === 'block', dead: f.s === 'dead',
      deadT: a.deadT, weapon: (src && src.weapon) || '',
    });
  });

  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ===========================================================================
// 6) KONTROLLER  (sadece niyet gönderir)
// ===========================================================================
const IN = {mx: 0, mz: 0, atk: false, blk: false, dash: false};
let lastSent = 0;

function pump() {
  if (S.running) {
    const now = performance.now();
    if (now - lastSent > 50) {                 // saniyede 20 kez yeter
      lastSent = now;
      // hareketi kameraya göre çevir: "yukarı" ekranda yukarı olsun
      const c = Math.cos(S.camYaw), s = Math.sin(S.camYaw);
      send({t:'in', mx: IN.mx * c - IN.mz * s, mz: -IN.mx * s - IN.mz * c,
            atk: IN.atk, blk: IN.blk, dash: IN.dash});
      IN.atk = false; IN.dash = false;         // tek seferlik
    }
  }
  requestAnimationFrame(pump);
}
requestAnimationFrame(pump);

// --- klavye ---
const keys = {};
addEventListener('keydown', e => {
  keys[e.code] = true;
  if (e.code === 'Space') { IN.atk = true; e.preventDefault(); }
  if (e.code === 'ControlLeft' || e.code === 'ControlRight') IN.dash = true;
});
addEventListener('keyup', e => { keys[e.code] = false; });
setInterval(() => {
  let x = 0, z = 0;
  if (keys.KeyW || keys.ArrowUp) z -= 1;
  if (keys.KeyS || keys.ArrowDown) z += 1;
  if (keys.KeyA || keys.ArrowLeft) x -= 1;
  if (keys.KeyD || keys.ArrowRight) x += 1;
  const l = Math.hypot(x, z) || 1;
  if (!touching) { IN.mx = x / l * (x||z ? 1 : 0); IN.mz = z / l * (x||z ? 1 : 0); }
  IN.blk = !!(keys.ShiftLeft || keys.ShiftRight) || blockHeld;
}, 33);

// --- dokunmatik çubuk ---
let touching = false, stickId = null;
const stick = el('stick'), knob = el('knob');
function stickMove(e, t) {
  const r = stick.getBoundingClientRect();
  let dx = t.clientX - (r.left + r.width/2), dy = t.clientY - (r.top + r.height/2);
  const max = r.width/2 - 8, d = Math.hypot(dx, dy);
  if (d > max) { dx = dx/d*max; dy = dy/d*max; }
  knob.style.transform = `translate(${dx}px,${dy}px)`;
  IN.mx = dx / max; IN.mz = dy / max;
}
stick.addEventListener('touchstart', e => {
  touching = true; stickId = e.changedTouches[0].identifier;
  stickMove(e, e.changedTouches[0]); e.preventDefault();
}, {passive:false});
stick.addEventListener('touchmove', e => {
  for (const t of e.changedTouches) if (t.identifier === stickId) stickMove(e, t);
  e.preventDefault();
}, {passive:false});
const stickEnd = e => {
  for (const t of e.changedTouches) if (t.identifier === stickId) {
    touching = false; stickId = null; IN.mx = IN.mz = 0;
    knob.style.transform = 'translate(0,0)';
  }
};
stick.addEventListener('touchend', stickEnd);
stick.addEventListener('touchcancel', stickEnd);

// --- eylem düğmeleri ---
let blockHeld = false;
function tapBtn(id, onDown, onUp) {
  const b = el(id);
  const down = e => { onDown(); e.preventDefault(); };
  const up = e => { if (onUp) onUp(); e.preventDefault(); };
  b.addEventListener('touchstart', down, {passive:false});
  b.addEventListener('touchend', up, {passive:false});
  b.addEventListener('mousedown', down);
  b.addEventListener('mouseup', up);
  b.addEventListener('mouseleave', () => { if (onUp) onUp(); });
}
tapBtn('bAtk', () => IN.atk = true);
tapBtn('bDash', () => IN.dash = true);
tapBtn('bBlock', () => { blockHeld = true; IN.blk = true; },
                 () => { blockHeld = false; IN.blk = false; });

// ===========================================================================
// 7) MENÜ DÜĞMELERİ
// ===========================================================================
el('btnFind').onclick = () => connect(() => send({t:'find', stake: S.sel}));
[...document.querySelectorAll('#trainRow button')].forEach(b => {
  b.onclick = () => connect(() => send({t:'train', level: b.dataset.lvl}));
});
el('btnCancel').onclick = () => { send({t:'cancel'}); show('lobby'); };
el('btnAgain').onclick = () => { loadMe().then(() => show('lobby')); };
el('btnLobby').onclick = () => { loadMe().then(() => show('lobby')); };
el('btnHow').onclick = () => show('how');
el('btnHowBack').onclick = () => show('lobby');

// Telegram Mini App içindeyse tam ekran aç
if (window.Telegram && window.Telegram.WebApp) {
  try { window.Telegram.WebApp.expand(); window.Telegram.WebApp.ready(); } catch (e) {}
}

loadMe();
connect();
