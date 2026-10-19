"use strict";

const layout = document.getElementById("layout");
const sidebar = document.getElementById("sidebar");
const tree = document.getElementById("tree");
const newConversationButton = document.getElementById("new-conversation");
const newProjectButton = document.getElementById("new-project");
const menuButton = document.getElementById("menu-button");
const menuEl = document.getElementById("menu");
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");
const composer = document.getElementById("composer");
const statusEl = document.getElementById("status");

const GREETING = "Guten Tag, Sir. Wie kann ich helfen?";

let busy = false;
let ended = false;
let projects = [];
let active = { project_id: null, conversation_id: null };
const expanded = loadExpanded();

// ======================================================================
// Hilfen
// ======================================================================

function loadExpanded() {
  try {
    return new Set(JSON.parse(localStorage.getItem("jarvis.expanded") || "[]"));
  } catch (error) {
    return new Set();
  }
}

function saveExpanded() {
  try {
    localStorage.setItem("jarvis.expanded", JSON.stringify([...expanded]));
  } catch (error) {
    /* ohne Speicher funktioniert die Seite trotzdem */
  }
}

// Spricht mit dem Server. Wirft einen Error mit dem Text des Servers.
async function api(method, path, body) {
  const options = { method, headers: {}, cache: "no-store" };

  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error("Keine Verbindung zu J.A.R.V.I.S.");
  }

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    /* Antwort ohne JSON */
  }

  if (!response.ok) {
    throw new Error(data.error || "Fehler " + response.status);
  }

  return data;
}

function setStatus(state, text) {
  statusEl.dataset.state = state;
  statusEl.textContent = "● " + text;
}

// ======================================================================
// Chat
// ======================================================================

// Text sicher anzeigen: erst alles als Text einsetzen, dann nur **fett**
// und `code` in Elemente umwandeln. Nie innerHTML mit fremdem Text.
function renderText(target, text) {
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;

  text.split(pattern).forEach((part) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      const strong = document.createElement("strong");
      strong.textContent = part.slice(2, -2);
      target.appendChild(strong);
    } else if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      const code = document.createElement("code");
      code.textContent = part.slice(1, -1);
      target.appendChild(code);
    } else {
      target.appendChild(document.createTextNode(part));
    }
  });
}

function addMessage(kind, text, label) {
  const bubble = document.createElement("div");
  bubble.className = "message " + kind;

  if (label) {
    const labelEl = document.createElement("span");
    labelEl.className = "label";
    labelEl.textContent = label;
    bubble.appendChild(labelEl);
  }

  renderText(bubble, text);
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
}

function showHistory(messages) {
  chat.replaceChildren();

  if (messages.length === 0) {
    addMessage("jarvis", GREETING);
    return;
  }

  messages.forEach((message) => {
    addMessage(message.role === "user" ? "user" : "jarvis", message.content);
  });
}

async function sendMessage(text) {
  setBusy(true);
  setStatus("busy", "THINKING...");
  addMessage("user", text);

  try {
    const data = await api("POST", "/api/message", { message: text });
    addMessage("jarvis", data.content);

    if (data.status === "exit") {
      ended = true;
      input.disabled = true;
      setStatus("ready", "BEENDET");
      return;
    }

    setStatus("ready", "READY");
  } catch (error) {
    addMessage("error", error.message);
    setStatus("error", "OFFLINE");
  } finally {
    setBusy(false);
    if (!ended) input.focus();
    // Befehle wie "Oeffne Projekt X" aendern den Stand der Seitenleiste
    refreshTree();
  }
}

function setBusy(value) {
  busy = value;
  sendButton.disabled = value || ended;
  // Waehrend Jarvis antwortet, darf niemand die Konversation wechseln.
  sidebar.classList.toggle("locked", value);
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();

  const text = input.value.trim();
  if (!text || busy || ended) return;

  input.value = "";
  resizeInput();
  sendMessage(text);
});

// Enter sendet, Shift+Enter macht eine neue Zeile
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

function resizeInput() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}
input.addEventListener("input", resizeInput);

// ======================================================================
// Dialog (Texteingabe oder Bestaetigung)
// ======================================================================

const dialog = document.getElementById("dialog");
const dialogForm = document.getElementById("dialog-form");
const dialogTitle = document.getElementById("dialog-title");
const dialogText = document.getElementById("dialog-text");
const dialogInput = document.getElementById("dialog-input");
const dialogError = document.getElementById("dialog-error");
const dialogOk = document.getElementById("dialog-ok");
const dialogCancel = document.getElementById("dialog-cancel");

let dialogSubmit = null;

// options: title, text, value (nur bei Texteingabe), okLabel, danger,
//          onSubmit(value): async; wirft einen Error, wenn es nicht klappt.
function openDialog(options) {
  dialogTitle.textContent = options.title;
  dialogText.textContent = options.text || "";
  dialogText.hidden = !options.text;
  dialogError.hidden = true;

  const withInput = options.value !== undefined;
  dialogInput.hidden = !withInput;
  dialogInput.value = withInput ? options.value : "";

  dialogOk.textContent = options.okLabel || "OK";
  dialogOk.className = options.danger ? "danger-fill" : "";
  dialogSubmit = options.onSubmit;

  dialog.showModal();

  if (withInput) {
    dialogInput.focus();
    dialogInput.select();
  }
}

dialogForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  dialogOk.disabled = true;

  try {
    await dialogSubmit(dialogInput.hidden ? undefined : dialogInput.value.trim());
    dialog.close();
  } catch (error) {
    dialogError.textContent = error.message;
    dialogError.hidden = false;
  } finally {
    dialogOk.disabled = false;
  }
});

dialogCancel.addEventListener("click", () => dialog.close());

// ======================================================================
// Kontextmenue
// ======================================================================

function closeMenu() {
  menuEl.hidden = true;
  menuEl.replaceChildren();
}

// items: [{ label, danger, run }]
function openMenu(anchor, items, event) {
  menuEl.replaceChildren();

  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.label;
    if (item.danger) button.className = "danger";
    button.addEventListener("click", () => {
      closeMenu();
      item.run();
    });
    menuEl.appendChild(button);
  });

  menuEl.hidden = false;

  const box = anchor.getBoundingClientRect();
  const x = event && event.clientX ? event.clientX : box.right;
  const y = event && event.clientY ? event.clientY : box.bottom;

  menuEl.style.left = Math.min(x, window.innerWidth - menuEl.offsetWidth - 8) + "px";
  menuEl.style.top = Math.min(y, window.innerHeight - menuEl.offsetHeight - 8) + "px";
}

document.addEventListener("click", (event) => {
  if (!menuEl.contains(event.target)) closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});
window.addEventListener("resize", closeMenu);
sidebar.addEventListener("scroll", closeMenu);

// ======================================================================
// Seitenleiste
// ======================================================================

function applyState(state) {
  projects = state.projects;
  active = state.active;

  if (active.project_id !== null) {
    expanded.add(active.project_id);
    saveExpanded();
  }

  renderTree();
}

async function refreshTree() {
  try {
    applyState(await api("GET", "/api/projects"));
  } catch (error) {
    /* die Seitenleiste bleibt, wie sie ist */
  }
}

function makeRow(className, label) {
  const row = document.createElement("div");
  row.className = "row " + className;
  row.tabIndex = 0;
  row.setAttribute("role", "button");

  const name = document.createElement("span");
  name.className = "name";
  name.textContent = label;
  row.appendChild(name);

  return row;
}

function addMoreButton(row, items) {
  const more = document.createElement("span");
  more.className = "more";
  more.textContent = "⋯";
  more.title = "Mehr";
  more.addEventListener("click", (event) => {
    event.stopPropagation();
    openMenu(more, items, event);
  });
  row.appendChild(more);

  row.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    openMenu(row, items, event);
  });
}

function onActivate(row, handler) {
  row.addEventListener("click", handler);
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handler();
    }
  });
}

function renderTree() {
  tree.replaceChildren();

  newConversationButton.disabled = active.project_id === null;
  newConversationButton.title =
    active.project_id === null ? "Öffne zuerst eine Konversation in einem Projekt" : "";

  if (projects.length === 0) {
    const hint = document.createElement("p");
    hint.className = "empty-hint";
    hint.textContent = "Noch keine Projekte. Lege mit „New Project“ eins an.";
    tree.appendChild(hint);
    return;
  }

  projects.forEach((project) => {
    const isOpen = expanded.has(project.id);

    const row = makeRow("project-row", project.name);
    if (project.id === active.project_id) row.classList.add("active");

    const arrow = document.createElement("span");
    arrow.className = "arrow";
    arrow.textContent = isOpen ? "▾" : "▸";
    row.prepend(arrow);

    onActivate(row, () => clickProject(project));

    const add = document.createElement("span");
    add.className = "more add";
    add.textContent = "＋";
    add.title = "Neue Konversation in diesem Projekt";
    add.addEventListener("click", (event) => {
      event.stopPropagation();
      newConversation(project);
    });
    row.appendChild(add);

    addMoreButton(row, [
      { label: "Rename Project", run: () => renameProject(project) },
      { label: "Delete Project", danger: true, run: () => deleteProject(project) },
    ]);
    tree.appendChild(row);

    if (!isOpen) return;

    if (project.conversations.length === 0) {
      const create = makeRow("conversation-row create-row", "＋ Neue Konversation");
      onActivate(create, () => newConversation(project));
      tree.appendChild(create);
    }

    project.conversations.forEach((conversation) => {
      const item = makeRow("conversation-row", conversation.title);
      if (conversation.id === active.conversation_id) item.classList.add("active");

      onActivate(item, () => openConversation(project, conversation));
      addMoreButton(item, [
        { label: "Rename", run: () => renameConversation(project, conversation) },
        { label: "Reset", run: () => resetConversation(project, conversation) },
        { label: "Delete", danger: true, run: () => deleteConversation(project, conversation) },
      ]);
      tree.appendChild(item);
    });
  });
}

// ---------- Aktionen ----------

// Klick auf ein Projekt: aktiv setzen und aufklappen. Ist es schon aktiv,
// klappt der Klick es auf oder zu.
async function clickProject(project) {
  if (busy) return;

  if (active.project_id === project.id) {
    if (expanded.has(project.id)) expanded.delete(project.id);
    else expanded.add(project.id);
    saveExpanded();
    renderTree();
    return;
  }

  try {
    const before = active.conversation_id;
    const data = await api("POST", "/api/project/open", { project_id: project.id });
    // Die offene Konversation gehoert zum alten Projekt: Chat leeren
    if (before !== data.active.conversation_id) showHistory([]);
    applyState(data);
  } catch (error) {
    addMessage("error", error.message);
    refreshTree();
  }
}

async function openConversation(project, conversation) {
  if (busy) return;
  layout.classList.remove("sidebar-open");

  try {
    const data = await api("POST", "/api/conversation/open", {
      project_id: project.id,
      conversation_id: conversation.id,
    });
    showHistory(data.messages);
    applyState(data);
    input.focus();
  } catch (error) {
    addMessage("error", error.message);
    refreshTree();
  }
}

function newProject() {
  openDialog({
    title: "New Project",
    text: "Name des Projekts:",
    value: "",
    okLabel: "Erstellen",
    onSubmit: async (name) => {
      const data = await api("POST", "/api/project/new", { name });
      // Das neue Projekt ist aktiv, eine alte Konversation gehoert nicht mehr dazu
      showHistory([]);
      applyState(data);
    },
  });
}

// Ohne Angabe im aktiven Projekt, sonst im angegebenen Projekt.
function newConversation(project) {
  const projectId = project ? project.id : active.project_id;
  if (projectId === null) return;

  openDialog({
    title: "New Conversation",
    text: project ? `Titel der Konversation in „${project.name}“:` : "Titel der Konversation:",
    value: "Neue Unterhaltung",
    okLabel: "Erstellen",
    onSubmit: async (title) => {
      const data = await api("POST", "/api/conversation/new", {
        title,
        project_id: projectId,
      });
      showHistory(data.messages);
      layout.classList.remove("sidebar-open");
      applyState(data);
    },
  });
}

function renameProject(project) {
  openDialog({
    title: "Rename Project",
    text: "Neuer Name:",
    value: project.name,
    okLabel: "Umbenennen",
    onSubmit: async (name) => {
      applyState(await api("POST", "/api/project/rename", { project_id: project.id, name }));
    },
  });
}

function deleteProject(project) {
  openDialog({
    title: "Delete Project",
    text: `Projekt „${project.name}“ löschen? Alle Konversationen darin werden ebenfalls gelöscht.`,
    okLabel: "Löschen",
    danger: true,
    onSubmit: async () => {
      const wasActive = active.project_id === project.id;
      const data = await api("POST", "/api/project/delete", { project_id: project.id });
      if (wasActive) showHistory([]);
      applyState(data);
    },
  });
}

function renameConversation(project, conversation) {
  openDialog({
    title: "Rename Conversation",
    text: "Neuer Titel:",
    value: conversation.title,
    okLabel: "Umbenennen",
    onSubmit: async (title) => {
      applyState(
        await api("POST", "/api/conversation/rename", {
          project_id: project.id,
          conversation_id: conversation.id,
          title,
        })
      );
    },
  });
}

function resetConversation(project, conversation) {
  openDialog({
    title: "Reset Conversation",
    text: `Alle Nachrichten in „${conversation.title}“ löschen? Die Konversation bleibt bestehen.`,
    okLabel: "Zurücksetzen",
    danger: true,
    onSubmit: async () => {
      const wasActive = active.conversation_id === conversation.id;
      const data = await api("POST", "/api/conversation/reset", {
        project_id: project.id,
        conversation_id: conversation.id,
      });
      if (wasActive) showHistory([]);
      applyState(data);
    },
  });
}

function deleteConversation(project, conversation) {
  openDialog({
    title: "Delete Conversation",
    text: `Konversation „${conversation.title}“ löschen?`,
    okLabel: "Löschen",
    danger: true,
    onSubmit: async () => {
      const wasActive = active.conversation_id === conversation.id;
      const data = await api("POST", "/api/conversation/delete", {
        project_id: project.id,
        conversation_id: conversation.id,
      });
      if (wasActive) showHistory([]);
      applyState(data);
    },
  });
}

newProjectButton.addEventListener("click", newProject);
newConversationButton.addEventListener("click", () => newConversation());
menuButton.addEventListener("click", () => layout.classList.toggle("sidebar-open"));

// ======================================================================
// Einstellungen
// ======================================================================

const settingsDialog = document.getElementById("settings");
const settingsNav = document.getElementById("settings-nav");
const settingsTitle = document.getElementById("settings-title");
const settingsDesc = document.getElementById("settings-desc");
const settingsRows = document.getElementById("settings-rows");
const settingsError = document.getElementById("settings-error");

let settings = {};
let about = { version: "", system: "" };
let currentPage = "General";

// live: true = wirkt wirklich und ist aenderbar. Alles andere ist (wie in der
// bisherigen Oberflaeche) sichtbar, aber ausgegraut, bis es funktioniert.
const PAGES = [
  {
    key: "General", icon: "⚙", desc: "Basic application behavior and startup settings.",
    rows: [
      { label: "Language", category: "general", key: "language", type: "select", options: ["English", "Deutsch", "Svenska"] },
      { label: "Startup behavior", category: "general", key: "startup_behavior", type: "select", options: ["Normal startup"] },
      { label: "Confirmations", category: "general", key: "confirmations", type: "toggle" },
    ],
  },
  {
    key: "Appearance", icon: "🎨", desc: "Visual settings for the J.A.R.V.I.S. interface.",
    rows: [
      { label: "Theme", category: "appearance", key: "theme", type: "select", options: ["Dark", "Light", "System"], live: true },
      { label: "Accent color", category: "appearance", key: "accent_color", type: "select", options: ["J.A.R.V.I.S. Blue", "Custom"] },
      { label: "Font size", category: "appearance", key: "font_size", type: "number", min: 11, max: 20, suffix: " px", live: true },
      { label: "UI scale", category: "appearance", key: "ui_scale", type: "select", options: ["80 %", "100 %", "125 %", "150 %"] },
    ],
  },
  {
    key: "J.A.R.V.I.S.", icon: "🤖", desc: "Identity, addressing and assistant behavior.",
    rows: [
      { label: "Name", category: "jarvis", key: "name", type: "text" },
      { label: "Address", category: "jarvis", key: "address", type: "text" },
      { label: "Personality / behavior", category: "jarvis", key: "personality", type: "select", options: ["Default", "Professional", "Casual", "Technical"] },
    ],
  },
  {
    key: "Voice", icon: "🔊", desc: "Input, output and speech settings.",
    rows: [
      { label: "Input", category: "voice", key: "input_device", type: "select", options: ["Default input"] },
      { label: "Output", category: "voice", key: "output_device", type: "select", options: ["Default output"] },
      { label: "Voice", category: "voice", key: "voice", type: "select", options: ["Default voice"] },
      { label: "Speed", category: "voice", key: "speed", type: "number", min: 50, max: 200, suffix: " %" },
    ],
  },
  {
    key: "Memory", icon: "🧠", desc: "Long-term memory and stored information.",
    rows: [
      { label: "Memory enabled", category: "memory", key: "enabled", type: "toggle", live: true,
        note: "Aus: J.A.R.V.I.S. lernt nichts Neues und nutzt nichts Gespeichertes." },
      { label: "Stored information", type: "readonly", text: "Managed by the J.A.R.V.I.S. memory system" },
      { label: "Memory management", type: "readonly", text: "Clear memory" },
    ],
  },
  {
    key: "About", icon: "ℹ", desc: "Information about this J.A.R.V.I.S. build.",
    rows: [
      { label: "Version", type: "readonly", live: true, text: () => about.version },
      { label: "System information", type: "readonly", live: true, text: () => about.system },
    ],
  },
];

function applyAppearance() {
  const theme = (settings.appearance && settings.appearance.theme) || "Dark";
  const size = settings.appearance && settings.appearance.font_size;
  const light =
    theme === "Light" || (theme === "System" && matchMedia("(prefers-color-scheme: light)").matches);

  if (light) document.documentElement.dataset.theme = "light";
  else delete document.documentElement.dataset.theme;

  if (Number.isInteger(size) && size >= 11 && size <= 20) {
    document.documentElement.style.fontSize = size + "px";
  }

  try {
    localStorage.setItem("jarvis.theme", theme);
    if (Number.isInteger(size)) localStorage.setItem("jarvis.fontsize", String(size));
  } catch (error) {
    /* ohne Speicher funktioniert die Seite trotzdem */
  }
}

matchMedia("(prefers-color-scheme: light)").addEventListener("change", applyAppearance);

function applySettingsState(data) {
  settings = data.settings;
  about = data.about;
  applyAppearance();
}

async function loadSettings() {
  try {
    applySettingsState(await api("GET", "/api/settings"));
  } catch (error) {
    /* Standard-Design bleibt */
  }
}

async function saveSetting(row, value) {
  settingsError.hidden = true;

  try {
    applySettingsState(
      await api("POST", "/api/settings", { category: row.category, key: row.key, value })
    );
  } catch (error) {
    settingsError.textContent = error.message;
    settingsError.hidden = false;
  }

  renderSettings();
}

function buildControl(row) {
  const stored = row.category ? (settings[row.category] || {})[row.key] : undefined;
  let control;

  if (row.type === "select") {
    control = document.createElement("select");
    row.options.forEach((option) => {
      const el = document.createElement("option");
      el.value = el.textContent = option;
      control.appendChild(el);
    });
    control.value = stored;
    control.addEventListener("change", () => saveSetting(row, control.value));
  } else if (row.type === "number") {
    control = document.createElement("input");
    control.type = "number";
    control.min = row.min;
    control.max = row.max;
    control.value = stored;
    control.title = row.suffix ? "in" + row.suffix : "";
    control.addEventListener("change", () => saveSetting(row, parseInt(control.value, 10)));
  } else if (row.type === "toggle") {
    control = document.createElement("input");
    control.type = "checkbox";
    control.checked = Boolean(stored);
    control.addEventListener("change", () => saveSetting(row, control.checked));
  } else {
    control = document.createElement("input");
    control.type = "text";
    control.readOnly = true;
    control.value = row.type === "readonly"
      ? (typeof row.text === "function" ? row.text() : row.text)
      : (stored === undefined ? "" : stored);
  }

  control.className = "setting-control";
  control.disabled = !row.live;

  // Nur-Lese-Felder mit Inhalt (About) sollen lesbar bleiben
  if (row.type === "readonly" && row.live) {
    control.disabled = false;
  }

  return control;
}

function renderSettings() {
  settingsNav.replaceChildren();

  PAGES.forEach((page) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = page.icon + "  " + page.key;
    if (page.key === currentPage) button.className = "current";
    button.addEventListener("click", () => {
      currentPage = page.key;
      settingsError.hidden = true;
      renderSettings();
    });
    settingsNav.appendChild(button);
  });

  const page = PAGES.find((p) => p.key === currentPage);
  settingsTitle.textContent = page.key;
  settingsDesc.textContent = page.desc;
  settingsRows.replaceChildren();

  page.rows.forEach((row) => {
    const wrapper = document.createElement("div");
    wrapper.className = "setting-row" + (row.live ? "" : " unavailable");

    const text = document.createElement("div");
    const label = document.createElement("span");
    label.className = "setting-label";
    label.textContent = row.label;
    text.appendChild(label);

    if (!row.live) {
      const note = document.createElement("span");
      note.className = "setting-note";
      note.textContent = "Not available yet";
      text.appendChild(note);
    } else if (row.note) {
      const note = document.createElement("span");
      note.className = "setting-note";
      note.textContent = row.note;
      text.appendChild(note);
    }

    wrapper.appendChild(text);
    wrapper.appendChild(buildControl(row));
    settingsRows.appendChild(wrapper);
  });
}

document.getElementById("open-settings").addEventListener("click", async () => {
  layout.classList.remove("sidebar-open");
  await loadSettings();
  renderSettings();
  settingsDialog.showModal();
});
document.getElementById("settings-close").addEventListener("click", () => settingsDialog.close());

// ======================================================================
// Meldungen im Hintergrund (z.B. Timer)
// ======================================================================

// Jede Meldung hat eine Nummer. Jeder Tab merkt sich die letzte, die er kennt,
// und fragt nur nach neueren. So sehen alle offenen Tabs jede Meldung.
let lastBackgroundId = null;

async function pollBackground() {
  try {
    const query = lastBackgroundId === null ? "" : "?after=" + lastBackgroundId;
    const data = await api("GET", "/api/background" + query);
    lastBackgroundId = data.last;
    data.messages.forEach((item) => addMessage("background", item.text, "HINTERGRUND"));
    if (!busy && !ended) setStatus("ready", "READY");
  } catch (error) {
    if (!busy && !ended) setStatus("error", "OFFLINE");
  }
}

setInterval(pollBackground, 1000);

// ======================================================================
// Start
// ======================================================================

addMessage("jarvis", GREETING);
refreshTree();
loadSettings();
