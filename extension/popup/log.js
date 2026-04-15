const STORAGE_KEY = "chevren_logs";

const logWrap = document.getElementById("log-wrap");

function renderLog(logs) {
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
