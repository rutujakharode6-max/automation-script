/* ─────────────────────────────────────────────
   DuplicateFinder — app.js
   Handles all UI logic, API calls, rendering
   ───────────────────────────────────────────── */

// Use the current origin for API calls so it works regardless of the port
const API = window.location.origin;

// ══════════════════════ State ══════════════════════
let allGroups    = [];   // full results from API
let filteredGrps = [];   // after search/sort
let selectedFiles = new Set(); // paths selected for deletion
let progressInterval = null;

// ══════════════════════ Directory Rows ══════════════════════
let dirCount = 1;

function addDirRow() {
  const group = document.getElementById("dirInputGroup");
  const row   = document.createElement("div");
  row.className = "dir-row";
  row.dataset.index = dirCount;
  row.innerHTML = `
    <input type="text" class="input dir-input" placeholder="C:\\Users\\YourName\\Downloads" id="dirInput${dirCount}" />
    <button class="btn-icon btn-remove-dir" onclick="removeDirRow(this)" title="Remove">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>`;
  group.appendChild(row);
  dirCount++;
  document.getElementById(`dirInput${dirCount - 1}`).focus();
}

function removeDirRow(btn) {
  const rows = document.querySelectorAll(".dir-row");
  if (rows.length <= 1) return; // keep at least one
  btn.closest(".dir-row").remove();
}

function getDirectories() {
  return [...document.querySelectorAll(".dir-input")]
    .map(i => i.value.trim())
    .filter(v => v.length > 0);
}

// ══════════════════════ Scan ══════════════════════
async function startScan() {
  const dirs = getDirectories();
  if (!dirs.length) {
    alert("Please enter at least one directory to scan.");
    return;
  }

  const algorithm  = document.getElementById("selectAlgo").value;
  const minSize    = parseInt(document.getElementById("inputMinSize").value) || 1;
  const extRaw     = document.getElementById("inputExtensions").value.trim();
  const extensions = extRaw
    ? extRaw.split(",").map(e => e.trim()).filter(e => e)
    : null;

  // UI state: scanning
  setSection("scanning");
  selectedFiles.clear();
  allGroups = [];
  filteredGrps = [];

  try {
    await apiFetch("/api/scan", "POST", { directories: dirs, algorithm, min_size: minSize, extensions });
    pollProgress();
  } catch (e) {
    alert("Could not start scan. Is the Python server running?\n\n" + e.message);
    setSection("idle");
  }
}

function pollProgress() {
  clearInterval(progressInterval);
  progressInterval = setInterval(async () => {
    try {
      const prog = await apiFetch("/api/progress");
      updateProgressBar(prog);

      if (prog.status === "done") {
        clearInterval(progressInterval);
        await loadResults();
      }
    } catch (_) { /* server might be starting */ }
  }, 400);
}

function updateProgressBar(prog) {
  const { scanned, total, current } = prog;
  const pct = total > 0 ? Math.round((scanned / total) * 100) : 0;
  document.getElementById("progressFill").style.width  = pct + "%";
  document.getElementById("progressCount").textContent = `${scanned.toLocaleString()} / ${total.toLocaleString()}`;
  document.getElementById("progressLabel").textContent = `Scanning files… ${pct}%`;
  if (current) document.getElementById("progressCurrent").textContent = current;
}

async function loadResults() {
  try {
    const data = await apiFetch("/api/results");
    allGroups    = data.groups || [];
    filteredGrps = [...allGroups];

    renderSummary(data.summary);
    renderGroups();

    if (allGroups.length > 0) {
      setSection("results");
    } else {
      setSection("empty");
    }
  } catch (e) {
    alert("Error loading results: " + e.message);
    setSection("idle");
  }
}

// ══════════════════════ Summary ══════════════════════
function renderSummary(summary) {
  document.getElementById("cardTotalScanned").textContent = summary.total_files_scanned.toLocaleString();
  document.getElementById("cardDupGroups").textContent    = summary.duplicate_groups.toLocaleString();
  document.getElementById("cardTotalDups").textContent    = summary.total_duplicates.toLocaleString();
  document.getElementById("cardWasted").textContent       = summary.total_wasted_human;

  // Header pills
  document.getElementById("hdrDuplicates").textContent = summary.total_duplicates.toLocaleString();
  document.getElementById("hdrWasted").textContent     = summary.total_wasted_human;
  document.getElementById("headerStats").style.display = "flex";
}

// ══════════════════════ Groups Rendering ══════════════════════
function renderGroups() {
  const container = document.getElementById("groupsContainer");
  container.innerHTML = "";

  if (filteredGrps.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:40px 0;">No groups match your search.</p>`;
    return;
  }

  filteredGrps.forEach((group, gi) => {
    const card = document.createElement("div");
    card.className = "group-card";
    card.dataset.hash = group.hash;
    card.style.animationDelay = (gi * 30) + "ms";

    card.innerHTML = `
      <div class="group-card-header">
        <span class="group-badge">${group.count} copies · ${group.algorithm.toUpperCase()}</span>
        <span class="group-hash">${group.hash}</span>
        <span class="group-wasted">
          ${group.wasted_space_human}
          <span class="group-wasted-label"> wasted</span>
        </span>
      </div>
      <div class="group-files" id="files_${gi}">
        ${group.files.map((f, fi) => buildFileRow(f, fi, gi, group.hash)).join("")}
      </div>`;

    container.appendChild(card);
  });
}

function buildFileRow(f, fi, gi, hash) {
  const ext     = (f.name.includes(".") ? f.name.split(".").pop().toLowerCase() : "?");
  const extCls  = `ext-${ext}`;
  const isFirst = fi === 0;  // first file = suggested "keep"
  const checkId = `chk_${gi}_${fi}`;

  return `
    <div class="file-row ${isFirst ? "selected" : ""}" id="row_${gi}_${fi}" data-path="${escHtml(f.path)}" data-gi="${gi}">
      <input type="checkbox" class="file-checkbox" id="${checkId}"
             data-path="${escHtml(f.path)}" data-gi="${gi}"
             ${isFirst ? "disabled title='Suggested keep — uncheck others to select this'" : ""}
             onchange="toggleFileSelection(this, '${gi}')">
      <div class="file-icon ${extCls}">${ext.substring(0,3)}</div>
      <div class="file-info">
        <div class="file-name">${escHtml(f.name)}</div>
        <div class="file-path">${escHtml(f.directory)}</div>
      </div>
      <div class="file-meta">
        <span class="file-size">${f.size_human}</span>
        <span class="file-date">${f.modified}</span>
        ${isFirst ? '<span class="file-keep-badge">keep</span>' : ""}
      </div>
    </div>`;
}

// ══════════════════════ Selection ══════════════════════
function toggleFileSelection(checkbox, gi) {
  const path = checkbox.dataset.path;
  const row  = checkbox.closest(".file-row");

  if (checkbox.checked) {
    selectedFiles.add(path);
    row.classList.add("checked-row");
  } else {
    selectedFiles.delete(path);
    row.classList.remove("checked-row");
  }

  updateDeleteButtons();
}

function autoSelectDuplicates() {
  // For each group: keep first file, check all others
  filteredGrps.forEach((group, gi) => {
    group.files.forEach((f, fi) => {
      if (fi === 0) return; // keep
      const chk = document.getElementById(`chk_${gi}_${fi}`);
      if (chk && !chk.disabled) {
        chk.checked = true;
        selectedFiles.add(f.path);
        chk.closest(".file-row").classList.add("checked-row");
      }
    });
  });
  updateDeleteButtons();
}

function updateDeleteButtons() {
  const count = selectedFiles.size;
  const disabled = count === 0;
  document.getElementById("btnDelete").disabled     = disabled;
  document.getElementById("btnDeletePerm").disabled = disabled;

  if (!disabled) {
    document.getElementById("btnDelete").innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
      </svg>
      Move to Trash (${count})`;
    document.getElementById("btnDeletePerm").innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
        <line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
      </svg>
      Delete Permanently (${count})`;
  }
}

// ══════════════════════ Delete ══════════════════════
async function deleteSelected(mode) {
  if (selectedFiles.size === 0) return;

  const modeLabel = mode === "trash" ? "move to Trash" : "PERMANENTLY delete";
  const confirmText = `You are about to ${modeLabel} ${selectedFiles.size} file(s).\n\nThis cannot be undone${mode === "trash" ? " from this app (but items will be in your Recycle Bin)" : ""}. Continue?`;

  showConfirm(
    mode === "trash" ? "Move to Trash" : "⚠️ Permanently Delete",
    confirmText,
    async () => {
      try {
        const result = await apiFetch("/api/delete", "POST", {
          files: [...selectedFiles],
          mode,
        });

        showToast(`✓ Freed ${result.space_freed_human} — ${result.success.length} file(s) removed`);

        // Remove deleted rows from UI
        result.success.forEach(path => {
          removeFileRowByPath(path);
          selectedFiles.delete(path);
        });

        if (result.failed.length > 0) {
          alert(`Failed to remove ${result.failed.length} file(s):\n` +
            result.failed.map(f => `• ${f.path}: ${f.error}`).join("\n"));
        }

        updateDeleteButtons();
        cleanEmptyGroups();
      } catch (e) {
        alert("Error during deletion: " + e.message);
      }
    }
  );
}

function removeFileRowByPath(path) {
  // Find all checkboxes with this path and remove their parent rows
  document.querySelectorAll(`.file-checkbox[data-path="${CSS.escape(path)}"]`).forEach(chk => {
    chk.closest(".file-row")?.remove();
  });
}

function cleanEmptyGroups() {
  document.querySelectorAll(".group-card").forEach(card => {
    const rows = card.querySelectorAll(".file-row");
    if (rows.length <= 1) {
      card.style.opacity = "0";
      card.style.transform = "scale(0.95)";
      card.style.transition = "opacity 0.3s, transform 0.3s";
      setTimeout(() => card.remove(), 300);
    }
  });
}

// ══════════════════════ Search & Sort ══════════════════════
function filterGroups() {
  const q = document.getElementById("searchInput").value.toLowerCase();
  filteredGrps = allGroups.filter(g =>
    g.files.some(f => f.path.toLowerCase().includes(q) || f.name.toLowerCase().includes(q)) ||
    g.hash.toLowerCase().includes(q)
  );
  renderGroups();
}

function sortGroups() {
  const sort = document.getElementById("sortSelect").value;
  filteredGrps.sort((a, b) => {
    if (sort === "wasted") return b.wasted_space - a.wasted_space;
    if (sort === "count")  return b.count - a.count;
    if (sort === "size")   return b.file_size - a.file_size;
    return 0;
  });
  renderGroups();
}

// ══════════════════════ Log Modal ══════════════════════
document.getElementById("btnViewLog").addEventListener("click", async () => {
  document.getElementById("logModal").style.display = "flex";
  document.getElementById("logContent").textContent = "Loading…";
  try {
    const data = await apiFetch("/api/logs");
    document.getElementById("logContent").textContent = data.log || "(empty)";
  } catch (e) {
    document.getElementById("logContent").textContent = "Could not load log: " + e.message;
  }
});

function closeLogModal(e) {
  if (e.target.id === "logModal") {
    document.getElementById("logModal").style.display = "none";
  }
}

// ══════════════════════ Confirm Modal ══════════════════════
function showConfirm(title, body, onOk) {
  document.getElementById("confirmTitle").textContent = title;
  document.getElementById("confirmBody").textContent  = body;
  document.getElementById("confirmModal").style.display = "flex";

  const okBtn = document.getElementById("confirmOk");
  const newOk = okBtn.cloneNode(true); // remove old listeners
  okBtn.parentNode.replaceChild(newOk, okBtn);
  newOk.addEventListener("click", () => {
    document.getElementById("confirmModal").style.display = "none";
    onOk();
  });
}

// ══════════════════════ Toast ══════════════════════
function showToast(msg) {
  const toast = document.getElementById("toastSaved");
  document.getElementById("toastText").textContent = msg;
  toast.style.display = "flex";
  setTimeout(() => { toast.style.display = "none"; }, 4000);
}

// ══════════════════════ UI Sections ══════════════════════
function setSection(state) {
  const progressPanel  = document.getElementById("progressPanel");
  const summaryCards   = document.getElementById("summaryCards");
  const actionBar      = document.getElementById("actionBar");
  const resultsSection = document.getElementById("resultsSection");
  const emptyState     = document.getElementById("emptyState");
  const btnScan        = document.getElementById("btnScan");

  progressPanel.style.display  = state === "scanning" ? "block" : "none";
  summaryCards.style.display   = ["results", "empty"].includes(state) ? "grid" : "none";
  actionBar.style.display      = state === "results" ? "flex" : "none";
  resultsSection.style.display = state === "results" ? "flex" : "none";
  emptyState.style.display     = state === "empty" ? "flex" : "none";

  btnScan.disabled = state === "scanning";
  btnScan.textContent = state === "scanning" ? "Scanning…" : "";
  if (state !== "scanning") {
    btnScan.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      ${allGroups.length ? "Re-scan" : "Start Scan"}`;
  }
}

// ══════════════════════ API Helper ══════════════════════
async function apiFetch(endpoint, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + endpoint, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

// ══════════════════════ Utilities ══════════════════════
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
