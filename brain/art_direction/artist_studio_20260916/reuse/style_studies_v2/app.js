(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const filter = $('filter');
  const inspector = $('inspector');
  const styleSelect = $('inspect-style');
  const comparison = $('comparison');
  let manifest;
  let faceIndex = 0;
  let returnFocus = null;
  let variants = [];
  let mobileDefaultApplied = false;

  const shortId = face => String(face.id).split('_')[0];
  const titleFor = face => `${shortId(face)} · ${face.label}`;
  const sourceFor = (face, style) => {
    const asset = manifest.assets[String(face.id)]?.[style];
    const file = asset?.file || (style === 'original' ? face.original : '');
    return file ? `${file}${file.includes('?') ? '&' : '?'}v=${encodeURIComponent(asset?.sha256 || manifest.version)}` : '';
  };
  const variantStyle = id => variants.find(style => style.id === id) || variants[0];
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function renderRows() {
    const chosen = filter.value;
    const original = manifest.styles.find(style => style.id === 'original') || { id: 'original', label: 'Current', description: '' };
    const styles = chosen === 'all' ? [original, ...variants] : [original, variantStyle(chosen)];
    comparison.style.setProperty('--columns', styles.length);
    comparison.dataset.columns = styles.length;
    $('column-heads').replaceChildren(...styles.map(style => {
      const heading = element('div');
      heading.append(element('p', 'column-title', style.label), element('p', 'column-description', style.description || ''));
      return heading;
    }));
    $('rows').replaceChildren(...manifest.faces.map((face, index) => {
      const section = element('section', 'face-row');
      const heading = element('h2', 'face-title');
      heading.id = `face-${index}`;
      heading.append(element('span', 'face-id', shortId(face)), document.createTextNode(face.label));
      section.setAttribute('aria-labelledby', heading.id);
      const images = element('div', 'face-images');
      for (const style of styles) {
        const button = element('button', 'tile');
        button.type = 'button';
        button.setAttribute('aria-label', `Inspect ${face.label}, ${style.label}`);
        const img = element('img');
        img.alt = `${face.label}, ${style.label}`;
        img.width = 512;
        img.height = 307;
        img.loading = index < 3 ? 'eager' : 'lazy';
        img.decoding = 'async';
        img.addEventListener('error', () => {
          img.hidden = true;
          button.append(element('span', 'missing', 'Image unavailable. Refresh to retry.'));
        }, { once: true });
        img.src = sourceFor(face, style.id);
        button.append(img);
        button.addEventListener('click', () => openFace(index, style.id === 'original' ? (chosen === 'all' ? variants[0].id : chosen) : style.id, button));
        images.append(button);
      }
      section.append(heading, images);
      return section;
    }));
  }

  function updateInspector() {
    const face = manifest.faces[faceIndex];
    const style = variantStyle(styleSelect.value);
    $('inspect-title').textContent = titleFor(face);
    $('face-position').textContent = `${faceIndex + 1} / ${manifest.faces.length}`;
    $('previous').disabled = faceIndex === 0;
    $('next').disabled = faceIndex === manifest.faces.length - 1;
    const original = $('inspect-original');
    const variant = $('inspect-variant');
    original.src = sourceFor(face, 'original');
    original.alt = `${face.label}, current MIST face`;
    variant.src = sourceFor(face, style.id);
    variant.alt = `${face.label}, ${style.label}`;
    $('inspect-label').textContent = style.label;
    $('inspect-description').textContent = style.description || '';
    for (const [linkId, styleId] of [['download-original', 'original'], ['download-variant', style.id]]) {
      const link = $(linkId);
      link.href = sourceFor(face, styleId);
      link.download = `MIST-${face.id}-${styleId}.png`;
      link.setAttribute('aria-label', `Download ${face.label}, ${styleId === 'original' ? 'current' : style.label}, PNG`);
    }
  }

  function openFace(index, style, trigger) {
    faceIndex = index;
    returnFocus = trigger;
    styleSelect.value = style;
    updateInspector();
    inspector.showModal();
  }

  filter.addEventListener('change', renderRows);
  styleSelect.addEventListener('change', updateInspector);
  $('close').addEventListener('click', () => inspector.close());
  inspector.addEventListener('close', () => returnFocus?.focus());
  $('previous').addEventListener('click', () => { if (faceIndex > 0) { faceIndex--; updateInspector(); } });
  $('next').addEventListener('click', () => { if (faceIndex < manifest.faces.length - 1) { faceIndex++; updateInspector(); } });
  inspector.addEventListener('click', event => {
    if (event.target !== inspector) return;
    const bounds = inspector.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) inspector.close();
  });

  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const command = `${$('folder-command').textContent}\r\n${$(button.dataset.copy).textContent}`;
      try {
        await navigator.clipboard.writeText(command);
        $('copy-status').textContent = 'Copied. Paste into PowerShell.';
      } catch {
        $('copy-status').textContent = 'Clipboard unavailable. Select and copy the commands above.';
      }
    });
  });

  async function load() {
    try {
      const response = await fetch('manifest.json', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Manifest returned ${response.status}`);
      manifest = await response.json();
      if (!Array.isArray(manifest.faces) || !manifest.faces.length || !Array.isArray(manifest.styles) || !manifest.assets) throw new Error('Incomplete manifest');
      variants = manifest.styles.filter(style => style.id !== 'original');
      if (!variants.length) throw new Error('No style studies listed');
      for (const style of variants) {
        filter.add(new Option(style.label, style.id));
        styleSelect.add(new Option(style.label, style.id));
      }
      if (window.matchMedia('(max-width: 640px)').matches && !mobileDefaultApplied) {
        filter.value = variants[0].id;
        mobileDefaultApplied = true;
      }
      $('selection-basis').textContent = manifest.basis || 'Main conversation faces, plus expressive alternatives.';
      renderRows();
      comparison.hidden = false;
      filter.disabled = false;
      $('status').hidden = true;
    } catch (error) {
      console.error('Face style studies:', error);
      $('status').hidden = true;
      $('error').hidden = false;
      $('error').textContent = 'The face files could not load. Check that the studio server is running, then refresh this page.';
    }
  }
  load();
})();
