// faces.js — loads the real robot faces from brain/face_assets/svg and maps the
// sim's overall verdict onto an emotion: green build -> happy, warnings ->
// annoyed, overload/tip -> angry. Textures are rasterized once and cached.
// Falls back to a drawn smiley if the assets aren't reachable (e.g. sim/ served
// standalone).

import * as THREE from 'three';

const BASE = '../brain/face_assets/svg/';
const FACES = {
  happy: ['12_happy_09_manual.svg', '10_happy_04_manual.svg', '13_happy_14_manual.svg'],
  annoyed: ['05_annoyed_01_manual.svg', '06_annoyed_02_manual.svg'],
  angry: ['01_angry_01_manual.svg', '03_angry_07_manual.svg'],
  sad: ['26_sad_01_manual.svg'],
  neutral: ['20_neutral_06_manual.svg'],
};
export const VERDICT_FACE = { ok: 'happy', warn: 'annoyed', bad: 'angry' };

const cache = new Map();

function fallbackTexture() {
  const cv = document.createElement('canvas');
  cv.width = 200; cv.height = 128;
  const g = cv.getContext('2d');
  g.fillStyle = '#0c0f11'; g.fillRect(0, 0, 200, 128);
  g.strokeStyle = '#5eeadd'; g.lineWidth = 7; g.lineCap = 'round';
  g.beginPath(); g.arc(70, 52, 15, 0, 2 * Math.PI); g.stroke();
  g.beginPath(); g.arc(130, 52, 15, 0, 2 * Math.PI); g.stroke();
  g.beginPath(); g.arc(100, 74, 24, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke();
  return new THREE.CanvasTexture(cv);
}

async function loadSvgTexture(file) {
  if (cache.has(file)) return cache.get(file);
  try {
    const resp = await fetch(BASE + file);
    if (!resp.ok) throw new Error(resp.status);
    const text = await resp.text();
    const blob = new Blob([text], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const img = await new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im);
      im.onerror = rej;
      im.src = url;
    });
    const cv = document.createElement('canvas');
    cv.width = 500; cv.height = 320; // face assets are 100:64
    cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
    URL.revokeObjectURL(url);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    cache.set(file, tex);
    return tex;
  } catch (e) {
    console.warn('[faces] falling back to drawn face:', file, e.message);
    const tex = fallbackTexture();
    cache.set(file, tex);
    return tex;
  }
}

export async function faceForVerdict(overall) {
  const emotion = VERDICT_FACE[overall] || 'neutral';
  return loadSvgTexture(FACES[emotion][0]);
}

// preload the three verdict faces so swaps are instant
export function preloadFaces() {
  ['ok', 'warn', 'bad'].forEach((v) => faceForVerdict(v));
}
