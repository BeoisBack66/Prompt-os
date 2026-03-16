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
    // 동일 텍스트이거나 2초 이내 재전송이면 무시 (중복 방지)
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

  // textarea에 MutationObserver 연결 — 비워지면 전송
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

  // SPA 네비게이션 대응: textarea가 교체될 때마다 재연결
  new MutationObserver(() => {
    const el = document.querySelector(s.textarea);
    if (el && el !== currentEl) attachObserver(el);
  }).observe(document.body, { childList: true, subtree: true });

  // 초기 연결
  const initial = document.querySelector(s.textarea);
  if (initial) attachObserver(initial);

  // Enter 키 전송 감지
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
