const SERVER = "http://localhost:8000";

chrome.runtime.onMessage.addListener(msg => {
  if (msg.type === "PROMPT_CAPTURED") sendPrompt(msg.payload);
  if (msg.type === "RATE_PROMPT")     ratePrompt(msg.id, msg.rating, msg.note);
});

async function sendPrompt(payload) {
  try {
    const res = await fetch(`${SERVER}/prompts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return;
    const data = await res.json();
    const { recentIds = [] } = await chrome.storage.local.get("recentIds");
    recentIds.unshift({ id: data.id, snippet: payload.prompt.slice(0, 60), score: data.quality?.total ?? 0 });
    if (recentIds.length > 20) recentIds.length = 20;
    await chrome.storage.local.set({ recentIds });
    const score = data.quality?.total ?? 0;
    chrome.action.setBadgeBackgroundColor({ color: score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : "#ef4444" });
    chrome.action.setBadgeText({ text: score ? String(score) : "?" });
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
  } catch (err) { console.warn("[POS]", err.message); }
}

async function ratePrompt(id, rating, note = "") {
  await fetch(`${SERVER}/prompts/${id}/rating`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, rating_note: note }),
  }).catch(() => {});
}
