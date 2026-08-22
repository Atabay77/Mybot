/* Ses motoru — hiçbir ses DOSYASI gerekmez, hepsi anında üretilir.
 *
 * Neden böyle: ses dosyaları megabaytlarca yer tutar ve yavaş bağlantıda
 * oyunun açılmasını geciktirir. Buradaki sesler tarayıcının kendi ses
 * üretecinden (WebAudio) çıkıyor — sıfır indirme, anında çalıyor.
 *
 * Müzik istersen: webapp/music.mp3 dosyasını koyman yeterli, kendiliğinden
 * bulup çalar. Yoksa sadece arena uğultusu olur.
 */
(function (root) {
  'use strict';

  let ctx = null, master = null, on = true, started = false;
  let crowdGain = null, musicEl = null;

  function init() {
    if (ctx) return true;
    const AC = root.AudioContext || root.webkitAudioContext;
    if (!AC) return false;
    try { ctx = new AC(); } catch (e) { return false; }
    master = ctx.createGain();
    master.gain.value = 0.85;
    master.connect(ctx.destination);
    startCrowd();
    return true;
  }

  /** Tarayıcılar sese ancak kullanıcı ekrana dokununca izin verir. */
  function unlock() {
    if (!init()) return;
    if (ctx.state === 'suspended') ctx.resume();
    if (!started) {
      started = true;
      tryMusic();
    }
  }

  function noiseBuffer(sec) {
    const n = Math.floor(ctx.sampleRate * sec);
    const buf = ctx.createBuffer(1, n, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }

  /** Sürekli arena uğultusu — kalabalık coşunca yükselir. */
  function startCrowd() {
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer(3);
    src.loop = true;
    const f = ctx.createBiquadFilter();
    f.type = 'bandpass'; f.frequency.value = 620; f.Q.value = 0.6;
    crowdGain = ctx.createGain();
    crowdGain.gain.value = 0.018;
    src.connect(f); f.connect(crowdGain); crowdGain.connect(master);
    src.start();
  }

  function beep(freq, dur, type, vol, slideTo) {
    if (!on || !ctx) return;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type || 'sine';
    o.frequency.setValueAtTime(freq, ctx.currentTime);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, ctx.currentTime + dur);
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(vol || 0.2, ctx.currentTime + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    o.connect(g); g.connect(master);
    o.start(); o.stop(ctx.currentTime + dur + 0.02);
  }

  function burst(dur, freq, q, vol, type) {
    if (!on || !ctx) return;
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer(Math.max(0.08, dur));
    const f = ctx.createBiquadFilter();
    f.type = type || 'bandpass';
    f.frequency.setValueAtTime(freq, ctx.currentTime);
    f.Q.value = q || 1;
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol || 0.25, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    src.connect(f); f.connect(g); g.connect(master);
    src.start(); src.stop(ctx.currentTime + dur + 0.02);
  }

  const SFX = {
    swing()  { burst(0.16, 1900, 1.6, 0.16); },                       // havada kılıç
    hit()    { burst(0.13, 340, 1.1, 0.34); beep(150, 0.16, 'sine', 0.30, 60); },
    crit()   { burst(0.20, 520, 1.0, 0.45); beep(210, 0.28, 'sawtooth', 0.30, 70);
               beep(1250, 0.22, 'triangle', 0.14, 900); },
    block()  { beep(2100, 0.13, 'square', 0.13, 1500);                // metal şıngırtısı
               beep(1450, 0.18, 'triangle', 0.11, 1000); burst(0.07, 3200, 3, 0.10); },
    miss()   { burst(0.11, 900, 1.2, 0.07); },
    step()   { burst(0.05, 240, 1.4, 0.055); },
    dash()   { burst(0.20, 700, 0.8, 0.14, 'lowpass'); },
    start()  { beep(440, 0.14, 'triangle', 0.22); setTimeout(() => beep(660, 0.22, 'triangle', 0.24), 150); },
    win()    { [523, 659, 784, 1046].forEach((f, i) =>
                 setTimeout(() => beep(f, 0.28, 'triangle', 0.24), i * 130)); },
    lose()   { [392, 330, 262].forEach((f, i) =>
                 setTimeout(() => beep(f, 0.36, 'sine', 0.22), i * 190)); },
    tap()    { beep(880, 0.05, 'square', 0.08); },
    cheer(v) { if (crowdGain && ctx) {
                 crowdGain.gain.setTargetAtTime(0.018 + v * 0.075, ctx.currentTime, 0.15); } },
  };

  /** Müzik dosyası varsa çalar (webapp/music.mp3). Yoksa sessizce geçer. */
  function tryMusic() {
    if (musicEl) return;
    musicEl = new Audio('/static/music.mp3');
    musicEl.loop = true;
    musicEl.volume = 0.28;
    musicEl.addEventListener('error', () => { musicEl = null; });   // dosya yok, sorun değil
    musicEl.play().catch(() => {});
  }

  const api = {
    unlock,
    play(name, arg) { if (!on || !ctx) return; const f = SFX[name]; if (f) f(arg); },
    cheer(v) { if (on) SFX.cheer(v); },
    toggle() {
      on = !on;
      if (master) master.gain.value = on ? 0.85 : 0;
      if (musicEl) { if (on) musicEl.play().catch(() => {}); else musicEl.pause(); }
      return on;
    },
    isOn() { return on; },
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SFX = api;
})(typeof window !== 'undefined' ? window : globalThis);
