'use strict';

const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.env.MIST_SHARP_PATH || '<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');

const SIZE = 256;
const CLEAR = {r: 0, g: 0, b: 0, alpha: 0};
const round = n => Math.round(n * 1000) / 1000;

function components(cell, threshold = 128) {
  const {buf, cw, ch} = cell;
  const seen = new Uint8Array(cw * ch), found = [];
  for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
    const start = y * cw + x;
    if (seen[start] || buf[start * 4 + 3] < threshold) continue;
    const queue = [start];
    seen[start] = 1;
    let left = x, right = x, top = y, bottom = y;
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i], px = p % cw, py = Math.floor(p / cw);
      left = Math.min(left, px); right = Math.max(right, px);
      top = Math.min(top, py); bottom = Math.max(bottom, py);
      for (const [nx, ny] of [[px - 1, py], [px + 1, py], [px, py - 1], [px, py + 1]]) {
        if (nx < 0 || nx >= cw || ny < 0 || ny >= ch) continue;
        const next = ny * cw + nx;
        if (!seen[next] && buf[next * 4 + 3] >= threshold) {
          seen[next] = 1;
          queue.push(next);
        }
      }
    }
    if (queue.length > 10) found.push({left, top, width: right - left + 1, height: bottom - top + 1, pixels: queue.length});
  }
  return found.sort((a, b) => b.pixels - a.pixels);
}

async function readCell(bytes, index) {
  const meta = await sharp(bytes).metadata();
  const x = Math.round((index % 6) * meta.width / 6);
  const y = Math.round(Math.floor(index / 6) * meta.height / 4);
  const cw = Math.round((index % 6 + 1) * meta.width / 6) - x;
  const ch = Math.round((Math.floor(index / 6) + 1) * meta.height / 4) - y;
  const buf = await sharp(bytes).ensureAlpha().extract({left: x, top: y, width: cw, height: ch}).raw().toBuffer();
  return {buf, cw, ch, sourceCell: [x, y, cw, ch]};
}

function padded(box, cell, padding = 2) {
  const left = Math.max(0, box.left - padding), top = Math.max(0, box.top - padding);
  return {
    left, top,
    width: Math.min(cell.cw, box.left + box.width + padding) - left,
    height: Math.min(cell.ch, box.top + box.height + padding) - top,
  };
}

async function saveCrop(root, file, cell, box, source, sourceBytes, sha) {
  const bytes = await sharp(cell.buf, {raw: {width: cell.cw, height: cell.ch, channels: 4}}).extract(box).png().toBuffer();
  fs.writeFileSync(path.join(root, file), bytes);
  return {
    bytes, width: box.width, height: box.height,
    metadata: {
      file, sha256: sha(bytes), source, sourceSha256: sha(sourceBytes),
      sourceCell: cell.sourceCell,
      cropWithinCell: [box.left, box.top, box.width, box.height],
      sourceRect: [cell.sourceCell[0] + box.left, cell.sourceCell[1] + box.top, box.width, box.height],
    },
  };
}

async function alphaBounds(bytes) {
  const data = await sharp(bytes).ensureAlpha().raw().toBuffer();
  let left = SIZE, top = SIZE, right = -1, bottom = -1;
  for (let y = 0; y < SIZE; y++) for (let x = 0; x < SIZE; x++) if (data[(y * SIZE + x) * 4 + 3] > 0) {
    left = Math.min(left, x); right = Math.max(right, x);
    top = Math.min(top, y); bottom = Math.max(bottom, y);
  }
  if (right < left) throw Error('The assembled frame is empty');
  if (left < 32 || top < 32 || right >= SIZE - 32 || bottom >= SIZE - 32) throw Error('The assembled frame exceeds its 32px margin');
  return [left, top, right - left + 1, bottom - top + 1];
}

async function composeScan(id, original, info, cells, root, sha) {
  if (!['checking', 'connecting'].includes(id)) throw Error('Unsupported rigid scan: ' + id);
  fs.mkdirSync(path.join(root, 'components'), {recursive: true});
  fs.mkdirSync(path.join(root, 'frames', id), {recursive: true});
  let body, marker, artScale, bodyLeft, bodyTop, markerStart, markerEnd;

  if (id === 'checking') {
    const source = 'source/checking_parts.png', sourceBytes = fs.readFileSync(path.join(root, source));
    const cell = await readCell(sourceBytes, 4), shapes = components(cell);
    const page = shapes[0];
    if (!page || page.width < 100 || page.height < 140) throw Error('Expected a complete page in checking_parts cell 4');
    const bracket = shapes.find(c => c.left > page.left + page.width && c.height > 20 && c.width < 30);
    if (!bracket) throw Error('Expected a separate right bracket in checking_parts cell 4');
    // The rectangle retains every interior line and all three empty checkboxes.
    body = await saveCrop(root, 'components/checking_body.png', cell, padded(page, cell), source, sourceBytes, sha);
    marker = await saveCrop(root, 'components/checking_bracket.png', cell, padded(bracket, cell), source, sourceBytes, sha);
    artScale = 1;
    bodyLeft = Math.round((SIZE - (bracket.left + bracket.width - page.left + 4)) / 2);
    bodyTop = Math.round((SIZE - body.height) / 2);
    const markerX = bodyLeft + bracket.left - page.left + marker.width / 2;
    markerStart = {x: markerX, y: bodyTop + marker.height / 2 + 8};
    markerEnd = {x: markerX, y: bodyTop + body.height - marker.height / 2 - 8};
  } else {
    // Cell 2 has two endpoints and three plain dashes. Cell 4 already has a packet.
    const bodyCell = cells[2], packetCell = cells[5];
    const shapes = components(bodyCell), endpoints = shapes.filter(c => c.height > 20).sort((a, b) => a.left - b.left);
    if (endpoints.length !== 2 || shapes.some(c => c.height > 8 && c.left > endpoints[0].left + endpoints[0].width && c.left < endpoints[1].left)) throw Error('Expected an unoccupied dashed path in connecting cell 2');
    const packet = components(packetCell).find(c => c.height >= 10 && c.height <= 20 && c.width >= 20 && c.width <= 40 && c.left > 80 && c.left < 160);
    if (!packet) throw Error('Expected a separate packet in connecting cell 5');
    body = await saveCrop(root, 'components/connecting_path.png', bodyCell, bodyCell.box, 'source/connecting.png', original, sha);
    marker = await saveCrop(root, 'components/connecting_packet.png', packetCell, padded(packet, packetCell), 'source/connecting.png', original, sha);
    artScale = 188 / body.width;
    bodyLeft = 34;
    bodyTop = Math.round((SIZE - Math.round(body.height * artScale)) / 2);
    const packetRadius = packet.width / 2;
    const minX = endpoints[0].left + endpoints[0].width + packetRadius + 6;
    const maxX = endpoints[1].left - packetRadius - 6;
    const pathY = (endpoints[0].top + endpoints[0].height / 2 + endpoints[1].top + endpoints[1].height / 2) / 2;
    markerStart = {x: bodyLeft + (minX - bodyCell.box.left) * artScale, y: bodyTop + (pathY - bodyCell.box.top) * artScale};
    markerEnd = {x: bodyLeft + (maxX - bodyCell.box.left) * artScale, y: markerStart.y};
  }

  const bodyWidth = Math.round(body.width * artScale), bodyHeight = Math.round(body.height * artScale);
  const markerWidth = Math.round(marker.width * artScale), markerHeight = Math.round(marker.height * artScale);
  const bodyPng = await sharp(body.bytes).resize(bodyWidth, bodyHeight).png().toBuffer();
  const markerPng = await sharp(marker.bytes).resize(markerWidth, markerHeight).png().toBuffer();
  // A quarter-frame phase offset gives different positions on the return leg.
  const positions = Array.from({length: 16}, (_, k) => {
    const phase = (k + 0.25) / 16, t = 1 - Math.abs(2 * phase - 1);
    return {
      left: Math.round(markerStart.x + (markerEnd.x - markerStart.x) * t - markerWidth / 2),
      top: Math.round(markerStart.y + (markerEnd.y - markerStart.y) * t - markerHeight / 2),
    };
  });
  if (new Set(positions.map(p => `${p.left},${p.top}`)).size !== 16) throw Error(id + ' needs sixteen distinct raster marker positions');
  const seam = Math.hypot(positions[15].left - positions[0].left, positions[15].top - positions[0].top);
  const largestStep = Math.max(...positions.slice(1).map((p, k) => Math.hypot(p.left - positions[k].left, p.top - positions[k].top)));
  if (seam > largestStep) throw Error(id + ' loop seam is larger than its normal motion');

  const frames = [];
  for (let i = 0; i < 24; i++) {
    const loopIndex = i < 4 ? 0 : i < 20 ? i - 4 : 15;
    const markerPose = positions[loopIndex];
    const phaseScale = i < 4 ? [0.55, 0.72, 0.88, 0.97][i] : i < 20 ? 1 : [0.94, 0.79, 0.61, 0.42][i - 20];
    const assembled = await sharp({create: {width: SIZE, height: SIZE, channels: 4, background: CLEAR}}).composite([
      {input: bodyPng, left: bodyLeft, top: bodyTop},
      {input: markerPng, left: markerPose.left, top: markerPose.top},
    ]).png().toBuffer();
    const dimension = Math.round(SIZE * phaseScale), offset = Math.round((SIZE - dimension) / 2), actualScale = dimension / SIZE;
    const bytes = dimension === SIZE ? assembled : await sharp({create: {width: SIZE, height: SIZE, channels: 4, background: CLEAR}}).composite([
      {input: await sharp(assembled).resize(dimension, dimension).png().toBuffer(), left: offset, top: offset},
    ]).png().toBuffer();
    const bounds = await alphaBounds(bytes), file = `frames/${id}/${String(i).padStart(2, '0')}.png`;
    fs.writeFileSync(path.join(root, file), bytes);
    const markerPosition = {x: round(offset + (markerPose.left + markerWidth / 2) * actualScale), y: round(offset + (markerPose.top + markerHeight / 2) * actualScale)};
    frames.push({
      file, pose: i < 4 ? `enter_${i}` : i < 20 ? `loop_${i - 4}` : `exit_${i - 20}`, bounds,
      sourceCell: body.metadata.sourceCell,
      sourceCells: [body.metadata.sourceCell, marker.metadata.sourceCell],
      componentFiles: [body.metadata.file, marker.metadata.file],
      components: [
        {file: body.metadata.file, sourceCell: body.metadata.sourceCell, x: round(offset + (bodyLeft + bodyWidth / 2) * actualScale), y: round(offset + (bodyTop + bodyHeight / 2) * actualScale), scale: actualScale},
        {file: marker.metadata.file, sourceCell: marker.metadata.sourceCell, x: markerPosition.x, y: markerPosition.y, scale: actualScale},
      ],
      markerPosition,
      markerBounds: [round(offset + markerPose.left * actualScale), round(offset + markerPose.top * actualScale), round(markerWidth * actualScale), round(markerHeight * actualScale)],
      bodyBounds: [round(offset + bodyLeft * actualScale), round(offset + bodyTop * actualScale), round(bodyWidth * actualScale), round(bodyHeight * actualScale)],
      assemblyScale: actualScale, markerLoopIndex: loopIndex, sha256: sha(bytes),
    });
  }
  return {
    type: 'activity', source: `source/${id}.png`, sourceSha256: sha(original), sourceSize: [info.width, info.height],
    columns: 6, rows: 4, registration: 'fixed ImageGen body with a translated ImageGen marker', scale: 1,
    assembly: {
      method: 'Rectangular crops of ImageGen artwork, uniform scaling and translation. Entrance and exit scale the complete assembly with its marker attached.',
      components: [body.metadata, marker.metadata],
      activeMotion: {path: id === 'checking' ? 'down then up' : 'out then back', interpolation: 'triangle', phaseOffsetFrames: 0.25, distinctPositions: positions.length, seamPixels: seam, maximumStepPixels: largestStep},
    },
    phaseFrames: {entrance: 4, loop: 16, exit: 4}, frames,
  };
}

module.exports = composeScan;
module.exports.composeScan = composeScan;
