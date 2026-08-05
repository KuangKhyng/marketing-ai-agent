import { useRef, useEffect } from 'react';

/**
 * Cảnh nền: khối tinh thể wireframe xoay chậm trên lưới phối cảnh.
 *
 * Vẽ bằng canvas 2D với phép chiếu phối cảnh tự viết — không kéo three.js
 * về chỉ để vẽ vài chục đoạn thẳng (three.js nặng hơn cả bundle hiện tại).
 *
 * Tự dừng khi tab ẩn và khi người dùng bật giảm chuyển động.
 */

const RING = 6;

// Khối bipyramid — đỉnh ngắn phía trên, mũi dài phía dưới
const GEM = (() => {
  const v = [[0, -1.05, 0]];
  for (let i = 0; i < RING; i++) {
    const a = (i / RING) * Math.PI * 2;
    v.push([Math.cos(a) * 0.74, 0.05, Math.sin(a) * 0.74]);
  }
  v.push([0, 1.5, 0]);

  const e = [];
  for (let i = 0; i < RING; i++) {
    e.push([0, 1 + i]);
    e.push([1 + i, 1 + ((i + 1) % RING)]);
    e.push([1 + i, RING + 1]);
  }
  return { v, e };
})();

// Vài khối hộp rải trên mặt lưới cho cảnh có chiều sâu
const BOXES = [
  [-3.4, 0, 1.2, 0.85, 0.42], [-2.1, 0, 2.6, 0.6, 0.3],
  [-4.3, 0, 3.4, 0.7, 0.5],   [ 2.4, 0, 1.6, 0.75, 0.36],
  [ 3.7, 0, 3.0, 0.55, 0.26], [ 1.5, 0, 3.9, 0.9, 0.22],
];

function boxEdges(cx, cy, cz, w, h) {
  const x0 = cx - w, x1 = cx + w, z0 = cz - w, z1 = cz + w, y0 = cy, y1 = cy - h;
  const p = [
    [x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1],
    [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1],
  ];
  const e = [[0,1],[1,2],[2,3],[3,0], [4,5],[5,6],[6,7],[7,4], [0,4],[1,5],[2,6],[3,7]];
  return { p, e };
}

export default function Scene({ intensity = 1 }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let w = 0, h = 0, dpr = 1, raf = 0, t = 0, running = true;

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    // Chiếu điểm 3D -> 2D. Camera nhìn hơi chếch xuống, tâm cảnh dưới giữa màn.
    const project = (x, y, z) => {
      const cz = z + 6.2;
      const d = 5.4 / Math.max(cz, 0.35);
      const scale = Math.min(w, 980) * 0.125;
      return [w / 2 + x * d * scale, h * 0.26 + (y - 0.35) * d * scale, d];
    };

    const line = (a, b, alpha) => {
      const a2 = alpha * intensity;
      if (a2 <= 0.004) return;
      ctx.globalAlpha = a2;
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]);
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.lineWidth = 1;

      // ---- Lưới mặt sàn, mờ dần về phía chân trời ----
      ctx.strokeStyle = '#ffffff';
      const FAR = 15, HALF = 9;
      for (let z = 0; z <= FAR; z++) {
        const a = project(-HALF, 0, z), b = project(HALF, 0, z);
        line(a, b, 0.05 * (1 - z / FAR) ** 1.5);
      }
      for (let x = -HALF; x <= HALF; x++) {
        const a = project(x, 0, 0), b = project(x, 0, FAR);
        ctx.globalAlpha = 1;
        const g = ctx.createLinearGradient(a[0], a[1], b[0], b[1]);
        g.addColorStop(0, `rgba(255,255,255,${.05 * intensity})`);
        g.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.strokeStyle = g;
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.stroke();
      }

      // ---- Khối hộp ----
      ctx.strokeStyle = '#ffffff';
      for (const [bx, by, bz, bw, bh] of BOXES) {
        const { p, e } = boxEdges(bx, by, bz, bw, bh);
        const pts = p.map(([x, y, z]) => project(x, y, z));
        const fade = Math.max(0, 1 - bz / 6);
        for (const [i, j] of e) line(pts[i], pts[j], 0.075 * fade);
      }

      // ---- Tinh thể, xoay quanh trục đứng ----
      const ang = t * 0.00022;
      const tilt = Math.sin(t * 0.00013) * 0.10;
      const cos = Math.cos(ang), sin = Math.sin(ang);
      const ct = Math.cos(tilt), st = Math.sin(tilt);

      const pts = GEM.v.map(([x, y, z]) => {
        const rx = x * cos - z * sin;
        const rz = x * sin + z * cos;
        const ry = y * ct - rz * st;
        const rz2 = y * st + rz * ct;
        return project(rx, ry - 0.55, rz2 + 0.4);
      });

      ctx.strokeStyle = '#a8c8a1';
      ctx.lineWidth = 1.25;
      for (const [i, j] of GEM.e) {
        const depth = (pts[i][2] + pts[j][2]) / 2;
        line(pts[i], pts[j], 0.22 + Math.max(0, depth - 0.7) * 0.34);
      }

      ctx.globalAlpha = 1;
    };

    const loop = (now) => {
      if (!running) return;
      t = now;
      draw();
      raf = requestAnimationFrame(loop);
    };

    const onVisibility = () => {
      running = !document.hidden && !reduced;
      if (running) raf = requestAnimationFrame(loop);
      else cancelAnimationFrame(raf);
    };

    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', onVisibility);

    if (reduced) {
      running = false;
      draw(); // một khung tĩnh
    } else {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intensity]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 w-full h-full"
      style={{ zIndex: 0 }}
    />
  );
}
