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
  if (uMode > 0.5 && uMode < 1.5) {        // gökyüzü: yukarıdan aşağı geçiş
    float h = clamp(vL.y + 0.5, 0.0, 1.0);
    col = mix(vec3(0.05,0.07,0.16), vec3(0.012,0.015,0.035), h);
    col += vec3(0.30,0.20,0.10) * pow(1.0 - h, 6.0) * 0.75;   // ufuktaki sıcak parıltı
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
  col = base * (0.32 + 0.68*d) + vec3(0.38,0.52,0.95)*rim*0.30;
  float spec = pow(max(dot(reflect(-L, n), normalize(vec3(0.0,0.4,1.0))), 0.0), 24.0);
  col += vec3(1.0,0.94,0.80) * spec * 0.22;
  col += uColor * uEmit;
  float fog = clamp((length(vW.xz) - 12.0) / 22.0, 0.0, 0.80);
  col = mix(col, vec3(0.030,0.040,0.085), fog);
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
  sand:  [0.42,0.33,0.21], sand2: [0.35,0.27,0.17],
  ring:  [0.30,0.22,0.13], wall:  [0.17,0.15,0.21], cap: [0.24,0.21,0.28],
  torch: [1.00,0.66,0.24], flame2:[1.00,0.86,0.42],
  skin:  [0.86,0.68,0.50], skin2: [0.76,0.58,0.42],
  p1:    [0.90,0.28,0.32], p2:    [0.26,0.55,0.95],
  steel: [0.76,0.78,0.84], wood:  [0.40,0.26,0.15], gold: [0.96,0.79,0.30],
  dark:  [0.13,0.14,0.19], crowd: [0.10,0.11,0.17],
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

function drawFighter(f, col, anim) {
  const {x, z, yaw} = f;
  const sw = Math.sin(anim.walk) * anim.moving;
  const dead = anim.dead;
  const lean = dead ? Math.PI/2 * anim.deadT : (anim.attack > 0 ? 0.16 : 0);
  const yBase = dead ? 0.4 * (1 - anim.deadT) : 0;

  const P = (lx, ly, lz) => {
    const c = Math.cos(yaw), s = Math.sin(yaw);
    return [x + lx*c + lz*s, ly + yBase, z - lx*s + lz*c];
  };
  const rot = (ex, ez) => [ (ex||0) + lean, yaw, ez||0 ];

  // gölge
  setMode(0);
  draw(MESH.disc, M4.mul(M4.scale(1.45, 0.02, 1.45), M4.trans(x, 0.03, z)), [0.05,0.05,0.10]);

  box(P(-0.22, 0.42 - Math.abs(sw)*0.05, sw*0.30), [0.26, 0.85, 0.26], COL.dark, rot(sw*0.75));
  box(P( 0.22, 0.42 - Math.abs(sw)*0.05, -sw*0.30), [0.26, 0.85, 0.26], COL.dark, rot(-sw*0.75));
  box(P(0, 1.28, 0), [0.74, 0.94, 0.46], col, rot());
  box(P(0, 1.02, 0.24), [0.50, 0.34, 0.06], [col[0]*0.7, col[1]*0.7, col[2]*0.7], rot());
  box(P(-0.47, 1.62, 0), [0.30, 0.30, 0.48], col, rot());
  box(P( 0.47, 1.62, 0), [0.30, 0.30, 0.48], col, rot());
  box(P(0, 1.95, 0), [0.44, 0.44, 0.44], COL.skin, rot());
  box(P(0, 2.13, 0), [0.50, 0.22, 0.50], col, rot());
  box(P(0, 2.30, 0), [0.14, 0.30, 0.14], COL.gold, rot());     // tepelik

  const atkA = anim.attack;
  const swing = atkA > 0 ? Math.sin(atkA * Math.PI) : 0;
  const blk = anim.block;

  box(P(blk ? -0.30 : -0.49, blk ? 1.42 : 1.25, (blk ? 0.34 : 0) + sw*0.20),
      [0.22, 0.7, 0.22], COL.skin2, rot(blk ? -1.1 : -sw*0.65));
  if (blk) {
    box(P(-0.26, 1.42, 0.64), [0.94, 1.04, 0.12], COL.steel, rot(0.1));
    box(P(-0.26, 1.42, 0.72), [0.34, 0.34, 0.06], COL.gold, rot(0.1));
  }

  const rSwing = swing * 1.9 - (atkA > 0 ? 0.5 : 0);
  box(P(0.49, 1.28 + swing*0.26, sw*-0.20 + swing*0.44), [0.22, 0.7, 0.22], COL.skin2,
      rot(-rSwing + sw*0.65));

  const wp = WEAPONS[anim.weapon] || WEAPONS._def;
  const wx = 0.53, wy = 1.15 + swing*0.52, wz = 0.30 + swing*0.88;
  const tilt = -0.9 - rSwing;
  box(P(wx, wy, wz), [wp.w, wp.len, wp.w], wp.col, rot(tilt));
  if (wp.blade) {
    const h = wp.head || [0.15,0.7,0.05];
    const hx = wx, hy = wy + Math.cos(tilt)*wp.len*0.52, hz = wz + Math.sin(tilt)*wp.len*0.52;
    box(P(hx, hy, hz), h, COL.steel, rot(tilt));
    // vuruş izi
    if (swing > 0.25) {
      setMode(3);
      for (let k = 1; k <= 3; k++) {
        const s2 = swing - k * 0.16;
        if (s2 <= 0) continue;
        const t2 = -0.9 - (s2 * 1.9 - 0.5);
        box(P(wx, 1.15 + s2*0.52 + Math.cos(t2)*wp.len*0.45, 0.30 + s2*0.88 + Math.sin(t2)*wp.len*0.45),
            [0.10, 0.36, 0.10], [0.85 - k*0.2, 0.90 - k*0.2, 1.0], rot(t2));
      }
      setMode(0);
    }
  }
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
  [S.my, S.foe].forEach(f => S.anim[f.id] = {walk:0, attack:0, deadT:0, hitT:0, lastX:0, lastZ:0});
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
  const a = S.anim[ev.to]; if (a) a.hitT = 1;
  cheer = 1;
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
  S.flash = Math.max(0, S.flash - dt * 2.6);
  el('dmgflash').style.opacity = S.flash * 0.45;

  gl.clearColor(0.012, 0.016, 0.036, 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.uniform1f(U.time, t);

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

  // --- kamera: OYUNCUNUN ARKASINDAN, yukarıdan, rakip hep kadrajda ---
  if (me && fo) {
    const d = Math.hypot(fo.x - me.x, fo.z - me.z);
    const want = CQ.camAngle(me.x, me.z, fo.x, fo.z);    // rakipten bana doğru
    S.camYaw = angLerp(S.camYaw, want, 1 - Math.pow(0.0015, dt));
    const dist = 7.2 + d * 0.42;
    const h = 6.6 + d * 0.30;                            // yüksek açı: duvar kapatmaz
    const ax = me.x + (fo.x - me.x) * 0.42;
    const az = me.z + (fo.z - me.z) * 0.42;
    const cp = CQ.camPos(ax, az, S.camYaw, dist);
    const ex = cp[0], ez = cp[1];
    const sm = 1 - Math.pow(0.002, dt);
    camEye = [lerp(camEye[0], ex, sm), lerp(camEye[1], h, 0.09), lerp(camEye[2], ez, sm)];
    camAt = [lerp(camAt[0], ax, 0.18), 1.35, lerp(camAt[2], az, 0.18)];
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
    const a = S.anim[f.id] || (S.anim[f.id] = {walk:0, attack:0, deadT:0, hitT:0, lastX:f.x, lastZ:f.z});
    const src = f.id === S.me ? S.my : S.foe;
    const moved = Math.hypot(f.x - (a.lastX||f.x), f.z - (a.lastZ||f.z));
    a.lastX = f.x; a.lastZ = f.z;
    const moving = moved > 0.008 ? 1 : 0;
    a.walk += dt * 10 * moving;
    a.attack = f.s === 'attack' ? Math.min(1, a.attack + dt * 4.4) : 0;
    a.deadT = f.s === 'dead' ? Math.min(1, a.deadT + dt * 3) : 0;
    a.hitT = Math.max(0, a.hitT - dt * 3.5);
    if (moving && Math.random() < (f.s === 'dash' ? 0.7 : 0.14)) {
      spawn(f.x, 0.12, f.z, 1, [0.45,0.36,0.24], 1.2, 4);   // ayak tozu
    }
    let col = f.id === S.me ? COL.p1.slice() : COL.p2.slice();
    if (a.hitT > 0) col = col.map(c => Math.min(1, c + a.hitT * 0.95));
    drawFighter(f, col, {
      walk: a.walk, moving: moving * (f.s === 'dash' ? 1.8 : 1),
      attack: a.attack, block: f.s === 'block', dead: f.s === 'dead',
      deadT: a.deadT, weapon: (src && src.weapon) || '',
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

loadMe();
connect();
