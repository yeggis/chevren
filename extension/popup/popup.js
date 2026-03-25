const dot = document.getElementById("dot");
const text = document.getElementById("status-text");

fetch("http://localhost:7373/status")
  .then(r => r.json())
  .then(data => {
    dot.classList.add("ok");
    text.textContent = `server v${data.version} çalışıyor`;
  })
  .catch(() => {
    dot.classList.add("err");
    text.textContent = "server kapalı";
  });
