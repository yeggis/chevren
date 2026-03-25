const SERVER = "http://localhost:7373";

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("v");
}

function injectButtons() {
  if (document.getElementById("chevren-btn-mpv")) return;

  const target = document.querySelector("#above-the-fold") ||
                 document.querySelector("#primary-inner") ||
                 document.querySelector("ytd-watch-flexy");
  if (!target) return;

  const container = document.createElement("div");
  container.id = "chevren-container";
  container.style.cssText = `
    display: flex;
    gap: 8px;
    margin: 8px 0;
    align-items: center;
  `;

  const btnMpv = document.createElement("button");
  btnMpv.id = "chevren-btn-mpv";
  btnMpv.textContent = "▶ mpv'de aç";
  btnMpv.style.cssText = buttonStyle("#7F77DD", "#fff");
  btnMpv.addEventListener("click", openInMpv);

  const btnOverlay = document.createElement("button");
  btnOverlay.id = "chevren-btn-overlay";
  btnOverlay.textContent = "altyazı";
  btnOverlay.style.cssText = buttonStyle("transparent", "#7F77DD", "#7F77DD");
  btnOverlay.addEventListener("click", toggleOverlay);

  const status = document.createElement("span");
  status.id = "chevren-status";
  status.style.cssText = "font-size: 12px; color: #aaa;";

  container.appendChild(btnMpv);
  container.appendChild(btnOverlay);
  container.appendChild(status);
  target.prepend(container);
}

function buttonStyle(bg, color, border) {
  return `
    background: ${bg};
    color: ${color};
    border: 1px solid ${border || bg};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  `;
}

async function openInMpv() {
  const id = getVideoId();
  if (!id) return;

  setStatus("gönderiliyor...");

  try {
    const res = await fetch(`${SERVER}/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: window.location.href }),
    });
    const data = await res.json();
    setStatus(res.ok ? "mpv açıldı" : `hata: ${data.message}`);
  } catch {
    setStatus("server'a ulaşılamadı");
  }
}

let overlayActive = false;
let overlayEl = null;

async function toggleOverlay() {
  const id = getVideoId();
  if (!id) return;

  if (overlayActive) {
    overlayActive = false;
    overlayEl?.remove();
    overlayEl = null;
    document.getElementById("chevren-btn-overlay").style.background = "transparent";
    return;
  }

  try {
    const res = await fetch(`${SERVER}/subtitle/${id}`);
    if (!res.ok) {
      setStatus("altyazı bulunamadı");
      return;
    }
    const srt = await res.text();
    const cues = parseSrt(srt);

    overlayActive = true;
    document.getElementById("chevren-btn-overlay").style.background = "#2d2b55";
    mountOverlay(cues);
  } catch {
    setStatus("server'a ulaşılamadı");
  }
}

function mountOverlay(cues) {
  const player = document.querySelector("#movie_player") ||
                 document.querySelector("video");
  if (!player) return;

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
    font-size: 16px;
    padding: 5px 16px;
    border-radius: 4px;
    display: inline-block;
  `;
  overlayEl.appendChild(text);

  const playerContainer = player.closest(".html5-video-container") || player.parentElement;
  playerContainer.style.position = "relative";
  playerContainer.appendChild(overlayEl);

  const video = document.querySelector("video");
  if (!video) return;

  video.addEventListener("timeupdate", () => {
    if (!overlayActive) return;
    const t = video.currentTime;
    const cue = cues.find(c => t >= c.start && t <= c.end);
    text.textContent = cue ? cue.text : "";
  });
}

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

function setStatus(msg) {
  const el = document.getElementById("chevren-status");
  if (el) el.textContent = msg;
}

function onUrlChange() {
  if (getVideoId()) {
    setTimeout(injectButtons, 1500);
  }
}

const observer = new MutationObserver(onUrlChange);
observer.observe(document.body, { childList: true, subtree: true });

let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    onUrlChange();
  }
}, 1000);

if (getVideoId()) {
  setTimeout(injectButtons, 1500);
}
