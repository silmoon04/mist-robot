// render.js — Three.js scene with 4 simultaneous views (3D orbit + side/front/top
// orthographic) and debug overlays: CoM plumb line, support polygon, GRF arrows,
// joint-utilization markers, ROM arcs, workspace cloud, foot targets, gravity arrow.
// World is Z-up. The robot group is rebuilt on every pipeline update (cheap at
// this mesh count); old geometries are disposed to avoid GPU leaks.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { V } from './kin.js';
import { faceForVerdict, preloadFaces } from './faces.js';

THREE.Object3D.DEFAULT_UP = new THREE.Vector3(0, 0, 1);

const COL = {
  bg: 0x14161a, shell: 0xd8d2c6, shellDark: 0x9a948a, servo: 0x22262e,
  femur: 0xcfc9bd, tibia: 0xbdb7ab, wheel: 0x15181d, phone: 0x0a0c10,
  ok: 0x37c871, warn: 0xe0a63c, bad: 0xe0483c, com: 0xff3b30,
  grf: 0x3f9dff, target: 0x9d6fff, poly: 0x37c871, grid: 0x2a2e36,
};

function utilColor(u) {
  if (u < 0.3) return new THREE.Color(COL.ok);
  if (u < 0.55) return new THREE.Color(COL.warn);
  return new THREE.Color(COL.bad);
}

export class Viewer {
  constructor(container) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(COL.bg);

    const amb = new THREE.AmbientLight(0xffffff, 0.55);
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(0.6, 0.4, 1.2);
    const fill = new THREE.DirectionalLight(0x88aaff, 0.35);
    fill.position.set(-0.5, -0.6, 0.5);
    this.scene.add(amb, key, fill);

    const grid = new THREE.GridHelper(2, 40, 0x3a3f4a, COL.grid);
    grid.rotation.x = Math.PI / 2;
    this.scene.add(grid);
    this.scene.add(new THREE.AxesHelper(0.12));

    // cameras
    this.persp = new THREE.PerspectiveCamera(42, 1, 0.01, 20);
    this.persp.position.set(0.75, -0.65, 0.55);
    this.persp.lookAt(0, 0, 0.15);
    this.controls = new OrbitControls(this.persp, this.renderer.domElement);
    this.controls.target.set(0, 0, 0.15);
    this.controls.update();

    const ext = 0.42;
    const mkOrtho = () => new THREE.OrthographicCamera(-ext, ext, ext, -ext, 0.01, 20);
    this.camSide = mkOrtho();  this.camSide.position.set(0, -3, 0.18);  this.camSide.lookAt(0, 0, 0.18);
    this.camFront = mkOrtho(); this.camFront.position.set(3, 0, 0.18);  this.camFront.lookAt(0, 0, 0.18);
    this.camTop = mkOrtho();   this.camTop.position.set(0, 0, 3);       this.camTop.up.set(1, 0, 0); this.camTop.lookAt(0, 0, 0);

    this.robot = new THREE.Group();
    this.overlay = new THREE.Group();
    this.wsGroup = new THREE.Group();
    this.scene.add(this.robot, this.overlay, this.wsGroup);

    this.toggles = { com: true, polygon: true, grf: true, joints: true, targets: true, rom: false, workspace: false, masses: false, gravity: true };
    this.faceTex = this.makeFaceTexture(); // instant placeholder; real SVG faces swap in async
    this.faceMat = new THREE.MeshBasicMaterial({ map: this.faceTex, toneMapped: false });
    this.faceMat._keep = true;
    this.currentFaceVerdict = null;
    preloadFaces();

    window.addEventListener('resize', () => this.resize());
    this.resize();
  }

  makeFaceTexture() {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 128;
    const g = cv.getContext('2d');
    g.fillStyle = '#05070d'; g.fillRect(0, 0, 128, 128);
    g.strokeStyle = '#37e0d8'; g.lineWidth = 7; g.lineCap = 'round';
    g.beginPath(); g.arc(42, 52, 15, 0, 2 * Math.PI); g.stroke();      // left eye
    g.beginPath(); g.arc(86, 52, 15, 0, 2 * Math.PI); g.stroke();      // right eye
    g.beginPath(); g.arc(64, 78, 22, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke(); // smile
    const tex = new THREE.CanvasTexture(cv);
    return tex;
  }

  resize() {
    const w = this.container.clientWidth, h = this.container.clientHeight;
    this.renderer.setSize(w, h);
    this.W = w; this.H = h;
  }

  disposeGroup(gr) {
    gr.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material && o.material !== this._sharedMat) {
        (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { if (!m._keep) m.dispose(); });
      }
    });
    gr.clear();
  }

  box(a, b, w, t, color) { // box from point a to b with cross-section w×t
    const dir = V.sub(b, a);
    const len = V.len(dir);
    const geo = new THREE.BoxGeometry(w, len, t);
    const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.65 }));
    const mid = V.scale(V.add(a, b), 0.5);
    mesh.position.set(...mid);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...V.norm(dir)));
    return mesh;
  }

  servoBox(p, color = COL.servo) {
    const geo = new THREE.BoxGeometry(0.0452, 0.0247, 0.035);
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.4, metalness: 0.2 }));
    m.position.set(...p);
    return m;
  }

  arrow(from, vec, color, scale = 1) {
    const len = V.len(vec) * scale;
    if (len < 1e-4) return null;
    return new THREE.ArrowHelper(new THREE.Vector3(...V.norm(vec)), new THREE.Vector3(...from), len, color, len * 0.25, len * 0.12);
  }

  update(res) {
    this.disposeGroup(this.robot);
    this.disposeGroup(this.overlay);
    const P = res.P;

    // ---- body ----
    const bottom = V.sub(res.bodyPos, [0, 0, P.legMountH]);
    const cyl = new THREE.Mesh(
      new THREE.CylinderGeometry(P.R, P.R, P.H, 40),
      new THREE.MeshStandardMaterial({ color: COL.shell, roughness: 0.55 }));
    cyl.rotation.x = Math.PI / 2;
    cyl.position.set(bottom[0], bottom[1], bottom[2] + P.H / 2);
    this.robot.add(cyl);
    const lid = new THREE.Mesh(
      new THREE.CylinderGeometry(P.R * 1.04, P.R * 1.04, 0.018, 40),
      new THREE.MeshStandardMaterial({ color: COL.shellDark, roughness: 0.5 }));
    lid.rotation.x = Math.PI / 2;
    lid.position.set(bottom[0], bottom[1], bottom[2] + P.H + 0.009);
    this.robot.add(lid);

    // phone slab + face screen (landscape, like the concept renders)
    const ph = res.items.find((i) => i.name === 'phone');
    if (ph) {
      const slab = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.155, 0.095),
        new THREE.MeshStandardMaterial({ color: COL.phone, roughness: 0.3 }));
      slab.position.set(...ph.p);
      this.robot.add(slab);
      const face = new THREE.Mesh(new THREE.PlaneGeometry(0.142, 0.142 * 0.64), this.faceMat);
      face.position.set(ph.p[0] + 0.0065, ph.p[1], ph.p[2]);
      // image-right -> +Y, image-up -> +Z, normal -> +X (right-handed; verified on screen)
      face.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(
        new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(1, 0, 0)));
      this.robot.add(face);
      this.updateFace(res.overall);
    }
    // battery ghost
    const bat = res.items.find((i) => i.name === 'battery');
    if (bat && this.toggles.masses) {
      const bg = new THREE.Mesh(new THREE.BoxGeometry(0.104, 0.035, 0.025),
        new THREE.MeshStandardMaterial({ color: 0xd9c552, transparent: true, opacity: 0.85 }));
      bg.position.set(...bat.p);
      this.robot.add(bg);
    }

    // ---- legs ----
    res.legs.forEach((leg, li) => {
      const fk = leg.fk;
      this.robot.add(this.servoBox(fk.mount));
      this.robot.add(this.servoBox(fk.p1));
      if (!P.linkage) this.robot.add(this.servoBox(fk.knee));
      this.robot.add(this.box(fk.p1, fk.knee, res.cfg.leg.beamW / 1000, res.cfg.leg.beamT / 1000, COL.femur));
      this.robot.add(this.box(fk.knee, fk.axle, res.cfg.leg.beamW / 1000 * 0.9, res.cfg.leg.beamT / 1000 * 0.9, COL.tibia));
      if (P.linkage) { // pushrod visual
        const rod = this.box(fk.p1, fk.knee, 0.004, 0.004, 0x666666);
        rod.position.z += 0.012;
        this.robot.add(rod);
      }
      // remote wheel drive: servo at knee/hip + belt line(s) down to the axle
      if (P.wheelMount !== 'foot') {
        const mountP = P.wheelMount === 'hip' ? fk.p1 : fk.knee;
        const off = V.scale(fk.wheelAxis, 0.02);
        const sb = this.servoBox(V.add(mountP, off), 0x2e3440);
        this.robot.add(sb);
        const beltMat = 0x556070;
        this.robot.add(this.box(V.add(fk.knee, off), V.add(fk.axle, off), 0.004, 0.012, beltMat));
        if (P.wheelMount === 'hip') {
          this.robot.add(this.box(V.add(fk.p1, off), V.add(fk.knee, off), 0.004, 0.012, beltMat));
        }
      }
      // wheel (axis = knee-parallel)
      const wheel = new THREE.Mesh(
        new THREE.CylinderGeometry(P.rw, P.rw, 0.024, 26),
        new THREE.MeshStandardMaterial({ color: COL.wheel, roughness: 0.9 }));
      wheel.position.set(...fk.axle);
      wheel.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...fk.wheelAxis));
      this.robot.add(wheel);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(P.rw * 0.45, P.rw * 0.45, 0.027, 18),
        new THREE.MeshStandardMaterial({ color: 0x8f897d, roughness: 0.5 }));
      hub.position.copy(wheel.position); hub.quaternion.copy(wheel.quaternion);
      this.robot.add(hub);

      // joint utilization markers
      if (this.toggles.joints) {
        const pts = [fk.mount, fk.p1, fk.knee];
        for (let j = 0; j < 3; j++) {
          const sv = res.power.perServo.find((s) => s.leg === li && s.joint === j);
          const u = sv ? sv.utilization : 0;
          const s = new THREE.Mesh(new THREE.SphereGeometry(0.008 + 0.014 * Math.min(u, 1.2), 12, 12),
            new THREE.MeshBasicMaterial({ color: utilColor(u) }));
          s.position.set(...pts[j]);
          this.overlay.add(s);
        }
      }
      // ROM arcs
      if (this.toggles.rom) this.addRomArcs(P, leg);
      // foot targets
      if (this.toggles.targets) {
        const tm = new THREE.Mesh(new THREE.SphereGeometry(0.007, 10, 10),
          new THREE.MeshBasicMaterial({ color: COL.target, wireframe: true }));
        tm.position.set(...leg.target);
        this.overlay.add(tm);
        if (!leg.reachable) {
          const ln = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...leg.target), new THREE.Vector3(...fk.contact)]),
            new THREE.LineBasicMaterial({ color: COL.bad }));
          this.overlay.add(ln);
        }
      }
    });

    // ---- overlays ----
    if (this.toggles.com) {
      const com = new THREE.Mesh(new THREE.SphereGeometry(0.012, 14, 14), new THREE.MeshBasicMaterial({ color: COL.com }));
      com.position.set(...res.com);
      this.overlay.add(com);
      const proj = res.stab.proj;
      const ln = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...res.com), new THREE.Vector3(proj[0], proj[1], 0.001)]),
        new THREE.LineDashedMaterial({ color: COL.com, dashSize: 0.015, gapSize: 0.01 }));
      ln.computeLineDistances();
      this.overlay.add(ln);
      const pm = new THREE.Mesh(new THREE.CircleGeometry(0.011, 16),
        new THREE.MeshBasicMaterial({ color: COL.com, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
      pm.position.set(proj[0], proj[1], 0.002);
      this.overlay.add(pm);
    }
    if (this.toggles.polygon && res.stab.hull.length >= 2) {
      const hpts = res.stab.hull.map((p) => new THREE.Vector3(p[0], p[1], 0.0015));
      const loop = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(hpts),
        new THREE.LineBasicMaterial({ color: res.stab.margin > 0 ? COL.poly : COL.bad }));
      this.overlay.add(loop);
      if (res.stab.hull.length >= 3) {
        const shape = new THREE.Shape(res.stab.hull.map((p) => new THREE.Vector2(p[0], p[1])));
        const fill = new THREE.Mesh(new THREE.ShapeGeometry(shape),
          new THREE.MeshBasicMaterial({ color: res.stab.margin > 0 ? COL.poly : COL.bad, transparent: true, opacity: 0.12, side: THREE.DoubleSide }));
        fill.position.z = 0.001;
        this.overlay.add(fill);
      }
    }
    if (this.toggles.grf) {
      res.contacts.forEach((c, ci) => {
        const F = res.grf.N[ci];
        if (F > 0.05) {
          const a = this.arrow([c.p[0], c.p[1], 0], [0, 0, F], COL.grf, 0.006);
          if (a) this.overlay.add(a);
        }
      });
    }
    // weakest tipping direction: ground arrow from the CoM projection toward the
    // easiest-to-tip support edge, colored by how close it is
    if (this.toggles.polygon && res.stab.edges.length && res.cfg.pose.mode === 'stand') {
      const e = res.stab.edges.reduce((a, b) => (b.tipDeg < a.tipDeg ? b : a));
      const ex = e.b[0] - e.a[0], ey = e.b[1] - e.a[1];
      const el = Math.hypot(ex, ey) || 1;
      const out = [ey / el, -ex / el, 0]; // outward normal of CCW hull edge
      const col = e.tipDeg > 15 ? COL.ok : e.tipDeg > 8 ? COL.warn : COL.bad;
      const a = this.arrow([res.stab.proj[0], res.stab.proj[1], 0.004], out, col, 0.06 + Math.max(0, 0.1 - e.tipDeg * 0.004));
      if (a) this.overlay.add(a);
    }
    if (this.toggles.gravity) {
      const gtip = [res.bodyPos[0], res.bodyPos[1], res.bodyPos[2] + res.P.H + 0.1];
      const a = this.arrow(gtip, res.P.gDir, 0xffffff, 0.1);
      if (a) this.overlay.add(a);
    }
    if (this.toggles.masses) {
      res.items.forEach((it) => {
        if (it.group !== 'body') return;
        const s = new THREE.Mesh(new THREE.SphereGeometry(0.004 + Math.cbrt(it.m) * 0.012, 10, 10),
          new THREE.MeshBasicMaterial({ color: 0xd9c552, transparent: true, opacity: 0.6 }));
        s.position.set(...it.p);
        this.overlay.add(s);
      });
    }
  }

  async updateFace(overall) {
    if (overall === this.currentFaceVerdict) return;
    this.currentFaceVerdict = overall;
    const tex = await faceForVerdict(overall);
    if (this.currentFaceVerdict === overall) {
      this.faceMat.map = tex;
      this.faceMat.needsUpdate = true;
    }
  }

  addRomArcs(P, leg) {
    const fk = leg.fk;
    const mkArc = (center, axis, refDir, lim, radius, color, cur) => {
      const pts = [];
      const n = 24;
      for (let i = 0; i <= n; i++) {
        const a = lim[0] + (i / n) * (lim[1] - lim[0]);
        const d = V.rotAxis(refDir, axis, a);
        pts.push(new THREE.Vector3(...V.add(center, V.scale(d, radius))));
      }
      const ln = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 }));
      this.overlay.add(ln);
      const dcur = V.rotAxis(refDir, axis, cur);
      const cm = new THREE.Mesh(new THREE.SphereGeometry(0.005, 8, 8), new THREE.MeshBasicMaterial({ color }));
      cm.position.set(...V.add(center, V.scale(dcur, radius)));
      this.overlay.add(cm);
    };
    const phi = leg.phi;
    const down = [0, 0, -1];
    // roll arc about a1 at mount; reference = straight down
    mkArc(fk.mount, fk.a1, down, P.rom.roll, 0.05, 0xff9dff, leg.q[0]);
    // hip pitch arc about a2 at p1; reference = rolled straight-down
    const rolledDown = V.rotAxis(down, fk.a1, leg.q[0]);
    mkArc(fk.p1, fk.a2, rolledDown, P.rom.hip, 0.06, 0x8fd0ff, leg.q[1]);
    // knee arc about a3 at knee; reference = femur direction
    mkArc(fk.knee, fk.a3, fk.femurDir, P.rom.knee, 0.045, 0xffd08f, leg.q[2]);
  }

  setWorkspace(clouds) { // clouds: array of {positions, colors} or null
    this.disposeGroup(this.wsGroup);
    if (!clouds) return;
    clouds.forEach((c) => {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(c.positions, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(c.colors, 3));
      const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.004, vertexColors: true, transparent: true, opacity: 0.5 }));
      this.wsGroup.add(pts);
    });
  }

  render() {
    const r = this.renderer;
    const W = this.W, H = this.H;
    const leftW = Math.floor(W * 0.26);
    const vh = Math.floor(H / 3);
    r.setScissorTest(true);

    const draw = (cam, x, y, w, h) => {
      r.setViewport(x, y, w, h); r.setScissor(x, y, w, h);
      if (cam.isPerspectiveCamera) { cam.aspect = w / h; }
      else {
        const ext = 0.42, asp = w / h;
        cam.left = -ext * asp; cam.right = ext * asp; cam.top = ext; cam.bottom = -ext;
      }
      cam.updateProjectionMatrix();
      r.render(this.scene, cam);
    };
    draw(this.camSide, 0, 2 * vh, leftW, H - 2 * vh);
    draw(this.camFront, 0, vh, leftW, vh);
    draw(this.camTop, 0, 0, leftW, vh);
    draw(this.persp, leftW, 0, W - leftW, H);
    r.setScissorTest(false);
  }
}
