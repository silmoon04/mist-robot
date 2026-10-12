import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
import {STLLoader} from './vendor/STLLoader.js';

const $ = id => document.getElementById(id);
const host = $('canvas-host');
const scene = new THREE.Scene();
scene.background = new THREE.Color('#edf0e9');
const renderer = new THREE.WebGLRenderer({antialias: true, alpha: false});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
host.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(34, 1, 1, 6000);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = .08;
controls.minDistance = 120;
controls.maxDistance = 2200;
controls.maxPolarAngle = Math.PI * .92;

scene.add(new THREE.HemisphereLight(0xffffff, 0x738375, 2.0));
const key = new THREE.DirectionalLight(0xfffaf0, 3.0);
key.position.set(350, -350, 750);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, {left: -650, right: 650, top: 650, bottom: -650, near: 50, far: 1500});
key.shadow.bias = -.0003;
key.shadow.normalBias = .25;
scene.add(key);
const fill = new THREE.DirectionalLight(0xe2eef8, 1.5);
fill.position.set(-400, 200, 280);
scene.add(fill);

const robot = new THREE.Group();
scene.add(robot);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600),
  new THREE.ShadowMaterial({opacity: .12}));
ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(1200, 24, 0xc9d4c7, 0xdce3d7);
grid.rotation.x = Math.PI / 2;
grid.material.transparent = true;
grid.material.opacity = .65;
scene.add(grid);

const groups = new Map();
const meshes = [];
let manifest;
let printedManifest;
let geometryManifestSha;
let printedManifestSha;
let massProvenanceError;
const printedParts = new Map();
let nominalBounds;
let currentBounds;
let currentView = 'perspective';
const loader = new STLLoader();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const radians = THREE.MathUtils.degToRad;

async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

async function readBytes(url) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error(`${url} could not load (${response.status})`);
  return response.arrayBuffer();
}

async function loadPrintedMass() {
  try {
    const [massBytes, propertiesBytes] = await Promise.all([
      readBytes('../cad/output/assembly_manifest_as_printed.json'),
      readBytes('../manufacturing/slicing_r5/output/production_mass_properties.json'),
    ]);
    const candidate = JSON.parse(new TextDecoder().decode(massBytes));
    const properties = JSON.parse(new TextDecoder().decode(propertiesBytes));
    const model = candidate.mass_model;
    if (candidate.revision !== manifest.revision || candidate.units !== manifest.units
        || model?.source_solid_manifest_sha256 !== geometryManifestSha
        || model?.source_production_properties_sha256 !== await sha256(propertiesBytes)
        || model?.as_sliced !== true || model?.physical_measurement !== false || properties.status !== 'pass'
        || !Number.isFinite(candidate.total_mass_kg) || candidate.total_mass_kg <= 0) {
      throw new Error('The sliced mass provenance does not match the current CAD and production properties.');
    }
    const names = new Set(candidate.parts.map(part => part.name));
    if (manifest.parts.some(part => !names.has(part.name))) {
      throw new Error('The sliced mass manifest omits a current CAD part.');
    }
    printedManifest = candidate;
    printedManifestSha = await sha256(massBytes);
    for (const part of candidate.parts) printedParts.set(part.name, part);
  } catch (error) {
    massProvenanceError = error.message;
    console.warn('Sliced mass estimate unavailable:', error.message);
  }
}

function matrix(rows) {
  return new THREE.Matrix4().set(...rows.flat());
}

function color(part) {
  if (part.material === 'servo') return '#303c39';
  if (part.material === 'phone') return '#293731';
  if (['metal', 'steel'].includes(part.material)) return '#b9c0b8';
  if (part.material !== 'pla') return part.name.includes('battery') ? '#455343' : '#537660';
  if (part.name === 'hex_faceted_cover') return '#505e58';
  if (part.name === 'body_deck') return '#849487';
  if (/^(FL|FR|RL|RR)_/.test(part.name)) return '#5c9690';
  if (part.name.startsWith('phone_cradle')) return '#a0b7a8';
  return '#789887';
}

function material(part) {
  return new THREE.MeshStandardMaterial({color: color(part),
    roughness: part.material === 'metal' ? .32 : .62,
    metalness: part.material === 'metal' ? .65 : .08});
}

function makeGroups() {
  const world = new Map(Object.entries(manifest.links).map(([name, data]) =>
    [name, matrix(data.assembly_transform)]));
  for (const [name, data] of Object.entries(manifest.links)) {
    const group = new THREE.Group();
    group.name = name;
    group.matrixAutoUpdate = false;
    const parentMatrix = data.joint ? world.get(data.joint.parent) : new THREE.Matrix4();
    group.userData.neutral = parentMatrix.clone().invert().multiply(world.get(name));
    group.matrix.copy(group.userData.neutral);
    group.userData.joint = data.joint;
    groups.set(name, group);
  }
  for (const [name, data] of Object.entries(manifest.links)) {
    (data.joint ? groups.get(data.joint.parent) : robot).add(groups.get(name));
  }
}

function addPhoneScreen(part, parent) {
  const [[x0, y0, z0], [x1, y1, z1]] = part.bounds_mm;
  const vertices = new Float32Array([
    x1 + .05, y0 + 2.1, z0 + 3.5,
    x1 + .05, y1 - 2.1, z0 + 3.5,
    x1 + .05, y1 - 2.1, z1 - 4.5,
    x1 + .05, y0 + 2.1, z1 - 4.5,
  ]);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geometry.setIndex([0, 1, 2, 0, 2, 3]);
  geometry.computeVertexNormals();
  const screen = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
    color: '#12251f', roughness: .18, metalness: .2, emissive: '#08291f', emissiveIntensity: .24,
  }));
  screen.userData.part = part;
  screen.userData.screen = true;
  parent.add(screen);
  meshes.push(screen);
}

async function loadParts() {
  const parts = manifest.parts.filter(p => !p.allowance_only);
  let next = 0;
  let loaded = 0;
  const failures = [];
  async function worker() {
    while (next < parts.length) {
      const part = parts[next++];
      try {
        if (!part.stl) throw new Error('Part mesh is absent from the manifest');
        const geometry = await loader.loadAsync(`../cad/output/${part.stl}`);
        geometry.computeBoundingBox();
        const mesh = new THREE.Mesh(geometry, material(part));
        mesh.name = part.name;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData.part = part;
        groups.get(part.link).add(mesh);
        meshes.push(mesh);
        if (part.material === 'phone') addPhoneScreen(part, groups.get(part.link));
      } catch (error) {
        failures.push(`${part.name}: ${error.message}`);
      }
      loaded++;
      $('load-count').textContent = `${loaded} of ${parts.length} parts`;
    }
  }
  await Promise.all(Array.from({length: 8}, worker));
  if (failures.length) throw new Error(`${failures.length} meshes could not load. ${failures[0]}`);
}

function explodeOffset(part) {
  if (!$('explode').checked) return new THREE.Vector3();
  if (part.name === 'hex_faceted_cover') return new THREE.Vector3(0, 0, 70);
  if (part.link === 'phone_pan' || part.name.startsWith('phone_pan_servo')) return new THREE.Vector3(0, 0, 145);
  if (part.name.startsWith('pan_cover_spacer')) return new THREE.Vector3(0, 0, 70);
  const match = part.name.match(/^(FL|FR|RL|RR)_/);
  if (match && part.link === 'base') {
    const azimuth = radians(manifest.parameters.leg_azimuth_deg[match[1]]);
    return new THREE.Vector3(Math.cos(azimuth) * 46, Math.sin(azimuth) * 46, 0);
  }
  return new THREE.Vector3();
}

function updatePose() {
  if (!manifest) return;
  const pan = Number($('pan').value);
  const stance = Number($('stance').value);
  const bend = stance * (stance < 0 ? 0.14 : 0.04);
  $('pan-value').value = `${pan}°`;
  $('stance-value').value = stance === 0 ? 'Nominal' : (stance < 0 ? 'Lower' : 'Higher');
  for (const [name, group] of groups) {
    const joint = group.userData.joint;
    let delta = name === 'phone_pan' ? radians(pan) :
      name.startsWith('femur_') ? radians(bend) :
      name.startsWith('tibia_') ? -radians(bend) : 0;
    if (joint && joint.type !== 'continuous') {
      const neutral = joint.neutral_angle_rad || 0;
      delta = THREE.MathUtils.clamp(neutral + delta, ...joint.limits_rad) - neutral;
    }
    group.matrix.copy(group.userData.neutral);
    if (joint && delta) group.matrix.multiply(new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(...joint.axis), delta));
    if ($('explode').checked && name.startsWith('coxa_')) {
      const azimuth = radians(manifest.parameters.leg_azimuth_deg[name.slice(-2)]);
      group.matrix.elements[12] += Math.cos(azimuth) * 46;
      group.matrix.elements[13] += Math.sin(azimuth) * 46;
    }
    group.matrixWorldNeedsUpdate = true;
  }
  for (const mesh of meshes) {
    const part = mesh.userData.part;
    mesh.visible = (part.name !== 'hex_faceted_cover' || $('shell').checked)
      && (part.printable || $('hardware').checked);
    mesh.position.copy(explodeOffset(part));
  }
  robot.updateMatrixWorld(true);
  currentBounds = visibleBounds();
  ground.position.z = currentBounds.min.z - .8;
  grid.position.z = currentBounds.min.z - .75;
}

function visibleBounds() {
  const box = new THREE.Box3();
  for (const mesh of meshes) {
    if (!mesh.visible || mesh.userData.screen) continue;
    if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
    box.union(mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld));
  }
  return box;
}

function fitView(view = currentView) {
  if (!currentBounds || currentBounds.isEmpty()) return;
  currentView = view;
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active', button.dataset.view === view));
  const center = currentBounds.getCenter(new THREE.Vector3());
  const size = currentBounds.getSize(new THREE.Vector3());
  const direction = view === 'front' ? new THREE.Vector3(1, 0, .03) :
    view === 'side' ? new THREE.Vector3(0, -1, .03) :
    view === 'top' ? new THREE.Vector3(.001, -.001, 1) : new THREE.Vector3(1.55, -1.0, .82);
  direction.normalize();
  const radius = size.length() / 2;
  const angle = Math.min(camera.fov * Math.PI / 360,
    Math.atan(Math.tan(camera.fov * Math.PI / 360) * camera.aspect));
  const distance = radius / Math.sin(angle) * .98;
  camera.position.copy(center).addScaledVector(direction, distance);
  controls.target.copy(center);
  controls.update();
}

function resize() {
  const width = host.clientWidth, height = host.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function stats() {
  const [low, high] = manifest.assembly_bounds_mm;
  const extent = high.map((v, i) => v - low[i]);
  $('mass').textContent = printedManifest ? `${printedManifest.total_mass_kg.toFixed(2)} kg` : 'Unavailable';
  $('solid-mass').textContent = `${manifest.total_mass_kg.toFixed(2)} kg`;
  $('mass-note').textContent = printedManifest
    ? 'Sliced model deposition, nominal hardware, wiring and fasteners. Support material is excluded. Parts have not been weighed.'
    : 'The sliced mass estimate could not be matched to this CAD revision. The full-solid reference is shown separately.';
  $('span').textContent = `${extent[0].toFixed(0)} × ${extent[1].toFixed(0)} mm`;
  $('height').textContent = `${extent[2].toFixed(0)} mm`;
  $('part-count').textContent = manifest.print_parts.length;
  $('piece-count').textContent = manifest.print_parts.reduce((total, part) => total + part.quantity, 0);
  $('servo-count').textContent = manifest.parameters.servo_count;
  $('revision').textContent = `${manifest.revision} · ${manifest.parts.filter(p => !p.allowance_only).length} actual CAD parts · Units: mm`;
}

function hover(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set((event.clientX - rect.left) / rect.width * 2 - 1,
    -(event.clientY - rect.top) / rect.height * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(meshes.filter(m => m.visible), false)[0];
  const tooltip = $('part-tooltip');
  tooltip.hidden = !hit;
  if (!hit) return;
  const part = hit.object.userData.part;
  const massPart = printedParts.get(part.name);
  const shownMass = massPart ? massPart.mass_kg : part.mass_kg;
  tooltip.querySelector('strong').textContent = part.display_name || part.name.replaceAll('_', ' ');
  tooltip.querySelector('span').textContent = `${part.printable ? (massPart ? 'Sliced PLA estimate' : 'Solid PLA reference') : 'Hardware envelope'} · ${(shownMass * 1000).toFixed(1)} g · ${part.link.replaceAll('_', ' ')}`;
}

$('pan').addEventListener('input', updatePose);
$('stance').addEventListener('input', updatePose);
for (const id of ['shell', 'hardware']) $(id).addEventListener('change', updatePose);
$('explode').addEventListener('change', () => {updatePose(); fitView();});
$('reset').addEventListener('click', () => {
  $('pan').value = '0'; $('stance').value = '0';
  $('shell').checked = true; $('hardware').checked = true; $('explode').checked = false;
  updatePose(); fitView('perspective');
});
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => fitView(button.dataset.view)));
renderer.domElement.addEventListener('pointermove', hover);
renderer.domElement.addEventListener('pointerleave', () => {$('part-tooltip').hidden = true;});
new ResizeObserver(() => {resize();}).observe(host);
resize();
renderer.setAnimationLoop(() => {controls.update(); renderer.render(scene, camera);});

async function start() {
  const bytes = await readBytes('../cad/output/assembly_manifest.json');
  geometryManifestSha = await sha256(bytes);
  manifest = JSON.parse(new TextDecoder().decode(bytes));
  makeGroups();
  await Promise.all([loadParts(), loadPrintedMass()]);
  stats();
  updatePose();
  nominalBounds = currentBounds.clone();
  fitView('perspective');
  $('loading').hidden = true;
  window.quadrupedReview = {
    revision: manifest.revision,
    loadedParts: meshes.filter(m => !m.userData.screen).length,
    expectedParts: manifest.parts.filter(p => !p.allowance_only).length,
    neutralBoundsMm: [nominalBounds.min.toArray(), nominalBounds.max.toArray()],
    geometryManifestSha,
    printedManifestSha,
    assembledMassKg: printedManifest?.total_mass_kg,
    solidReferenceMassKg: manifest.total_mass_kg,
    massProvenanceMatched: Boolean(printedManifest),
    massProvenanceError,
    ready: true,
  };
}

start().catch(error => {
  $('loading').classList.add('error');
  $('loading').querySelector('strong').textContent = 'The complete assembly could not load';
  $('load-count').textContent = error.message;
  window.quadrupedReview = {ready: false, error: error.message};
  console.error(error);
});
