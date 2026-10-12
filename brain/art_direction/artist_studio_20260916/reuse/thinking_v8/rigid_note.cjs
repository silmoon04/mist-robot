'use strict';

const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.env.MIST_SHARP_PATH || '<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');

// All visible pixels come from the generated sheet. The empty interior is an
// alpha cutout; handwriting is revealed by clipping its original pixels.
async function composeNote(id, original, info, cells, root, sha) {
  const source = 'source/note.png';
  const sourceSha256 = sha(original);
  const components = [];
  const directory = path.join(root, 'components');
  fs.mkdirSync(directory, { recursive: true });
  fs.mkdirSync(path.join(root, 'frames/note'), { recursive: true });

  async function component(name, cellIndex, rect, cutouts = []) {
    const cell = cells[cellIndex];
    const data = Buffer.from(cell.buf);
    for (const cutout of cutouts) {
      for (let y = cutout.top; y < cutout.top + cutout.height; y++) {
        for (let x = cutout.left; x < cutout.left + cutout.width; x++) data[(y * cell.cw + x) * 4 + 3] = 0;
      }
    }
    const bytes = await sharp(data, { raw: { width: cell.cw, height: cell.ch, channels: 4 } }).extract(rect).png().toBuffer();
    const file = `components/note_${name}.png`;
    fs.writeFileSync(path.join(root, file), bytes);
    components.push({
      id: name, file, sha256: sha(bytes), source, sourceSha256,
      sourceCellIndex: cellIndex, sourceCell: cell.sourceCell,
      sourceRect: [cell.sourceCell[0] + rect.left, cell.sourceCell[1] + rect.top, rect.width, rect.height],
      cellRect: [rect.left, rect.top, rect.width, rect.height], alphaCutouts: cutouts,
    });
    const raw = await sharp(bytes).raw().toBuffer();
    return { bytes, raw, width: rect.width, height: rect.height, rect, cellIndex, file };
  }

  // Cell 11 has an uninterrupted pad outline; its marks and pen are entirely
  // inside this cutout. Cell 17 supplies a pen separated from the turning page.
  const pad = await component('pad', 11, { left: 52, top: 67, width: 150, height: 162 }, [{ left: 68, top: 121, width: 116, height: 71 }]);
  const pen = await component('pen', 17, { left: 171, top: 0, width: 59, height: 74 });
  const first = await component('stroke_first', 9, { left: 63, top: 130, width: 109, height: 18 });
  const second = await component('stroke_second', 15, { left: 66, top: 147, width: 112, height: 17 });
  // The pen's enclosed silhouette hides the underlying page through its two
  // transparent holes. This mask contributes no visible pixels of its own.
  const outside = new Uint8Array(pen.width * pen.height), queue = [];
  const visit = (x, y) => {
    if (x < 0 || y < 0 || x >= pen.width || y >= pen.height) return;
    const p = y * pen.width + x;
    if (outside[p] || pen.raw[p * 4 + 3] > 24) return;
    outside[p] = 1; queue.push(p);
  };
  for (let x = 0; x < pen.width; x++) { visit(x, 0); visit(x, pen.height - 1); }
  for (let y = 0; y < pen.height; y++) { visit(0, y); visit(pen.width - 1, y); }
  for (let q = 0; q < queue.length; q++) {
    const p = queue[q], x = p % pen.width, y = Math.floor(p / pen.width);
    visit(x - 1, y); visit(x + 1, y); visit(x, y - 1); visit(x, y + 1);
  }
  const mask = Buffer.alloc(pen.raw.length);
  for (let p = 0; p < outside.length; p++) if (!outside[p]) mask[p * 4 + 3] = 255;
  const penMask = await sharp(mask, { raw: { width: pen.width, height: pen.height, channels: 4 } }).png().toBuffer();

  const stageAnchor = [128, 224];
  const scale = 200 / 256;
  const bodyAnchors = { 14: [124, 216], 15: [122, 216], 16: [123, 215], 17: [127, 216], 18: [131, 201], 19: [127, 200] };
  const nativeTips = { 14: [133, 170], 15: [180, 164], 16: [173, 79], 17: [174, 70], 18: [121, 117], 19: [96, 111] };
  const turnStages = { 14: 'second-stroke-finishing', 15: 'pen-lifts-from-completed-page', 16: 'page-corner-curls', 17: 'marked-page-turns', 18: 'blank-page-settles', 19: 'pen-returns-over-blank-page' };
  const frames = [];

  function strokeTip(part, left, top, progress) {
    const width = Math.max(3, Math.round(part.width * progress));
    let x = Math.min(part.width - 3, width - 1), total = 0, moment = 0;
    for (let y = 0; y < part.height; y++) {
      const a = part.raw[(y * part.width + x) * 4 + 3];
      total += a; moment += a * y;
    }
    return [left + x, top + (total ? moment / total : part.height / 2)];
  }

  async function lineLayer(part, left, top, progress) {
    if (progress <= 0) return null;
    const width = Math.max(1, Math.min(part.width, Math.round(part.width * progress)));
    return { input: await sharp(part.bytes).extract({ left: 0, top: 0, width, height: part.height }).png().toBuffer(), left, top };
  }

  for (let i = 0; i < 24; i++) {
    let stage, marker, firstProgress = 0, secondProgress = 0, size = 1;
    let sourceCellIndex = 11, offset = [1, -2], method = 'generated-components';
    let action = i < 4 ? 'pad-enters-and-pen-approaches' : i >= 20 ? 'pad-and-pen-withdraw' : 'writing';
    if (i >= 14 && i <= 19) {
      sourceCellIndex = i;
      const c = cells[i], anchor = bodyAnchors[i];
      offset = [stageAnchor[0] - anchor[0], stageAnchor[1] - anchor[1]];
      const bytes = await sharp(c.buf, { raw: { width: c.cw, height: c.ch, channels: 4 } }).extract(c.box).png().toBuffer();
      stage = await sharp({ create: { width: 256, height: 256, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
        .composite([{ input: bytes, left: c.box.left + offset[0], top: c.box.top + offset[1] }]).png().toBuffer();
      marker = [nativeTips[i][0] + offset[0], nativeTips[i][1] + offset[1]];
      method = 'registered-generated-page-cel';
      action = turnStages[i];
      firstProgress = i <= 16 ? 1 : null;
      secondProgress = i === 14 ? 0.72 : i <= 16 ? 1 : null;
    } else {
      if (i < 4) {
        size = [0.55, 0.72, 0.88, 1][i];
        marker = [[181, 172], [154, 151], [115, 138], [75, 128]][i];
      } else if (i <= 8) {
        firstProgress = [0, 0.23, 0.48, 0.75, 1][i - 4];
        marker = strokeTip(first, 73, 119, firstProgress);
        action = firstProgress ? 'first-stroke-grows-under-pen' : 'pen-touches-blank-page';
      } else if (i <= 13) {
        firstProgress = 1;
        secondProgress = [0, 0, 0, 0.27, 0.58][i - 9];
        marker = i === 9 ? [173, 111] : i === 10 ? [123, 131] : strokeTip(second, 72, 155, secondProgress);
        action = i <= 10 ? 'pen-lifts-and-returns-to-next-line' : 'second-stroke-grows-under-pen';
      } else {
        size = [1, 0.86, 0.68, 0.49][i - 20];
        marker = [[113, 100], [145, 116], [171, 144], [184, 168]][i - 20];
      }
      const layers = [{ input: pad.bytes, left: 53, top: 65 }];
      for (const layer of [await lineLayer(first, 73, 119, firstProgress), await lineLayer(second, 72, 155, secondProgress)]) if (layer) layers.push(layer);
      const penLeft = Math.round(marker[0] - 3), penTop = Math.round(marker[1] - 70);
      layers.push({ input: penMask, left: penLeft, top: penTop, blend: 'dest-out' }, { input: pen.bytes, left: penLeft, top: penTop });
      stage = await sharp({ create: { width: 256, height: 256, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } }).composite(layers).png().toBuffer();
    }
    const width = Math.round(200 * size), effectiveScale = width / 256;
    const left = Math.round(120 - stageAnchor[0] * effectiveScale), top = Math.round(194 - stageAnchor[1] * effectiveScale);
    const image = await sharp(stage).resize(width, width).png().toBuffer();
    const bytes = await sharp({ create: { width: 256, height: 256, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } }).composite([{ input: image, left, top }]).png().toBuffer();
    const raw = await sharp(bytes).raw().toBuffer();
    let l = 256, t = 256, r = -1, b = -1;
    for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) if (raw[(y * 256 + x) * 4 + 3] > 0) { l = Math.min(l, x); r = Math.max(r, x); t = Math.min(t, y); b = Math.max(b, y); }
    const file = `frames/note/${String(i).padStart(2, '0')}.png`;
    fs.writeFileSync(path.join(root, file), bytes);
    const markerPosition = marker.map((n, k) => +(n * effectiveScale + (k ? top : left)).toFixed(3));
    const markerPositionKind = method === 'generated-components' ? 'component-tip' : 'source-tip-approximation';
    frames.push({
      file, pose: i < 4 ? `enter_${i}` : i < 20 ? `loop_${i - 4}` : `exit_${i - 20}`,
      bounds: [l, t, r - l + 1, b - t + 1], sha256: sha(bytes), sourceCell: cells[sourceCellIndex].sourceCell,
      sourceCellIndex, registrationOffset: offset, bodyAnchor: [120, 194], scale: effectiveScale,
      assemblyMethod: method, action, markerPosition, markerPositionKind,
      placements: [{ component: 'pen', anchor: 'tip', x: markerPosition[0], y: markerPosition[1], scale: effectiveScale, evidence: markerPositionKind }],
      strokeProgress: { first: firstProgress, second: secondProgress },
      componentIds: method === 'generated-components' ? ['pad', 'pen', ...(firstProgress ? ['stroke_first'] : []), ...(secondProgress ? ['stroke_second'] : [])] : [],
    });
  }
  return {
    type: 'activity', source, sourceSha256, sourceSize: [info.width, info.height], columns: 6, rows: 4,
    registration: 'Fixed generated pad during writing; explicit pad-body baseline for the generated page turn; common uniform scale',
    scale, phaseFrames: { entrance: 4, loop: 16, exit: 4 },
    assembly: {
      components,
      method: 'Crop and reuse generated pad, pen and handwriting pixels; reveal each stroke with a left-to-right alpha clip while translating the pen. The pen silhouette occludes the page beneath it. Preserve generated cels 14 through 19 for finishing, curl, page turn and settling. All page cels use the same uniform scale and an explicit pad-body bottom anchor.',
      noNewDrawing: true, sourceOriginalUnchanged: true,
      bodyRegistration: Object.entries(bodyAnchors).map(([cell, anchor]) => ({ sourceCellIndex: +cell, nativeBodyAnchor: anchor, targetStageAnchor: stageAnchor })),
    }, frames,
  };
}

module.exports = { composeNote };
