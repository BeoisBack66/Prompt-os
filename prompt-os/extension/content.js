(function () {
  "use strict";
  const PLATFORM   = location.hostname.includes("chatgpt") ? "chatgpt" : "claude";
  const SESSION_ID = `${PLATFORM}-${Date.now()}`;
  const SEL = {
    chatgpt: { textarea: "#prompt-textarea" },
    claude:  { textarea: "div.tiptap.ProseMirror" },
  };
  const s = SEL[PLATFORM];

  let lastSent     = "";
  let lastSentTime = 0;
  let lastText     = "";
  let currentEl    = null;
  let taObserver   = null;

  function getText() {
    const el = document.querySelector(s.textarea);
    return el ? (el.value || el.innerText || "").trim() : null;
  }

  function send(text) {
    const now = Date.now();
    // Skip if same text or sent within the last 2 seconds (duplicate prevention)
    if (!text || text === lastSent || now - lastSentTime < 2000) return;
    lastSent     = text;
    lastSentTime = now;
    chrome.runtime.sendMessage({
      type: "PROMPT_CAPTURED",
      payload: {
        prompt: text, platform: PLATFORM,
        url: location.href, captured_at: new Date().toISOString(),
        session_id: SESSION_ID,
      },
    });
  }

  // Attach MutationObserver to textarea — triggers send when cleared
  function attachObserver(el) {
    if (taObserver) taObserver.disconnect();
    currentEl  = el;
    taObserver = new MutationObserver(() => {
      const t = getText();
      if (t) {
        lastText = t;
      } else if (lastText) {
        send(lastText);
        lastText = "";
      }
    });
    taObserver.observe(el, { childList: true, subtree: true, characterData: true });
  }

  // SPA navigation support: re-attach observer whenever textarea is replaced
  new MutationObserver(() => {
    const el = document.querySelector(s.textarea);
    if (el && el !== currentEl) attachObserver(el);
  }).observe(document.body, { childList: true, subtree: true });

  // Initial attach
  const initial = document.querySelector(s.textarea);
  if (initial) attachObserver(initial);

  // Detect Enter key submission
  document.addEventListener("keydown", e => {
    if (e.key !== "Enter" || e.shiftKey) return;
    const a = document.activeElement;
    if (a && (a.matches(s.textarea) || a.closest(s.textarea))) {
      const t = getText();
      if (t) send(t);
    }
  }, true);

  console.log(`[Prompt OS] Watching ${PLATFORM}`);
})();
