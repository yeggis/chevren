const SERVER = "http://localhost:7373";
const MAX_LOG = 200;
const STORAGE_KEY = "chevren_logs";

let logs = [];
let lastStage = null;
let lastChunk = null;
let videoId = null;

const serverDot  = document.getElementById("server-dot");
const serverText = document.getElementById("server-text");
const stVideo    = document.getElementById("st-video");
const stStage    = document.getElementById("st-stage");
const stChunk    = document.getElementById("st-chunk");
const logWrap    = document.getElementById("log-wrap");

// ── Storage ───────────────────────────────────────────────────────────────────
function saveLogs() {
  chrome.storage.local.set({ [STORAGE_KEY]: logs });
}

function loadLogs(cb) {
  chrome.storage.local.get(STORAGE_KEY, result => {
    logs = result[STORAGE_KEY] || [];
    cb();
  });
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderLog() {
  if (!logs.length) {
    logWrap.innerHTML = '<div class="log-empty">henüz log yok</div>';
    return;
  }
  const atBottom = logWrap.scrollHeight - logWrap.scrollTop - logWrap.clientHeight < 40;
  logWrap.innerHTML = logs.map(e =>
    `<div class="log-entry">
      <span class="log-time">${e.time}</span>
      <span class="log-msg ${e.cls}">${e.msg}</span>
    </div>`
  ).join("");
  if (atBottom) logWrap.scrollTop = logWrap.scrollHeight;
}

// ── Log ───────────────────────────────────────────────────────────────────────
function ts() {
  return new Date().toTimeString().slice(0, 8);
}

function addLog(msg, cls = "") {
  logs.push({ time: ts(), msg, cls });
  if (logs.length > MAX_LOG) logs.shift();
  saveLogs();
  renderLog();
}

document.getElementById("clear-log").addEventListener("click", () => {
  logs = [];
  saveLogs();
  renderLog();
});

// ── Aşama ────────────────────────────────────────────────────────────────────
function stageInfo(data) {
  switch (data.stage) {
    case "idle":         return { text: "bekliyor",                                                    cls: "" };
    case "downloading":  return { text: "ses indiriliyor — yt-dlp",                                    cls: "working" };
    case "transcribing": return { text: "transkript oluşturuluyor — whisper",                          cls: "working" };
    case "translating":  return { text: `çeviri — parça ${data.chunk ?? "?"}/${data.chunk_max ?? "?"}`, cls: "working" };
    case "ready":        return { text: "altyazı hazır ✓",                                             cls: "done" };
    case "error":        return { text: `hata: ${data.message || "bilinmeyen"}`,                       cls: "err" };
    default:             return { text: data.stage,                                                    cls: "" };
  }
}

// ── Poll ──────────────────────────────────────────────────────────────────────
async function poll() {
  try {
    const url = videoId ? `${SERVER}/status?v=${videoId}` : `${SERVER}/status`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    serverDot.className = "dot ok";
    serverText.textContent = "çalışıyor";

    stVideo.textContent = data.video_id || videoId || "—";
    stChunk.textContent = data.chunk != null ? `${data.chunk} / ${data.chunk_max ?? "?"}` : "—";

    const { text, cls } = stageInfo(data);
    stStage.textContent  = data.stage || "—";
    stStage.className    = "st-val " + cls;

    if (data.stage !== lastStage) {
      addLog(text, cls);
      lastStage = data.stage;
      lastChunk = data.chunk;
    } else if (data.stage === "translating" && data.chunk !== lastChunk) {
      addLog(text, cls);
      lastChunk = data.chunk;
    }

  } catch {
    serverDot.className = "dot err";
    serverText.textContent = "kapalı";
    if (lastStage !== "__offline__") {
      addLog("server'a ulaşılamadı", "err");
      lastStage = "__offline__";
    }
    stStage.textContent = "—";
    stChunk.textContent = "—";
  }
}

// ── Başlat ────────────────────────────────────────────────────────────────────
chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
  const url = tabs[0]?.url || "";
  const match = url.match(/[?&]v=([^&]+)/);
  videoId = match ? match[1] : null;
  stVideo.textContent = videoId || "—";
  loadLogs(() => {
    renderLog();
    poll();
    setInterval(poll, 1000);
  });
});
