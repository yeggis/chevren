const STORAGE_KEY = "chevren_logs";

const logWrap = document.getElementById("log-wrap");

function renderLog(logs) {
  const atBottom = logWrap.scrollHeight - logWrap.scrollTop - logWrap.clientHeight < 40;
  while (logWrap.firstChild) logWrap.removeChild(logWrap.firstChild);
  if (!logs.length) {
    const empty = document.createElement("div");
    empty.className = "log-empty";
    empty.textContent = "henüz log yok";
    logWrap.appendChild(empty);
    if (atBottom) logWrap.scrollTop = logWrap.scrollHeight;
    return;
  }
  logs.forEach(e => {
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
    logWrap.appendChild(entry);
  });
  if (atBottom) logWrap.scrollTop = logWrap.scrollHeight;
}

document.getElementById("clear-log").addEventListener("click", () => {
  chrome.storage.local.set({ [STORAGE_KEY]: [] });
  renderLog([]);
});

// Storage değişince otomatik güncelle
chrome.storage.onChanged.addListener((changes) => {
  if (changes[STORAGE_KEY]) {
    renderLog(changes[STORAGE_KEY].newValue || []);
  }
});

// İlk yükleme
chrome.storage.local.get(STORAGE_KEY, result => {
  renderLog(result[STORAGE_KEY] || []);
});
