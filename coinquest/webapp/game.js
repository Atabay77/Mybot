/* CoinQuest 3D Arena — istemci
 *
 * Kendi WebGL motoru: hiçbir dış kütüphane yok, tek dosya, hızlı açılır.
 * (Yavaş internette CDN beklemesin diye three.js gibi kütüphane kullanmadık.)
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
const clamp = (v,a,b) => v < a ? a : (v > b ? b : v);
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
varying vec3 vN; varying vec3 vW; varying vec3 vL;
void main(){ vN = uNM * aNrm; vW = (uModel * vec4(aPos,1.0)).xyz; vL = aPos;
  gl_Position = uMVP * vec4(aPos,1.0); }`;

// uMode: 0 normal · 1 gökyüzü · 2 zemin (halkalı) · 3 ışıklı (kıvılcım/alev)
const FS = `
precision mediump float;
varying vec3 vN; varying vec3 vW; varying vec3 vL;
uniform vec3 uColor; uniform float uEmit; uniform float uMode; uniform float uTime;
void main(){
  vec3 col;
  if (uMode > 2.5) {                       // ışık veren: gölgesiz, parlak
    gl_FragColor = vec4(uColor, 1.0);
    return;
  }
  if (uMode > 0.5 && uMode < 1.5) {        // gökyüzü: geçiş + yıldızlar
    float h = clamp(vL.y + 0.5, 0.0, 1.0);
    col = mix(vec3(0.09,0.11,0.22), vec3(0.015,0.02,0.05), h);
    col += vec3(0.55,0.30,0.12) * pow(1.0 - h, 5.0) * 0.85;   // ufuktaki meşale parıltısı
    vec2 sp = floor(vec2(atan(vW.z, vW.x) * 46.0, vW.y * 1.7));
    float st = fract(sin(dot(sp, vec2(12.9898, 78.233))) * 43758.5453);
    col += vec3(0.9, 0.93, 1.0) * step(0.9955, st) * h * 1.4;  // yıldızlar
    gl_FragColor = vec4(col, 1.0);
    return;
  }
  vec3 n = normalize(vN);
  vec3 L = normalize(vec3(0.42, 0.88, 0.30));
  float d = max(dot(n, L), 0.0);
  vec3 base = uColor;
  if (uMode > 1.5) {                       // zemin: eş merkezli halkalar + ışınlar
    float r = length(vW.xz);
    float ring = smoothstep(0.42, 0.5, abs(fract(r * 0.34) - 0.5));
    base *= 0.82 + 0.30 * ring;
    float ray = abs(fract(atan(vW.z, vW.x) * 3.8) - 0.5);
    base *= 0.92 + 0.16 * smoothstep(0.34, 0.5, ray);
    float glow = 1.0 - smoothstep(2.0, 5.0, r);
    base += vec3(0.16,0.10,0.03) * glow;   // ortadaki amblem parıltısı
  }
  float rim = pow(1.0 - max(dot(n, normalize(vec3(0.0,0.30,1.0))), 0.0), 3.0);
  // iki ışık: üstten ay ışığı + kenardaki meşalelerden sıcak dolgu
  float warm = max(dot(n, normalize(vec3(-0.5, 0.35, -0.6))), 0.0);
  col = base * (0.42 + 0.62*d) + base * vec3(1.0,0.55,0.22) * warm * 0.30
      + vec3(0.40,0.55,1.0)*rim*0.26;
  float spec = pow(max(dot(reflect(-L, n), normalize(vec3(0.0,0.4,1.0))), 0.0), 24.0);
  col += vec3(1.0,0.94,0.80) * spec * 0.22;
  col += uColor * uEmit;
  float fog = clamp((length(vW.xz) - 13.0) / 26.0, 0.0, 0.72);
  col = mix(col, vec3(0.045,0.055,0.105), fog);
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
           emit: gl.getUniformLocation(prog,'uEmit'), mode: gl.getUniformLocation(prog,'uMode'),
           time: gl.getUniformLocation(prog,'uTime')};
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

function cylMesh(seg) {
  const v = [], n = [], i = [];
  for (let s = 0; s < seg; s++) {
    const a0 = s/seg*2*Math.PI, a1 = (s+1)/seg*2*Math.PI;
    const x0 = Math.cos(a0)*.5, z0 = Math.sin(a0)*.5;
    const x1 = Math.cos(a1)*.5, z1 = Math.sin(a1)*.5;
    const b = v.length/3;
    v.push(x0,-.5,z0, x1,-.5,z1, x1,.5,z1, x0,.5,z0);
    n.push(x0*2,0,z0*2, x1*2,0,z1*2, x1*2,0,z1*2, x0*2,0,z0*2);
    i.push(b,b+1,b+2, b,b+2,b+3);
    const c = v.length/3;
    v.push(0,.5,0, x0,.5,z0, x1,.5,z1);
    n.push(0,1,0, 0,1,0, 0,1,0);
    i.push(c, c+1, c+2);
    const d = v.length/3;
    v.push(0,-.5,0, x1,-.5,z1, x0,-.5,z0);
    n.push(0,-1,0, 0,-1,0, 0,-1,0);
    i.push(d, d+1, d+2);
  }
  return mesh(v, n, i);
}

const MESH = {box: boxMesh(), cyl: cylMesh(14), disc: cylMesh(56), sky: cylMesh(20)};
let VIEWPROJ = M4.ident();
let MODE = 0;

function setMode(m) { if (m !== MODE) { MODE = m; gl.uniform1f(U.mode, m); } }

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

function box(pos, size, color, rot, emit) {
  let m = M4.scale(size[0], size[1], size[2]);
  if (rot) {
    if (rot[2]) m = M4.mul(m, M4.rotZ(rot[2]));
    if (rot[0]) m = M4.mul(m, M4.rotX(rot[0]));
    if (rot[1]) m = M4.mul(m, M4.rotY(rot[1]));
  }
  draw(MESH.box, M4.mul(m, M4.trans(pos[0], pos[1], pos[2])), color, emit);
}

// ===========================================================================
// 3) SAHNE
// ===========================================================================
const COL = {
  sand:  [0.62,0.49,0.31], sand2: [0.52,0.40,0.25],
  ring:  [0.40,0.30,0.18], wall:  [0.30,0.27,0.31], cap: [0.40,0.36,0.40],
  torch: [1.00,0.62,0.18], flame2:[1.00,0.90,0.50],
  skin:  [0.90,0.72,0.54], skin2: [0.80,0.62,0.45],
  p1:    [0.92,0.26,0.30], p1d:   [0.62,0.16,0.20],
  p2:    [0.24,0.52,0.96], p2d:   [0.14,0.32,0.66],
  steel: [0.78,0.81,0.88], steel2:[0.55,0.58,0.66],
  wood:  [0.42,0.27,0.15], gold:  [0.98,0.80,0.28],
  dark:  [0.16,0.16,0.20], leather:[0.35,0.24,0.16],
};

let R = 12;

// seyirciler (bir kez üretilir)
const CROWD = [];
for (let i = 0; i < 44; i++) {
  const a = i / 44 * Math.PI * 2 + 0.07;
  const row = i % 2;
  CROWD.push({a, r: 14.6 + row * 1.5, h: 1.5 + Math.random() * 0.45,
              ph: Math.random() * 6.28, y: 0.9 + row * 0.75,
              c: [0.09 + Math.random()*0.07, 0.10 + Math.random()*0.07, 0.16 + Math.random()*0.09]});
}
const TORCHES = [];
for (let i = 0; i < 10; i++) TORCHES.push(i / 10 * Math.PI * 2 + 0.3);

let cheer = 0;                  // vuruş olunca kalabalık coşar

function drawScene(t, eye, focus) {
  // --- gökyüzü ---
  setMode(1);
  gl.disable(gl.CULL_FACE);
  draw(MESH.sky, M4.mul(M4.scale(130, 90, 130), M4.trans(0, 20, 0)), [1,1,1]);
  gl.enable(gl.CULL_FACE);

  // --- zemin ---
  setMode(2);
  draw(MESH.disc, M4.mul(M4.scale(R*2, 0.6, R*2), M4.trans(0,-0.3,0)), COL.sand);
  setMode(0);
  draw(MESH.disc, M4.mul(M4.scale(R*2.24, 0.5, R*2.24), M4.trans(0,-0.45,0)), COL.ring);

  // --- duvar (alçak, görüşü kapatmasın) ---
  const seg = 30;
  for (let i = 0; i < seg; i++) {
    const a = i / seg * Math.PI * 2;
    const x = Math.cos(a) * (R + 0.75), z = Math.sin(a) * (R + 0.75);
    // kameraya dövüşçülerden daha yakın olan parçayı çizme (önü kapamasın)
    const dc = Math.hypot(x - eye[0], z - eye[2]);
    const df = Math.hypot(focus[0] - eye[0], focus[2] - eye[2]);
    if (dc < df - 1.5) continue;
    box([x, 0.55, z], [1.5, 1.1, 0.9], COL.wall, [0, -a, 0]);
    box([x, 1.18, z], [1.6, 0.18, 1.0], COL.cap, [0, -a, 0]);
  }

  // --- meşaleler (canlı alev) ---
  for (const a of TORCHES) {
    const x = Math.cos(a) * (R + 0.75), z = Math.sin(a) * (R + 0.75);
    const dc = Math.hypot(x - eye[0], z - eye[2]);
    const df = Math.hypot(focus[0] - eye[0], focus[2] - eye[2]);
    if (dc < df - 1.5) continue;
    box([x, 1.75, z], [0.16, 1.2, 0.16], COL.wood);
    const fl = 0.5 + Math.sin(t*9 + a*5) * 0.14 + Math.sin(t*17 + a) * 0.06;
    setMode(3);
    box([x, 2.5 + fl*0.18, z], [0.34, 0.42 + fl*0.5, 0.34], COL.torch);
    box([x, 2.62 + fl*0.22, z], [0.18, 0.26 + fl*0.3, 0.18], COL.flame2);
    setMode(0);
  }

  // --- seyirciler ---
  const co = cheer;
  for (const p of CROWD) {
    const x = Math.cos(p.a) * p.r, z = Math.sin(p.a) * p.r;
    const dc = Math.hypot(x - eye[0], z - eye[2]);
    const df = Math.hypot(focus[0] - eye[0], focus[2] - eye[2]);
    if (dc < df - 1.5) continue;
    const bob = Math.sin(t * 2.4 + p.ph) * 0.06 + co * Math.abs(Math.sin(t * 13 + p.ph)) * 0.34;
    box([x, p.y + bob, z], [0.5, p.h, 0.5], p.c, [0, -p.a, 0]);
    box([x, p.y + p.h * 0.62 + bob, z], [0.32, 0.32, 0.32], p.c, [0, -p.a, 0]);
  }
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

/* ŞÖVALYE — gerçek iskelet hiyerarşisi.
 *
 * Önemli: her parça KENDİ EKLEMİNDEN döner (kalça, diz, omuz, dirsek).
 * Daha önce her kutu kendi merkezinden dönüyordu; eğilme/düşme açısı
 * büyüyünce gövde dağılıyordu. Artık kol omuzdan, bacak kalçadan dönüyor.
 *
 * Ölçüler "kalça uzayında": kalça y=0, ayaklar y=-1.05, baş y=+0.95.
 */
const HIP_Y = 1.05;             // kalçanın yerden yüksekliği

/** Eklemden sarkan uzuv. Döndürme eklemde olur. Çocuk eklem matrisini döner. */
function limb(parent, jx, jy, jz, rx, rz, sx, sy, sz, color) {
  let j = M4.ident();
  if (rz) j = M4.mul(j, M4.rotZ(rz));
  if (rx) j = M4.mul(j, M4.rotX(rx));
  j = M4.mul(j, M4.trans(jx, jy, jz));
  j = M4.mul(j, parent);
  draw(MESH.box, M4.mul(M4.mul(M4.scale(sx, sy, sz), M4.trans(0, -sy / 2, 0)), j), color);
  return j;
}

/** Merkezi verilen noktada duran kutu (gövde, kafa, kemer gibi). */
function at(parent, cx, cy, cz, sx, sy, sz, color, rx, rz) {
  let m = M4.scale(sx, sy, sz);
  if (rz) m = M4.mul(m, M4.rotZ(rz));
  if (rx) m = M4.mul(m, M4.rotX(rx));
  m = M4.mul(m, M4.trans(cx, cy, cz));
  draw(MESH.box, M4.mul(m, parent), color);
}

function drawFighter(f, col, colDark, anim) {
  const {x, z, yaw} = f;
  const mv = Math.min(1, anim.move);
  const ph = anim.walk;
  const dT = anim.deadT, dead = anim.dead;
  const atk = anim.attack, blk = anim.block, flinch = anim.hitT;

  // --- gövde duruşu (TEK bir kök dönüşü; parçalar buna asılı) ---
  const breathe = Math.sin(anim.t * 1.9) * 0.02 * (1 - mv);
  const bob = Math.abs(Math.sin(ph)) * 0.07 * mv;
  let lean = mv * 0.16 - flinch * 0.30 + (blk ? 0.10 : 0);
  if (atk > 0) lean += Math.sin(atk * Math.PI) * 0.22;
  let roll = 0, y = HIP_Y + bob + breathe - (blk ? 0.12 : 0);
  if (dead) { lean = 0; roll = -Math.PI * 0.47 * dT; y = HIP_Y - 0.58 * dT; }

  // kök: önce eğil/devril, sonra yöne dön, sonra dünyaya yerleş
  let root = M4.rotX(lean);
  root = M4.mul(root, M4.rotZ(roll));
  root = M4.mul(root, M4.rotY(yaw));
  root = M4.mul(root, M4.trans(x, y, z));

  setMode(0);
  const sh = 1.45 - bob * 1.1;
  draw(MESH.disc, M4.mul(M4.scale(sh, 0.02, sh), M4.trans(x, 0.03, z)), [0.05,0.05,0.11]);

  // --- BACAKLAR: kalça -> diz -> ayak ---
  for (const side of [-1, 1]) {
    const p = ph + (side > 0 ? Math.PI : 0);
    const hip = Math.sin(p) * mv * 0.85;
    const knee = Math.max(0, -Math.cos(p)) * mv * 0.95;
    const thigh = limb(root, side * 0.20, 0.02, 0, hip, 0, 0.27, 0.55, 0.29, colDark);
    const shin = limb(thigh, 0, -0.55, 0, knee, 0, 0.23, 0.50, 0.25, COL.leather);
    at(M4.mul(M4.trans(0, -0.50, 0), shin), 0, -0.08, 0.08, 0.28, 0.17, 0.42, COL.dark);
  }

  // --- GÖVDE ---
  at(root, 0, 0.14, 0, 0.66, 0.15, 0.45, COL.gold);          // kemer
  at(root, 0, 0.46, 0, 0.80, 0.60, 0.47, col);               // göğüs zırhı
  at(root, 0, 0.48, 0.25, 0.34, 0.40, 0.06, COL.gold);       // arma
  for (const side of [-1, 1]) {                              // omuzluk
    at(root, side * 0.50, 0.70, 0, 0.34, 0.28, 0.50, col, 0, side * 0.28);
    at(root, side * 0.52, 0.82, 0, 0.30, 0.10, 0.44, COL.gold, 0, side * 0.28);
  }

  // --- PELERİN: omuzdan asılı, koşarken savrulur ---
  const capeA = 0.30 + mv * 0.60 + Math.sin(anim.t * 4.2 + ph) * 0.07 * mv;
  const cape1 = limb(root, 0, 0.74, -0.26, capeA, 0, 0.76, 0.80, 0.06, colDark);
  limb(cape1, 0, -0.80, 0, capeA * 0.55, 0, 0.66, 0.62, 0.05, colDark);

  // --- KAFA + MİĞFER ---
  const neck = M4.mul(M4.trans(0, 0.78, 0), root);
  const nod = -flinch * 0.35 + Math.sin(anim.t * 1.9) * 0.02;
  at(neck, 0, 0.20, 0, 0.40, 0.42, 0.40, COL.skin, nod);
  at(neck, 0, 0.30, 0, 0.46, 0.30, 0.46, COL.steel, nod);
  at(neck, 0, 0.22, 0.21, 0.30, 0.07, 0.06, COL.dark, nod);
  at(neck, 0, 0.52, -0.06, 0.09, 0.28, 0.30, col, 0.30 + nod);      // sorguç
  at(neck, 0, 0.62, -0.20, 0.08, 0.18, 0.34, col, 0.70 + nod);

  // --- SOL KOL (kalkan) ---
  {
    const p = ph + Math.PI;
    const up = blk ? -1.25 : -Math.sin(p) * mv * 0.70;
    const elbow = blk ? 1.15 : 0.22;
    const upper = limb(root, -0.50, 0.62, 0, up, -0.10, 0.24, 0.46, 0.25, col);
    const fore = limb(upper, 0, -0.46, 0, elbow, 0, 0.21, 0.44, 0.22, COL.skin2);
    if (blk) {
      const hand = M4.mul(M4.trans(0, -0.44, 0), fore);
      at(hand, 0, -0.02, 0.16, 1.00, 1.12, 0.13, COL.steel, -0.35);
      at(hand, 0, -0.02, 0.23, 0.72, 0.84, 0.05, COL.steel2, -0.35);
      at(hand, 0, -0.02, 0.27, 0.30, 0.30, 0.05, COL.gold, -0.35);
    }
  }

  // --- SAĞ KOL + SİLAH: hazırlık -> savurma -> toparlanma ---
  {
    const p = ph;
    let up, elbow;
    if (atk > 0) {
      if (atk < 0.34) {                       // silahı arkaya kaldır
        const k = atk / 0.34;
        up = -0.2 - k * 2.2; elbow = 0.3 + k * 1.1;
      } else if (atk < 0.58) {                // hızlı savur
        const k = (atk - 0.34) / 0.24;
        up = -2.4 + k * 3.5; elbow = 1.4 - k * 1.2;
      } else {                                // toparlan
        const k = (atk - 0.58) / 0.42;
        up = 1.1 - k * 1.3; elbow = 0.2 + k * 0.1;
      }
    } else {
      up = -Math.sin(p) * mv * 0.70; elbow = 0.22;
    }
    const upper = limb(root, 0.50, 0.62, 0, up, 0.10, 0.24, 0.46, 0.25, col);
    const fore = limb(upper, 0, -0.46, 0, elbow, 0, 0.21, 0.44, 0.22, COL.skin2);
    const hand = M4.mul(M4.trans(0, -0.44, 0), fore);

    const wp = WEAPONS[anim.weapon] || WEAPONS._def;
    at(hand, 0, 0, 0.02, wp.w + 0.05, 0.20, wp.w + 0.05, COL.leather);        // kabza
    at(hand, 0, 0, 0.16 + wp.len * 0.5, wp.w, wp.w, wp.len, wp.col);          // sap ileri
    if (wp.blade) {
      const h = wp.head || [0.15, 0.7, 0.05];
      at(hand, 0, 0, 0.16 + wp.len * 0.95, h[0], h[2] * 3.0, h[1], COL.steel);
    }
    if (atk > 0.30 && atk < 0.70) {                                          // savurma izi
      setMode(3);
      for (let k = 1; k <= 4; k++) {
        const back = atk - k * 0.05;
        if (back < 0.30) break;
        const kk = (back - 0.34) / 0.24;
        const u2 = back < 0.58 ? -2.4 + kk * 3.5 : 1.1;
        const e2 = back < 0.58 ? 1.4 - kk * 1.2 : 0.2;
        const up2 = limbGhost(root, 0.50, 0.62, 0, u2, 0.10);
        const fo2 = limbGhost(up2, 0, -0.46, 0, e2, 0);
        const h2 = M4.mul(M4.trans(0, -0.44, 0), fo2);
        const fade = 1 - k * 0.21;
        at(h2, 0, 0, 0.16 + wp.len * 0.7, 0.10, 0.10, wp.len * 0.55,
           [0.80 * fade, 0.90 * fade, 1.0]);
      }
      setMode(0);
    }
  }
}

/** Çizmeden sadece eklem matrisi üretir (silah izi için). */
function limbGhost(parent, jx, jy, jz, rx, rz) {
  let j = M4.ident();
  if (rz) j = M4.mul(j, M4.rotZ(rz));
  if (rx) j = M4.mul(j, M4.rotX(rx));
  j = M4.mul(j, M4.trans(jx, jy, jz));
  return M4.mul(j, parent);
}


// ===========================================================================
// 4) PARÇACIKLAR (kıvılcım, toz)
// ===========================================================================
const PARTS = [];
function spawn(x, y, z, n, color, power, grav) {
  for (let i = 0; i < n; i++) {
    if (PARTS.length > 90) break;
    PARTS.push({x, y, z,
      vx: (Math.random()-.5) * power, vy: Math.random() * power * 0.8 + 0.5,
      vz: (Math.random()-.5) * power,
      life: 1, size: 0.10 + Math.random()*0.14, c: color, g: grav === undefined ? 9 : grav});
  }
}
function stepParts(dt) {
  setMode(3);
  for (let i = PARTS.length - 1; i >= 0; i--) {
    const p = PARTS[i];
    p.life -= dt * 1.7;
    if (p.life <= 0) { PARTS.splice(i, 1); continue; }
    p.vy -= p.g * dt;
    p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
    if (p.y < 0.05) { p.y = 0.05; p.vy *= -0.35; p.vx *= 0.7; p.vz *= 0.7; }
    const s = p.size * p.life;
    box([p.x, p.y, p.z], [s, s, s], p.c);
  }
  setMode(0);
}

// ===========================================================================
// 5) DURUM VE AĞ
// ===========================================================================
const S = {
  me: 0, my: null, foe: null, stake: 0, sel: 0, training: false,
  prev: null, cur: null, prevT: 0, curT: 0,
  running: false, anim: {}, ws: null, pending: null, coins: 0,
  camYaw: 0, shake: 0, hitStop: 0, flash: 0,
};
/* Animasyon durumu TEK yerden kurulur.
 * Daha önce iki ayrı yerde kuruluyordu; biri eksik alanlıydı ve
 * "undefined + sayı = NaN" yüzünden tüm matris NaN olup karakter
 * ekrandan tamamen kayboluyordu. Bir daha olmasın. */
function yeniAnim() {
  return {walk: 0, move: 0, attack: 0, deadT: 0, hitT: 0, t: 0, stepPh: 0};
}

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
  const box2 = el('stakes'); box2.innerHTML = '';
  d.stakes.forEach((v, i) => {
    const b = document.createElement('button');
    b.textContent = v === 0 ? 'Bedava' : (v >= 1e6 ? (v/1e6)+'M' : (v/1000)+'K');
    b.className = i === 0 ? 'on' : '';
    b.onclick = () => { S.sel = v; [...box2.children].forEach(c => c.className = '');
                        b.className = 'on'; };
    box2.appendChild(b);
  });
  S.sel = d.stakes[0] || 0;
  el('hint').textContent = 'Gücün bottaki eşyalarından geliyor. Daha iyi silah al, daha güçlü ol.';
}

let reconnectTimer = null;
function setConn(txt) { const c = el('conn'); if (c) c.textContent = txt; }

function connect(onOpen) {
  if (S.ws && (S.ws.readyState === 0 || S.ws.readyState === 1)) {
    if (S.ws.readyState === 1 && onOpen) onOpen();
    else if (onOpen) S.pending = onOpen;
    return;
  }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  setConn('Bağlanıyor…');
  S.ws = new WebSocket(`${proto}://${location.host}/ws`);
  S.ws.onopen = () => { setConn(''); const f = onOpen || S.pending; S.pending = null; if (f) f(); };
  S.ws.onmessage = (e) => onMsg(JSON.parse(e.data));
  S.ws.onerror = () => setConn('Bağlantı hatası');
  S.ws.onclose = () => {
    setConn('Bağlantı koptu — yeniden bağlanılıyor…');
    if (S.running) flash('BAĞLANTI KOPTU\nyeniden bağlanılıyor…', '#ffd66b');
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => connect(), 1200);
  };
}
const send = (o) => { if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify(o)); };

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && (!S.ws || S.ws.readyState > 1)) connect();
});

function onMsg(m) {
  if (m.t === 'queued') {
    show('waiting');
    el('waitInfo').textContent = m.stake ? `Bahis: ${fmt(m.stake)} 🪙` : 'Bedava maç';
  } else if (m.t === 'start') { startMatch(m); }
  else if (m.t === 's') {
    S.prev = S.cur; S.prevT = S.curT;
    S.cur = m; S.curT = performance.now();
    if (m.ev) m.ev.forEach(handleEvent);
    updateHud(m);
  }
  else if (m.t === 'end') endMatch(m);
  else if (m.t === 'err') { show('lobby'); el('hint').textContent = m.m; }
  else if (m.t === 'idle') show('lobby');
}

function startMatch(m) {
  R = m.arena.r;
  const [a, b] = m.f;
  if (m.you) S.me = m.you;
  S.my = a.id === S.me ? a : b;
  S.foe = a.id === S.me ? b : a;
  S.training = !!m.training;
  S.stake = m.stake;
  S.prev = S.cur = null;
  S.anim = {};
  [S.my, S.foe].forEach(f => S.anim[f.id] = yeniAnim());
  el('n1').textContent = S.my.name + ' (sen)';
  el('n2').textContent = S.foe.name;
  el('h1').style.width = '100%'; el('h2').style.width = '100%';
  S.running = true;
  show('game');
  flash(S.training ? 'ANTRENMAN!' : 'DÖVÜŞ!', '#ffd66b');
  SFX.play('start');
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
  if (ev.e === 'miss') { if (ev.id === S.me) SFX.play('swing'); return; }
  if (ev.e !== 'hit') return;
  SFX.play(ev.blk ? 'block' : (ev.crit ? 'crit' : 'hit'));
  const a = S.anim[ev.to]; if (a) a.hitT = 1;
  cheer = 1;
  SFX.cheer(1);
  const pos = S.cur ? S.cur.f.find(f => f.id === ev.to) : null;
  if (pos) {
    const c = ev.blk ? [0.75,0.85,1.0] : (ev.crit ? [1.0,0.85,0.35] : [1.0,0.32,0.28]);
    spawn(pos.x, 1.4, pos.z, ev.crit ? 16 : 9, c, ev.crit ? 7 : 4.5);
  }
  if (ev.to === S.me) {
    S.shake = ev.crit ? 1.0 : 0.55;
    S.flash = ev.crit ? 0.8 : 0.45;
  } else {
    S.shake = Math.max(S.shake, ev.crit ? 0.5 : 0.25);
  }
  S.hitStop = ev.crit ? 0.09 : 0.05;
  popDamage(ev, pos);
}

function popDamage(ev, fpos) {
  const d = document.createElement('div');
  d.className = 'pop';
  const mine = ev.id === S.me;
  d.textContent = (ev.crit ? '💥' : '') + (ev.blk ? '🛡' : '') + '-' + Math.round(ev.d);
  d.style.color = mine ? '#8ef08e' : '#ff8a8a';
  d.style.fontSize = ev.crit ? '28px' : '20px';
  const p = fpos ? project(fpos.x, 2.5, fpos.z) : {x: innerWidth/2, y: innerHeight/2};
  d.style.left = (p.x - 22) + 'px'; d.style.top = p.y + 'px';
  el('hud').appendChild(d);
  requestAnimationFrame(() => { d.style.transform = 'translateY(-80px)'; d.style.opacity = '0'; });
  setTimeout(() => d.remove(), 780);
}

function flash(text, color) {
  const m = el('msg');
  m.textContent = text; m.style.color = color || '#fff'; m.style.opacity = '1';
  setTimeout(() => m.style.opacity = '0', 900);
}

function endMatch(m) {
  S.running = false;
  show('result');
  const win = m.win, draw2 = m.draw;
  el('resTitle').textContent = draw2 ? '🤝 BERABERE' : (win ? '🏆 KAZANDIN!' : '☠️ KAYBETTİN');
  el('resTitle').style.color = draw2 ? '#ffd66b' : (win ? '#8ef08e' : '#ff8a8a');
  SFX.play(win ? 'win' : (draw2 ? 'start' : 'lose'));
  el('resBody').innerHTML =
    (m.training ? '<div class="sub">🥊 Antrenman maçı — coin ve istatistik yok.</div>' : '') +
    (m.prize ? `<div class="stat"><span>💰 Ödül</span><b>+${fmt(m.prize)} 🪙</b></div>` :
     (m.stake && !draw2 && !win ? `<div class="stat"><span>💸 Kaybettiğin</span>` +
        `<b>${fmt(m.stake)} 🪙</b></div>` : '')) +
    `<div class="stat"><span>💢 Verdiğin hasar</span><b>${fmt(m.dmg)}</b></div>` +
    `<div class="stat"><span>🩸 Yediğin hasar</span><b>${fmt(m.taken)}</b></div>` +
    `<div class="stat"><span>👊 İsabetli vuruş</span><b>${m.hits}</b></div>` +
    `<div class="stat"><span>🪙 Bakiyen</span><b>${fmt(m.coins)}</b></div>`;
  S.coins = m.coins;
}

// ===========================================================================
// 6) KAMERA VE ÇİZİM DÖNGÜSÜ
// ===========================================================================
const INTERP = 60;          // ms — bir kare geriden oynatıp arayı doldururuz
let camEye = [0, 11, 17], camAt = [0, 1.4, 0];

function project(wx, wy, wz) {
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
  let dt = Math.min(0.05, (now - last) / 1000); last = now;
  const t = now / 1000;
  if (S.hitStop > 0) { S.hitStop -= dt; dt *= 0.25; }   // vuruş anında zamanı yavaşlat
  cheer = Math.max(0, cheer - dt * 1.2);
  SFX.cheer(cheer);
  S.flash = Math.max(0, S.flash - dt * 2.6);
  el('dmgflash').style.opacity = S.flash * 0.45;

  gl.clearColor(0.012, 0.016, 0.036, 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.uniform1f(U.time, t);

  // Sunucu 20 Hz gönderiyor, biz 60 Hz çiziyoruz.
  // Bir kare geriden (INTERP) oynatıp iki paket ARASINI dolduruyoruz —
  // böylece hareket akıcı olur, zıplamaz.
  let fighters = [];
  if (S.cur) {
    const span = Math.max(1, S.curT - S.prevT);
    const k = clamp((now - INTERP - S.prevT) / span, 0, 1);
    fighters = S.cur.f.map(f => {
      const p = S.prev ? S.prev.f.find(q => q.id === f.id) : null;
      if (!p) return {id: f.id, hp: f.hp, s: f.s, x: f.x, z: f.z, yaw: f.y};
      return {id: f.id, hp: f.hp, s: f.s,
              x: lerp(p.x, f.x, k), z: lerp(p.z, f.z, k),
              yaw: angLerp(p.y, f.y, k)};
    });
  }

  const me = fighters.find(f => f.id === S.me);
  const fo = fighters.find(f => f.id !== S.me);

  // --- kamera: OYUNCUNUN ARKASINDAN, yukarıdan, rakip hep kadrajda ---
  if (me && fo) {
    const d = Math.hypot(fo.x - me.x, fo.z - me.z);
    const want = CQ.camAngle(me.x, me.z, fo.x, fo.z);    // rakipten bana doğru
    S.camYaw = angLerp(S.camYaw, want, 1 - Math.pow(0.0015, dt));
    // Bakış noktası: ikisinin ortası, ama bana biraz yakın.
    const ax = me.x + (fo.x - me.x) * 0.40;
    const az = me.z + (fo.z - me.z) * 0.40;
    // Uzaklık ve yükseklik: iki dövüşçü de hep kadrajda kalsın diye
    // aralarındaki mesafeye göre büyür. Yükseklik uzaklıkla orantılı
    // tutuluyor -> bakış açısı hep ~45 derece, duvar önü kapatmıyor.
    const dist = clamp(8.5 + d * 0.34, 8.5, 15.0);
    const h = clamp(8.0 + d * 0.26, 8.0, 13.5);
    const cp = CQ.camPos(ax, az, S.camYaw, dist);
    const sm = 1 - Math.pow(0.0025, dt);
    camEye = [lerp(camEye[0], cp[0], sm), lerp(camEye[1], h, 0.10), lerp(camEye[2], cp[1], sm)];
    camAt = [lerp(camAt[0], ax, 0.20), 1.25, lerp(camAt[2], az, 0.20)];
  }
  let eye = camEye;
  if (S.shake > 0) {
    S.shake = Math.max(0, S.shake - dt * 3.2);
    eye = [eye[0] + (Math.random()-.5)*S.shake*0.8, eye[1] + (Math.random()-.5)*S.shake*0.4,
           eye[2] + (Math.random()-.5)*S.shake*0.8];
  }
  const proj = M4.persp(0.95, cv.width / cv.height, 0.1, 320);
  VIEWPROJ = M4.mul(M4.look(eye, camAt, [0,1,0]), proj);

  drawScene(t, eye, camAt);

  fighters.forEach(f => {
    const a = S.anim[f.id] || (S.anim[f.id] = yeniAnim());
    const src = f.id === S.me ? S.my : S.foe;
    a.t += dt;

    // Gerçek hız: iki SUNUCU paketi arasındaki yol / geçen süre.
    // (Ekran karesinden ölçersek duruyorken bile titreşim çıkıyordu.)
    let hiz = 0;
    if (S.prev && S.cur) {
      const p = S.prev.f.find(q => q.id === f.id), c2 = S.cur.f.find(q => q.id === f.id);
      if (p && c2) hiz = Math.hypot(c2.x - p.x, c2.z - p.z) / ((S.curT - S.prevT) / 1000 || 0.05);
    }
    const hedef = f.s === 'dead' ? 0 : clamp(hiz / 4.2, 0, 1.35);
    // Kalkan: herhangi bir alan bozulursa (NaN) karakter görünmez olurdu.
    for (const k of ['walk','move','attack','deadT','hitT','t','stepPh']) {
      if (!isFinite(a[k])) a[k] = 0;
    }
    a.move = lerp(a.move, hedef, 1 - Math.pow(0.0008, dt));   // yumuşak geçiş
    if (a.move < 0.02) a.move = 0;                            // DURUNCA TAM DUR
    a.walk += dt * (7 + a.move * 5) * (a.move > 0 ? 1 : 0);
    if (a.move === 0) a.walk = lerp(a.walk % (Math.PI*2), 0, 1 - Math.pow(0.02, dt));

    a.attack = f.s === 'attack' ? Math.min(1, a.attack + dt * 3.2) : 0;
    a.deadT = f.s === 'dead' ? Math.min(1, a.deadT + dt * 2.6) : 0;
    a.hitT = Math.max(0, a.hitT - dt * 3.2);

    // ayak sesi + toz: adım tam yere basınca
    if (a.move > 0.15) {
      const yeni = Math.floor(a.walk / Math.PI);
      if (yeni !== a.stepPh) {
        a.stepPh = yeni;
        spawn(f.x, 0.10, f.z, 2, [0.55,0.44,0.30], 1.3, 5);
        if (f.id === S.me) SFX.play('step');
      }
    }
    if (f.s === 'dash' && Math.random() < 0.6) spawn(f.x, 0.14, f.z, 1, [0.6,0.5,0.35], 2.0, 4);

    const mine = f.id === S.me;
    let col = (mine ? COL.p1 : COL.p2).slice();
    let colD = (mine ? COL.p1d : COL.p2d).slice();
    if (a.hitT > 0) {
      col = col.map(v => Math.min(1, v + a.hitT * 0.95));
      colD = colD.map(v => Math.min(1, v + a.hitT * 0.8));
    }
    drawFighter(f, col, colD, {
      walk: a.walk, move: a.move, t: a.t,
      attack: a.attack, block: f.s === 'block', dead: f.s === 'dead',
      deadT: a.deadT, hitT: a.hitT, weapon: (src && src.weapon) || '',
    });
  });

  stepParts(dt);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// ===========================================================================
// 7) KONTROLLER  (sadece niyet gönderir)
// ===========================================================================
const IN = {mx: 0, mz: 0, atk: false, blk: false, dash: false};
let lastSent = 0;

function pump() {
  if (S.running) {
    const now = performance.now();
    if (now - lastSent > 50) {
      lastSent = now;
      // Çubuğu kameraya göre dünyaya çevir (matematik controls.js'te, testi var)
      const w = CQ.moveToWorld(IN.mx, IN.mz, S.camYaw);
      if (IN.atk) SFX.play('swing');
      if (IN.dash) SFX.play('dash');
      send({t:'in', mx: w[0], mz: w[1], atk: IN.atk, blk: IN.blk, dash: IN.dash});
      IN.atk = false; IN.dash = false;
    }
  }
  requestAnimationFrame(pump);
}
requestAnimationFrame(pump);

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
  if (!touching) {
    const l = Math.hypot(x, z);
    IN.mx = l ? x / l : 0; IN.mz = l ? z / l : 0;
  }
  IN.blk = !!(keys.ShiftLeft || keys.ShiftRight) || blockHeld;
}, 33);

// --- dokunmatik çubuk ---
let touching = false, stickId = null;
const stick = el('stick'), knob = el('knob');
function stickMove(t) {
  const r = stick.getBoundingClientRect();
  let dx = t.clientX - (r.left + r.width/2), dy = t.clientY - (r.top + r.height/2);
  const max = r.width/2 - 8, d = Math.hypot(dx, dy);
  if (d > max) { dx = dx/d*max; dy = dy/d*max; }
  knob.style.transform = `translate(${dx}px,${dy}px)`;
  // Ekranda YUKARI çekmek = ileri.  dy negatif olur, mz de negatif olur. Doğru.
  IN.mx = dx / max; IN.mz = dy / max;
}
stick.addEventListener('touchstart', e => {
  touching = true; stickId = e.changedTouches[0].identifier;
  stickMove(e.changedTouches[0]); e.preventDefault();
}, {passive:false});
stick.addEventListener('touchmove', e => {
  for (const t of e.changedTouches) if (t.identifier === stickId) stickMove(t);
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
// 8) MENÜ DÜĞMELERİ
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

if (window.Telegram && window.Telegram.WebApp) {
  try { window.Telegram.WebApp.expand(); window.Telegram.WebApp.ready(); } catch (e) {}
}

// Tarayıcı sese ancak ilk dokunuştan sonra izin verir
['touchstart', 'mousedown', 'keydown'].forEach(ev =>
  addEventListener(ev, () => SFX.unlock(), {once: true, passive: true}));

el('btnSound').onclick = () => {
  SFX.unlock();
  el('btnSound').textContent = SFX.toggle() ? '🔊' : '🔇';
};

loadMe();
connect();
