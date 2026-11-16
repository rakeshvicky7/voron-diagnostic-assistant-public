// Shared 3D printer for the Assembly page and the Repair assistant.
// createPrinter(viewElement, hooks) builds the scene: a simplified Voron 0.2 from the documented sizes, the official CAD
// (when it has been converted), the print simulation driven by /api/twin, part picking and highlighting, and the
// "units" used by the assembly animation.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

// Each solid of the CAD assembly is mapped to one of the 31 parts by its name and the names of the assemblies above it.
const CAD_RULES = [
 [/Filament Runout|Runout Sensor/i, 'filament_runout_sensor'], [/PTFE Tube Insert/i, 'heatbreak_ptfe'],
 [/Filament Spool|Spool Holder|\/Spool\b|Filament Guide Path|\/Filament\b|PTFE Tube|Bowden/i, 'filament_material'],
 [/Revo[^/]*\/[^/]*Nozzle|\/Nozzle(?! LED)/i, 'nozzle'], [/Revo Voron Mount|Hotend Mounts/i, 'toolhead'], [/Revo/i, 'hotend_heater'],
 [/36mm Round Stepper/i, 'extruder_motor'], [/BMG|Drive Gear|Idler Gear|Guidler|50 Tooth Gear|Extruder|Extriuder/i, 'extruder_gears_guidler'],
 [/Blower/i, 'part_cooling_fan'], [/Electronics[^]*Fan/i, 'controller_board'], [/Axial Fan/i, 'hotend_fan'],
 [/Mini Stealthburner|Nozzle LEDs|ADXL|X Carriage/i, 'toolhead'], [/Drag Chain|Strain Relief/i, 'umbilical_wiring'],
 [/A Belt|B Belt|\/Belts/i, 'xy_belts'], [/Pulley|Idler|Bearing Stacks|F623|Shuttle|XY Joint/i, 'xy_pulleys_idlers'],
 [/A Drive|B Drive|AB Drives|Nema14/i, 'xy_motors_drivers'],
 [/Z Endstop|Omron|Microswitch/i, 'z_endstop'], [/Integrated Leadscrew|Z Motor|TR8x8|T8 Nut|Leadscrew/i, 'z_motor_leadscrew'],
 [/X Axis[^]*(MGN7|Linear Rail)/i, 'x_linear_rail'], [/Y Axis[^]*(MGN7|Linear Rail)|Y Rail Stop/i, 'y_linear_rails'], [/Z Axis[^]*(MGN7|Linear Rail)|Z Rail Stop/i, 'z_rails'],
 [/Silicone Bed Heater/i, 'bed_heater'], [/MIC6|Build Plate|Flex Plate|Magnetic Sheet|Bed Assembly|Die Spring|Rear Bed Mount|Stealth Bed|Thumb Nut/i, 'bed_plate_carrier'],
 [/LRS-150|PSU/i, 'power_supply'], [/Mains Inlet/i, 'mains_power_input'], [/SKR Pico|BTT/i, 'controller_board'], [/Raspberry|RPi|Pi 4/i, 'host_computer'],
];
const CAD_PANEL = /Side Panels|Door Assembly|Extrusion Tophat\/Panels|Tophat Top Panel|Tophat Side Panel/i, CAD_HIDE = /\/Banana|\/Tools\//i, CAD_FRAME = /Extrusions|\/1515/i;
const CAD_MOVE = [['head', /X Carriage|Mini Stealthburner|Revo|Extruder|BMG|Hotend Mounts|Nozzle LEDs|ADXL|36mm Round Stepper/i], ['gantry', /X Axis|XY Joint/i], ['bed', /Bed Assembly/i]];
const LAYERS = 18, LH_VIS = 0.7, LW_VIS = 1.1, CUBE = 30, TIP = 170, FRAME_H = 262, HALF = 115;
const W = (X, Y) => [X - 60, 60 - Y];        // printer coordinates (bed 0..120 mm) -> world x, z
const v3 = (x, y, z) => new THREE.Vector3(x, y, z);

export function createPrinter(view, hooks = {}) {
  const P = { opt: { speed: 5, follow: false, static: false }, glow: new Set(), selected: null, hooks };
  // ---------------- scene ----------------
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false }); renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  view.appendChild(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0xf3f4f6);
  try { const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; } catch (e) { /* plain lights only */ }
  const camera = new THREE.PerspectiveCamera(38, 1, 1, 9000); const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
  let camGoal = null, userMoved = false; controls.addEventListener('start', () => { userMoved = true; camGoal = null; });
  P.resetView = (dist = 1) => { const far = Math.max(1, 1.25 / Math.max(.6, camera.aspect)) * dist; camera.position.set(430 * far, 330 * far, 560 * far); controls.target.set(0, 110, 0); controls.update(); userMoved = false; };
  P.flyTo = (pos, target) => { camGoal = { pos: pos.clone(), target: (target || controls.target).clone() }; userMoved = false; };
  P.snapView = () => { if (!camGoal) return; camera.position.copy(camGoal.pos); controls.target.copy(camGoal.target); controls.update(); camGoal = null; };   // jump to where the camera was flying to
  const hemi = new THREE.HemisphereLight(0xffffff, 0xb9bec6, 0.7); scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffffff, 1.1); sun.position.set(300, 600, 400); scene.add(sun);
  const grid = new THREE.GridHelper(3200, 128, 0xd2d6dc, 0xe4e7eb); grid.position.y = -82; scene.add(grid);
  function resize() { const r = view.getBoundingClientRect(); if (r.width < 10 || r.height < 10) return; renderer.setSize(r.width, r.height); camera.aspect = r.width / r.height; camera.updateProjectionMatrix(); }
  new ResizeObserver(resize).observe(view); resize(); P.resetView(); P.resize = resize;

  // ---------------- materials and helpers ----------------
  const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: .6, metalness: .2, ...o });
  const mat = { alu: M(0x9aa3ad, { metalness: .6, roughness: .4 }), black: M(0x2a2e34), steel: M(0xc8ced6, { metalness: .8, roughness: .3 }), printed: M(0x34383f),
    green: M(0x1e7a3b), pei: M(0xc9a54a, { roughness: .8 }), copper: M(0xb87333, { metalness: .7 }),
    acrylic: new THREE.MeshPhysicalMaterial({ color: 0x7fb8e6, transparent: true, opacity: .14, roughness: .1, depthWrite: false }) };
  const parts = {}; P.parts = parts; const extra = { frame: [], deck: [], skirts: [], panels: [] };
  function tag(mesh, part) { if (!part) return mesh; mesh.userData.part = part; (parts[part] ||= []).push(mesh); return mesh; }
  function box(w, h, d, m, x, y, z, part, parent = scene) { const g = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m.clone()); g.position.set(x, y, z); parent.add(g); return tag(g, part); }
  function cyl(r, h, m, x, y, z, part, parent = scene, axis = 'y', seg = 24) { const g = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, seg), m.clone()); g.position.set(x, y, z);
    if (axis === 'x') g.rotation.z = Math.PI / 2; if (axis === 'z') g.rotation.x = Math.PI / 2; parent.add(g); return tag(g, part); }
  function seg(mesh, a, b, t) { const d = b.clone().sub(a); const L = d.length(); mesh.scale.set(t, L || .001, t); mesh.position.copy(a).add(b).multiplyScalar(.5);
    mesh.quaternion.setFromUnitVectors(v3(0, 1, 0), d.normalize()); }
  const unitBox = new THREE.BoxGeometry(1, 1, 1);

  // ---------------- simplified printer (documented sizes) ----------------
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) extra.frame.push(box(15, FRAME_H, 15, mat.black, sx * (HALF - 7.5), FRAME_H / 2, sz * (HALF - 7.5)));
  for (const y of [7.5, FRAME_H - 7.5]) for (const sz of [-1, 1]) { extra.frame.push(box(2 * HALF - 30, 15, 15, mat.black, 0, y, sz * (HALF - 7.5))); extra.frame.push(box(15, 15, 2 * HALF - 30, mat.black, sz * (HALF - 7.5), y, 0)); }
  extra.deck.push(box(2 * HALF, 3, 2 * HALF, M(0x3a4048), 0, 0, 0)); extra.deck.push(box(2 * HALF, 3, 2 * HALF, M(0x3a4048), 0, -80, 0));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) extra.skirts.push(box(12, 80, 12, mat.printed, sx * (HALF - 6), -40, sz * (HALF - 6)));
  for (const sx of [-1, 1]) { const p = new THREE.Mesh(new THREE.PlaneGeometry(2 * HALF, FRAME_H), mat.acrylic.clone()); p.rotation.y = Math.PI / 2; p.position.set(sx * HALF, FRAME_H / 2, 0); scene.add(p); extra.panels.push(p); }
  { const p = new THREE.Mesh(new THREE.PlaneGeometry(2 * HALF, FRAME_H), mat.acrylic.clone()); p.position.set(0, FRAME_H / 2, HALF); scene.add(p); extra.panels.push(p);
    const t = new THREE.Mesh(new THREE.PlaneGeometry(2 * HALF, 2 * HALF), mat.acrylic.clone()); t.rotation.x = -Math.PI / 2; t.position.set(0, FRAME_H, 0); scene.add(t); extra.panels.push(t); }
  const ZR_Z = -100;
  for (const sx of [-1, 1]) box(7, 150, 8, mat.steel, sx * 35, 95, ZR_Z, 'z_rails');
  cyl(4, 260, mat.steel, 0, 100, ZR_Z, 'z_motor_leadscrew'); box(42, 48, 42, mat.black, 0, -45, ZR_Z, 'z_motor_leadscrew');
  box(12, 6, 20, M(0xeeeeee), 52, 32, ZR_Z, 'z_endstop'); box(2, 8, 2, M(0xd04040), 52, 37, ZR_Z + 8, 'z_endstop');
  const bed = new THREE.Group(); scene.add(bed);
  box(120, 6.35, 120, mat.alu, 0, -3.2, 0, 'bed_plate_carrier', bed); box(120, .6, 120, mat.pei, 0, .3, 0, 'bed_plate_carrier', bed);
  const pad = box(100, 1.5, 100, M(0x7a1f1a), 0, -7.2, 0, 'bed_heater', bed);
  box(6, 2, 4, M(0x444444), 30, -8.5, 30, 'bed_thermistor', bed); box(8, 3, 5, M(0x6a6a6a), -30, -8.5, 30, 'bed_thermal_fuse', bed);
  for (const [bx, by] of [[60, 5], [5, 115], [115, 115]]) { const [x, z] = W(bx, by); cyl(4, 20, M(0xd8c22a), x, -18, z, 'bed_plate_carrier', bed); }
  box(110, 6, 12, mat.printed, 0, -30, -50, 'bed_plate_carrier', bed); box(12, 6, 70, mat.printed, -50, -30, -20, 'bed_plate_carrier', bed);
  box(12, 6, 70, mat.printed, 50, -30, -20, 'bed_plate_carrier', bed); box(90, 20, 14, mat.printed, 0, -30, ZR_Z + 6, 'bed_plate_carrier', bed);
  const printGroup = new THREE.Group(); bed.add(printGroup);
  const GY = TIP + 52;
  for (const sx of [-1, 1]) box(7, 8, 150, mat.steel, sx * 100, GY, 0, 'y_linear_rails');
  const gantry = new THREE.Group(); scene.add(gantry);
  box(150, 8, 7, mat.steel, 0, GY, 0, 'x_linear_rail', gantry);
  for (const sx of [-1, 1]) { box(22, 18, 30, mat.printed, sx * 100, GY, 0, 'y_linear_rails', gantry); cyl(5, 10, mat.steel, sx * 100, GY + 14, 8, 'xy_pulleys_idlers', gantry); }
  box(35, 35, 35, mat.black, -95, GY + 10, -105, 'xy_motors_drivers'); box(35, 35, 35, mat.black, 95, GY + 10, -105, 'xy_motors_drivers');
  cyl(6, 8, mat.steel, -95, GY + 31, -105, 'xy_pulleys_idlers'); cyl(6, 8, mat.steel, 95, GY + 37, -105, 'xy_pulleys_idlers');
  for (const sx of [-1, 1]) cyl(5, 10, mat.steel, sx * 100, GY + 34, 100, 'xy_pulleys_idlers');
  const beltA = [], beltB = [];
  for (let i = 0; i < 7; i++) { beltA.push(tag(new THREE.Mesh(unitBox, M(0x2f6fb5)), 'xy_belts')); beltB.push(tag(new THREE.Mesh(unitBox, M(0xc8762b)), 'xy_belts')); scene.add(beltA[i], beltB[i]); }
  const head = new THREE.Group(); scene.add(head);
  box(40, 46, 30, mat.printed, 0, 50, 0, 'toolhead', head); box(32, 28, 26, M(0x3a3f47), 0, 86, -2, 'extruder_gears_guidler', head);
  cyl(18, 14, mat.black, 0, 107, -2, 'extruder_motor', head);
  const heatsink = cyl(11, 22, mat.alu, 0, 24, 0, 'heatbreak_ptfe', head); cyl(2, 10, mat.steel, 0, 10, 0, 'heatbreak_ptfe', head);
  const block = box(20, 10, 16, M(0x8f949a, { metalness: .7 }), 0, 4, 0, 'hotend_heater', head);
  cyl(3, 18, M(0x8a2a20), 0, 4, 5, 'hotend_heater', head, 'x'); cyl(1.4, 10, M(0xdddddd), -5, 3, -6, 'hotend_thermistor', head, 'x');
  { const nz = new THREE.Mesh(new THREE.ConeGeometry(3.5, 6, 16), mat.copper.clone()); nz.rotation.x = Math.PI; nz.position.set(0, -4, 0); head.add(nz); tag(nz, 'nozzle'); }
  const hfan = new THREE.Group(); hfan.position.set(0, 26, 17); head.add(hfan); box(30, 30, 8, mat.black, 0, 0, 0, 'hotend_fan', hfan);
  const hblades = new THREE.Group(); hfan.add(hblades);
  for (let i = 0; i < 7; i++) { const b = box(3, 12, 1, M(0x555a60), 0, 6, 4.5, 'hotend_fan', hblades); b.position.set(Math.sin(i * .9) * 6, Math.cos(i * .9) * 6, 4.5); b.rotation.z = -i * .9; }
  const pfans = [];
  for (const sx of [-1, 1]) { const g = new THREE.Group(); g.position.set(sx * 26, 30, 0); head.add(g); box(10, 30, 30, M(0x2f343b), 0, 0, 0, 'part_cooling_fan', g);
    const w = new THREE.Group(); g.add(w); for (let i = 0; i < 6; i++) { const b = box(1, 10, 2.5, M(0x666b72), 5.5, 0, 0, 'part_cooling_fan', w); b.position.set(5.5, Math.sin(i * 1.05) * 6, Math.cos(i * 1.05) * 6); } pfans.push(w);
    box(6, 6, 6, M(0x2f343b), sx * 14, 2, 0, 'part_cooling_fan', head); }
  const tube = () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3([v3(0, 0, 0), v3(0, 1, 0)]), 8, 3, 6);
  const umb = tag(new THREE.Mesh(tube(), M(0x1d1f22)), 'umbilical_wiring'); scene.add(umb);
  const fil = tag(new THREE.Mesh(tube(), M(0xd9d9d9, { transparent: true, opacity: .9 })), 'filament_material'); scene.add(fil);
  const spool = new THREE.Group(); spool.position.set(0, 175, -170); scene.add(spool);
  { const s = new THREE.Mesh(new THREE.TorusGeometry(45, 18, 12, 40), M(0xe0e0e0)); s.rotation.y = Math.PI / 2; spool.add(s); tag(s, 'filament_material'); cyl(28, 40, M(0x333333), 0, 0, 0, 'filament_material', spool, 'x'); }
  box(16, 14, 14, mat.printed, 0, FRAME_H + 10, -100, 'filament_runout_sensor');
  box(99, 30, 82, mat.alu, -55, -60, 15, 'power_supply'); const psuLed = box(3, 3, 3, M(0x30ff60, { emissive: 0x30ff60 }), -8, -50, 56);
  box(85, 3, 56, mat.green, 45, -62, 40, 'controller_board'); box(10, 6, 8, M(0xcccccc), 30, -58, 55, 'controller_board');
  box(85, 3, 56, M(0x1f6b33), 45, -62, -40, 'host_computer'); const piLed = box(3, 3, 3, M(0xff3030, { emissive: 0xff3030 }), 80, -59, -20);
  box(10, 8, 8, M(0x6b4bc4), 60, -56, -30, 'firmware_config_macros');
  box(30, 24, 10, M(0x111111), -80, -40, -HALF + 5, 'mains_power_input'); cyl(4, 120, M(0x111111), -80, -40, -HALF - 60, 'mains_power_input', scene, 'z');
  for (const [c, dx] of [[0xd02020, 0], [0x202020, 4]]) { const w = tag(new THREE.Mesh(unitBox, M(c)), 'dc_power_wiring'); scene.add(w); seg(w, v3(-5, -55, 30 + dx), v3(30, -60, 60 + dx), 2.5); }
  box(14, 10, 2, M(0x2f6fb5), 80, -40, HALF - 2, 'slicer_settings');

  // ---------------- print simulation state ----------------
  const S = { X: 60, Y: 60, Z: 0, sim: null, path: [], i: 0, layer: 0, running: false, paused: false, phase: 'idle', fanOn: true, partFan: false,
    hot: 22, bedT: 22, err: null, beltSag: { a: 0, b: 0 }, shiftAcc: [0, 0], power: true, cursor: 0, zDrop: 0, layers: LAYERS };
  P.S = S;
  function buildPath() { const p = []; const c = 60, h = CUBE / 2;
    for (let L = 0; L < LAYERS; L++) {
      for (const inset of [0, 1.6]) { const a = h - inset; const pts = [[c - a, c - a], [c + a, c - a], [c + a, c + a], [c - a, c + a], [c - a, c - a]];
        p.push({ L, travel: true, to: pts[0] }); for (let k = 1; k < pts.length; k++) p.push({ L, to: pts[k] }); }
      const a = h - 3.2; const dir = L % 2;
      for (let k = -a; k <= a; k += 4) { const s = dir ? [[c + k, c - a], [c + k, c + a]] : [[c - a, c + k], [c + a, c + k]];
        const [s0, s1] = (Math.round((k + a) / 4) % 2) ? [s[1], s[0]] : s; p.push({ L, travel: true, to: s0 }); p.push({ L, to: s1 }); } }
    return p; }
  const depMat = M(0xe8a33d, { roughness: .5 }), depMatThin = M(0xf0c070, { roughness: .5 }), depMatSquish = M(0xb57a22, { roughness: .4 });
  // the printed lines are drawn as instances (3 draw calls for the whole print instead of one per line)
  const DEP_MAX = 12000, depMats = [depMat, depMatThin, depMatSquish], depObj = new THREE.Object3D();
  const depInst = depMats.map(m => { const im = new THREE.InstancedMesh(unitBox, m, DEP_MAX); im.count = 0; im.frustumCulled = false; printGroup.add(im); return im; });
  function clearPrint() { for (const im of depInst) { im.count = 0; im.instanceMatrix.needsUpdate = true; } }
  function gapAt(X, Y) { const g = S.sim?.z_grid; if (!g || g.length < 9) return 0;
    const fx = Math.min(1, Math.max(0, (X - 10) / 100)) * 2, fy = Math.min(1, Math.max(0, (Y - 10) / 100)) * 2;
    const ix = Math.min(1, Math.floor(fx)), iy = Math.min(1, Math.floor(fy)), tx = fx - ix, ty = fy - iy, G = (i, j) => g[i * 3 + j];
    return (G(ix, iy) * (1 - tx) + G(ix + 1, iy) * tx) * (1 - ty) + (G(ix, iy + 1) * (1 - tx) + G(ix + 1, iy + 1) * tx) * ty; }
  function deposit(a, b, L) { const sim = S.sim || {}; let flow;
    if (sim.flow_stop_layer) flow = L < sim.flow_stop_layer ? (sim.flow_start ?? 1) : 0; else flow = L < 1 ? (sim.flow_start ?? 1) : (sim.flow_late ?? 1);
    if (flow <= 0.03 || Math.random() > Math.min(1, flow + .15)) return;
    let w = LW_VIS * Math.min(1.4, Math.max(.35, flow)), h = LH_VIS, m = flow > 1.05 ? depMatSquish : flow < .9 ? depMatThin : depMat;
    if (L === 0) { const e = gapAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
      if (e > .12 && Math.random() < .5) return; w *= Math.min(1.8, Math.max(.4, 1 - e * 5)); h *= Math.min(1.3, Math.max(.5, 1 + e * 3)); m = e < -.06 ? depMatSquish : e > .06 ? depMatThin : m; }
    const im = depInst[depMats.indexOf(m)]; if (im.count >= DEP_MAX) return; const [ax, az] = W(...a), [bx, bz] = W(...b); const y = (L + .5) * LH_VIS + .6;
    const len = Math.hypot(bx - ax, bz - az); if (len < .05) return;
    depObj.scale.set(len + w * .5, h, w); depObj.position.set((ax + bx) / 2, y, (az + bz) / 2); depObj.rotation.set(0, -Math.atan2(bz - az, bx - ax), 0); depObj.updateMatrix();
    im.setMatrixAt(im.count++, depObj.matrix); im.instanceMatrix.needsUpdate = true; }
  const banner = (msg, bad = true, sticky = false) => hooks.onBanner && hooks.onBanner(msg, bad, sticky);
  function updateMachine(dt) {
    const [hx, hz] = W(S.X, S.Y); let jx = 0, jz = 0;
    if (S.sim?.ringing && S.phase === 'print') { jx = (Math.random() - .5) * 1.2; jz = (Math.random() - .5) * 1.2; }
    head.position.set(hx + jx, TIP + 4, hz + jz); gantry.position.set(0, 0, hz);
    const tilt = S.sim?.bed_tilt || [0, 0]; const drop = (S.phase === 'print' || S.phase === 'done') ? (S.layer + 1) * LH_VIS : S.Z;
    bed.position.y = TIP - 3.6 - drop - (S.zDrop || 0); bed.rotation.z = -tilt[0] / 120 * 10; bed.rotation.x = tilt[1] / 120 * 10;
    const loopB = (arr, y, side, sag) => { const pts = [v3(hx + side * 20, y, hz), v3(side * 100, y, hz), v3(side * 100, y - sag, -105 + (hz + 105) / 2), v3(side * 95, y, -105), v3(-side * 95, y, -105), v3(-side * 100, y, 100), v3(-side * 100, y - sag, hz + (100 - hz) / 2), v3(hx - side * 20, y, hz)];
      for (let k = 0; k < arr.length; k++) seg(arr[k], pts[k], pts[k + 1], 2.5); };
    loopB(beltA, GY + 31, -1, S.beltSag.a); loopB(beltB, GY + 37, 1, S.beltSag.b);
    umb.geometry.dispose(); umb.geometry = new THREE.TubeGeometry(new THREE.CatmullRomCurve3([v3(hx, TIP + 70, hz - 10), v3(hx * .6, FRAME_H + 30, hz * .5 - 40), v3(0, FRAME_H - 10, -HALF + 10)]), 24, 3, 6);
    fil.geometry.dispose(); fil.geometry = new THREE.TubeGeometry(new THREE.CatmullRomCurve3([v3(0, 175, -170 + 45), v3(0, FRAME_H + 10, -110), v3(hx * .5, FRAME_H + 45, hz * .5 - 30), v3(hx, TIP + 115, hz)]), 30, 1.1, 6);
    if (S.power && S.fanOn) hblades.rotation.z += dt * 40; if (S.power && S.partFan) pfans.forEach(w => w.rotation.x += dt * 50);
    const hc = Math.min(1, Math.max(0, (S.hot - 22) / 230)); block.material.color.setRGB(.56 + .44 * hc, .58 - .3 * hc, .6 - .45 * hc);
    const creep = S.sim?.creep && S.layer >= 3 ? Math.min(1, (S.layer - 3) / 3) : 0; heatsink.material.color.setRGB(.6 + .4 * creep, .64 - .2 * creep, .68 - .5 * creep);
    psuLed.material.emissive.setHex(S.power ? 0x30ff60 : 0x000000); piLed.material.emissive.setHex(S.power ? 0xff3030 : 0x000000);
    renderer.toneMappingExposure = S.power ? 1.0 : .35;
    if (S.sim?.umbilical_flicker && S.phase === 'print' && Math.random() < .03) banner('Toolhead cable: the thermistor / fan signal drops for a moment');
  }
  function stopWith(msg) { S.running = false; S.err = msg; banner(msg, true, true); hooks.onStop && hooks.onStop(msg); }
  // run one simulated print: {fault, severity, seed, settings}
  P.run = async (o = {}) => {
    const st = encodeURIComponent(JSON.stringify(o.settings || {}));
    let sim; try { sim = await (await fetch(`/api/twin?fault=${o.fault || ''}&severity=${o.severity ?? 0.6}&seed=${o.seed ?? 1}&settings=${st}`)).json(); } catch (e) { banner('The assistant server is not running.', true, true); return null; }
    S.sim = sim; S.path = buildPath(); S.i = 0; S.layer = -1; S.resumed = false; bed.position.x = 0; S.Z = 0; S.zDrop = 0; S.err = null; S.power = true; S.shiftAcc = [0, 0]; S.cursor = 0;
    S.hot = 22; S.bedT = 22; S.fanOn = false; S.partFan = false; clearPrint(); banner(null);
    const ta = sim.belt_hz?.a ?? 110, tb = sim.belt_hz?.b ?? 110; S.beltSag = { a: Math.max(0, (1 - (ta / 110) ** 2)) * 25, b: Math.max(0, (1 - (tb / 110) ** 2)) * 25 };
    S.running = true; S.paused = false; S.phase = 'home'; S.phaseT = 0; return sim; };
  P.pause = (on) => { S.paused = on ?? !S.paused; if (!S.paused && !S.err) banner(null); return S.paused; };
  function step(dt) {
    if (!S.running || S.paused) return; const sim = S.sim; dt *= P.opt.speed; S.phaseT += dt;
    if (S.phase === 'home') {
      S.X += (120 - S.X) * Math.min(1, dt * 1.5); S.Y += (120 - S.Y) * Math.min(1, dt * 1.5);
      const zt = sim.z_home === 'Stops too early' ? 50 : sim.z_home === 'Z does not move' ? 0 : 120; S.Z += (zt - S.Z) * Math.min(1, dt * 1.2);
      if (sim.z_home === 'Bed crashes / does not stop') { S.zDrop = Math.min(25, S.zDrop + dt * 8); bed.position.x = (Math.random() - .5) * 1.5; }
      if (!sim.homed && S.phaseT > .5) return stopWith('Klipper: ' + (sim.errors[0] || 'cannot connect to the printer'));
      if (S.phaseT > 3) { if (sim.z_home !== 'Homes correctly') return stopWith(`Z homing: ${sim.z_home.toLowerCase()}` + (sim.errors.length ? ` — "${sim.errors[sim.errors.length - 1]}"` : ''));
        S.phase = 'heat'; S.phaseT = 0; S.fanOn = sim.hotend_fan; }
      return; }
    if (S.phase === 'heat') {
      const k = Math.min(sim.hot.length - 1, Math.floor(S.phaseT * 20)); S.cursor = k; S.hot = Math.max(22, sim.hot[k] ?? 22); S.bedT = Math.max(22, sim.bed[k] ?? 22);
      S.Z += (0 - S.Z) * Math.min(1, dt); S.X += (60 - S.X) * Math.min(1, dt); S.Y += (45 - S.Y) * Math.min(1, dt);
      if (sim.off_phase === 'heat' && S.phaseT > 4) { if (sim.power_lost) { S.power = false; return stopWith('The whole printer switched off while heating' + (sim.restarted ? ' (it came back on, the print was lost)' : '')); }
        return stopWith('Klipper: ' + (sim.errors[0] || 'shutdown')); }
      if (S.phaseT > 5) { S.phase = 'print'; S.phaseT = 0; S.Z = 0; } return; }
    S.cursor = Math.min(sim.hot.length - 1, S.cursor + dt * 2); S.hot = Math.max(22, sim.hot[Math.floor(S.cursor)] ?? S.hot); S.bedT = Math.max(22, sim.bed[Math.floor(S.cursor)] ?? S.bedT);
    let budget = 60 * dt;
    while (budget > 0 && S.i < S.path.length) {
      const mv = S.path[S.i];
      if (mv.L !== S.layer) {
        S.layer = mv.L; S.Z = S.layer * .2; S.partFan = sim.part_fan && S.layer >= 3;
        if (sim.stop_layer && S.layer + 1 >= sim.stop_layer) { if (sim.power_lost) { S.power = false; return stopWith('The whole printer switched off' + (sim.restarted ? ' — it came back on by itself, the print is lost' : '')); }
          return stopWith('Klipper: ' + (sim.errors[0] || 'shutdown') + ` (layer ${S.layer + 1})`); }
        if (sim.runout_pause && S.layer === 6 && !S.resumed) { S.paused = true; S.resumed = true; banner('Print paused: "Filament runout detected" — but there is filament in the sensor.', true, true); return; }
        const sh = sim.shift; if (sh && S.layer >= sh.from_layer && (S.layer - sh.from_layer) % sh.every === 0) { S.shiftAcc[0] += sh.dx * 2; S.shiftAcc[1] += sh.dy * 2;
          banner(`Layer shift at layer ${S.layer + 1}` + (sim.noise !== 'No' ? ` (${sim.noise.toLowerCase()})` : '')); }
        if (sim.flow_stop_layer && S.layer === sim.flow_stop_layer) banner(sim.e_motor !== 'Turns normally' ? `Extrusion stops — extruder: ${sim.e_motor.toLowerCase()}` : 'Extrusion stops');
      }
      const tgt = mv.to, skew = (sim.skew_deg || 0) * Math.PI / 180;
      const real = [tgt[0] + S.shiftAcc[0] + (tgt[1] - 60) * Math.tan(skew), tgt[1] + S.shiftAcc[1]];
      const dx = real[0] - S.X, dy = real[1] - S.Y, d = Math.hypot(dx, dy);
      if (d <= budget) { const from = [S.X, S.Y]; S.X = real[0]; S.Y = real[1]; budget -= d; if (!mv.travel) deposit(from, real, S.layer); S.i++; }
      else { const from = [S.X, S.Y]; S.X += dx / d * budget; S.Y += dy / d * budget; if (!mv.travel) deposit(from, [S.X, S.Y], S.layer); budget = 0; }
    }
    if (S.i >= S.path.length) { S.running = false; S.phase = 'done'; banner(sim.fault ? 'Print finished. Compare the result with your printer.' : 'Print finished: a healthy print.', !!sim.fault); hooks.onDone && hooks.onDone(sim); }
  }

  // ---------------- official CAD ----------------
  const cadParts = {}; let CAD = null, cadOn = false; P.cadOn = () => cadOn;
  const nm = o => (o.name || '').replace(/_/g, ' ');
  const pathOf = o => { const n = []; for (let x = o; x && x !== CAD?.root; x = x.parent) if (x.name) n.unshift(nm(x)); return '/' + n.join('/'); };
  const INSIDE = { nozzle: 'hotend_heater', hotend_thermistor: 'hotend_heater', heatbreak_ptfe: 'hotend_heater', bed_thermistor: 'bed_heater', bed_thermal_fuse: 'bed_heater', dc_power_wiring: 'power_supply', firmware_config_macros: 'controller_board', slicer_settings: 'host_computer' };
  function activeParts() { if (!cadOn) return parts; const out = { ...cadParts }; for (const [pid, list] of Object.entries(parts)) if (!out[pid]) out[pid] = (INSIDE[pid] && cadParts[INSIDE[pid]]) || list; return out; }
  P.activeParts = activeParts;
  const bb = o => new THREE.Box3().setFromObject(o), boxOf = list => list.reduce((b, o) => b.union(bb(o)), new THREE.Box3());
  async function loadCad() {
    let gltf; try { gltf = await new GLTFLoader().loadAsync('/cad/voron02r1.glb'); } catch (e) { return null; }
    const root = gltf.scene; CAD = { root, groups: {}, panel: [], frame: [], solids: 0, mapped: 0 }; scene.add(root);
    root.traverse(o => { if (!o.isMesh) return; CAD.solids++; o.material = o.material.clone(); const p = pathOf(o);
      const rule = CAD_RULES.find(([rx]) => rx.test(p)); if (rule) { o.userData.part = rule[1]; (cadParts[rule[1]] ||= []).push(o); CAD.mapped++; }
      if (CAD_PANEL.test(p)) { o.material.transparent = true; o.material.opacity = .2; o.material.depthWrite = false; CAD.panel.push(o); }
      if (CAD_FRAME.test(p)) CAD.frame.push(o);
      if (CAD_HIDE.test(p)) { o.visible = false; o.userData.hidden = true; } });
    const taken = new Set();
    for (const [g, rx] of CAD_MOVE) { CAD.groups[g] = [];
      root.traverse(o => { if (o === root || !rx.test(nm(o))) return; for (let x = o.parent; x; x = x.parent) if (taken.has(x)) return;
        if (CAD.groups[g].some(a => { let y = o.parent; while (y) { if (y === a) return true; y = y.parent; } return false; })) return;
        CAD.groups[g].push(o); taken.add(o); }); }
    const find = rx => { const l = []; root.traverse(o => { if (rx.test(nm(o))) l.push(o); }); return l; };
    root.updateMatrixWorld(true);
    const size = boxOf([root]).getSize(v3(0, 0, 0)); if (Math.max(size.x, size.y, size.z) < 5) root.scale.setScalar(1000);
    root.updateMatrixWorld(true);
    const feet = find(/Feet|Rubber Foot/i), top = find(/Tophat Top Panel|Top Panel/i);
    if (feet.length && top.length) { const d = boxOf(top).getCenter(v3(0, 0, 0)).sub(boxOf(feet).getCenter(v3(0, 0, 0)));
      const ax = ['x', 'y', 'z'].reduce((a, b) => Math.abs(d[b]) > Math.abs(d[a]) ? b : a, 'y');
      if (ax === 'z') root.rotation.x = d.z > 0 ? -Math.PI / 2 : Math.PI / 2; else if (ax === 'x') root.rotation.z = d.x > 0 ? Math.PI / 2 : -Math.PI / 2; else if (d.y < 0) root.rotation.x = Math.PI; }
    root.updateMatrixWorld(true);
    const door = find(/Door Assembly|Door Panel/i), all = boxOf([root]).getCenter(v3(0, 0, 0));
    if (door.length && boxOf(door).getCenter(v3(0, 0, 0)).z < all.z) root.rotation.y += Math.PI;
    root.updateMatrixWorld(true);
    const plates = find(/MIC6/i).length ? find(/MIC6/i) : find(/Build Plate/i), deck = find(/Deck Panel/i);
    const c = boxOf(plates.length ? plates : CAD.groups.bed).getCenter(v3(0, 0, 0)); const deckTop = deck.length ? boxOf(deck).max.y : boxOf([root]).min.y + 80;
    root.position.set(-c.x, -deckTop, -c.z); root.updateMatrixWorld(true);
    const hot = find(/^Revo Voron$/i), headB = boxOf(hot.length ? hot : CAD.groups.head);
    const plate = boxOf(find(/Build Plate|Flex Plate|MIC6/i).length ? find(/Build Plate|Flex Plate|MIC6/i) : CAD.groups.bed);
    const nz = headB.getCenter(v3(0, 0, 0));
    CAD.ref = { X0: nz.x + 60, Y0: 60 - nz.z, gap0: headB.min.y - plate.max.y, bedTop0: plate.max.y };
    for (const g of Object.values(CAD.groups)) for (const o of g) o.userData.w0 = o.getWorldPosition(v3(0, 0, 0));
    CAD.printHolder = new THREE.Group(); scene.add(CAD.printHolder);
    CAD.floor = feet.length ? boxOf(feet).min.y : boxOf([root]).min.y;
    mergeCad(root);
    return CAD;
  }
  // The CAD has about 2000 small solids. Drawing each one by itself is slow on a laptop GPU, so solids that always move together and belong to the
  // same part are joined into one mesh (colours go into the vertices). Result: about 100 draw calls instead of 2000.
  function mergeCad(root) {
    root.updateMatrixWorld(true);
    const moving = new Set(Object.values(CAD.groups).flat()), isPanel = new Set(CAD.panel), isFrame = new Set(CAD.frame), buckets = new Map();
    const segs = o => { let n = 0; for (let x = o; x && x !== root; x = x.parent) if (x.name) n++; return n; };
    root.traverse(m => { if (!m.isMesh || m.userData.hidden || moving.has(m) || !m.geometry?.attributes?.position) return;
      let anchor = null; for (let x = m.parent; x && x !== root; x = x.parent) if (moving.has(x) || (x.name && segs(x) === 3)) { anchor = x; break; }
      if (!anchor) return;
      const key = [anchor.uuid, m.userData.part || '', isPanel.has(m) ? 1 : 0, isFrame.has(m) ? 1 : 0, m.material.transparent ? m.material.opacity : 1].join('|');
      if (!buckets.has(key)) buckets.set(key, { anchor, list: [] }); buckets.get(key).list.push(m); });
    const swap = (arr, old, neu) => { const out = arr.filter(m => !old.has(m)); if (out.length !== arr.length) out.push(neu); return out; };
    const M = new THREE.Matrix4(), inv = new THREE.Matrix4(), N = new THREE.Matrix3(), v = v3(0, 0, 0);
    for (const { anchor, list } of buckets.values()) { if (list.length < 2) continue;
      let nv = 0, ni = 0; for (const m of list) { const g = m.geometry; if (!g.attributes.normal) g.computeVertexNormals(); nv += g.attributes.position.count; ni += g.index ? g.index.count : g.attributes.position.count; }
      const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), col = new Float32Array(nv * 3), idx = new Uint32Array(ni); let vo = 0, io = 0; inv.copy(anchor.matrixWorld).invert();
      for (const m of list) { const g = m.geometry, P0 = g.attributes.position, N0 = g.attributes.normal, c = m.material.color, n = P0.count; M.multiplyMatrices(inv, m.matrixWorld); N.getNormalMatrix(M);
        for (let i = 0; i < n; i++) { const k = (vo + i) * 3; v.fromBufferAttribute(P0, i).applyMatrix4(M); pos[k] = v.x; pos[k + 1] = v.y; pos[k + 2] = v.z;
          v.fromBufferAttribute(N0, i).applyMatrix3(N).normalize(); nor[k] = v.x; nor[k + 1] = v.y; nor[k + 2] = v.z; col[k] = c.r; col[k + 1] = c.g; col[k + 2] = c.b; }
        if (g.index) { const a = g.index.array, L = g.index.count; for (let i = 0; i < L; i++) idx[io + i] = a[i] + vo; io += L; } else { for (let i = 0; i < n; i++) idx[io + i] = vo + i; io += n; }
        vo += n; }
      const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); geo.setAttribute('color', new THREE.BufferAttribute(col, 3)); geo.setIndex(new THREE.BufferAttribute(idx, 1));
      const first = list[0], mat = first.material; mat.color.setRGB(1, 1, 1); mat.vertexColors = true; mat.needsUpdate = true;
      const merged = new THREE.Mesh(geo, mat); merged.userData.part = first.userData.part; anchor.add(merged);
      const old = new Set(list); for (const m of list) m.parent.remove(m);
      if (merged.userData.part) cadParts[merged.userData.part] = swap(cadParts[merged.userData.part], old, merged);
      CAD.panel = swap(CAD.panel, old, merged); CAD.frame = swap(CAD.frame, old, merged); }
    root.updateMatrixWorld(true);
  }
  function moveGroup(list, d) { for (const o of list) { const w = o.userData.w0.clone().add(d); o.position.copy(o.parent.worldToLocal(w)); } }
  function updateCad() {
    if (!cadOn || !CAD?.ref) return; const r = CAD.ref;
    const dx = S.X - r.X0, dz = -(S.Y - r.Y0); const drop = (S.phase === 'print' || S.phase === 'done') ? (S.layer + 1) * LH_VIS : S.Z;
    moveGroup(CAD.groups.head, v3(dx, 0, dz)); moveGroup(CAD.groups.gantry, v3(0, 0, dz));
    const dy = r.gap0 - drop - (S.zDrop || 0); moveGroup(CAD.groups.bed, v3(0, dy, 0)); CAD.printHolder.position.set(0, r.bedTop0 + dy - .6, 0); }
  const simpleObjs = scene.children.filter(o => o !== hemi && o !== sun && o !== grid);
  // switch between the official CAD and the simplified model; returns {ok, solids, mapped}
  P.setCad = async (on) => {
    if (on && !CAD && !(await loadCad())) return { ok: false };
    if (!CAD) return { ok: false };
    cadOn = on; CAD.root.visible = on; grid.position.y = on ? CAD.floor - .5 : -82;
    if (on) CAD.printHolder.add(printGroup); else bed.add(printGroup);
    const keep = new Set(Object.entries(parts).filter(([pid]) => !cadParts[pid]).flatMap(([, l]) => l));
    // markers of things that are not a solid in the CAD (configuration, slicer, bay wiring) would float next to the model: they appear only while they glow
    const ghost = new Set(['firmware_config_macros', 'slicer_settings', 'dc_power_wiring'].flatMap(pid => parts[pid] || []));
    for (const o of simpleObjs) o.traverse(m => { if (!m.isMesh) return; m.userData.ghost = on && ghost.has(m); m.visible = !on || (keep.has(m) && !P.opt.static && !m.userData.ghost); });
    return { ok: true, solids: CAD.solids, mapped: CAD.mapped }; };
  P.setPanels = (on) => { extra.panels.forEach(p => p.visible = on && !cadOn); CAD?.panel.forEach(m => m.visible = on); };
  P.setXray = (on) => { for (const m of [...extra.frame, ...(CAD?.frame || [])]) { m.material.transparent = on; m.material.opacity = on ? .15 : 1; m.userData.op0 = null; } spotKey = ''; };

  // ---------------- highlight, selection, picking ----------------
  let pulse = 0;
  function highlight(dt) { pulse += dt * 4; const k = .55 + .45 * Math.sin(pulse); const ap = activeParts(), on = new Set(), sel = new Set();
    for (const pid of P.glow) (ap[pid] || []).forEach(m => on.add(m)); (ap[P.selected] || []).forEach(m => sel.add(m));
    spotlight(on);
    for (const list of Object.values(ap)) for (const m of list) { if (!m.material?.emissive || m.userData.unitGlow) continue;
      if (m.userData.ghost) m.visible = (on.has(m) || sel.has(m)) && !P.opt.static;
      if (on.has(m)) { m.material.emissive.setRGB(k, k * .8, 0); m.userData.hl = true; }
      else if (sel.has(m)) { m.material.emissive.setRGB(.1, .3, .6); m.userData.hl = true; }
      else if (m.userData.hl) { m.material.emissive.setRGB(0, 0, 0); m.userData.hl = false; } } }
  // While a part glows on the CAD model, everything else turns faint, so the part can be seen even when it sits deep inside the printer.
  let spotKey = '';
  function spotlight(on) {
    if (!cadOn || !CAD || P.opt.static) return; const key = [...P.glow].sort().join(','); if (key === spotKey) return; spotKey = key; const any = on.size > 0;
    CAD.root.traverse(m => { if (!m.isMesh || m.userData.hidden) return; const a = m.userData.op0 ||= { t: m.material.transparent, o: m.material.opacity, d: m.material.depthWrite }, dim = any && !on.has(m);
      m.material.transparent = dim ? true : a.t; m.material.opacity = dim ? a.o * .12 : a.o; m.material.depthWrite = dim ? false : a.d; m.material.needsUpdate = true; }); }
  P.focusPart = (pid) => { const list = (activeParts()[pid] || []).filter(m => m.visible || m.userData.ghost); if (!list.length) return; const b = new THREE.Box3(); list.forEach(m => b.expandByObject(m));
    const c = b.getCenter(v3(0, 0, 0)); const size = b.getSize(v3(0, 0, 0)).length(); const dir = v3(.5, .42, .76).normalize();
    P.flyTo(c.clone().add(dir.multiplyScalar(Math.max(380, size * 2.2))), c); };
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(); let downAt = null;
  function pick(ev) { const r = renderer.domElement.getBoundingClientRect(); mouse.set((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(mouse, camera); const hit = ray.intersectObjects(Object.values(activeParts()).flat().filter(m => m.visible), false)[0]; return hit?.object.userData.part; }
  renderer.domElement.addEventListener('pointerdown', e => downAt = [e.clientX, e.clientY]);
  renderer.domElement.addEventListener('pointerup', e => { if (downAt && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 4) { const p = pick(e); if (p && hooks.onPick) hooks.onPick(p); } });
  let hoverAt = 0;
  let hoverPid = null;
  renderer.domElement.addEventListener('pointermove', e => { if (!hooks.onHover) return; if (e.buttons) { hoverPid = null; hooks.onHover(null, 0, 0); return; }
    if (performance.now() - hoverAt >= 66) { hoverAt = performance.now(); hoverPid = pick(e) || null; }       // the name follows the mouse; the part under it is looked up 15 times a second
    const r = view.getBoundingClientRect(); hooks.onHover(hoverPid, e.clientX - r.left, e.clientY - r.top); });
  renderer.domElement.addEventListener('pointerleave', () => { hoverPid = null; hooks.onHover && hooks.onHover(null, 0, 0); });

  // ---------------- assembly units (groups that fly in one after another) ----------------
  // steps: [{cad: [regex strings on the CAD path], simple: [part ids or '#frame', '#deck', '#skirts', '#panels']}]
  P.buildUnits = (steps) => {
    updateMachine(0); scene.updateMatrixWorld(true); P.units = [];
    for (const st of steps) { let objs = [];
      if (cadOn) { const rxs = (st.cad || []).map(r => new RegExp(r)); CAD.root.traverse(o => { if (o !== CAD.root && o.name && rxs.some(rx => rx.test(pathOf(o)))) objs.push(o); });
        const set = new Set(objs); objs = objs.filter(o => { for (let x = o.parent; x; x = x.parent) if (set.has(x)) return false; return true; }); }
      else for (const id of st.simple || []) objs = objs.concat(id[0] === '#' ? extra[id.slice(1)] || [] : (parts[id] || []));
      objs = [...new Set(objs)]; const meshes = [];
      for (const o of objs) { o.userData.r0 = o.getWorldPosition(v3(0, 0, 0)); o.traverse(m => { if (m.isMesh && !m.userData.hidden) meshes.push(m); }); }
      const b = objs.length ? boxOf(objs) : new THREE.Box3(v3(0, 100, 0), v3(0, 100, 0));
      P.units.push({ objs, meshes, center: b.getCenter(v3(0, 0, 0)), size: b.getSize(v3(0, 0, 0)), offset: v3(0, 0, 0), t: 1 }); }
    // laid-out view: every unit lies on the floor on a ring around the place where the printer is built; big units get more room
    const w = P.units.map(u => Math.hypot(u.size.x, u.size.z) * .8 + 70), sum = w.reduce((a, b) => a + b, 0) || 1, R = Math.max(cadOn ? 520 : 460, sum / (2 * Math.PI));
    const floor = grid.position.y + .5; let acc = 0;
    P.units.forEach((u, i) => { const a = -Math.PI / 2 + (acc + w[i] / 2) / sum * Math.PI * 2; acc += w[i];
      u.offset = v3(Math.cos(a) * R - u.center.x, floor - (u.center.y - u.size.y / 2), Math.sin(a) * R - u.center.z); });
    const all = new THREE.Box3(); P.units.forEach(u => { all.expandByPoint(u.center.clone().sub(u.size.clone().multiplyScalar(.5))); all.expandByPoint(u.center.clone().add(u.size.clone().multiplyScalar(.5))); });
    P.build = { box: all, R };
    return P.units; };
  const ease = t => { t = Math.min(1, Math.max(0, t)); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  // where a unit is at time t (0 = on the floor on the ring, 1 = in its place): first it lifts to its height, then slides in, then settles
  const disp = (u, t) => { const up = ease(t / .38), across = ease((t - .22) / .78); return v3(u.offset.x * (1 - across), u.offset.y * (1 - up) + Math.sin(Math.PI * across) * 45, u.offset.z * (1 - across)); };
  P.setUnit = (i, t) => { const u = P.units[i]; if (!u) return; u.t = t; const d = disp(u, t);
    for (const o of u.objs) o.position.copy(o.parent.worldToLocal(o.userData.r0.clone().add(d))); };
  P.glowUnit = (i, k) => { const u = P.units[i]; if (!u) return; for (const m of u.meshes) { if (!m.material?.emissive) continue; m.userData.unitGlow = k > 0.01; m.material.emissive.setRGB(k * .95, k * .6, k * .05); } };
  // waiting units can be shown faint, so the eye stays on the part that is being fitted
  P.dimUnit = (i, on) => { const u = P.units?.[i]; if (!u || u.dim === on) return; u.dim = on;
    for (const m of u.meshes) { const a = m.userData.op0 ||= { t: m.material.transparent, o: m.material.opacity, d: m.material.depthWrite };
      m.material.transparent = on ? true : a.t; m.material.opacity = on ? a.o * .16 : a.o; m.material.depthWrite = on ? false : a.d; m.material.needsUpdate = true; } };
  // move the camera so that the whole box is in the picture, seen from direction dir
  const DIR_ALL = v3(.38, .66, .65).normalize(), DIR_BUILD = v3(.46, .44, .77).normalize();
  const corners = (c, size, out = []) => { for (const x of [-.5, .5]) for (const y of [-.5, .5]) for (const z of [-.5, .5]) out.push(v3(c.x + x * size.x, c.y + y * size.y, c.z + z * size.z)); return out; };
  const unitPts = (u, out) => corners(u.center.clone().add(disp(u, u.t)), u.size, out);
  const framePts = (pts, dir, margin = .9) => { if (!pts.length) return; const c = new THREE.Box3().setFromPoints(pts).getCenter(v3(0, 0, 0)), cam = camera.clone();
    let lo = 60, hi = 9000;
    for (let k = 0; k < 20; k++) { const d = (lo + hi) / 2; cam.position.copy(c).addScaledVector(dir, d); cam.lookAt(c); cam.updateMatrixWorld(true); cam.matrixWorldInverse.copy(cam.matrixWorld).invert();
      const ok = pts.every(p => { if (p.clone().applyMatrix4(cam.matrixWorldInverse).z > -5) return false; const q = p.clone().project(cam); return Math.abs(q.x) <= margin && Math.abs(q.y) <= margin; });
      if (ok) hi = d; else lo = d; }
    P.flyTo(c.clone().addScaledVector(dir, hi), c); };
  // camera on everything, wherever the units are now
  P.fitAll = () => { const pts = []; (P.units || []).forEach(u => unitPts(u, pts)); const up = Math.min(.74, Math.max(.44, 1.02 / camera.aspect)), flat = Math.sqrt(1 - up * up);   // a wide window looks at the ring from a lower angle, so the parts can be shown larger
    framePts(pts, v3(.5 * flat, up, .866 * flat), .98); };
  // camera on the place where the printer is built; with a unit number, that unit stays in the picture while it flies in
  P.fitBuild = (i = -1) => { if (!P.build) return; const pts = corners(P.build.box.getCenter(v3(0, 0, 0)), P.build.box.getSize(v3(0, 0, 0))); if (P.units[i]) unitPts(P.units[i], pts); framePts(pts, DIR_BUILD, P.units[i] ? .88 : 1.02); };

  // ---------------- loop ----------------
  const clock = new THREE.Clock(); P.scene = scene; P.camera = camera; P.controls = controls;
  P.perf = { frames: 0, logic: 0, render: 0 }; window.voronPrinter = P;       // for checking speed from the browser console
  function loop() { const dt = Math.min(.2, clock.getDelta()), t0 = performance.now();
    if (!P.opt.static) { step(dt); updateMachine(dt); updateCad(); }
    highlight(dt); hooks.onTick && hooks.onTick(dt); hooks.onFrame && hooks.onFrame(S);
    if (camGoal && !userMoved) { const k = 1 - Math.exp(-dt * 3.6); camera.position.lerp(camGoal.pos, k); controls.target.lerp(camGoal.target, k); if (camera.position.distanceTo(camGoal.pos) < 1) camGoal = null; }
    if (P.opt.follow && !P.opt.static) controls.target.lerp(head.position, .1);
    controls.update(); const t1 = performance.now(); renderer.render(scene, camera); const t2 = performance.now();
    P.perf.frames++; P.perf.logic += (t1 - t0 - P.perf.logic) * .1; P.perf.render += (t2 - t1 - P.perf.render) * .1; P.perf.calls = renderer.info.render.calls; P.perf.tris = renderer.info.render.triangles;
    requestAnimationFrame(loop); }
  updateMachine(0); loop();
  return P;
}
