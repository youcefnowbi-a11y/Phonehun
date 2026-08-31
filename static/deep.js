/* ============================================================
   DroidCommand — Deep Access view logic
   Loaded after app.js; uses its global helpers ($, esc, API,
   guard, toast). Panels are built on first open of the tab.
   ============================================================ */
"use strict";

function initDeep() {
  const root = $("#deepRoot");
  if (!root || root.dataset.ready) return;
  root.dataset.ready = "1";

  root.innerHTML = `
  <div class="panel tool-card span2">
    <div class="panel-title">ui inspector
      <span class="right"><button class="mini-btn" id="uiDumpBtn">dump foreground ui</button></span>
    </div>
    <div class="dim small mono" id="uiFocusLine">foreground: —</div>
    <div class="scroll-list tall" id="uiTree"><div class="dim small">no dump yet</div></div>
  </div>

  <div class="panel tool-card">
    <div class="panel-title">settings console</div>
    <div class="row2">
      <select class="field" id="setNs">
        <option value="global">global</option>
        <option value="secure">secure</option>
        <option value="system">system</option>
      </select>
      <button class="mini-btn" id="setListBtn">list</button>
    </div>
    <input type="text" class="field mono" id="setSearch" placeholder="filter keys…">
    <div class="scroll-list tall" id="setList"><div class="dim small">no table loaded</div></div>
    <div class="row2" style="margin-top:10px">
      <input type="text" class="field mono" id="setKey" placeholder="key">
      <button class="ghost-btn" id="setGet">get</button>
    </div>
    <div class="row2">
      <input type="text" class="field mono" id="setValue" placeholder="value to write">
      <button class="ghost-btn" id="setPut">put</button>
    </div>
    <button class="danger-btn block" id="setDel">delete key</button>
  </div>

  <div class="panel tool-card">
    <div class="panel-title">permissions &amp; appops</div>
    <input type="text" class="field mono" id="pkgIn" placeholder="com.example.package">
    <div class="row2">
      <button class="acc-btn" id="permShowBtn">permissions</button>
      <button class="acc-btn" id="opsShowBtn">appops</button>
    </div>
    <div class="scroll-list tall" id="permOpsOut"><div class="dim small">pick a package above</div></div>
    <div class="row2" style="margin-top:10px">
      <input type="text" class="field mono" id="permIn" placeholder="CAMERA">
      <button class="ghost-btn" id="permGrantBtn">grant</button>
    </div>
    <div class="row2">
      <button class="ghost-btn block" id="permRevokeBtn">revoke permission</button>
    </div>
    <div class="row2">
      <input type="text" class="field mono" id="opIn" placeholder="OP_CAMERA">
      <select class="field" id="opMode">
        <option>allow</option><option>ignore</option><option>deny</option><option>default</option>
      </select>
    </div>
    <button class="acc-btn block" id="opApplyBtn">apply appop</button>
  </div>

  <div class="panel tool-card">
    <div class="panel-title">display overrides</div>
    <div class="kv-grid" id="dispInfo"><div class="dim small">not loaded</div></div>
    <div class="row2">
      <input type="text" class="field mono" id="dispSizeIn" placeholder="720x1600">
      <button class="ghost-btn" id="dispSizeBtn">set size</button>
    </div>
    <div class="row2">
      <input type="text" class="field mono" id="dispDpiIn" placeholder="320">
      <button class="ghost-btn" id="dispDpiBtn">set density</button>
    </div>
    <button class="danger-btn block" id="dispResetBtn">reset size + density</button>
  </div>

  <div class="panel tool-card span2">
    <div class="panel-title">usage timeline &amp; service explorer</div>
    <div class="row2">
      <button class="acc-btn" id="usageBtn">usage timeline</button>
      <button class="mini-btn" id="svcLoadBtn">list services</button>
    </div>
    <datalist id="svcDatalist"></datalist>
    <div class="row3">
      <input type="text" class="field mono" id="svcIn" list="svcDatalist" placeholder="dumpsys service…">
      <select class="field" id="svcLines">
        <option value="100">100 lines</option>
        <option value="200" selected>200 lines</option>
        <option value="400">400 lines</option>
      </select>
      <button class="ghost-btn" id="svcRun">run</button>
    </div>
    <pre class="log-box" id="dumpOut" style="max-height:340px">output appears here</pre>
  </div>`;

  /* ---------------- ui inspector ---------------- */

  $("#uiDumpBtn").addEventListener("click", guard($("#uiDumpBtn"), async () => {
    $("#uiTree").innerHTML = `<div class="dim small">capturing hierarchy…</div>`;
    const r = await API.get("/api/deep/ui-tree");
    if (!r.success) {
      $("#uiFocusLine").textContent = `foreground: ${r.focus || "unknown"}`;
      $("#uiTree").innerHTML = `<div class="dim small">${esc(r.error || "dump failed")}</div>`;
      return;
    }
    $("#uiFocusLine").textContent = `foreground: ${r.focus || "unknown"} · ${r.count} nodes`;
    $("#uiTree").innerHTML = r.nodes.map((n, i) => {
      const label = n.text || n.desc || n.id || "(unlabelled)";
      const meta = [n.class, n.id ? "#" + n.id : ""].filter(Boolean).join(" ");
      const flags = [
        n.clickable ? `<span class="badge ok">tap</span>` : "",
        n.editable ? `<span class="badge amber">edit</span>` : ""
      ].join(" ");
      const cx = n.bounds ? n.bounds.cx : null;
      const cy = n.bounds ? n.bounds.cy : null;
      const act = cx != null
        ? `<button class="mini-btn" data-tapx="${cx}" data-tapy="${cy}">tap</button>` : "";
      return `<div class="ui-node-row">
        <div class="uinode-main"><b>${esc(label)}</b> <span class="dim">${esc(meta)}</span> ${flags}</div>
        ${act}
      </div>`;
    }).join("");
    $$("#uiTree [data-tapx]").forEach(b =>
      b.addEventListener("click", guard(b, async () => {
        await API.post("/api/system/tap",
          { x: +b.dataset.tapx, y: +b.dataset.tapy });
        toast(`tapped ${b.dataset.tapx},${b.dataset.tapy}`, "ok", 1800);
      })));
    toast(`${r.count} nodes captured`, "ok");
  }));

  /* ---------------- settings console ---------------- */

  async function loadSettings() {
    const ns = $("#setNs").value;
    const q = encodeURIComponent($("#setSearch").value.trim());
    const r = await API.get(`/api/deep/settings/list?ns=${ns}&q=${q}`);
    if (!r.success) throw new Error(r.error || "list failed");
    $("#setList").innerHTML = r.settings.length ? r.settings.map(s => `
      <div class="set-row" data-k="${esc(s.key)}" data-v="${esc(s.value)}">
        <div class="setk mono">${esc(s.key)}</div>
        <div class="setv mono dim">${esc(String(s.value).slice(0, 60))}</div>
      </div>`).join("")
      : `<div class="dim small">no matching keys</div>`;
    $$("#setList .set-row").forEach(row =>
      row.addEventListener("click", () => {
        $("#setKey").value = row.dataset.k;
        $("#setValue").value = row.dataset.v;
      }));
    toast(`${r.count} keys (${ns})`, "ok", 2200);
  }

  $("#setListBtn").addEventListener("click", guard($("#setListBtn"), loadSettings));

  $("#setGet").addEventListener("click", guard($("#setGet"), async () => {
    const k = encodeURIComponent($("#setKey").value.trim());
    if (!k) throw new Error("type a key first");
    const r = await API.get(`/api/deep/settings/get?ns=${$("#setNs").value}&key=${k}`);
    $("#setValue").value = r.value != null ? String(r.value) : "";
    toast(r.value == null ? "key unset (null)" : `= ${r.value}`, "ok", 2600);
  }));

  $("#setPut").addEventListener("click", guard($("#setPut"), async () => {
    const r = await API.post("/api/deep/settings/put", {
      ns: $("#setNs").value,
      key: $("#setKey").value.trim(),
      value: $("#setValue").value
    });
    if (!r.success) throw new Error(r.error || "write rejected");
    toast(r.verified ? `written + verified: ${r.key}` : "written (verify failed)", r.verified ? "ok" : "warn");
  }));

  $("#setDel").addEventListener("click", guard($("#setDel"), async () => {
    const r = await API.post("/api/deep/settings/delete", {
      ns: $("#setNs").value, key: $("#setKey").value.trim()
    });
    toast(r.success ? `${r.key} deleted` : (r.error || "delete failed"), r.success ? "ok" : "err");
  }));

  /* ---------------- permissions & appops ---------------- */

  function renderPermRows(perms) {
    return perms.map(p => `
      <div class="perm-row">
        <div class="perm-main mono">${esc(p.permission.replace("android.permission.", ""))}
          <span class="badge ${p.granted ? "ok" : "dim"}">${p.granted ? "granted" : "revoked"}</span>
        </div>
      </div>`).join("");
  }

  $("#permShowBtn").addEventListener("click", guard($("#permShowBtn"), async () => {
    const pkg = encodeURIComponent($("#pkgIn").value.trim());
    if (!pkg) throw new Error("package required");
    const r = await API.get(`/api/deep/perms/show?package=${pkg}`);
    if (!r.success && !r.permissions?.length) throw new Error(r.error || "no data");
    $("#permOpsOut").innerHTML = renderPermRows(r.permissions);
    toast(`${r.count} runtime permissions`, "ok", 2200);
  }));

  $("#opsShowBtn").addEventListener("click", guard($("#opsShowBtn"), async () => {
    const pkg = encodeURIComponent($("#pkgIn").value.trim());
    if (!pkg) throw new Error("package required");
    const r = await API.get(`/api/deep/appops/get?package=${pkg}`);
    if (!r.success && !r.ops?.length) throw new Error(r.error || "no data");
    $("#permOpsOut").innerHTML = r.ops.map(o => `
      <div class="perm-row">
        <div class="perm-main mono">${esc(o.op)}
          <span class="badge ${o.mode === "allow" ? "ok" : o.mode === "deny" ? "err" : "dim"}">${esc(o.mode)}</span>
        </div>
      </div>`).join("");
    toast(`${r.count} appops`, "ok", 2200);
  }));

  $("#permGrantBtn").addEventListener("click", guard($("#permGrantBtn"), async () => {
    const r = await API.post("/api/deep/perms/set", {
      package: $("#pkgIn").value.trim(),
      permission: $("#permIn").value.trim(),
      grant: true
    });
    if (!r.success) throw new Error(r.error || "grant failed");
    $("#permOpsOut").insertAdjacentHTML("afterbegin",
      renderPermRows([{ permission: r.permission, granted: true }]));
    toast(`${r.permission} granted`, "ok");
  }));

  $("#permRevokeBtn").addEventListener("click", guard($("#permRevokeBtn"), async () => {
    const r = await API.post("/api/deep/perms/set", {
      package: $("#pkgIn").value.trim(),
      permission: $("#permIn").value.trim(),
      grant: false
    });
    if (!r.success) throw new Error(r.error || "revoke failed");
    toast(`${r.permission} revoked`, "ok");
  }));

  $("#opApplyBtn").addEventListener("click", guard($("#opApplyBtn"), async () => {
    const r = await API.post("/api/deep/appops/set", {
      package: $("#pkgIn").value.trim(),
      op: $("#opIn").value.trim().toUpperCase(),
      mode: $("#opMode").value
    });
    if (!r.success) throw new Error(r.error || "appop failed");
    toast(`appop ${r.op} → ${r.now ?? r.mode}`, "ok");
  }));

  /* ---------------- display overrides ---------------- */

  function showDisplay(info) {
    $("#dispInfo").innerHTML = ["size", "density", "overscan"].map(k => `
      <div class="kv-item"><div class="kv-key">${k}</div>
      <div class="kv-val mono">${esc((info[k] || "").replace(/^.*?:\s*/, ""))}</div></div>`).join("");
  }

  async function refreshDisplay() {
    const r = await API.get("/api/deep/display");
    if (r.success) { showDisplay(r); return r; }
    throw new Error("wm query failed");
  }

  $("#dispSizeBtn").addEventListener("click", guard($("#dispSizeBtn"), async () => {
    const r = await API.post("/api/deep/display/set",
      { kind: "size", value: $("#dispSizeIn").value.trim() });
    showDisplay(r.info);
    toast(r.success ? `size → ${$("#dispSizeIn").value}` : (r.error || "rejected"),
      r.success ? "ok" : "err");
  }));

  $("#dispDpiBtn").addEventListener("click", guard($("#dispDpiBtn"), async () => {
    const r = await API.post("/api/deep/display/set",
      { kind: "density", value: $("#dispDpiIn").value.trim() });
    showDisplay(r.info);
    toast(r.success ? `density → ${$("#dispDpiIn").value}` : (r.error || "rejected"),
      r.success ? "ok" : "err");
  }));

  $("#dispResetBtn").addEventListener("click", guard($("#dispResetBtn"), async () => {
    const r = await API.post("/api/deep/display/reset");
    showDisplay(r.info);
    toast("size + density reset", "ok");
  }));

  refreshDisplay().catch(() => {});

  /* ---------------- usage timeline & dumpsys ---------------- */

  $("#usageBtn").addEventListener("click", guard($("#usageBtn"), async () => {
    $("#dumpOut").textContent = "collecting usagestats…";
    const r = await API.get("/api/deep/usage?lines=300");
    if (!r.success) throw new Error(r.error || "usagestats failed");
    $("#dumpOut").textContent = r.text;
    toast("timeline ready", "ok", 1800);
  }));

  $("#svcLoadBtn").addEventListener("click", guard($("#svcLoadBtn"), async () => {
    const r = await API.get("/api/deep/services");
    if (!r.success) throw new Error("service list failed");
    $("#svcDatalist").innerHTML = r.services.map(s => `<option value="${esc(s)}">`).join("");
    toast(`${r.count} services listed`, "ok", 2200);
  }));

  $("#svcRun").addEventListener("click", guard(null, async () => {
    const svc = encodeURIComponent($("#svcIn").value.trim());
    if (!svc) throw new Error("pick or type a service name");
    $("#dumpOut").textContent = `dumpsys ${svc} …`;
    const r = await API.get(`/api/deep/dumpsys?service=${svc}&lines=${$("#svcLines").value}`);
    if (!r.success) throw new Error(r.error || "dumpsys failed");
    $("#dumpOut").textContent = r.text;
  }));
}
