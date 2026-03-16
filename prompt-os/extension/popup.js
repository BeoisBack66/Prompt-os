const S = "http://127.0.0.1:8000";

// Tab switching
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".tab,.section").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  document.getElementById("tab-" + t.dataset.tab).classList.add("active");
}));

// Server health check
async function checkServer() {
  try {
    await fetch(S + "/health");
    document.getElementById("srv").textContent = "✅ Connected";
  } catch {
    document.getElementById("srv").textContent = "❌ Server offline";
  }
}

// Load recent prompts
async function loadRecent() {
  const el = document.getElementById("recent-list");
  try {
    const data = await (await fetch(S + "/prompts?limit=15")).json();
    if (!data.length) {
      el.innerHTML = '<p class="empty">No prompts yet.</p>';
      return;
    }
    el.innerHTML = data.map(p =>
      '<div class="card" id="card-' + p.id + '">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start">' +
          '<div style="flex:1">' + p.prompt.slice(0, 80) + (p.prompt.length > 80 ? "…" : "") + '</div>' +
          '<span class="del-btn" data-id="' + p.id + '" style="cursor:pointer;color:#ef4444;font-size:16px;margin-left:8px;flex-shrink:0">🗑</span>' +
        '</div>' +
        '<div class="meta">' + p.platform + ' · ' + (p.category || "other") +
          ' · <span class="score-badge ' + gc(p.score) + '">' + p.score + ' pts</span></div>' +
        '<div class="stars" data-id="' + p.id + '">' +
          [1,2,3,4,5].map(n =>
            '<span class="star ' + (n <= (p.rating || 0) ? "on" : "") + '" data-n="' + n + '">★</span>'
          ).join("") +
        '</div>' +
      '</div>'
    ).join("");

    // Star rating events
    el.querySelectorAll(".stars").forEach(row =>
      row.querySelectorAll(".star").forEach(s => s.addEventListener("click", () => {
        const id = +row.dataset.id, n = +s.dataset.n;
        fetch(S + "/prompts/" + id + "/rating", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating: n }),
        });
        row.querySelectorAll(".star").forEach(x => x.classList.toggle("on", +x.dataset.n <= n));
      }))
    );

    // Individual delete events
    el.querySelectorAll(".del-btn").forEach(btn =>
      btn.addEventListener("click", async () => {
        const id = +btn.dataset.id;
        if (!confirm("Delete this prompt?")) return;
        await fetch(S + "/prompts/" + id, { method: "DELETE" });
        document.getElementById("card-" + id)?.remove();
        if (!el.querySelector(".card")) {
          el.innerHTML = '<p class="empty">No prompts yet.</p>';
        }
      })
    );
  } catch {
    el.innerHTML = '<p class="empty">Cannot connect to server.</p>';
  }
}

// Delete all prompts
async function deleteAll() {
  if (!confirm("⚠️ Delete all prompts? This cannot be undone.")) return;
  await fetch(S + "/prompts", { method: "DELETE" });
  loadRecent();
  loadStats();
}

// Load analytics summary
async function loadStats() {
  const el = document.getElementById("stats-content");
  try {
    const d = await (await fetch(S + "/analysis/summary")).json();
    if (d.total === 0) {
      el.innerHTML = '<p class="empty">No data yet.</p>';
      return;
    }
    const cats = Object.entries(d.by_category || {})
      .map(([k, v]) => '<span class="chip">' + k + ' ' + v + '</span>').join("");
    const tips = (d.suggestions || [])
      .map(t => '<div class="tip">💡 ' + t + '</div>').join("");
    el.innerHTML =
      '<div class="card">' +
        '<div class="stat-row"><span>Total prompts</span><span class="stat-val">' + d.total + '</span></div>' +
        '<div class="stat-row"><span>Avg quality score</span><span class="stat-val">' + d.avg_quality_score + ' pts</span></div>' +
      '</div>' +
      '<div class="card"><div style="margin-bottom:6px;color:#94a3b8;font-size:11px">Category breakdown</div>' + cats + '</div>' +
      '<div style="color:#94a3b8;font-size:11px;margin-bottom:4px">Suggestions</div>' + tips;
  } catch {
    el.innerHTML = '<p class="empty">Cannot connect to server.</p>';
  }
}

// Load templates
async function loadTemplates() {
  const el = document.getElementById("tpl-list");
  try {
    const data = await (await fetch(S + "/templates")).json();
    if (!data.length) {
      el.innerHTML = '<p class="empty">No templates saved.</p>';
      return;
    }
    el.innerHTML = data.map(t =>
      '<div class="tpl-card">' +
        '<div><strong>' + t.title + '</strong> <span class="chip">' + t.category + '</span></div>' +
        '<div class="tpl-text">' + t.template + '</div>' +
        '<div class="meta" style="margin-top:4px">Used ' + t.use_count + ' times</div>' +
      '</div>'
    ).join("");
  } catch {
    el.innerHTML = '<p class="empty">Cannot connect to server.</p>';
  }
}

document.getElementById("tpl-save").addEventListener("click", async () => {
  const title = document.getElementById("tpl-title").value.trim();
  const cat   = document.getElementById("tpl-cat").value.trim();
  const body  = document.getElementById("tpl-body").value.trim();
  if (!title || !cat || !body) return alert("Please fill in all fields.");
  await fetch(S + "/templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, category: cat, template: body }),
  });
  document.getElementById("tpl-title").value =
  document.getElementById("tpl-cat").value   =
  document.getElementById("tpl-body").value  = "";
  loadTemplates();
});

// Returns CSS class based on score value
function gc(s) { return s >= 80 ? "score-a" : s >= 60 ? "score-b" : "score-c"; }

// Delete all button
document.getElementById("delete-all").addEventListener("click", deleteAll);

// Initial load
checkServer();
loadRecent();
loadStats();
loadTemplates();
