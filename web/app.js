const messages = document.getElementById("messages");
const promptInput = document.getElementById("prompt");
const sendBtn = document.getElementById("sendBtn");
const themeBtn = document.getElementById("themeBtn");

const THEME_KEY = "smsrag_theme";

function setTheme(theme) {
  document.body.setAttribute("data-theme", theme);
  const isDark = theme === "dark";
  themeBtn.textContent = isDark ? "☀️ Light mode" : "🌙 Dark mode";
  localStorage.setItem(THEME_KEY, theme);
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") {
    setTheme(saved);
    return;
  }
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(prefersDark ? "dark" : "light");
}

function appendMessage(text, cls, sources = [], mode = "") {
  const el = document.createElement("div");
  el.className = `msg ${cls}`;
  el.textContent = text;
  messages.appendChild(el);

  const lines = [];
  if (mode) lines.push(`rejim: ${mode}`);
  if (sources.length) {
    for (const s of sources.slice(0, 3)) {
      lines.push(
        `#${s.rank} | ${s.date || "-"} | user:${s.user_id || "-"} | məsafə:${Number(s.distance).toFixed(4)}`
      );
    }
  }
  if (lines.length) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = lines.join(" • ");
    messages.appendChild(meta);
  }
  messages.scrollTop = messages.scrollHeight;
}

async function send() {
  const message = promptInput.value.trim();
  if (!message) return;
  appendMessage(message, "user");
  promptInput.value = "";
  sendBtn.disabled = true;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    appendMessage(data.answer || "Cavab alınmadı.", "bot", data.sources || [], data.mode || "");
  } catch (err) {
    appendMessage(`Xəta: ${err.message}`, "bot");
  } finally {
    sendBtn.disabled = false;
    promptInput.focus();
  }
}

themeBtn.addEventListener("click", () => {
  const current = document.body.getAttribute("data-theme");
  setTheme(current === "dark" ? "light" : "dark");
});
sendBtn.addEventListener("click", send);
promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

initTheme();
