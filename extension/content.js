const SERVER = "http://localhost:7373";

// ── Gürültü dokusu (SVG data URI) ────────────────────────────────────────────
const CV_NOISE_BG = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.78' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")";

// ── Global durum ──────────────────────────────────────────────────────────────
let currentStage      = "idle";
let overlayActive     = false;
let overlayEl         = null;
let userClosedOverlay = false;
let lastOverlayChunk  = 0;
let pollInterval      = null;
let lastUrl           = location.href;

// Overlay kişiselleştirme (chrome.storage'dan yüklenir)
const OV = { fontSizeRatio: 0.040, fontSizeMin: 14, fontSizeMax: 28 };
let fontSizeDelta     = 0;   // scroll ile ±px
let overlayDragOffset = 0;   // sürükle ile bottom offset (yukarı = pozitif)

// Overlay bottom güncelleyici — mountOverlay içinde set edilir
let _applyOvBottom = () => {};
// Overlay cue güncelleyici — mountOverlay içinde set edilir
let _updateOverlayCues = (_cues) => {};

// Depolanan ayarları yükle
chrome.storage.local.get(["cv_drag_offset", "cv_font_delta"], (r) => {
  if (r.cv_drag_offset != null) overlayDragOffset = r.cv_drag_offset;
  if (r.cv_font_delta  != null) fontSizeDelta     = r.cv_font_delta;
});

function getVideoId() {
  return new URLSearchParams(window.location.search).get("v");
}

// ── Stiller ───────────────────────────────────────────────────────────────────
function injectStyles() {
  if (document.getElementById("chevren-styles")) return;
  const s = document.createElement("style");
  s.id = "chevren-styles";
  s.textContent = `
  /* ─ Strip ─────────────────────────────────────────────────────────────── */
  #cv-strip {
    display:flex; align-items:stretch;
    background:rgba(255,255,255,0.04);
    border:0.5px solid rgba(255,255,255,0.10);
    border-radius:8px; overflow:hidden;
    margin:8px 0 4px; position:relative;
    min-height:40px; transition:border-color 0.2s;
    font-family:Roboto,Arial,sans-serif;
  }
  #cv-strip:hover { border-color:rgba(255,255,255,0.18); }
  #cv-left {
    display:flex; align-items:center; gap:6px; padding:0 12px;
    border-right:0.5px solid rgba(255,255,255,0.07); flex-shrink:0;
  }
  #cv-dot {
    width:6px; height:6px; border-radius:50%;
    background:rgba(255,255,255,0.18); flex-shrink:0; transition:background 0.3s;
  }
  #cv-dot.done    { background:#5cb85c; }
  #cv-dot.working { background:#c8a84b; animation:cv-pulse 1.4s ease-in-out infinite; }
  #cv-dot.error   { background:#e05c5c; }
  #cv-badge-label { font-size:10px; font-weight:700; color:#c8a84b; letter-spacing:0.6px; }
  #cv-main {
    flex:1; display:flex; align-items:center;
    padding:0 12px; cursor:pointer; gap:8px;
    min-width:0; position:relative;
  }
  #cv-status {
    font-size:13px; color:#e0e0e0;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1;
  }
  #cv-status.done  { color:#7dcf7d; }
  #cv-status.idle  { color:rgba(255,255,255,0.45); }
  #cv-status.error { color:#e07070; }
  #cv-sub { font-size:11px; color:rgba(255,255,255,0.28); flex-shrink:0; white-space:nowrap; }
  #cv-tooltip {
    position:absolute; bottom:calc(100% + 7px); left:50%;
    transform:translateX(-50%);
    background:rgba(20,20,20,0.97);
    border:0.5px solid rgba(255,255,255,0.12);
    border-radius:5px; padding:5px 10px;
    font-size:11px; color:rgba(255,255,255,0.75);
    white-space:nowrap; opacity:0; transition:opacity 0.15s;
    z-index:10001; pointer-events:none;
  }
  #cv-tooltip::after {
    content:''; position:absolute; top:100%; left:50%;
    transform:translateX(-50%);
    border:5px solid transparent; border-top-color:rgba(20,20,20,0.97);
  }
  #cv-main:hover #cv-tooltip { opacity:1; }
  #cv-right {
    display:flex; align-items:stretch;
    border-left:0.5px solid rgba(255,255,255,0.07);
    flex-shrink:0; position:relative;
  }
  #cv-gear-btn {
    display:flex; align-items:center; gap:6px;
    padding:0 14px; background:none; border:none;
    color:rgba(255,255,255,0.40); font-size:12px; cursor:pointer;
    transition:color 0.15s,background 0.15s;
    font-family:inherit; border-radius:0 7px 7px 0;
  }
  #cv-gear-btn:hover { color:#f1f1f1; background:rgba(255,255,255,0.06); }
  #cv-gear-btn.open  { color:#c8a84b; }
  #cv-gear-btn svg   { width:14px; height:14px; flex-shrink:0; }
  #cv-panel {
    position:fixed; width:240px;
    background:rgba(18,18,18,0.97);
    backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
    border:0.5px solid rgba(255,255,255,0.12);
    border-radius:10px; overflow:hidden;
    z-index:99999; display:none;
    box-shadow:0 8px 32px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.05) inset;
  }
  #cv-panel.open { display:block; animation:cv-panel-in 0.15s cubic-bezier(0.22,1,0.36,1); }
  @keyframes cv-panel-in {
    from { opacity:0; transform:translateY(-6px) scale(0.97); }
    to   { opacity:1; transform:translateY(0)    scale(1); }
  }
  .cv-panel-section { padding:5px 0; border-bottom:0.5px solid rgba(255,255,255,0.07); }
  .cv-panel-section:last-child { border-bottom:none; }
  .cv-section-label {
    font-size:10px; color:rgba(255,255,255,0.28);
    padding:4px 14px 2px; letter-spacing:0.5px;
    text-transform:uppercase; font-family:Roboto,Arial,sans-serif;
  }
  .cv-panel-row {
    display:flex; align-items:center; gap:10px;
    padding:7px 14px; cursor:pointer; transition:background 0.12s;
  }
  .cv-panel-row:hover { background:rgba(255,255,255,0.06); }
  .cv-panel-row svg { width:14px; height:14px; flex-shrink:0; color:rgba(255,255,255,0.40); }
  .cv-row-label { font-size:13px; color:#e0e0e0; flex:1; font-family:Roboto,Arial,sans-serif; }
  .cv-row-value { font-size:12px; color:rgba(255,255,255,0.30); font-family:Roboto,Arial,sans-serif; }
  #cv-lang-toggle { display:flex; gap:4px; }
  .cv-lang-pill {
    padding:3px 10px; border-radius:4px; font-size:11px; font-weight:600;
    cursor:pointer; border:0.5px solid rgba(255,255,255,0.10);
    background:none; color:rgba(255,255,255,0.30);
    font-family:inherit; transition:background 0.15s,color 0.15s,border-color 0.15s;
  }
  .cv-lang-pill.active-tr { background:rgba(200,168,75,0.18); color:#c8a84b; border-color:rgba(200,168,75,0.35); }
  .cv-lang-pill.active-en { background:rgba(107,197,248,0.14); color:#6bc5f8; border-color:rgba(107,197,248,0.30); }
  .cv-panel-row.danger .cv-row-label { color:#e07070; }
  .cv-panel-row.danger svg { color:#e07070; }
  .cv-panel-row.danger:hover { background:rgba(224,80,80,0.08); }
  .cv-panel-row.disabled { opacity:0.35; pointer-events:none; }
  #cv-progress {
    position:absolute; bottom:0; left:0; height:2px;
    background:#c8a84b; border-radius:0 0 8px 8px;
    transition:width 0.5s ease; display:none;
  }
  #cv-progress.indeterminate {
    width:100% !important;
    background:linear-gradient(90deg,transparent 0%,#c8a84b 20%,#e8c86b 50%,#c8a84b 80%,transparent 100%);
    background-size:200% 100%;
    animation:cv-shimmer 1.6s ease-in-out infinite;
  }
  @keyframes cv-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  @keyframes cv-pulse   { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.65)} }

  /* ─ Overlay ────────────────────────────────────────────────────────────── */
  #chevren-overlay {
    position:absolute; left:0; right:0; bottom:0;
    text-align:center; pointer-events:none;
    z-index:9999;
    /* ytp-autohide sınıfına göre smooth geçiş */
    transition:bottom 0.30s cubic-bezier(0.32,1.1,0.55,1), opacity 0.25s ease;
    user-select:none;
  }
  /* Cam kutu */
  #chevren-overlay-wrap {
    display:inline-block; position:relative;
    max-width:84%; border-radius:7px;
    overflow:hidden;
    backdrop-filter:blur(24px) saturate(160%) brightness(1.05);
    -webkit-backdrop-filter:blur(24px) saturate(160%) brightness(1.05);
    /* İnce beyaz → saydam gradyan arka plan */
    background:linear-gradient(
      160deg,
      rgba(0,0,0,0.42) 0%,
      rgba(0,0,0,0.55) 100%
    );
    border:0.5px solid rgba(255,255,255,0.14);
    box-shadow:
      0 4px 28px rgba(0,0,0,0.45),
      0 1px 0   rgba(255,255,255,0.10) inset,
      0 -1px 0  rgba(0,0,0,0.30) inset;
    pointer-events:auto;
    cursor:grab;
    transition:background 0.2s ease, box-shadow 0.2s ease;
  }
  #chevren-overlay-wrap:hover {
    border-color:rgba(255,255,255,0.22);
  }
  #chevren-overlay-wrap.dragging {
    cursor:grabbing;
    transition:none;
    box-shadow:
      0 10px 40px rgba(0,0,0,0.35),
      0 1px 0 rgba(255,255,255,0.20) inset;
  }
  /* Gürültü katmanı */
  #chevren-overlay-noise {
    position:absolute; inset:0; z-index:1;
    opacity:0.12; mix-blend-mode:overlay;
    pointer-events:none; border-radius:inherit;
    background-repeat:repeat; background-size:180px 180px;
  }
  /* Altyazı metni */
  #chevren-overlay-text {
    position:relative; z-index:2;
    display:block;
    padding:7px 20px 8px;
    font-family:'Segoe UI',system-ui,-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;
    font-weight:400; color:#f0f0f0;
    text-shadow:
      0 1px 0   rgba(0,0,0,0.90),
      0 2px 8px rgba(0,0,0,0.70),
      0 0  12px rgba(0,0,0,0.40);
    line-height:1.5; letter-spacing:0.015em;
    transition:opacity 0.18s ease;
  }
  /* Sürükleme ipucu */
  #chevren-overlay-hint {
    position:absolute; bottom:calc(100% + 6px); left:50%;
    transform:translateX(-50%);
    background:rgba(16,16,16,0.92);
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
    border:0.5px solid rgba(255,255,255,0.12);
    border-radius:5px; padding:4px 9px;
    font-size:10px; color:rgba(255,255,255,0.55);
    white-space:nowrap; opacity:0; transition:opacity 0.2s;
    pointer-events:none; font-family:Roboto,Arial,sans-serif; z-index:99999;
  }
  #chevren-overlay-wrap:hover #chevren-overlay-hint { opacity:1; }
  `;
  document.head.appendChild(s);
}

// ── Strip inject ──────────────────────────────────────────────────────────────
function injectStrip() {
  if (document.getElementById("cv-strip")) return;
  const topRow = document.querySelector("ytd-watch-metadata #top-row");
  if (!topRow) return;
  injectStyles();
  const strip = document.createElement("div");
  strip.id = "cv-strip";
  strip.innerHTML = `
    <div id="cv-left">
      <div id="cv-dot"></div>
      <span id="cv-badge-label">CV</span>
    </div>
    <div id="cv-main">
      <span id="cv-status" class="idle">Altyazı oluştur</span>
      <span id="cv-sub"></span>
      <div id="cv-tooltip">Tıkla: altyazı oluşturmayı başlat</div>
    </div>
    <div id="cv-right">
      <button id="cv-gear-btn" aria-label="Chevren ayarları">
        <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2">
          <circle cx="7" cy="7" r="2.2"/>
          <path d="M7 1v1.5M7 11.5V13M1 7h1.5M11.5 7H13M2.6 2.6l1 1M10.4 10.4l1 1M11.4 2.6l-1 1M3.6 10.4l-1 1"/>
        </svg>
        Ayarlar
      </button>
      <div id="cv-panel">
        <div class="cv-panel-section">
          <div class="cv-section-label">Dil</div>
          <div class="cv-panel-row" id="cv-row-lang">
            <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2">
              <circle cx="7" cy="7" r="5.5"/>
              <path d="M7 1.5c-2 2-2 7 0 11M7 1.5c2 2 2 7 0 11M1.5 7h11"/>
            </svg>
            <span class="cv-row-label">Altyazı dili</span>
            <div id="cv-lang-toggle">
              <button class="cv-lang-pill" data-lang="tr">TR</button>
              <button class="cv-lang-pill" data-lang="en">EN</button>
            </div>
          </div>
        </div>
        <div class="cv-panel-section">
          <div class="cv-section-label">Oynatıcı</div>
          <div class="cv-panel-row" id="cv-row-mpv">
            <svg viewBox="0 0 14 14" fill="none">
              <path fill="currentColor" d="M2 2.5v9l7-4.5-7-4.5zm7 0v3.5l3.5-1.75L9 2.5zm0 5.5v3.5l3.5-1.75L9 8z"/>
            </svg>
            <span class="cv-row-label">mpv'de aç</span>
          </div>
        </div>
        <div class="cv-panel-section" id="cv-section-danger" style="display:none">
          <div class="cv-section-label">Tehlikeli alan</div>
          <div class="cv-panel-row danger" id="cv-row-cancel" style="display:none">
            <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2">
              <path d="M7 1a6 6 0 1 0 0 12A6 6 0 0 0 7 1zM4 7h6"/>
            </svg>
            <span class="cv-row-label">İşlemi iptal et</span>
          </div>
          <div class="cv-panel-row danger" id="cv-row-delete">
            <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2">
              <path d="M2 2l10 10M12 2L2 12"/>
            </svg>
            <span class="cv-row-label">Altyazıyı sil</span>
          </div>
        </div>
      </div>
    </div>
    <div id="cv-progress"></div>
  `;
  topRow.parentNode.insertBefore(strip, topRow.nextSibling);
  bindStripEvents();
  syncLangUI();
}

// ── Eski MPV butonu temizleme ─────────────────────────────────────────────────
function injectMpvButton() {
  document.getElementById("chevren-btn-mpv")?.remove();
}

// ── Olay bağlama ──────────────────────────────────────────────────────────────
function bindStripEvents() {
  document.getElementById("cv-main").addEventListener("click", onStripClick);

  function positionPanel() {
    const panel = document.getElementById("cv-panel");
    const gear  = document.getElementById("cv-gear-btn");
    if (!panel || !gear || !panel.classList.contains("open")) return;
    const rect = gear.getBoundingClientRect();
    panel.style.top   = (rect.bottom + 6) + "px";
    panel.style.right = (window.innerWidth - rect.right) + "px";
  }

  document.getElementById("cv-gear-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    const panel = document.getElementById("cv-panel");
    const gear  = document.getElementById("cv-gear-btn");
    const isOpen = panel.classList.contains("open");
    panel.classList.toggle("open", !isOpen);
    gear.classList.toggle("open", !isOpen);
    if (!isOpen) positionPanel();
  });

  window.addEventListener("scroll", positionPanel, { passive: true });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#cv-right")) {
      document.getElementById("cv-panel")?.classList.remove("open");
      document.getElementById("cv-gear-btn")?.classList.remove("open");
    }
  });

  document.getElementById("cv-row-mpv").addEventListener("click", () => {
    openInMpv(); closePanel();
  });

  document.getElementById("cv-row-cancel").addEventListener("click", async () => {
    closePanel();
    const vid = getVideoId();
    if (!vid) return;
    await fetch(`${SERVER}/subtitle/${vid}`, { method: "DELETE" }).catch(() => {});
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
    currentStage = "idle";
    updateStrip({ stage: "idle" });
  });

  document.getElementById("cv-row-delete").addEventListener("click", async () => {
    closePanel();
    const vid = getVideoId();
    if (!vid) return;
    await fetch(`${SERVER}/subtitle/${vid}`, { method: "DELETE" }).catch(() => {});
    if (overlayActive) {
      overlayActive = false;
      overlayEl?.remove();
      overlayEl = null;
    }
    currentStage = "idle";
    updateStrip({ stage: "idle" });
  });

  document.querySelectorAll(".cv-lang-pill").forEach((pill) => {
    pill.addEventListener("click", async (e) => {
      e.stopPropagation();
      await applyLang(pill.dataset.lang);
    });
  });
}

function closePanel() {
  document.getElementById("cv-panel")?.classList.remove("open");
  document.getElementById("cv-gear-btn")?.classList.remove("open");
}

// ── Dil toggle ────────────────────────────────────────────────────────────────
const LANG_KEY = "chevren_lang";

async function applyLang(lang) {
  try {
    await fetch(`${SERVER}/config/lang`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lang }),
    });
    chrome.storage.local.set({ [LANG_KEY]: lang });
    syncLangUI(lang);
  } catch {}
}

function syncLangUI(lang) {
  if (lang) { _applyLangUI(lang); return; }
  chrome.storage.local.get(LANG_KEY, (r) => _applyLangUI(r[LANG_KEY] || "tr"));
}

function _applyLangUI(lang) {
  document.querySelectorAll(".cv-lang-pill").forEach((p) => {
    p.classList.remove("active-tr", "active-en");
    if (p.dataset.lang === lang)
      p.classList.add(lang === "tr" ? "active-tr" : "active-en");
  });
  const sub = document.getElementById("cv-sub");
  if (sub && (currentStage === "ready" || currentStage === "translating"))
    sub.textContent = lang.toUpperCase();
}

// ── Strip durumu ──────────────────────────────────────────────────────────────
function updateStrip(status) {
  if (!document.getElementById("cv-status")) tryInjectAll();
  const statusEl  = document.getElementById("cv-status");
  const subEl     = document.getElementById("cv-sub");
  const dot       = document.getElementById("cv-dot");
  const bar       = document.getElementById("cv-progress");
  const tooltip   = document.getElementById("cv-tooltip");
  const dangerSec = document.getElementById("cv-section-danger");
  if (!statusEl) return;

  const stage = status.stage || "idle";
  currentStage = stage;
  dot.className = "";
  bar.style.display = "none";
  bar.classList.remove("indeterminate");
  statusEl.className = "";
  if (dangerSec) dangerSec.style.display = "none";
  const cancelBtn = document.getElementById("cv-row-cancel");
  const isWorking = ["downloading", "transcribing", "translating"].includes(stage);
  if (cancelBtn) cancelBtn.style.display = isWorking ? "flex" : "none";
  if (dangerSec && isWorking) dangerSec.style.display = "block";

  const showBar = () => { bar.style.display = "block"; bar.classList.add("indeterminate"); };

  switch (stage) {
    case "idle":
      statusEl.textContent = "Altyazı oluştur";
      statusEl.className = "idle"; subEl.textContent = "";
      tooltip.textContent = "Tıkla: altyazı oluşturmayı başlat";
      break;
    case "downloading":
      statusEl.textContent = "Ses indiriliyor";
      subEl.textContent = "yt-dlp"; dot.classList.add("working");
      tooltip.textContent = ""; showBar();
      break;
    case "transcribing":
      statusEl.textContent = "Transkript oluşturuluyor";
      subEl.textContent = "Whisper"; dot.classList.add("working");
      tooltip.textContent = "Tıkla: altyazıyı göster/gizle"; showBar();
      break;
    case "translating": {
      const chunk = status.chunk ?? "…", max = status.chunk_max ?? "…";
      statusEl.textContent = `Çeviri yapılıyor — ${chunk}/${max}`;
      subEl.textContent = "Gemini"; dot.classList.add("working");
      tooltip.textContent = "Tıkla: mevcut altyazıyı göster/gizle"; showBar();
      break;
    }
    case "ready":
      statusEl.textContent = overlayActive ? "Altyazı gösteriliyor" : "Altyazı hazır";
      statusEl.className = "done"; subEl.textContent = "";
      dot.classList.add("done");
      tooltip.textContent = overlayActive ? "Tıkla: altyazıyı kapat" : "Tıkla: altyazıyı göster";
      if (dangerSec) dangerSec.style.display = "block";
      syncLangUI();
      break;
    case "error":
      statusEl.textContent = `Hata: ${status.message || "bilinmeyen"}`;
      statusEl.className = "error"; subEl.textContent = "tekrar dene";
      dot.classList.add("error"); tooltip.textContent = "Tıkla: tekrar dene";
      break;
    default:
      statusEl.textContent = "Altyazı oluştur"; statusEl.className = "idle";
      subEl.textContent = ""; tooltip.textContent = "Tıkla: altyazı oluşturmayı başlat";
  }
}

// ── Polling ───────────────────────────────────────────────────────────────────
function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    try {
      const vid = getVideoId();
      if (!vid) return;
      const res = await fetch(`${SERVER}/status?v=${vid}`);
      if (!res.ok) return;
      const data = await res.json();
      if (!data.video_id || data.video_id === vid) {
        const shouldAutoOpen =
          !overlayActive && !userClosedOverlay &&
          (data.stage === "ready" ||
           (data.stage === "translating" && (data.chunk_max ?? 0) >= 1));
        if (shouldAutoOpen) {
          const srtRes = await fetch(`${SERVER}/subtitle/${vid}`).catch(() => null);
          if (srtRes?.ok) {
            const srt = await srtRes.text();
            if (srt.trim()) { overlayActive = true; mountOverlay(parseSrt(srt)); }
          }
        }
        const isReady = data.stage === "ready";
        const chunkChanged = data.stage === "translating" &&
          (data.chunk ?? 0) !== lastOverlayChunk;
        if (overlayActive && (isReady || chunkChanged)) {
          lastOverlayChunk = data.chunk ?? 0;
          const srtRes = await fetch(`${SERVER}/subtitle/${vid}`).catch(() => null);
          if (srtRes?.ok) {
            const srt = await srtRes.text();
            if (srt.trim()) { _updateOverlayCues(parseSrt(srt)); }
          }
        }
        if (isReady) lastOverlayChunk = 0;
        updateStrip(data);
      }
    } catch {}
  }, 1000);
}

function stopPolling() {
  clearInterval(pollInterval);
  pollInterval = null;
}

// ── Strip tıklaması ───────────────────────────────────────────────────────────
async function onStripClick() {
  const vid = getVideoId();
  if (!vid) return;
  if (["ready", "translating", "transcribing"].includes(currentStage)) {
    await toggleOverlay(vid);
    updateStrip({ stage: currentStage });
    return;
  }
  if (currentStage === "downloading") return;
  updateStrip({ stage: "downloading" });
  try {
    const res = await fetch(`${SERVER}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      updateStrip({ stage: "error", message: data.message || res.status });
    }
  } catch {
    updateStrip({ stage: "error", message: "server'a ulaşılamadı" });
  }
}

// ── MPV ───────────────────────────────────────────────────────────────────────
async function openInMpv() {
  try {
    await fetch(`${SERVER}/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });
  } catch {}
}

// ── Overlay aç/kapat ──────────────────────────────────────────────────────────
async function toggleOverlay(videoId) {
  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
    userClosedOverlay = true;
    return;
  }
  userClosedOverlay = false;
  const res = await fetch(`${SERVER}/subtitle/${videoId}`).catch(() => null);
  if (!res?.ok) return;
  const srt = await res.text();
  overlayActive = true;
  mountOverlay(parseSrt(srt));
}

// ── Font boyutu hesaplama ─────────────────────────────────────────────────────
function calcFontSize(video) {
  const h = video.getBoundingClientRect().height;
  const base = Math.min(OV.fontSizeMax, Math.max(OV.fontSizeMin, Math.round(h * OV.fontSizeRatio)));
  return base + fontSizeDelta;
}

// ── Overlay yerleştirme ───────────────────────────────────────────────────────
function mountOverlay(cues) {
  const video = document.querySelector("video");
  if (!video) return;

  const player = document.querySelector("#movie_player") ||
                 video.closest("[id='movie_player']");

  // Ana kapsayıcı
  overlayEl = document.createElement("div");
  overlayEl.id = "chevren-overlay";

  // Cam kutu
  const wrap = document.createElement("div");
  wrap.id = "chevren-overlay-wrap";

  // Gürültü katmanı
  const noiseEl = document.createElement("div");
  noiseEl.id = "chevren-overlay-noise";
  noiseEl.style.backgroundImage = CV_NOISE_BG;

  // Metin
  const textEl = document.createElement("span");
  textEl.id = "chevren-overlay-text";
  textEl.style.fontSize = calcFontSize(video) + "px";

  // İpucu
  const hintEl = document.createElement("div");
  hintEl.id = "chevren-overlay-hint";
  hintEl.textContent = "Sürükle: konumu ayarla  •  Çift tık: sıfırla  •  Kaydır: yazı boyutu";

  wrap.appendChild(noiseEl);
  wrap.appendChild(textEl);
  wrap.appendChild(hintEl);
  overlayEl.appendChild(wrap);

  if (player) {
    player.style.position = "relative";
    player.appendChild(overlayEl);
  } else {
    overlayEl.style.position = "fixed";
    overlayEl.style.zIndex = "99999";
    document.body.appendChild(overlayEl);
  }

  // ── Dinamik konum: ytp-autohide sınıfını izle ─────────────────────────────
  // YouTube kontrolleri görünür → ytp-autohide YOK → daha yüksek bottom
  // YouTube kontrolleri gizli  → ytp-autohide VAR → daha düşük bottom
  // Bu yaklaşım: kontrol çubuğu animasyonu sırasında sürekli ölçüm yapmak
  // yerine yalnızca sınıf değişiminde tetiklenir → sıçrama sorunu ortadan kalkar
  const CTRL_VISIBLE_H = 56; // kontroller görünürken bottom (px)
  const CTRL_HIDDEN_H  = 14; // kontroller gizliyken bottom (px)

  function computeBottom() {
    const autohide = player?.classList.contains("ytp-autohide") ?? false;
    return (autohide ? CTRL_HIDDEN_H : CTRL_VISIBLE_H) + overlayDragOffset;
  }

  function applyBottom(animate) {
    if (!overlayEl) return;
    overlayEl.style.transition = animate
      ? "bottom 0.30s cubic-bezier(0.32,1.1,0.55,1), opacity 0.25s ease"
      : "opacity 0.25s ease";
    overlayEl.style.bottom = computeBottom() + "px";
  }

  // Modül düzeyindeki güncelleyiciyi bu overlay'e bağla
  _applyOvBottom = () => applyBottom(true);
  applyBottom(false); // ilk yerleşim — animasyonsuz

  // ytp-autohide değişim gözlemcisi
  if (player) {
    const mo = new MutationObserver(() => applyBottom(true));
    mo.observe(player, { attributes: true, attributeFilter: ["class"] });
  }

  // Video boyutu değişince font güncelle (tam ekran vb.)
  const ro = new ResizeObserver(() => {
    textEl.style.fontSize = calcFontSize(video) + "px";
    applyBottom(false);
  });
  ro.observe(video);

  // ── Sürükleme ─────────────────────────────────────────────────────────────
  let dragStartY = 0, dragBase = 0, isDragging = false;

  wrap.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    isDragging = true;
    dragStartY = e.clientY;
    dragBase   = overlayDragOffset;
    wrap.classList.add("dragging");
    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup",   onDragUp);
  });

  function onDragMove(e) {
    if (!isDragging) return;
    const playerH = player ? player.getBoundingClientRect().height : 400;
    const maxUp   = Math.floor(playerH * 0.80);  // player yüksekliğinin %80'i
    const maxDown = -(CTRL_VISIBLE_H - 4);        // kontrol çubuğunun altına giremez
    overlayDragOffset = dragBase + (dragStartY - e.clientY);
    overlayDragOffset = Math.max(maxDown, Math.min(maxUp, overlayDragOffset));
    applyBottom(false);
  }

  function onDragUp() {
    if (!isDragging) return;
    isDragging = false;
    wrap.classList.remove("dragging");
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup",   onDragUp);
    // Konumu kaydet
    chrome.storage.local.set({ cv_drag_offset: overlayDragOffset });
  }

  // Çift tıkla konumu sıfırla
  wrap.addEventListener("dblclick", () => {
    overlayDragOffset = 0;
    chrome.storage.local.set({ cv_drag_offset: 0 });
    applyBottom(true);
  });

  // ── Kaydırarak yazı boyutu ────────────────────────────────────────────────
  wrap.addEventListener("wheel", (e) => {
    e.preventDefault();
    fontSizeDelta = Math.max(-6, Math.min(12, fontSizeDelta - Math.sign(e.deltaY)));
    chrome.storage.local.set({ cv_font_delta: fontSizeDelta });
    textEl.style.fontSize = calcFontSize(video) + "px";
  }, { passive: false });

  // ── Cue güncelleme ────────────────────────────────────────────────────────
  let activeCues = cues;
  let lastText = null;
  const updateCue = () => {
    if (!overlayActive) return;
    const t = video.currentTime;
    const cue = activeCues.find((c) => t >= c.start && t <= c.end);
    const newText = cue ? cue.text : "";
    if (newText === lastText) return;
    lastText = newText;
    if (newText) {
      textEl.textContent = newText;
      textEl.style.opacity = "1";
      overlayEl.style.opacity = "1";
    } else {
      overlayEl.style.opacity = "0";
    }
  };
  // Cue'ları dışarıdan güncellemek için — overlay yeniden kurulmaz
  _updateOverlayCues = (newCues) => {
    activeCues = newCues;
    lastText = null; // zorla yeniden render
  };
  video.addEventListener("timeupdate", updateCue);
  updateCue();
}

// ── SRT parser ────────────────────────────────────────────────────────────────
function parseSrt(srt) {
  return srt.trim().split(/\n\n+/).flatMap((block) => {
    const lines    = block.trim().split("\n");
    const timeLine = lines.find((l) => l.includes("-->"));
    if (!timeLine) return [];
    const [s, e] = timeLine.split("-->").map((x) => x.trim());
    return [{ start: srtToSec(s), end: srtToSec(e),
              text: lines.slice(lines.indexOf(timeLine) + 1).join(" ") }];
  });
}

function srtToSec(t) {
  const [h, m, s] = t.replace(",", ".").split(":");
  return parseFloat(h) * 3600 + parseFloat(m) * 60 + parseFloat(s);
}

// ── Klavye kısayolu: Alt+C → overlay aç/kapat ────────────────────────────────
document.addEventListener("keydown", (e) => {
  if (e.altKey && e.key === "c" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    const vid = getVideoId();
    if (!vid) return;
    if (["ready", "translating", "transcribing"].includes(currentStage)) {
      toggleOverlay(vid).then(() => updateStrip({ stage: currentStage }));
    }
  }
});

// ── Injection ─────────────────────────────────────────────────────────────────
let domObserver = null;

function tryInjectAll() {
  injectMpvButton();
  injectStrip();
}

function waitForElements() {
  tryInjectAll();
  if (document.getElementById("cv-strip")) return;
  if (domObserver) domObserver.disconnect();
  domObserver = new MutationObserver(() => {
    injectMpvButton();
    injectStrip();
    if (document.getElementById("cv-strip")) domObserver.disconnect();
  });
  domObserver.observe(document.body, { childList: true, subtree: true });
}

// ── URL takibi ────────────────────────────────────────────────────────────────
setInterval(() => {
  if (location.href === lastUrl) return;
  lastUrl = location.href;
  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
  }
  userClosedOverlay = false;
  lastOverlayChunk  = 0;
  overlayDragOffset = 0;         // URL değişince drag offset sıfırla
  _applyOvBottom       = () => {};  // eski overlay referansını temizle
  _updateOverlayCues   = (_cues) => {};  // eski cue referansını temizle
  document.getElementById("chevren-btn-mpv")?.remove();
  document.getElementById("cv-strip")?.remove();
  currentStage = "idle";
  if (getVideoId()) { waitForElements(); startPolling(); }
  else stopPolling();
}, 500);

// ── Başlat ────────────────────────────────────────────────────────────────────
async function init() {
  if (!getVideoId()) return;
  waitForElements();
  startPolling();
  // Cache'de altyazı var mı? Server'ı beklemeden kontrol et
  try {
    const vid = getVideoId();
    const res = await fetch(`${SERVER}/status?v=${vid}`);
    if (res.ok) {
      const data = await res.json();
      if (data.stage === "ready" || data.stage === "translating" || data.stage === "transcribing") {
        updateStrip(data);
        if ((data.stage === "ready" || (data.stage === "translating" && (data.chunk_max ?? 0) >= 1))
            && !userClosedOverlay) {
          const srtRes = await fetch(`${SERVER}/subtitle/${vid}`).catch(() => null);
          if (srtRes?.ok) {
            const srt = await srtRes.text();
            if (srt.trim()) { overlayActive = true; mountOverlay(parseSrt(srt)); }
          }
        }
      }
    }
  } catch {}
}

init();
