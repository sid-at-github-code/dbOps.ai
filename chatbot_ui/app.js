// Minimal chat client. Talks to POST /chat, keeps the running history in memory,
// renders assistant replies and any data tables the server returns.

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");

// Conversation history sent to the server each turn (text only).
const history = [];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addMessage(role, text) {
  const msg = el("div", `msg ${role === "user" ? "user" : "bot"}`);
  msg.appendChild(el("div", "bubble", text));
  messagesEl.appendChild(msg);
  scrollDown();
  return msg;
}

function addTable(table) {
  const msg = el("div", "msg bot table-block");

  // Toolbar: row count + export buttons
  const toolbar = el("div", "table-toolbar");
  const count = table.rows.length;
  toolbar.appendChild(
    el("span", "table-count", `${count} row${count === 1 ? "" : "s"}`)
  );
  const actions = el("div", "table-actions");
  const csvBtn = el("button", "dl-btn", "⬇ CSV");
  const xlsxBtn = el("button", "dl-btn", "⬇ Excel");
  csvBtn.addEventListener("click", () => exportCSV(table.columns, table.rows));
  xlsxBtn.addEventListener("click", () => exportExcel(table.columns, table.rows));
  actions.appendChild(csvBtn);
  actions.appendChild(xlsxBtn);
  toolbar.appendChild(actions);
  msg.appendChild(toolbar);

  const wrap = el("div", "table-wrap");
  const tbl = el("table");

  const thead = el("thead");
  const htr = el("tr");
  table.columns.forEach((c) => htr.appendChild(el("th", null, c)));
  thead.appendChild(htr);
  tbl.appendChild(thead);

  const tbody = el("tbody");
  table.rows.forEach((row) => {
    const tr = el("tr");
    table.columns.forEach((c) => {
      const val = row[c];
      if (val === null || val === undefined) {
        tr.appendChild(el("td", "td-null", "null"));
      } else {
        tr.appendChild(el("td", null, String(val)));
      }
    });
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);

  wrap.appendChild(tbl);
  msg.appendChild(wrap);
  messagesEl.appendChild(msg);
  scrollDown();
}

// ── Export helpers (CSV + Excel), mirroring the dashboard ──────────────────────

function exportFilename(ext) {
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `chatbot-results-${ts}.${ext}`;
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportCSV(columns, rows) {
  if (!rows.length) return;

  const escape = (v) => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };

  const header = columns.map(escape).join(",");
  const body = rows.map((row) => columns.map((c) => escape(row[c])).join(","));
  const csv = [header, ...body].join("\r\n");

  // Leading BOM so Excel opens UTF-8 correctly.
  triggerDownload(
    new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }),
    exportFilename("csv")
  );
}

function exportExcel(columns, rows) {
  if (!rows.length) return;
  if (typeof XLSX === "undefined") {
    addMessage("bot", "⚠️ Excel export library didn't load. CSV still works.");
    return;
  }

  const data = [
    columns,
    ...rows.map((row) =>
      columns.map((c) => {
        const v = row[c];
        return v === null || v === undefined
          ? ""
          : typeof v === "object"
          ? JSON.stringify(v)
          : v;
      })
    ),
  ];

  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Results");
  XLSX.writeFile(wb, exportFilename("xlsx"));
}

function showTyping() {
  const msg = el("div", "msg bot typing");
  const bubble = el("div", "bubble");
  bubble.appendChild(el("span"));
  bubble.appendChild(el("span"));
  bubble.appendChild(el("span"));
  msg.appendChild(bubble);
  messagesEl.appendChild(msg);
  scrollDown();
  return msg;
}

function scrollDown() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(text) {
  addMessage("user", text);
  history.push({ role: "user", content: text });

  inputEl.value = "";
  setBusy(true);
  const typing = showTyping();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    typing.remove();
    const reply = data.reply || "(no response)";
    addMessage("bot", reply);
    history.push({ role: "assistant", content: reply });

    (data.tables || []).forEach(addTable);
  } catch (err) {
    typing.remove();
    addMessage("bot", `⚠️ Something went wrong: ${err.message}`);
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

function setBusy(busy) {
  sendEl.disabled = busy;
  inputEl.disabled = busy;
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (text) sendMessage(text);
});

// Greeting
addMessage(
  "bot",
  "Hi! I'm your AdventureWorks assistant. Ask me things like " +
    "\"top 10 products by list price\" or \"how many employees are in Sales?\""
);
inputEl.focus();
