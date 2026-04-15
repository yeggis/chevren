const SERVER = "http://localhost:7373";
const STORAGE_KEY = "chevren_logs";

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
  chrome.storage.local.set({ [STORAGE_KEY]: [] });
  renderLog([]);
});

document.getElementById("open-log").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("popup/log.html") });
});

// ── Log render ────────────────────────────────────────────────────────────────
function renderLog(logs) {
  while (logList.firstChild) logList.removeChild(logList.firstChild);
  if (!logs.length) {
    const empty = document.createElement("div");
    empty.className = "log-empty";
    empty.textContent = "henüz log yok";
    logList.appendChild(empty);
    return;
  }
  logs.slice().reverse().forEach(e => {
    const entry = document.createElement("div");
    entry.className = "log-entry";
    const time = document.createElement("span");
    time.className = "log-time";
    time.textContent = e.time;
    const msg = document.createElement("span");
    msg.className = "log-msg " + e.cls;
    msg.textContent = e.msg;
    entry.appendChild(time);
    entry.appendChild(msg);
    logList.appendChild(entry);
  });
}

// ── Status render ─────────────────────────────────────────────────────────────
function stageLabel(stage) {
  const map = {
    idle: "", downloading: "working", transcribing: "working",
    translating: "working", ready: "done", error: "err"
  };
  return map[stage] || "";
}

function renderStatus(data) {
  serverDot.className = "dot ok";
  serverText.textContent = "çalışıyor";
  stVideo.textContent   = data.video_id || "—";
  stStage.textContent   = data.stage || "—";
  stStage.className     = "row-value " + stageLabel(data.stage);
  stChunk.textContent   = data.chunk != null
    ? `${data.chunk} / ${data.chunk_max ?? "?"}`
    : "—";
  stMessage.textContent = data.message || "—";
}

// ── Poll (sadece status paneli için) ─────────────────────────────────────────
async function pollStatus(videoId) {
  try {
    const url = videoId ? `${SERVER}/status?v=${videoId}` : `${SERVER}/status`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    renderStatus(data);
  } catch {
    serverDot.className = "dot err";
    serverText.textContent = "kapalı";
    stStage.textContent = "—";
    stChunk.textContent = "—";
    stMessage.textContent = "—";
  }
}

// ── Storage dinle (log güncellemeleri için) ───────────────────────────────────
chrome.storage.onChanged.addListener((changes) => {
  if (changes[STORAGE_KEY]) {
    renderLog(changes[STORAGE_KEY].newValue || []);
  }
});

// ── Başlat ────────────────────────────────────────────────────────────────────
chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
  const url = tabs[0]?.url || "";
  const match = url.match(/[?&]v=([^&]+)/);
  const videoId = match ? match[1] : null;
  stVideo.textContent = videoId || "YouTube videosu değil";

  chrome.storage.local.get(STORAGE_KEY, result => {
    renderLog(result[STORAGE_KEY] || []);
  });

  pollStatus(videoId);
  setInterval(() => pollStatus(videoId), 1000);
});
