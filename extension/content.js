const SERVER = "http://localhost:7373";

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("v");
}

// ── Styles ───────────────────────────────────────────────────────────────────
function injectStyles() {
  if (document.getElementById("chevren-styles")) return;
  const style = document.createElement("style");
  style.id = "chevren-styles";
  style.textContent = `
    #chevren-btn-mpv {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
    }
    #chevren-strip {
      margin: 8px 0 4px;
      padding: 0 2px;
    }
    #chevren-strip-main {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px;
      padding: 7px 12px;
      cursor: pointer;
      overflow: hidden;
      position: relative;
      transition: border-color 0.2s, background 0.2s;
    }
    #chevren-strip-main:hover {
      border-color: rgba(255,255,255,0.2);
      background: rgba(255,255,255,0.08);
    }
    #chevren-badge {
      background: #c8a84b;
      color: #1a1206;
      font-size: 9px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
      flex-shrink: 0;
      font-family: sans-serif;
    }
    #chevren-status-text {
      font-size: 12px;
      color: #e0e0e0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
      font-family: sans-serif;
    }
    #chevren-sub-text {
      font-size: 11px;
      color: rgba(255,255,255,0.35);
      white-space: nowrap;
      flex-shrink: 0;
      font-family: sans-serif;
    }
    #chevren-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;
      transition: background 0.3s;
    }
    .cv-dot-idle    { background: rgba(255,255,255,0.2); }
    .cv-dot-working { background: #c8a84b; animation: cv-pulse 1.4s ease-in-out infinite; }
    .cv-dot-done    { background: #5cb85c; }
    .cv-dot-error   { background: #e05c5c; }
    #chevren-delete-btn {
      background: none;
      border: none;
      color: rgba(255,255,255,0.3);
      font-size: 15px;
      line-height: 1;
      cursor: pointer;
      padding: 0 2px;
      flex-shrink: 0;
      display: none;
      transition: color 0.2s;
      font-family: sans-serif;
    }
    #chevren-delete-btn:hover {
      color: #e05c5c;
    }

    @keyframes cv-pulse {
      0%,100% { opacity:1; transform:scale(1); }
      50%     { opacity:0.3; transform:scale(0.6); }
    }
    #chevren-progress-bar {
      position: absolute;
      bottom: 0; left: 0;
      height: 2px;
      background: #c8a84b;
      transition: width 0.5s ease;
    }
    #chevren-progress-bar.cv-indeterminate {
      width: 33% !important;
      animation: cv-slide 1.8s ease-in-out infinite;
    }
    @keyframes cv-slide {
      0%   { left: -33%; }
      100% { left: 100%; }
    }
  `;
  document.head.appendChild(style);
}

// ── Controls bar: sadece mpv butonu ─────────────────────────────────────────
function injectMpvButton() {
  if (document.getElementById("chevren-btn-mpv")) return;
  const controls = document.querySelector(".ytp-right-controls");
  if (!controls) return;
  injectStyles();
  const btn = document.createElement("button");
  btn.id = "chevren-btn-mpv";
  btn.className = "ytp-button";
  btn.title = "mpv'de aç";
  btn.innerHTML = `<svg viewBox="0 0 36 36" width="22" height="22">
    <path fill="white" d="M8 11v14l12-7L8 11zm14 0v6l5-3-5-3zm0 8v6l5-3-5-3z"/>
  </svg>`;
  btn.addEventListener("click", openInMpv);
  controls.insertBefore(btn, controls.firstChild);
}

// ── Strip ────────────────────────────────────────────────────────────────────
function injectStrip() {
  if (document.getElementById("chevren-strip")) return;
  const topRow = document.querySelector("ytd-watch-metadata #top-row");
  if (!topRow) return;
  injectStyles();
  const strip = document.createElement("div");
  strip.id = "chevren-strip";
  strip.innerHTML = `
    <div id="chevren-strip-main">
      <span id="chevren-badge">CV</span>
      <span id="chevren-status-text">Türkçe altyazı oluştur</span>
      <span id="chevren-sub-text"></span>
      <button id="chevren-delete-btn" title="Altyazıyı sil">×</button>
      <div id="chevren-dot" class="cv-dot-idle"></div>
      <div id="chevren-progress-bar" style="display:none;width:0;"></div>
    </div>
  `;
  topRow.parentNode.insertBefore(strip, topRow.nextSibling);
  document
    .getElementById("chevren-strip-main")
    .addEventListener("click", onStripClick);
  document
    .getElementById("chevren-delete-btn")
    .addEventListener("click", async (e) => {
      e.stopPropagation();
      const vid = getVideoId();
      if (!vid) return;
      await fetch(`${SERVER}/subtitle/${vid}`, { method: "DELETE" }).catch(
        () => {},
      );
      if (overlayActive) {
        overlayActive = false;
        overlayEl?.remove();
        overlayEl = null;
      }
      currentStage = "idle";
      updateStrip({ stage: "idle" });
    });
}

// ── Strip state update ───────────────────────────────────────────────────────
let currentStage = "idle";

function updateStrip(status) {
  const statusText = document.getElementById("chevren-status-text");
  const subText = document.getElementById("chevren-sub-text");
  const dot = document.getElementById("chevren-dot");
  const bar = document.getElementById("chevren-progress-bar");
  const deleteBtn = document.getElementById("chevren-delete-btn");
  if (!statusText) return;

  const stage = status.stage || "idle";
  currentStage = stage;

  dot.className = ""; // sıfırla
  bar.style.display = "none";
  bar.classList.remove("cv-indeterminate");
  statusText.style.color = "#e0e0e0";
  if (deleteBtn) deleteBtn.style.display = "none";

  const showBar = () => {
    bar.style.display = "block";
    bar.classList.add("cv-indeterminate");
  };

  switch (stage) {
    case "idle":
      statusText.textContent = "Türkçe altyazı oluştur";
      subText.textContent = "";
      dot.classList.add("cv-dot-idle");
      break;
    case "downloading":
      statusText.textContent = "Ses indiriliyor";
      subText.textContent = "yt-dlp";
      dot.classList.add("cv-dot-working");
      showBar();
      break;
    case "transcribing":
      statusText.textContent = "Transkript oluşturuluyor";
      subText.textContent = "faster-whisper";
      dot.classList.add("cv-dot-working");
      showBar();
      break;
    case "translating":
      statusText.textContent = `Çeviri yapılıyor — parça ${status.chunk ?? "…"}`;
      subText.textContent = "Gemini";
      dot.classList.add("cv-dot-working");
      showBar();
      break;
    case "ready":
      statusText.textContent = overlayActive
        ? "Altyazı gösteriliyor — kapatmak için tıkla"
        : "Altyazı hazır — göstermek için tıkla";
      statusText.style.color = "#7dcf7d";
      subText.textContent = "";
      dot.classList.add("cv-dot-done");
      if (deleteBtn) deleteBtn.style.display = "inline-flex";
      break;
    case "error":
      statusText.textContent = `Hata: ${status.message || "bilinmeyen"}`;
      statusText.style.color = "#e07070";
      subText.textContent = "tekrar dene";
      dot.classList.add("cv-dot-error");
      break;
    default:
      statusText.textContent = "Türkçe altyazı oluştur";
      subText.textContent = "";
      dot.classList.add("cv-dot-idle");
  }
}

// ── Status polling ───────────────────────────────────────────────────────────
let pollInterval = null;

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
          !overlayActive &&
          !userClosedOverlay &&
          (data.stage === "ready" ||
            (data.stage === "translating" && (data.chunk_max ?? 0) >= 1));
        if (shouldAutoOpen) {
          const srtRes = await fetch(`${SERVER}/subtitle/${vid}`).catch(
            () => null,
          );
          if (srtRes && srtRes.ok) {
            const srt = await srtRes.text();
            if (srt.trim()) {
              overlayActive = true;
              mountOverlay(parseSrt(srt));
            }
          }
        }
        // overlay açıksa SRT güncelle: chunk değişince (translating) veya ready'ye geçince
        const isReady = data.stage === "ready";
        const chunkChanged = data.stage === "translating" && (data.chunk ?? 0) !== lastOverlayChunk;
        if (overlayActive && (isReady || chunkChanged)) {
          lastOverlayChunk = data.chunk ?? 0;
          const srtRes = await fetch(`${SERVER}/subtitle/${vid}`).catch(() => null);
          if (srtRes && srtRes.ok) {
            const srt = await srtRes.text();
            if (srt.trim()) {
              overlayEl?.remove();
              overlayEl = null;
              mountOverlay(parseSrt(srt));
            }
          }
        }
        if (isReady) lastOverlayChunk = 0; // sıfırla, bir sonraki video için
        updateStrip(data);
      }
    } catch {}
  }, 1000);
}

function stopPolling() {
  clearInterval(pollInterval);
  pollInterval = null;
}
// ── Strip tıklama ────────────────────────────────────────────────────────────
async function onStripClick() {
  const vid = getVideoId();
  if (!vid) return;

  if (
    currentStage === "ready" ||
    currentStage === "translating" ||
    currentStage === "transcribing"
  ) {
    await toggleOverlay(vid);
    updateStrip({ stage: currentStage });
    return;
  }

  if (currentStage === "downloading") return; // ses inmeden SRT yok, tıklamayı yoksay

  // Başlat — optimistic UI
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

// ── mpv ──────────────────────────────────────────────────────────────────────
async function openInMpv() {
  const btn = document.getElementById("chevren-btn-mpv");
  if (btn) btn.style.opacity = "0.5";
  try {
    await fetch(`${SERVER}/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });
  } catch {}
  if (btn)
    setTimeout(() => {
      btn.style.opacity = "1";
    }, 2500);
}

// ── Overlay ──────────────────────────────────────────────────────────────────
let overlayActive = false;
let overlayEl = null;
let userClosedOverlay = false;
let lastOverlayChunk = 0;

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
  if (!res || !res.ok) return;
  const srt = await res.text();
  overlayActive = true;
  mountOverlay(parseSrt(srt));
}

function mountOverlay(cues) {
  const video = document.querySelector("video");
  if (!video) return;

  overlayEl = document.createElement("div");
  overlayEl.id = "chevren-overlay";
  overlayEl.style.cssText =
    "position:absolute;bottom:60px;left:0;right:0;text-align:center;pointer-events:none;z-index:9999;";

  const text = document.createElement("span");
  text.id = "chevren-overlay-text";
  text.style.cssText = `background:rgba(0,0,0,0.78);color:#fff;padding:5px 16px;border-radius:4px;display:inline-block;font-size:${getOverlayFontSize()}px;font-family:sans-serif;`;
  overlayEl.appendChild(text);

  const container =
    document.querySelector("#movie_player") ||
    video.closest("[id='movie_player']");
  if (container) {
    container.style.position = "relative";
    container.appendChild(overlayEl);
  } else {
    Object.assign(overlayEl.style, {
      position: "fixed",
      bottom: "80px",
      zIndex: "99999",
    });
    document.body.appendChild(overlayEl);
  }

  new ResizeObserver(() => {
    text.style.fontSize = getOverlayFontSize() + "px";
  }).observe(video);
  const updateCue = () => {
    if (!overlayActive) return;
    const t = video.currentTime;
    const cue = cues.find((c) => t >= c.start && t <= c.end);
    text.textContent = cue ? cue.text : "";
  };
  video.addEventListener("timeupdate", updateCue);
  updateCue();
}

function getOverlayFontSize() {
  const v = document.querySelector("video");
  return v
    ? Math.max(14, Math.round(v.getBoundingClientRect().height * 0.045))
    : 16;
}

// ── SRT parser ───────────────────────────────────────────────────────────────
function parseSrt(srt) {
  return srt
    .trim()
    .split(/\n\n+/)
    .flatMap((block) => {
      const lines = block.trim().split("\n");
      const timeLine = lines.find((l) => l.includes("-->"));
      if (!timeLine) return [];
      const [s, e] = timeLine.split("-->").map((x) => x.trim());
      return [
        {
          start: srtToSec(s),
          end: srtToSec(e),
          text: lines.slice(lines.indexOf(timeLine) + 1).join(" "),
        },
      ];
    });
}
function srtToSec(t) {
  const [h, m, s] = t.replace(",", ".").split(":");
  return parseFloat(h) * 3600 + parseFloat(m) * 60 + parseFloat(s);
}

// ── Injection ────────────────────────────────────────────────────────────────
let domObserver = null;

function tryInjectAll() {
  injectMpvButton();
  injectStrip();
}

function waitForElements() {
  tryInjectAll();
  if (
    document.getElementById("chevren-btn-mpv") &&
    document.getElementById("chevren-strip")
  )
    return;
  if (domObserver) domObserver.disconnect();
  domObserver = new MutationObserver(() => {
    injectMpvButton();
    injectStrip();
    if (
      document.getElementById("chevren-btn-mpv") &&
      document.getElementById("chevren-strip")
    ) {
      domObserver.disconnect();
    }
  });
  domObserver.observe(document.body, { childList: true, subtree: true });
}

// ── URL takibi ───────────────────────────────────────────────────────────────
let lastUrl = location.href;
setInterval(() => {
  if (location.href === lastUrl) return;
  lastUrl = location.href;

  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
  }
  userClosedOverlay = false;
  lastOverlayChunk = 0;
  document.getElementById("chevren-btn-mpv")?.remove();
  document.getElementById("chevren-strip")?.remove();
  currentStage = "idle";

  if (getVideoId()) {
    waitForElements();
    startPolling();
  } else {
    stopPolling();
  }
}, 500);

// ── Başlat ───────────────────────────────────────────────────────────────────
if (getVideoId()) {
  waitForElements();
  startPolling();
}
