const SERVER = "http://localhost:7373";

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("v");
}

// ── Buton enjeksiyonu ────────────────────────────────────────────────────────

function injectStyles() {
  if (document.getElementById("chevren-styles")) return;
  const style = document.createElement("style");
  style.id = "chevren-styles";
  style.textContent = `
    #chevren-btn-mpv,
    #chevren-btn-overlay,
    #chevren-btn-regen {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      position: relative;
    }
    #chevren-tooltip {
      position: fixed;
      background: rgba(28,28,28,0.95);
      color: #fff;
      font-size: 12px;
      font-family: sans-serif;
      padding: 4px 8px;
      border-radius: 4px;
      pointer-events: none;
      z-index: 999999;
      white-space: nowrap;
      transform: translateX(-50%);
    }
  `;
  document.head.appendChild(style);
}

function initTooltip() {
  if (document.getElementById("chevren-tooltip")) return;
  const tip = document.createElement("div");
  tip.id = "chevren-tooltip";
  tip.style.display = "none";
  document.body.appendChild(tip);
}

function bindTooltip(el, text) {
  el.setAttribute("data-chevren-tip", text);
  el.addEventListener("mouseenter", (e) => {
    const tip = document.getElementById("chevren-tooltip");
    if (!tip) return;
    tip.textContent = el.getAttribute("data-chevren-tip");
    tip.style.display = "block";
    const rect = el.getBoundingClientRect();
    tip.style.left = (rect.left + rect.width / 2) + "px";
    tip.style.top = (rect.top - 32) + "px";
  });
  el.addEventListener("mouseleave", () => {
    const tip = document.getElementById("chevren-tooltip");
    if (tip) tip.style.display = "none";
  });
}

function injectButtons() {
  if (document.getElementById("chevren-btn-mpv")) return;

  const controls = document.querySelector(".ytp-right-controls");
  if (!controls) return;

  injectStyles();
  initTooltip();

  // mpv butonu
  const btnMpv = document.createElement("button");
  btnMpv.id = "chevren-btn-mpv";
  btnMpv.className = "ytp-button";
  bindTooltip(btnMpv, "mpv'de aç");
  btnMpv.innerHTML = `<svg viewBox="0 0 36 36" width="22" height="22">
    <path fill="white" d="M8 11v14l12-7L8 11zm14 0v6l5-3-5-3zm0 8v6l5-3-5-3z"/>
  </svg>`;
  btnMpv.addEventListener("click", openInMpv);

  // Altyazı butonu
  const btnOverlay = document.createElement("button");
  btnOverlay.id = "chevren-btn-overlay";
  btnOverlay.className = "ytp-button";
  bindTooltip(btnOverlay, "Türkçe altyazı");
  btnOverlay.innerHTML = `<svg viewBox="0 0 36 36" width="22" height="22">
    <path fill="white" d="M5 8h26v16H5V8zm3 4v2h16v-2H8zm0 4v2h10v-2H8z" opacity="0.9"/>
  </svg>`;
  btnOverlay.addEventListener("click", toggleOverlay);

  // Yeniden oluştur butonu
  const btnRegen = document.createElement("button");
  btnRegen.id = "chevren-btn-regen";
  btnRegen.className = "ytp-button";
  bindTooltip(btnRegen, "Altyazıyı yeniden oluştur");
  btnRegen.innerHTML = `<svg viewBox="0 0 36 36" width="22" height="22">
    <path fill="white" d="M18 8a10 10 0 0 0-9.95 11H5l4 4 4-4H9.1A8 8 0 1 1 18 26v2a10 10 0 0 0 0-20z"/>
  </svg>`;
  btnRegen.addEventListener("click", regenerateSubtitle);

  // Sol başa ekle: mpv → altyazı → yeniden oluştur
  const firstChild = controls.firstChild;
  controls.insertBefore(btnRegen, firstChild);
  controls.insertBefore(btnOverlay, btnRegen);
  controls.insertBefore(btnMpv, btnOverlay);
}

// ── mpv modu ─────────────────────────────────────────────────────────────────

async function openInMpv() {
  const id = getVideoId();
  if (!id) return;

  setTooltip("chevren-btn-mpv", "gönderiliyor...");

  try {
    const res = await fetch(`${SERVER}/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });
    const data = await res.json();
    setTooltip("chevren-btn-mpv", res.ok ? "mpv açıldı ✓" : `hata: ${data.message}`);
    setTimeout(() => setTooltip("chevren-btn-mpv", "mpv'de aç"), 2500);
  } catch {
    setTooltip("chevren-btn-mpv", "server'a ulaşılamadı");
    setTimeout(() => setTooltip("chevren-btn-mpv", "mpv'de aç"), 2500);
  }
}

// ── Overlay altyazı ───────────────────────────────────────────────────────────

let overlayActive = false;
let overlayEl = null;

async function toggleOverlay() {
  const id = getVideoId();
  if (!id) return;

  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
    document.getElementById("chevren-btn-overlay").style.opacity = "1";
    return;
  }

  setTooltip("chevren-btn-overlay", "kontrol ediliyor...");

  let res = await fetch(`${SERVER}/subtitle/${id}`).catch(() => null);

  if (!res || !res.ok) {
    setTooltip("chevren-btn-overlay", "altyazı üretiliyor...");
    try {
      await fetch(`${SERVER}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: window.location.href }),
      });
      res = await fetch(`${SERVER}/subtitle/${id}`).catch(() => null);
    } catch {
      setTooltip("chevren-btn-overlay", "server'a ulaşılamadı");
      setTimeout(() => setTooltip("chevren-btn-overlay", "Türkçe altyazı"), 2500);
      return;
    }
  }

  if (!res || !res.ok) {
    setTooltip("chevren-btn-overlay", "altyazı bulunamadı");
    setTimeout(() => setTooltip("chevren-btn-overlay", "Türkçe altyazı"), 2500);
    return;
  }

  const srt = await res.text();
  const cues = parseSrt(srt);
  overlayActive = true;
  setTooltip("chevren-btn-overlay", "Türkçe altyazı");
  document.getElementById("chevren-btn-overlay").style.opacity = "0.6";
  mountOverlay(cues);
}

// ── Yeniden oluştur ───────────────────────────────────────────────────────────

async function regenerateSubtitle() {
  const id = getVideoId();
  if (!id) return;

  // Aktif overlay varsa kapat
  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
  }

  setTooltip("chevren-btn-regen", "siliniyor...");

  try {
    // Cache'i sil
    await fetch(`${SERVER}/subtitle/${id}`, { method: "DELETE" }).catch(() => null);

    setTooltip("chevren-btn-regen", "üretiliyor...");

    // Yeni altyazı üret
    const res = await fetch(`${SERVER}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });

    if (res.ok) {
      setTooltip("chevren-btn-regen", "hazır ✓");
    } else {
      const data = await res.json().catch(() => ({}));
      setTooltip("chevren-btn-regen", `hata: ${data.message || res.status}`);
    }
  } catch {
    setTooltip("chevren-btn-regen", "server'a ulaşılamadı");
  }

  setTimeout(() => setTooltip("chevren-btn-regen", "Altyazıyı yeniden oluştur"), 3000);
}

// ── Overlay render ────────────────────────────────────────────────────────────

function getOverlayFontSize() {
  const video = document.querySelector("video");
  if (!video) return 16;
  const height = video.getBoundingClientRect().height;
  return Math.max(14, Math.round(height * 0.045));
}

function mountOverlay(cues) {
  const video = document.querySelector("video");
  if (!video) return;

  overlayEl = document.createElement("div");
  overlayEl.id = "chevren-overlay";
  overlayEl.style.cssText = `
    position: absolute;
    bottom: 60px;
    left: 0; right: 0;
    text-align: center;
    pointer-events: none;
    z-index: 9999;
  `;

  const text = document.createElement("span");
  text.id = "chevren-overlay-text";
  text.style.cssText = `
    background: rgba(0,0,0,0.75);
    color: #fff;
    padding: 5px 16px;
    border-radius: 4px;
    display: inline-block;
    font-size: ${getOverlayFontSize()}px;
  `;
  overlayEl.appendChild(text);

  const playerContainer = document.querySelector("#movie_player") ||
                         video.closest("ytd-player") ||
                         video.closest("[id='movie_player']");

  if (playerContainer) {
    playerContainer.style.position = "relative";
    playerContainer.appendChild(overlayEl);
  } else {
    document.body.appendChild(overlayEl);
    overlayEl.style.position = "fixed";
    overlayEl.style.bottom = "80px";
    overlayEl.style.left = "0";
    overlayEl.style.right = "0";
    overlayEl.style.zIndex = "99999";
  }

  const resizeObserver = new ResizeObserver(() => {
    text.style.fontSize = getOverlayFontSize() + "px";
  });
  resizeObserver.observe(video);

  video.addEventListener("timeupdate", () => {
    if (!overlayActive) return;
    const t = video.currentTime;
    const cue = cues.find(c => t >= c.start && t <= c.end);
    text.textContent = cue ? cue.text : "";
  });
}

// ── SRT parser ────────────────────────────────────────────────────────────────

function parseSrt(srt) {
  const blocks = srt.trim().split(/\n\n+/);
  return blocks.flatMap(block => {
    const lines = block.trim().split("\n");
    const timeLine = lines.find(l => l.includes("-->"));
    if (!timeLine) return [];
    const [startStr, endStr] = timeLine.split("-->").map(s => s.trim());
    return [{
      start: srtTimeToSeconds(startStr),
      end: srtTimeToSeconds(endStr),
      text: lines.slice(lines.indexOf(timeLine) + 1).join(" "),
    }];
  });
}

function srtTimeToSeconds(t) {
  const [h, m, s] = t.replace(",", ".").split(":");
  return parseFloat(h) * 3600 + parseFloat(m) * 60 + parseFloat(s);
}

// ── Yardımcı ─────────────────────────────────────────────────────────────────

function setTooltip(id, msg) {
  const el = document.getElementById(id);
  if (el) el.setAttribute("data-chevren-tip", msg);
}

// ── Injection — .ytp-right-controls hazır olunca inject et ───────────────────

let controlsObserver = null;

function waitForControls() {
  // Zaten inject edilmişse dur
  if (document.getElementById("chevren-btn-mpv")) return;

  // Element hazırsa hemen inject et
  if (document.querySelector(".ytp-right-controls")) {
    injectButtons();
    return;
  }

  // DOM değişikliklerini izle, .ytp-right-controls çıkınca inject et
  if (controlsObserver) controlsObserver.disconnect();
  controlsObserver = new MutationObserver(() => {
    if (document.querySelector(".ytp-right-controls")) {
      controlsObserver.disconnect();
      injectButtons();
    }
  });
  controlsObserver.observe(document.body, { childList: true, subtree: true });
}

// ── URL takibi ────────────────────────────────────────────────────────────────

let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    // Butonları temizle (yeni video)
    ["chevren-btn-mpv", "chevren-btn-overlay", "chevren-btn-regen"]
      .forEach(id => document.getElementById(id)?.remove());
    if (getVideoId()) waitForControls();
  }
}, 500);

if (getVideoId()) waitForControls();
