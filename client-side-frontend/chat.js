// Chat client: talks to POST {API_BASE}/chat, keeps conversations in
// localStorage (the backend is stateless per-request), renders markdown
// replies + data tables.

const messagesEl = document.getElementById("messages");
const messagesInner = document.getElementById("messagesInner");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");
const conversationListEl = document.getElementById("conversationList");
const appEl = document.getElementById("app");
const heroEl = document.getElementById("hero");
const apiStatusEl = document.getElementById("apiStatus");
const apiStatusTextEl = document.getElementById("apiStatusText");

const CONV_KEY = "aw_chat_conversations";
const ACTIVE_KEY = "aw_chat_active_id";
const THEME_KEY = "aw_chat_theme";

let conversations = [];
let activeId = null;

// ── API health check (proves cross-origin CORS wiring is working) ──────────────
async function checkApiHealth() {
  try {
    const resp = await fetch(`${API_BASE}/health`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    apiStatusEl.className = "api-status online";
    apiStatusTextEl.textContent = `API online`;
  } catch (err) {
    apiStatusEl.className = "api-status offline";
    apiStatusTextEl.textContent = `API unreachable`;
  }
}
checkApiHealth();

// ── small DOM helper ────────────────────────────────────────────────────────

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

// ── markdown (lightweight, escapes HTML first) ──────────────────────────────

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function renderMarkdown(raw) {
  const codeBlocks = [];
  let text = raw.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push({ lang, code });
    return ` CODEBLOCK${codeBlocks.length - 1} `;
  });

  text = escapeHtml(text);
  text = text.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  text = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  const lines = text.split("\n");
  let html = "";
  let listType = null;
  let paraBuf = [];

  const flushPara = () => {
    if (paraBuf.length) {
      html += `<p>${paraBuf.join("<br>")}</p>`;
      paraBuf = [];
    }
  };
  const closeList = () => {
    if (listType) {
      html += `</${listType}>`;
      listType = null;
    }
  };

  for (const line of lines) {
    const codeMatch = line.match(/^ CODEBLOCK(\d+) $/);
    const ulMatch = line.match(/^\s*[-*]\s+(.*)/);
    const olMatch = line.match(/^\s*\d+\.\s+(.*)/);

    if (codeMatch) {
      closeList();
      flushPara();
      html += line;
    } else if (ulMatch) {
      flushPara();
      if (listType !== "ul") {
        closeList();
        html += "<ul>";
        listType = "ul";
      }
      html += `<li>${ulMatch[1]}</li>`;
    } else if (olMatch) {
      flushPara();
      if (listType !== "ol") {
        closeList();
        html += "<ol>";
        listType = "ol";
      }
      html += `<li>${olMatch[1]}</li>`;
    } else if (line.trim() === "") {
      closeList();
      flushPara();
    } else {
      closeList();
      paraBuf.push(line);
    }
  }
  closeList();
  flushPara();

  html = html.replace(/ CODEBLOCK(\d+) /g, (_, i) => {
    const { lang, code } = codeBlocks[+i];
    const cls = lang ? ` class="lang-${escapeHtml(lang)}"` : "";
    return `<pre class="code-block"><code${cls}>${escapeHtml(code.replace(/\n$/, ""))}</code></pre>`;
  });

  return html || "<p></p>";
}

// ── persistence ──────────────────────────────────────────────────────────────

function loadConversations() {
  try {
    const raw = localStorage.getItem(CONV_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveConversations() {
  localStorage.setItem(CONV_KEY, JSON.stringify(conversations));
  localStorage.setItem(ACTIVE_KEY, activeId);
}

function currentConv() {
  return conversations.find((c) => c.id === activeId);
}

function makeConversation() {
  return {
    id: uid(),
    title: "New chat",
    updatedAt: Date.now(),
    items: [],
    history: [],
  };
}

function initState() {
  conversations = loadConversations();
  activeId = localStorage.getItem(ACTIVE_KEY);

  if (!conversations.length) {
    const conv = makeConversation();
    conversations = [conv];
    activeId = conv.id;
    saveConversations();
  } else if (!conversations.some((c) => c.id === activeId)) {
    activeId = conversations[0].id;
  }
}

// ── sidebar ──────────────────────────────────────────────────────────────────

function renderSidebar() {
  conversationListEl.innerHTML = "";
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  sorted.forEach((conv) => {
    const item = el("div", "conversation-item" + (conv.id === activeId ? " active" : ""));
    item.appendChild(el("span", "conversation-title", conv.title));

    const del = el("button", "conversation-delete");
    del.type = "button";
    del.setAttribute("aria-label", "Delete conversation");
    del.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m2 0v14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6h12Z"/></svg>';
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(conv.id);
    });

    item.appendChild(del);
    item.addEventListener("click", () => switchConversation(conv.id));
    conversationListEl.appendChild(item);
  });
}

function switchConversation(id) {
  if (id === activeId) return;
  activeId = id;
  saveConversations();
  renderSidebar();
  renderActiveConversation();
  closeMobileSidebar();
}

function newConversation() {
  const conv = makeConversation();
  conversations.push(conv);
  activeId = conv.id;
  saveConversations();
  renderSidebar();
  renderActiveConversation();
  closeMobileSidebar();
  inputEl.focus();
}

function deleteConversation(id) {
  conversations = conversations.filter((c) => c.id !== id);
  if (id === activeId) {
    if (conversations.length) {
      activeId = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt)[0].id;
    } else {
      const conv = makeConversation();
      conversations = [conv];
      activeId = conv.id;
    }
  }
  saveConversations();
  renderSidebar();
  renderActiveConversation();
}

// ── rendering ────────────────────────────────────────────────────────────────

function createMessageNode(role, content) {
  const row = el("div", `msg-row ${role === "user" ? "user" : "bot"}`);
  const inner = el("div", "msg-inner");

  const avatar = el("div", `avatar ${role === "user" ? "user-avatar" : "bot-avatar"}`, role === "user" ? "U" : "AI");
  inner.appendChild(avatar);

  const contentWrap = el("div", "msg-content");
  const bubble = el("div", "bubble");
  bubble.innerHTML = renderMarkdown(content);
  contentWrap.appendChild(bubble);

  if (role !== "user") {
    const actions = el("div", "msg-actions");
    const copyBtn = el("button", "copy-btn");
    copyBtn.type = "button";
    copyBtn.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>Copy</span>';
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(content).then(() => {
        const label = copyBtn.querySelector("span");
        const original = label.textContent;
        label.textContent = "Copied!";
        setTimeout(() => (label.textContent = original), 1500);
      });
    });
    actions.appendChild(copyBtn);
    contentWrap.appendChild(actions);
  }

  inner.appendChild(contentWrap);
  row.appendChild(inner);
  return row;
}

function createTableNode(table) {
  const row = el("div", "msg-row bot");
  const inner = el("div", "msg-inner");
  inner.appendChild(el("div", "avatar bot-avatar", " "));
  inner.firstChild.style.visibility = "hidden";

  const contentWrap = el("div", "msg-content table-block");

  const toolbar = el("div", "table-toolbar");
  const count = table.rows.length;
  toolbar.appendChild(el("span", "table-count", `${count} row${count === 1 ? "" : "s"}`));
  const actions = el("div", "table-actions");
  const csvBtn = el("button", "dl-btn", "⬇ CSV");
  const xlsxBtn = el("button", "dl-btn", "⬇ Excel");
  csvBtn.type = "button";
  xlsxBtn.type = "button";
  csvBtn.addEventListener("click", () => exportCSV(table.columns, table.rows));
  xlsxBtn.addEventListener("click", () => exportExcel(table.columns, table.rows));
  actions.appendChild(csvBtn);
  actions.appendChild(xlsxBtn);
  toolbar.appendChild(actions);
  contentWrap.appendChild(toolbar);

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
  contentWrap.appendChild(wrap);

  inner.appendChild(contentWrap);
  row.appendChild(inner);
  return row;
}

function appendItemToDOM(item) {
  let node;
  if (item.type === "table") node = createTableNode(item.table);
  else node = createMessageNode(item.type, item.content);
  messagesInner.appendChild(node);
  return node;
}

function refreshHeroVisibility() {
  const conv = currentConv();
  messagesEl.classList.toggle("has-hero", !!conv && conv.items.length === 0);
}

function renderActiveConversation() {
  messagesInner.innerHTML = "";
  const conv = currentConv();
  if (!conv) return;
  conv.items.forEach(appendItemToDOM);
  refreshHeroVisibility();
  scrollDown();
}

function scrollDown() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ── item mutators (persist + render) ────────────────────────────────────────

function addUserMessage(text) {
  const conv = currentConv();
  conv.items.push({ type: "user", content: text });
  conv.history.push({ role: "user", content: text });
  if (conv.title === "New chat") {
    conv.title = text.length > 42 ? text.slice(0, 42) + "…" : text;
  }
  conv.updatedAt = Date.now();
  saveConversations();
  renderSidebar();
  refreshHeroVisibility();
  appendItemToDOM(conv.items[conv.items.length - 1]);
  scrollDown();
}

function addBotMessage(text) {
  const conv = currentConv();
  conv.items.push({ type: "bot", content: text });
  conv.history.push({ role: "assistant", content: text });
  conv.updatedAt = Date.now();
  saveConversations();
  appendItemToDOM(conv.items[conv.items.length - 1]);
  scrollDown();
}

function addTableItem(table) {
  const conv = currentConv();
  conv.items.push({ type: "table", table });
  conv.updatedAt = Date.now();
  saveConversations();
  appendItemToDOM(conv.items[conv.items.length - 1]);
  scrollDown();
}

// ── export helpers (CSV + Excel) ────────────────────────────────────────────

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
  triggerDownload(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }), exportFilename("csv"));
}

function exportExcel(columns, rows) {
  if (!rows.length) return;
  if (typeof XLSX === "undefined") {
    addBotMessage("⚠️ Excel export library didn't load. CSV still works.");
    return;
  }
  const data = [
    columns,
    ...rows.map((row) =>
      columns.map((c) => {
        const v = row[c];
        return v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : v;
      })
    ),
  ];
  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Results");
  XLSX.writeFile(wb, exportFilename("xlsx"));
}

// ── typing indicator (not persisted) ────────────────────────────────────────

function showTyping() {
  const row = el("div", "msg-row bot typing");
  const inner = el("div", "msg-inner");
  inner.appendChild(el("div", "avatar bot-avatar", "AI"));
  const contentWrap = el("div", "msg-content");
  const bubble = el("div", "bubble");
  bubble.appendChild(el("span"));
  bubble.appendChild(el("span"));
  bubble.appendChild(el("span"));
  contentWrap.appendChild(bubble);
  inner.appendChild(contentWrap);
  row.appendChild(inner);
  messagesInner.appendChild(row);
  scrollDown();
  return row;
}

// ── chat send flow ──────────────────────────────────────────────────────────

async function sendMessage(text) {
  addUserMessage(text);
  setBusy(true);
  const typing = showTyping();

  try {
    const conv = currentConv();
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: conv.history }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    typing.remove();
    addBotMessage(data.reply || "(no response)");
    (data.tables || []).forEach(addTableItem);
  } catch (err) {
    typing.remove();
    addBotMessage(`⚠️ Something went wrong: ${err.message}`);
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

function setBusy(busy) {
  sendEl.disabled = busy;
  inputEl.disabled = busy;
}

// ── composer: auto-growing textarea + enter-to-send ─────────────────────────

function resizeInput() {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + "px";
}

inputEl.addEventListener("input", resizeInput);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    formEl.requestSubmit();
  }
});

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  resizeInput();
  sendMessage(text);
});

// ── sidebar toggle (mobile) ──────────────────────────────────────────────────

document.getElementById("sidebarToggle").addEventListener("click", () => {
  appEl.classList.toggle("sidebar-open");
});
document.getElementById("sidebarBackdrop").addEventListener("click", closeMobileSidebar);
function closeMobileSidebar() {
  appEl.classList.remove("sidebar-open");
}

document.getElementById("newChatBtn").addEventListener("click", newConversation);

// ── hero suggestion cards ────────────────────────────────────────────────────

heroEl.querySelectorAll(".suggestion-card").forEach((card) => {
  card.addEventListener("click", () => {
    inputEl.value = card.textContent.trim();
    resizeInput();
    inputEl.focus();
  });
});

// ── theme toggle ─────────────────────────────────────────────────────────────

const themeIcon = document.getElementById("themeIcon");
const themeLabel = document.getElementById("themeLabel");

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const isDark = theme === "dark";
  themeIcon.textContent = isDark ? "☀️" : "\u{1F319}";
  themeLabel.textContent = isDark ? "Light mode" : "Dark mode";
  localStorage.setItem(THEME_KEY, theme);
}

document.getElementById("themeToggle").addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
});

// ── boot ─────────────────────────────────────────────────────────────────────

applyTheme(localStorage.getItem(THEME_KEY) || "dark");
initState();
renderSidebar();
renderActiveConversation();
inputEl.focus();
