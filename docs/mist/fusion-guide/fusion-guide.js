(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const storageKey = "mist-fusion-guide-progress-v1";

  function buildNavigation() {
    const nav = $("#chapter-nav");
    if (!nav) return;
    const chapters = $$(".chapter[data-chapter]");
    nav.innerHTML = chapters
      .map((chapter) => {
        const number = chapter.dataset.chapter;
        const heading = $("h2", chapter)?.textContent?.trim() || chapter.id;
        return `<a href="#${chapter.id}" data-nav-for="${chapter.id}"><span>${number}</span><span>${heading}</span></a>`;
      })
      .join("");

    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting && !entry.target.hidden)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (!visible.length) return;
        const id = visible[0].target.id;
        $$("[data-nav-for]", nav).forEach((link) => {
          const active = link.dataset.navFor === id;
          link.classList.toggle("active", active);
          if (active) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        });
      },
      { rootMargin: "-10% 0px -72% 0px", threshold: [0, 0.05, 0.2] },
    );
    chapters.forEach((chapter) => observer.observe(chapter));
  }

  function setupMobileNavigation() {
    const menu = $("#menu-button");
    const sidebar = $("#sidebar");
    if (!menu || !sidebar) return;
    const mobile = window.matchMedia("(max-width: 820px)");
    const focusableSelector = "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex='-1'])";
    const close = (restoreFocus = false) => {
      document.body.classList.remove("nav-open");
      menu.setAttribute("aria-expanded", "false");
      sidebar.inert = mobile.matches;
      if (restoreFocus && mobile.matches) menu.focus();
    };
    menu.addEventListener("click", () => {
      const open = !document.body.classList.contains("nav-open");
      document.body.classList.toggle("nav-open", open);
      menu.setAttribute("aria-expanded", String(open));
      sidebar.inert = !open && mobile.matches;
      if (open) $("#guide-search", sidebar)?.focus();
    });
    sidebar.addEventListener("click", (event) => {
      if (event.target.closest("a[href^='#']")) close(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
        close(true);
        return;
      }
      if (event.key !== "Tab" || !mobile.matches || !document.body.classList.contains("nav-open")) return;
      const focusable = $$(focusableSelector, sidebar).filter((item) => !item.hidden && item.getClientRects().length);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
    mobile.addEventListener("change", () => {
      document.body.classList.remove("nav-open");
      menu.setAttribute("aria-expanded", "false");
      sidebar.inert = mobile.matches;
    });
    sidebar.inert = mobile.matches;
  }

  function setupSearch() {
    const input = $("#guide-search");
    const count = $("#search-count");
    const empty = $("#no-results");
    if (!input) return;
    const chapters = $$(".chapter[data-chapter]");
    const normalize = (value) => value.toLocaleLowerCase().replace(/\s+/g, " ").trim();
    let timer;

    const run = () => {
      const query = normalize(input.value);
      const tokens = query.split(" ").filter(Boolean);
      let matches = 0;
      chapters.forEach((chapter) => {
        const text = normalize(chapter.textContent || "");
        const show = !tokens.length || tokens.every((token) => text.includes(token));
        chapter.hidden = !show;
        const link = $(`[data-nav-for="${chapter.id}"]`);
        if (link) link.hidden = !show;
        if (show) matches += 1;
      });
      if (count) {
        count.textContent = tokens.length ? `${matches} of ${chapters.length} chapters match` : `${chapters.length} chapters`;
      }
      if (empty) empty.hidden = matches > 0;
    };

    input.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(run, 90);
    });
    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        input.focus();
        input.select();
      } else if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest("input, textarea, select, [contenteditable='true']")) {
        event.preventDefault();
        input.focus();
      }
    });
    run();
  }

  function readProgress() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
    } catch {
      return {};
    }
  }

  function setupGates() {
    const gates = $$("input[data-gate]");
    const fill = $("#progress-fill");
    const label = $("#progress-label");
    const reset = $("#reset-progress");
    const state = readProgress();

    gates.forEach((gate) => {
      gate.checked = Boolean(state[gate.dataset.gate]);
    });

    const render = () => {
      const done = gates.filter((gate) => gate.checked).length;
      const percent = gates.length ? Math.round((done / gates.length) * 100) : 0;
      if (fill) {
        fill.style.width = `${percent}%`;
        fill.parentElement?.setAttribute("aria-valuenow", String(percent));
        fill.parentElement?.setAttribute("aria-valuetext", `${done} of ${gates.length} build gates complete`);
      }
      if (label) label.textContent = `${done}/${gates.length}`;
    };

    const persist = () => {
      const next = {};
      gates.forEach((gate) => {
        next[gate.dataset.gate] = gate.checked;
      });
      try {
        localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // The guide remains usable when local storage is unavailable.
      }
      render();
    };

    gates.forEach((gate) => gate.addEventListener("change", persist));
    reset?.addEventListener("click", () => {
      if (!window.confirm("Clear every saved guide gate on this browser?")) return;
      gates.forEach((gate) => {
        gate.checked = false;
      });
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // Ignore storage denial.
      }
      render();
    });
    render();
  }

  function setupCopyButtons() {
    $$("pre").forEach((pre) => {
      if ($(".copy-button", pre)) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy-button no-print";
      button.textContent = "Copy";
      button.setAttribute("aria-label", "Copy code block");
      button.addEventListener("click", async () => {
        const text = $("code", pre)?.textContent || pre.textContent || "";
        try {
          await navigator.clipboard.writeText(text);
          button.textContent = "Copied";
          window.setTimeout(() => (button.textContent = "Copy"), 1300);
        } catch {
          const code = $("code", pre);
          if (code) {
            const range = document.createRange();
            range.selectNodeContents(code);
            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(range);
            button.textContent = "Selected — Ctrl+C";
            window.setTimeout(() => (button.textContent = "Copy"), 2200);
          } else {
            button.textContent = "Select text";
          }
        }
      });
      pre.append(button);
    });
  }

  function setupImageDialog() {
    const dialog = $("#image-dialog");
    const image = $("#dialog-image");
    const title = $("#dialog-title");
    const close = $("#dialog-close");
    if (!dialog || !image || !title) return;

    $$('[data-zoom-src]').forEach((trigger) => {
      const open = () => {
        image.src = trigger.dataset.zoomSrc || "";
        image.alt = trigger.dataset.zoomTitle || "Expanded guide image";
        title.textContent = trigger.dataset.zoomTitle || "Guide image";
        dialog.showModal();
      };
      trigger.addEventListener("click", open);
      if (!(trigger instanceof HTMLButtonElement) && !(trigger instanceof HTMLAnchorElement)) {
        trigger.tabIndex = 0;
        trigger.setAttribute("role", "button");
        trigger.setAttribute("aria-label", `Expand image: ${trigger.dataset.zoomTitle || "guide image"}`);
        trigger.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          open();
        });
      }
    });
    close?.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  }

  function setupPrint() {
    $("#print-guide")?.addEventListener("click", () => window.print());
    let detailState = [];
    window.addEventListener("beforeprint", () => {
      detailState = $$("details").map((item) => item.open);
      $$("details").forEach((item) => (item.open = true));
    });
    window.addEventListener("afterprint", () => {
      $$("details").forEach((item, index) => (item.open = detailState[index] ?? item.open));
    });
  }

  const presets = {
    A: { bodyDia: 180, bodyH: 260, d1: 32, femur: 110, tibia: 70, wheelDia: 70, stanceR: 176, bodyClearance: 148, beamT: 14, frontAz: 25, rearAz: 109 },
    B: { bodyDia: 180, bodyH: 260, d1: 31, femur: 82, tibia: 91, wheelDia: 70, stanceR: 169, bodyClearance: 140, beamT: 14, frontAz: 25, rearAz: 119 },
    C: { bodyDia: 180, bodyH: 260, d1: 37, femur: 73, tibia: 85, wheelDia: 70, stanceR: 157, bodyClearance: 132, beamT: 14, frontAz: 25, rearAz: 114 },
    D: { bodyDia: 180, bodyH: 260, d1: 42, femur: 70, tibia: 101, wheelDia: 70, stanceR: 168, bodyClearance: 132, beamT: 14, frontAz: 25, rearAz: 111 },
    E: { bodyDia: 180, bodyH: 260, d1: 59, femur: 70, tibia: 96, wheelDia: 70, stanceR: 183, bodyClearance: 130, beamT: 14, frontAz: 25, rearAz: 124 },
  };

  const controls = {
    bodyDia: { id: "p-body-dia", unit: "mm" },
    bodyH: { id: "p-body-h", unit: "mm" },
    d1: { id: "p-d1", unit: "mm" },
    femur: { id: "p-femur", unit: "mm" },
    tibia: { id: "p-tibia", unit: "mm" },
    wheelDia: { id: "p-wheel-dia", unit: "mm" },
    stanceR: { id: "p-stance-r", unit: "mm" },
    bodyClearance: { id: "p-body-clearance", unit: "mm" },
    beamT: { id: "p-beam-t", unit: "mm" },
    frontAz: { id: "p-front-az", unit: "°" },
    rearAz: { id: "p-rear-az", unit: "°" },
  };

  const rom = { q2Min: -35, q2Max: 110, q3Min: -135, q3Max: 135 };

  function valuesFromControls() {
    return Object.fromEntries(
      Object.entries(controls).map(([key, spec]) => [key, Number($(`#${spec.id}`)?.value || presets.A[key])]),
    );
  }

  function setControls(values) {
    Object.entries(controls).forEach(([key, spec]) => {
      const input = $(`#${spec.id}`);
      const output = $(`[data-output-for="${spec.id}"]`);
      if (!input || values[key] == null) return;
      input.value = String(values[key]);
      if (output) output.textContent = `${Number(values[key]).toFixed(Number(values[key]) % 1 ? 1 : 0)} ${spec.unit}`;
    });
  }

  function solveGeometry(p) {
    const bodyR = p.bodyDia / 2;
    const mountR = bodyR + 10;
    const hipR = mountR + p.d1;
    const hipZ = p.bodyClearance + 35;
    const axleX = p.stanceR;
    const axleZ = p.wheelDia / 2;
    const dx = axleX - hipR;
    const down = hipZ - axleZ;
    const reach = Math.hypot(dx, down);
    const denominator = 2 * p.femur * p.tibia;
    const cosine = denominator ? (reach ** 2 - p.femur ** 2 - p.tibia ** 2) / denominator : 2;
    const reachable = cosine >= -1 && cosine <= 1;
    const clamped = Math.max(-1, Math.min(1, cosine));
    const q3 = -Math.acos(clamped);
    const gamma = Math.atan2(dx, down);
    const q2 = gamma - Math.atan2(p.tibia * Math.sin(q3), p.femur + p.tibia * Math.cos(q3));
    const kneeX = hipR + p.femur * Math.sin(q2);
    const kneeZ = hipZ - p.femur * Math.cos(q2);
    const solvedAxleX = kneeX + p.tibia * Math.sin(q2 + q3);
    const solvedAxleZ = kneeZ - p.tibia * Math.cos(q2 + q3);
    const q2Deg = (q2 * 180) / Math.PI;
    const q3Deg = (q3 * 180) / Math.PI;
    const q2Within = reachable && q2Deg >= rom.q2Min && q2Deg <= rom.q2Max;
    const q3Within = reachable && q3Deg >= rom.q3Min && q3Deg <= rom.q3Max;
    return { bodyR, mountR, hipR, hipZ, axleX, axleZ, dx, down, reach, reachable, q2, q3, q2Deg, q3Deg, q2Within, q3Within, romValid: q2Within && q3Within, kneeX, kneeZ, solvedAxleX, solvedAxleZ };
  }

  function maximumFootprint(p) {
    const angles = [p.frontAz, -p.frontAz, p.rearAz, -p.rearAz].map((angle) => (angle * Math.PI) / 180);
    const points = angles.map((angle) => [p.stanceR * Math.cos(angle), p.stanceR * Math.sin(angle)]);
    let maximum = 0;
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        maximum = Math.max(maximum, Math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1]));
      }
    }
    return maximum + p.wheelDia;
  }

  function drawExplorer(svg, p, g) {
    if (!svg) return;
    const sx = (x) => 178 + x * 1.05;
    const sy = (z) => 300 - z * 0.64;
    const bodyLeft = sx(-g.bodyR);
    const bodyRight = sx(g.bodyR);
    const bodyBottom = sy(p.bodyClearance);
    const bodyTop = sy(p.bodyClearance + p.bodyH);
    const wheelRadius = (p.wheelDia / 2) * 0.64;
    const mountX = sx(g.mountR);
    const hipX = sx(g.hipR);
    const jointY = sy(g.hipZ);
    const kneeX = sx(g.kneeX);
    const kneeY = sy(g.kneeZ);
    const targetAxleX = sx(g.axleX);
    const targetAxleY = sy(g.axleZ);
    const axleX = sx(g.solvedAxleX);
    const axleY = sy(g.solvedAxleZ);
    const topCx = 585;
    const topCy = 112;
    const topScale = 0.42;
    const mountAngles = [p.frontAz, -p.frontAz, p.rearAz, -p.rearAz];
    const topR = g.bodyR * topScale;
    const mountMarkup = mountAngles
      .map((angle, index) => {
        const rad = (angle * Math.PI) / 180;
        const mx = topCx + g.mountR * topScale * Math.cos(rad);
        const my = topCy - g.mountR * topScale * Math.sin(rad);
        const fx = topCx + p.stanceR * topScale * Math.cos(rad);
        const fy = topCy - p.stanceR * topScale * Math.sin(rad);
        const names = ["FL", "FR", "RL", "RR"];
        return `<line x1="${mx}" y1="${my}" x2="${fx}" y2="${fy}" stroke="#c95618" stroke-width="2" stroke-dasharray="4 3"/><circle cx="${mx}" cy="${my}" r="4" fill="#0f766e"/><circle cx="${fx}" cy="${fy}" r="5" fill="#1d211f"/><text x="${fx + 7}" y="${fy - 5}" font-size="10" font-family="Consolas" fill="#1d211f">${names[index]} ${angle > 0 ? "+" : ""}${angle}°</text>`;
      })
      .join("");
    const reachErrorMarkup = g.reachable
      ? ""
      : `<line x1="${axleX}" y1="${axleY}" x2="${targetAxleX}" y2="${targetAxleY}" stroke="#b42318" stroke-width="2" stroke-dasharray="5 4"/><path d="M ${targetAxleX - 7} ${targetAxleY - 7} L ${targetAxleX + 7} ${targetAxleY + 7} M ${targetAxleX + 7} ${targetAxleY - 7} L ${targetAxleX - 7} ${targetAxleY + 7}" stroke="#b42318" stroke-width="3"/><text x="${targetAxleX + 10}" y="${targetAxleY - 9}" font-size="10" font-family="Consolas" fill="#b42318">UNREACHABLE TARGET</text>`;

    svg.innerHTML = `
      <line x1="25" y1="300" x2="695" y2="300" stroke="#565b56" stroke-width="2"/>
      <text x="28" y="292" font-family="Consolas" font-size="10" fill="#565b56">GROUND</text>
      <line x1="${sx(0)}" y1="18" x2="${sx(0)}" y2="305" stroke="#9f998e" stroke-width="1" stroke-dasharray="5 5"/>
      <path d="M ${bodyLeft} ${bodyBottom} L ${bodyLeft} ${bodyTop + 12} Q ${sx(0)} ${bodyTop - 18} ${bodyRight} ${bodyTop + 12} L ${bodyRight} ${bodyBottom} Z" fill="#efede7" stroke="#1d211f" stroke-width="2"/>
      <line x1="${bodyRight}" y1="${jointY}" x2="${mountX}" y2="${jointY}" stroke="#235b9a" stroke-width="7"/>
      <line x1="${mountX}" y1="${jointY}" x2="${hipX}" y2="${jointY}" stroke="#d69b25" stroke-width="7"/>
      <line x1="${hipX}" y1="${jointY}" x2="${kneeX}" y2="${kneeY}" stroke="#c95618" stroke-width="13" stroke-linecap="round"/>
      <line x1="${kneeX}" y1="${kneeY}" x2="${axleX}" y2="${axleY}" stroke="#0f766e" stroke-width="13" stroke-linecap="round"/>
      <circle cx="${mountX}" cy="${jointY}" r="7" fill="#235b9a" stroke="#fff" stroke-width="2"/>
      <circle cx="${hipX}" cy="${jointY}" r="7" fill="#d69b25" stroke="#fff" stroke-width="2"/>
      <circle cx="${kneeX}" cy="${kneeY}" r="7" fill="#c95618" stroke="#fff" stroke-width="2"/>
      <circle cx="${axleX}" cy="${axleY}" r="${wheelRadius}" fill="${g.reachable ? "#303532" : "#f9e2df"}" stroke="${g.reachable ? "#1d211f" : "#b42318"}" stroke-width="3"/>
      <circle cx="${axleX}" cy="${axleY}" r="5" fill="#d9d6ce"/>
      ${reachErrorMarkup}
      <text x="${mountX - 18}" y="${jointY - 13}" font-family="Consolas" font-size="10" fill="#235b9a">q1</text>
      <text x="${hipX + 7}" y="${jointY - 13}" font-family="Consolas" font-size="10" fill="#8a620c">q2</text>
      <text x="${kneeX + 8}" y="${kneeY - 8}" font-family="Consolas" font-size="10" fill="#9b3e0d">q3</text>
      <text x="${bodyLeft}" y="${bodyTop - 8}" font-family="Consolas" font-size="10" fill="#1d211f">SIDE / ONE LEG</text>
      <circle cx="${topCx}" cy="${topCy}" r="${topR}" fill="#efede7" stroke="#1d211f" stroke-width="2"/>
      <line x1="${topCx}" y1="${topCy + topR + 20}" x2="${topCx}" y2="${topCy - topR - 30}" stroke="#235b9a" stroke-width="1.5" marker-end="url(#arrow)"/>
      <text x="${topCx + 6}" y="${topCy - topR - 23}" font-family="Consolas" font-size="10" fill="#235b9a">+X FRONT</text>
      ${mountMarkup}
      <text x="500" y="225" font-family="Consolas" font-size="10" fill="#565b56">TOP / PHYSICAL MOUNT RAYS</text>
      <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#235b9a"/></marker></defs>
    `;
  }

  function setMetric(id, value, status = "") {
    const card = $(`#${id}`);
    if (!card) return;
    $("strong", card).textContent = value;
    card.classList.remove("warn", "fail");
    if (status) card.classList.add(status);
    $(".metric-status", card)?.remove();
    if (status) {
      const marker = document.createElement("span");
      marker.className = "metric-status";
      marker.textContent = status === "fail" ? "Outside screen" : "Review";
      card.append(marker);
    }
    const label = $("span:not(.metric-status)", card)?.textContent?.trim() || id;
    card.setAttribute("aria-label", `${label}: ${value}${status ? `, ${status === "fail" ? "outside screen" : "review required"}` : ""}`);
  }

  function renderExplorer() {
    const p = valuesFromControls();
    const g = solveGeometry(p);
    const reachRatio = g.reach / (p.femur + p.tibia);
    const reachStatus = !g.reachable || reachRatio > 0.94 ? "fail" : reachRatio > 0.86 ? "warn" : "";
    const footprint = maximumFootprint(p);
    const stiffness = (p.beamT / 14) ** 3 * (110 / p.femur) ** 3;
    const shellProxy = (p.bodyDia * p.bodyH) / (180 * 260);
    const zMargin = 265 - p.bodyH;
    const bedStatus = p.bodyDia > 225 || p.bodyH > 265 ? "fail" : p.bodyDia > 215 || zMargin < 15 ? "warn" : "";

    Object.entries(controls).forEach(([key, spec]) => {
      const output = $(`[data-output-for="${spec.id}"]`);
      if (output) output.textContent = `${p[key].toFixed(p[key] % 1 ? 1 : 0)} ${spec.unit}`;
    });

    drawExplorer($("#parameter-svg"), p, g);
    setMetric("metric-reach", `${(reachRatio * 100).toFixed(1)}%`, reachStatus);
    setMetric("metric-footprint", `${footprint.toFixed(0)} mm`);
    setMetric("metric-stiffness", `${stiffness.toFixed(2)}×`, stiffness < 0.72 ? "warn" : "");
    setMetric("metric-shell", `${shellProxy.toFixed(2)}×`, shellProxy > 1.12 ? "warn" : "");
    setMetric("metric-bed", `${Math.min(225 - p.bodyDia, zMargin).toFixed(0)} mm`, bedStatus);
    setMetric("metric-hip-radius", `${g.hipR.toFixed(0)} mm`);
    setMetric("metric-q2", g.reachable ? `${g.q2Deg.toFixed(1)}°` : "n/a", !g.reachable || !g.q2Within ? "fail" : "");
    setMetric("metric-q3", g.reachable ? `${g.q3Deg.toFixed(1)}°` : "n/a", !g.reachable || !g.q3Within ? "fail" : "");

    const message = $("#explorer-message");
    if (!message) return;
    message.className = "explorer-message";
    if (!g.reachable) {
      message.classList.add("fail");
      message.textContent = "Outside geometry screen: the target is outside the two-link workspace. The red wheel is the nearest solved endpoint and the red cross is the requested axle; change stance/height or link lengths before modeling brackets.";
    } else if (!g.romValid) {
      message.classList.add("fail");
      const failures = [!g.q2Within ? `q2 ${g.q2Deg.toFixed(1)}° is outside ${rom.q2Min}°…${rom.q2Max}°` : "", !g.q3Within ? `q3 ${g.q3Deg.toFixed(1)}° is outside ${rom.q3Min}°…${rom.q3Max}°` : ""].filter(Boolean);
      message.textContent = `Outside joint-limit screen: ${failures.join("; ")}. Reach alone is not enough—change the pose or geometry and re-run the full Fusion sweep.`;
    } else if (reachRatio > 0.86) {
      message.classList.add(reachRatio > 0.94 ? "fail" : "warn");
      message.textContent = `The leg uses ${(reachRatio * 100).toFixed(1)}% of straight-line reach. The MIST study reserves about 14% for stride and tolerance; this edit consumes that headroom.`;
    } else if (bedStatus) {
      message.classList.add(bedStatus);
      message.textContent = "Geometry is reachable, but the one-piece barrel is close to or beyond the Neptune 4 Pro envelope. Split the shell and add indexed fasteners.";
    } else {
      message.textContent = "Geometry-only preview passes the 86% reach-headroom and q2/q3 joint-limit screens. It does not calculate q1, collision, cable bend, servo torque, mass, print strength, or wheel scrub.";
    }
  }

  function setupExplorer() {
    const svg = $("#parameter-svg");
    if (!svg) return;
    const markPreset = (activeButton = null) => {
      $$(".preset-button[data-preset]").forEach((button) => {
        const active = button === activeButton;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
    };
    Object.values(controls).forEach((spec) => {
      $(`#${spec.id}`)?.addEventListener("input", () => {
        markPreset();
        renderExplorer();
      });
    });
    $$(".preset-button[data-preset]").forEach((button) => {
      button.addEventListener("click", () => {
        const preset = presets[button.dataset.preset];
        if (!preset) return;
        setControls(preset);
        markPreset(button);
        renderExplorer();
      });
    });
    setControls(presets.A);
    markPreset($(".preset-button[data-preset='A']"));
    renderExplorer();
  }

  function markExternalLinks() {
    $$("a[href^='http']").forEach((link) => {
      link.target = "_blank";
      link.rel = "noreferrer noopener";
    });
  }

  buildNavigation();
  setupMobileNavigation();
  setupSearch();
  setupGates();
  setupCopyButtons();
  setupImageDialog();
  setupPrint();
  setupExplorer();
  markExternalLinks();
})();
