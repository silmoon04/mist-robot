import * as THREE from './vendor/three.module.js';
import {STLLoader} from './vendor/STLLoader.js';
import {PoseTimeline} from './pose_timeline.mjs';
import {scheduleFrame} from './frame_clock.mjs';

const canvas = document.getElementById('viewer');
const frame = document.getElementById('viewframe');
const status = document.getElementById('viewerstatus');
const empty = frame.querySelector('.view-empty');
const timeline = new PoseTimeline();
const geometries = new Map(), links = new Map();
const metrics = {mode: 'loading', fps: 0, poseAgeMs: null, samples: 0, epoch: null,
  renderedTimeS: null, bodyPosition: null, links: 0, drawCalls: 0, triangles: 0, error: null};
window.mistViewer = {metrics};
let renderer, scene, camera, assembly, ground, modelEpoch, modelPromise;
let disposed = false, frameCount = 0, fpsStart = performance.now(), lastStatusMs = 0;
const loader = new STLLoader();
const cameraTarget = new THREE.Vector3(), cameraOffset = new THREE.Vector3(.437, -.520, .317);
const modelMaterials = new Set();
const modelGeometries = new Set();

function notice(message) { status.textContent = message; }
function fail(error) {
  metrics.mode = 'unavailable'; metrics.error = error.message;
  frame.dataset.viewer = 'unavailable';
  canvas.hidden = true;
  empty.hidden = false;
  empty.querySelector('strong').textContent = 'CAD view unavailable';
  empty.querySelector('p').textContent = error.message + ' Movement controls and telemetry remain available.';
  notice('CAD view unavailable');
}
async function json(url) {
  const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 1500);
  try {
    const response = await fetch(url, {cache: 'no-store', signal: abort.signal});
    if (!response.ok) throw Error('The simulator is not ready to provide the CAD view.');
    return await response.json();
  } finally { clearTimeout(timeout); }
}
function clearModel() {
  if (assembly) scene.remove(assembly);
  if (ground) {
    scene.remove(ground);
    ground.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
  }
  for (const material of modelMaterials) material.dispose();
  for (const geometry of modelGeometries) geometry.dispose();
  modelGeometries.clear();
  modelMaterials.clear(); links.clear(); timeline.clear();
}
async function geometry(visual) {
  if (visual.type === 'mesh') {
    if (!geometries.has(visual.url)) geometries.set(visual.url, loader.loadAsync(visual.url).catch(error => { geometries.delete(visual.url); throw error; }));
    return await geometries.get(visual.url);
  }
  if (visual.type === 'box') return new THREE.BoxGeometry(...visual.size);
  if (visual.type === 'sphere') return new THREE.SphereGeometry(visual.radius, 20, 12);
  if (visual.type === 'cylinder') {
    const result = new THREE.CylinderGeometry(visual.radius, visual.radius, visual.length, 24);
    result.rotateX(Math.PI / 2);
    return result;
  }
  throw Error('The simulator returned an unsupported CAD shape.');
}
function surface(terrain) {
  const group = new THREE.Group();
  group.position.fromArray(terrain?.position || [0, 0, -.01]);
  group.quaternion.fromArray(terrain?.quaternion || [0, 0, 0, 1]);
  const material = new THREE.MeshStandardMaterial({color: '#dbe4e7', roughness: 1, metalness: 0, side: THREE.DoubleSide});
  if (terrain?.type === 'rough' && terrain.heights && terrain.rows && terrain.columns) {
    const vertices = [], indices = [], rows = terrain.rows, columns = terrain.columns;
    for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
      vertices.push((column - (columns - 1) / 2) * terrain.spacing,
        (row - (rows - 1) / 2) * terrain.spacing, terrain.heights[row * columns + column]);
      if (row < rows - 1 && column < columns - 1) {
        const here = row * columns + column;
        indices.push(here, here + 1, here + columns, here + 1, here + columns + 1, here + columns);
      }
    }
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    mesh.setIndex(indices); mesh.computeVertexNormals();
    group.add(new THREE.Mesh(mesh, material));
  } else if (terrain?.vertices && terrain?.indices) {
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute('position', new THREE.Float32BufferAttribute(terrain.vertices.flat(), 3));
    mesh.setIndex(terrain.indices.flat()); mesh.computeVertexNormals();
    group.add(new THREE.Mesh(mesh, material));
  } else {
    group.add(new THREE.Mesh(new THREE.BoxGeometry(...(terrain?.size || [6, 6, .02])), material));
    const grid = new THREE.GridHelper(6, 60, '#a3b8c0', '#b9cbd1');
    grid.rotateX(Math.PI / 2); grid.position.z = .0102;
    grid.material.transparent = true; grid.material.opacity = .7;
    group.add(grid);
  }
  return group;
}
async function loadModel() {
  if (modelPromise) return modelPromise;
  modelPromise = (async () => {
    const model = await json('/api/model');
    if (model.version !== 1 || !Array.isArray(model.links)) throw Error('Restart the remote to load the smooth CAD viewer.');
    const nextAssembly = new THREE.Group(), nextLinks = new Map(), nextMaterials = new Set(), nextGeometries = new Set();
    try {
      await Promise.all(model.links.map(async link => {
        const group = new THREE.Group(); group.name = link.name || String(link.index);
        await Promise.all(link.visuals.map(async visual => {
          const shape = await geometry(visual), rgba = visual.color || [.3, .6, .65, 1];
          if (visual.type !== 'mesh') nextGeometries.add(shape);
          const material = new THREE.MeshStandardMaterial({color: new THREE.Color(...rgba.slice(0, 3)),
            roughness: .72, metalness: .05, transparent: rgba[3] < 1, opacity: rgba[3],
            depthWrite: rgba[3] >= 1, side: THREE.DoubleSide});
          nextMaterials.add(material);
          const mesh = new THREE.Mesh(shape, material);
          mesh.position.fromArray(visual.position || [0, 0, 0]);
          mesh.quaternion.fromArray(visual.quaternion || [0, 0, 0, 1]);
          mesh.scale.fromArray(visual.scale || [1, 1, 1]);
          group.add(mesh);
        }));
        nextLinks.set(link.index, group); nextAssembly.add(group);
      }));
    } catch (error) {
      for (const material of nextMaterials) material.dispose();
      for (const geometry of nextGeometries) geometry.dispose();
      throw error;
    }
    clearModel(); assembly = nextAssembly; ground = surface(model.terrain);
    for (const [index, group] of nextLinks) links.set(index, group);
    for (const material of nextMaterials) modelMaterials.add(material);
    for (const geometry of nextGeometries) modelGeometries.add(geometry);
    scene.add(assembly, ground); assembly.visible = false;
    modelEpoch = model.epoch; metrics.epoch = model.epoch;
    metrics.links = links.size;
    metrics.mode = 'webgl'; metrics.error = null;
  })().finally(() => { modelPromise = null; });
  return modelPromise;
}
function resize() {
  const width = Math.max(1, frame.clientWidth), height = Math.max(1, frame.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height; camera.updateProjectionMatrix();
}
function draw(now) {
  if (disposed) return;
  scheduleFrame(draw);
  if (document.hidden) return;
  const pose = timeline.sample(now);
  if (pose && pose.epoch === modelEpoch) {
    for (const link of pose.links) {
      const group = links.get(link.index);
      if (group) { group.position.fromArray(link.position); group.quaternion.fromArray(link.quaternion); }
    }
    const body = links.get(-1);
    if (body) {
      cameraTarget.copy(body.position); cameraTarget.z += .035;
      camera.position.copy(cameraTarget).add(cameraOffset); camera.lookAt(cameraTarget);
    }
    assembly.visible = true;
    const renderStarted = performance.now();
    renderer.render(scene, camera); frameCount++;
    frame.dataset.renderMs = (performance.now()-renderStarted).toFixed(2);
    metrics.renderedTimeS = pose.time_s;
    metrics.bodyPosition = body?.position.toArray() || null;
    metrics.drawCalls = renderer.info.render.calls;
    metrics.triangles = renderer.info.render.triangles;
    frame.dataset.triangles = String(metrics.triangles);
    frame.dataset.drawCalls = String(metrics.drawCalls);
    frame.dataset.renderedTime = String(pose.time_s);
    metrics.poseAgeMs = Math.round(timeline.ageMs(now));
    if (frame.dataset.viewer !== 'ready') {
      frame.dataset.viewer = 'ready'; empty.hidden = true; canvas.hidden = false;
      window.dispatchEvent(new Event('mist-viewer-ready'));
    }
  }
  if (now - fpsStart >= 1000) {
    metrics.fps = Math.round(frameCount * 1000 / (now - fpsStart)); frameCount = 0; fpsStart = now;
  }
  if (now - lastStatusMs >= 500 && pose) {
    const age = metrics.poseAgeMs;
    notice(age > 500 ? 'CAD updates paused · last pose ' + (age / 1000).toFixed(1) + ' s ago'
      : 'Smooth CAD view · ' + metrics.fps + ' fps · pose ' + age + ' ms old');
    lastStatusMs = now;
  }
}
async function pollPose() {
  if (disposed) return;
  const started = performance.now();
  try {
    if (!document.hidden) {
      if (modelEpoch === undefined) await loadModel();
      const pose = await json('/api/pose');
      if (pose.epoch !== modelEpoch) {
        if (assembly) assembly.visible = false;
        timeline.clear(); await loadModel();
      }
      if (pose.epoch === modelEpoch && timeline.push(pose, performance.now())) {
        metrics.samples++; metrics.error = null;
      }
    }
  } catch (error) {
    metrics.error = error.name === 'AbortError' ? 'CAD update timed out.' : error.message;
    notice('Reconnecting CAD view… ' + metrics.error);
  }
  setTimeout(pollPose, Math.max(0, (metrics.error ? 500 : 50) - (performance.now() - started)));
}
try {
  renderer = new THREE.WebGLRenderer({canvas, antialias: true, powerPreference: 'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene(); scene.background = new THREE.Color('#dfe7ea');
  camera = new THREE.PerspectiveCamera(55, 4 / 3, .02, 12); camera.up.set(0, 0, 1);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x70828a, 2.3));
  const light = new THREE.DirectionalLight(0xffffff, 2.5); light.position.set(-.7, -.7, 1.6); scene.add(light);
  new ResizeObserver(resize).observe(frame); resize();
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); disposed = true; fail(Error('The graphics connection was lost. Reload this page to restore the CAD view.')); });
  scheduleFrame(draw); pollPose();
} catch (error) {
  fail(Error('WebGL could not start on this device. Enable browser graphics acceleration and reload.'));
}
