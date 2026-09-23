// Escena `contador3d`: columnas de monedas en Three.js. Misma curva que el contador HTML (GSAP
// power1.in = u^2, power3.in = u^4) INVERTIDA: cada moneda aparece en el instante exacto en que la
// cifra pasa por su valor -> 3D y número no pueden desincronizarse. Determinista vía hf-seek.
import * as THREE from "./assets/_motor/three/three.module.min.js";
import { RoomEnvironment } from "./assets/_motor/three/RoomEnvironment.js";

const { P1, P2, t0: T0, t1: T1, cols: COLS, valor: V } = window.__P3D;
const timeForValue = (v) => v <= P1[2]
  ? P1[0] + P1[1] * Math.sqrt(v / P1[2])
  : P2[0] + P2[1] * Math.pow((v - P1[2]) / (P2[2] - P1[2]), 0.25);
const TLAND = P2[0] + P2[1];

const canvas = document.getElementById("three-layer");
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
renderer.setSize(1080, 1920, false); renderer.setPixelRatio(1);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(30, 1080 / 1920, 0.1, 200);
const key = new THREE.DirectionalLight(0xfff1d0, 2.4); key.position.set(4, 9, 6); scene.add(key);
const rim = new THREE.DirectionalLight(0x1f9e6e, 1.6); rim.position.set(-6, 3, -5); scene.add(rim);
const burst = new THREE.PointLight(0xffd27a, 0, 30); burst.position.set(3.8, 5, 2.5); scene.add(burst);
const grid = new THREE.GridHelper(24, 24, 0x1f9e6e, 0x1f9e6e);
grid.material.transparent = true; grid.material.opacity = 0.22; scene.add(grid);

const SP = 1.25, CH = 0.14, wts = [...Array(COLS)].map((_, i) => Math.exp(0.75 * i));
const WS = wts.reduce((a, b) => a + b, 0);
const counts = wts.map((x) => Math.round(30 * x / wts[COLS - 1]) + 1);
const coins = []; let cum = 0;
for (let c = 0; c < COLS; c++) {
  const colValue = V * wts[c] / WS, unit = colValue / counts[c];
  for (let j = 0; j < counts[c]; j++) coins.push({ c, j, t: Math.min(timeForValue(Math.min(cum + unit * (j + 0.5), V - 1)), TLAND - 0.01) });
  cum += colValue;
}
const geo = new THREE.CylinderGeometry(0.52, 0.52, CH * 0.86, 48);
const mat = [new THREE.MeshStandardMaterial({ color: 0xa8812f, metalness: 0.95, roughness: 0.42 }),
  new THREE.MeshStandardMaterial({ color: 0xe6c46e, metalness: 0.85, roughness: 0.18 }),
  new THREE.MeshStandardMaterial({ color: 0xe6c46e, metalness: 0.85, roughness: 0.18 })];
const mesh = new THREE.InstancedMesh(geo, mat, coins.length); scene.add(mesh);
const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), pos = new THREE.Vector3(), sc = new THREE.Vector3(1, 1, 1), up = new THREE.Vector3(0, 1, 0);
let seed = 99; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
coins.forEach((k) => { k.dx = (rnd() - 0.5) * 0.06; k.dz = (rnd() - 0.5) * 0.06; k.rot = rnd() * 6.28; });
const clamp = (x) => Math.max(0, Math.min(1, x));

function renderAt(time) {
  const FALL = 0.24;
  coins.forEach((k, i) => {
    const u = clamp((time - k.t) / FALL), vis = time >= k.t;
    const drop = (1 - u * u) * 3.2;
    const settle = u >= 1 ? Math.max(0, 0.05 * Math.sin((time - k.t - FALL) * 30) * Math.exp(-(time - k.t - FALL) * 12)) : 0;
    pos.set((k.c - (COLS - 1) / 2) * SP + k.dx, CH / 2 + k.j * CH + drop + settle, k.dz);
    qt.setFromAxisAngle(up, k.rot); sc.setScalar(vis ? 1 : 0.0001);
    m4.compose(pos, qt, sc); mesh.setMatrixAt(i, m4);
  });
  mesh.instanceMatrix.needsUpdate = true;
  const p = clamp((time - T0) / (T1 - T0));
  const yaw = -0.35 + 0.55 * p, dist = 26 - 4 * p;
  const hit = time > TLAND ? Math.exp(-(time - TLAND) * 9) : 0;
  const shake = hit * 0.12 * Math.sin(time * 90);
  camera.position.set(Math.sin(yaw) * dist + shake, 9 + 1.2 * p, Math.cos(yaw) * dist);
  camera.lookAt(0.2, 2.2 + shake, 0);
  burst.intensity = hit * 60;
  renderer.render(scene, camera);
}
window.addEventListener("hf-seek", (e) => renderAt(e.detail.time));
renderAt(window.__hfThreeTime || 0);
