/* Kontrol matematiği — ayrı dosya, çünkü test edilebilir olması şart.
 *
 * Buradaki tek iş: oyuncunun çubuğu (ekran yönü) hangi DÜNYA yönüne karşılık
 * geliyor onu bulmak. Bir kez ters çevrildiği için ayrı tutuluyor ve testi var.
 *
 * Kamera hedefin (sin(yaw), cos(yaw)) yönünde durur:
 *    ileri (ekranda yukarı) = (-sin, -cos)
 *    sağ   (ekranda sağ)    = ( cos, -sin)
 * Çubukta yukarı = mz -1 olduğundan, ileri katsayısı -mz olur.
 */
(function (root) {
  'use strict';

  /** Çubuk yönünü (mx, mz) kamera açısına göre dünya yönüne çevirir. */
  function moveToWorld(mx, mz, yaw) {
    const c = Math.cos(yaw), s = Math.sin(yaw);
    //  mx * sağ + (-mz) * ileri
    //  = mx*( cos, -sin) + (-mz)*(-sin, -cos)
    //  = ( mx*cos + mz*sin ,  -mx*sin + mz*cos )
    return [mx * c + mz * s, -mx * s + mz * c];
  }

  /** Kameranın durması gereken açı: rakipten oyuncuya doğru bakış. */
  function camAngle(meX, meZ, foeX, foeZ) {
    return Math.atan2(meX - foeX, meZ - foeZ);
  }

  /** Kamera göz konumu (hedefin arkasında ve yukarıda). */
  function camPos(ax, az, yaw, dist) {
    return [ax + Math.sin(yaw) * dist, az + Math.cos(yaw) * dist];
  }

  const api = {moveToWorld, camAngle, camPos};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CQ = api;
})(typeof window !== 'undefined' ? window : globalThis);
