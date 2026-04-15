const SERVER = "http://localhost:7373";
const MAX_LOG = 200;
const STORAGE_KEY = "chevren_logs";

let lastStage = null;
let lastChunk = null;

function ts() {
  return new Date().toTimeString().slice(0, 8);
}

async function addLog(msg, cls = "") {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  const logs = result[STORAGE_KEY] || [];
  logs.push({ time: ts(), msg, cls });
  if (logs.length > MAX_LOG) logs.shift();
  await chrome.storage.local.set({ [STORAGE_KEY]: logs });
}

function stageInfo(data) {
  switch (data.stage) {
    case "idle":         return { text: "bekliyor", cls: "" };
    case "downloading":  return { text: "ses indiriliyor — yt-dlp", cls: "working" };
    case "transcribing": return { text: "transkript oluşturuluyor — whisper", cls: "working" };
    case "translating":  return { text: `çeviri — parça ${data.chunk ?? "?"}/${data.chunk_max ?? "?"}`, cls: "working" };
    case "ready":        return { text: "altyazı hazır ✓", cls: "done" };
    case "error":        return { text: `hata: ${data.message || "bilinmeyen"}`, cls: "err" };
    default:             return { text: data.stage, cls: "" };
  }
}

async function poll() {
  try {
    const res = await fetch(`${SERVER}/status`);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    const { text, cls } = stageInfo(data);
    if (data.stage !== lastStage) {
      await addLog(text, cls);
      lastStage = data.stage;
      lastChunk = data.chunk;
    } else if (data.stage === "translating" && data.chunk !== lastChunk) {
      await addLog(text, cls);
      lastChunk = data.chunk;
    }
  } catch {
    if (lastStage !== "__offline__") {
      await addLog("server'a ulaşılamadı", "err");
      lastStage = "__offline__";
    }
  }
}

// Service worker'da setInterval çalışmaz, alarm API kullan
chrome.alarms.create("chevren-poll", { periodInMinutes: 1 / 60 }); // ~1 saniye
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "chevren-poll") poll();
});

poll(); // ilk çağrı hemen
