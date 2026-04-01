const SERVER = "http://localhost:7373";
const MAX_LOG = 200;
const STORAGE_KEY = "chevren_logs";

let logs = [];
let lastStage = null;
let lastChunk = null;
let videoId = null;

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

// DOM
const serverDot  = document.getElementById("server-dot");
const serverText = document.getElementById("server-text");
const stVideo    = document.getElementById("st-video");
const stStage    = document.getElementById("st-stage");
const stChunk    = document.getElementById("st-chunk");
const stMessage  = document.getElementById("st-message");
const logList    = document.getElementById("log-list");

// ── Sekmeler ─────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
  });
});

document.getElementById("clear-log").addEventListener("click", () => {
  logs = [];
  saveLogs();
  renderLog();
});

document.getElementById("open-log").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("popup/log.html") });
});

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

function renderLog() {
  if (!logs.length) {
    logList.innerHTML = '<div class="log-empty">henüz log yok</div>';
    return;
  }
  logList.innerHTML = logs.slice().reverse().map(e =>
    `<div class="log-entry">
      <span class="log-time">${e.time}</span>
      <span class="log-msg ${e.cls}">${e.msg}</span>
    </div>`
  ).join("");
}

// ── Aşama etiketi ─────────────────────────────────────────────────────────────
function stageInfo(data) {
  switch (data.stage) {
    case "idle":         return { text: "bekliyor",                                    cls: "" };
    case "downloading":  return { text: "ses indiriliyor — yt-dlp",                    cls: "working" };
    case "transcribing": return { text: "transkript oluşturuluyor — whisper",           cls: "working" };
    case "translating":  return { text: `çeviri — parça ${data.chunk ?? "?"}/${data.chunk_max ?? "?"}`, cls: "working" };
    case "ready":        return { text: "altyazı hazır ✓",                             cls: "done" };
    case "error":        return { text: `hata: ${data.message || "bilinmeyen"}`,       cls: "err" };
    default:             return { text: data.stage,                                    cls: "" };
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

    // Durum paneli
    stVideo.textContent   = data.video_id || videoId || "—";
    stStage.textContent   = data.stage || "—";
    stChunk.textContent   = data.chunk != null
      ? `${data.chunk} / ${data.chunk_max ?? "?"}`
      : "—";
    stMessage.textContent = data.message || "—";

    // Aşama rengini güncelle
    const { cls } = stageInfo(data);
    stStage.className = "row-value " + cls;

    // Log — aşama değişince veya chunk ilerleyince
    const { text } = stageInfo(data);
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
    stMessage.textContent = "—";
  }
}

// ── Başlat ────────────────────────────────────────────────────────────────────
chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
  const url = tabs[0]?.url || "";
  const match = url.match(/[?&]v=([^&]+)/);
  videoId = match ? match[1] : null;
  stVideo.textContent = videoId || "YouTube videosu değil";
  loadLogs(() => {
    renderLog();
    poll();
    setInterval(poll, 1000);
  });
});
