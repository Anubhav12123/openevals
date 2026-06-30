// OpenEvals — content.js

const PLATFORM = detectPlatform();
if (PLATFORM) setup();

function detectPlatform() {
  const h = location.hostname;
  if (h.includes('chatgpt.com')) return 'chatgpt';
  if (h.includes('claude.ai')) return 'claude';
  if (h.includes('gemini.google.com')) return 'gemini';
  return null;
}

function setup() {

const SELECTORS = {
  chatgpt: { response: '[data-message-author-role="assistant"]', text: '.markdown, .whitespace-pre-wrap', input: '#prompt-textarea' },
  claude:  { response: '[data-testid="assistant-message"]',      text: '.font-claude-message',            input: '.ProseMirror' },
  gemini:  { response: 'message-content, model-response',        text: '.markdown, p',                    input: 'rich-textarea .ql-editor, .ql-editor' },
};

const sel = SELECTORS[PLATFORM].response;

// Mark all responses already on the page as "old" — no auto-popup for these
document.querySelectorAll(sel).forEach(el => {
  el.dataset.pgOld = '1';
  el.dataset.pgDone = '1'; // don't re-score old responses either
});

// ── Scoring ───────────────────────────────────────────────────────────────────

function score(text) {
  const lower = text.toLowerCase();
  let risk = 0.10;

  [
    [0.15, [/i('m| am) not (sure|certain|aware)/g, /i (think|believe|suppose|guess)\b/g,
            /it('s| is) (possible|likely) that/g, /\bmight\b/g, /\bcould be\b/g,
            /i may be wrong/g, /if i recall correctly/g, /to (my|the best of my) knowledge/g,
            /as far as i know/g, /i cannot (verify|confirm|guarantee)/g,
            /my (knowledge|training) (cutoff|data)/g, /i don't have (access|information)/g,
            /\buncertain\b/g, /\bpossibly\b/g, /\bperhaps\b/g, /\bprobably\b/g,
            /\bi'd (guess|say|estimate)\b/g, /\bspeculat/g, /\bhypothet/g]],
    [0.06, [/\bapproximately\b/g, /\baround \d/g, /\broughly\b/g, /\bseems?\b/g,
            /\bappears?\b/g, /\bgenerally\b/g, /\btypically\b/g, /\busually\b/g,
            /\boften\b/g, /\bmay\b/g, /\bsomewhat\b/g, /\blikely\b/g, /\bpotentially\b/g]],
    [-0.05,[/according to (studies|research|data|reports)/g,
            /research (shows|indicates|demonstrates|confirms)/g,
            /it (is|was|has been) (proven|established|confirmed)/g,
            /\bdefinitely\b/g, /\bcertainly\b/g, /\bconfirmed\b/g, /\bproven\b/g]],
  ].forEach(([w, patterns]) => {
    patterns.forEach(p => { const m = lower.match(p); if (m) risk += m.length * w; });
  });

  risk = Math.max(0, Math.min(1, risk));
  const level = risk >= 0.35 ? 'high' : risk >= 0.20 ? 'medium' : 'low';
  return { level, pct: Math.round(risk * 100) };
}

// ── Suggestions ───────────────────────────────────────────────────────────────

function suggestions(p) {
  p = p.trim().replace(/\?$/, '');
  return [
    `${p}? Only include facts you are certain about — say "I don't know" for anything uncertain.`,
    `Walk me through step by step: ${p.toLowerCase()}? Cite sources where possible, skip anything you can't verify.`,
    `Give me a precise, factual answer to: ${p.toLowerCase()}. No speculation or guessing.`,
  ];
}

// ── Popup ─────────────────────────────────────────────────────────────────────

function showPopup(originalPrompt) {
  // Only one popup at a time
  if (document.querySelector('.pg-popup')) return;

  const s = suggestions(originalPrompt);
  const overlay = document.createElement('div');
  overlay.className = 'pg-overlay';
  document.body.appendChild(overlay);

  const popup = document.createElement('div');
  popup.className = 'pg-popup';
  popup.innerHTML = s.map((t, i) => `
    <div class="pg-suggestion">
      <div class="pg-suggestion-num">${i + 1}</div>
      <div class="pg-suggestion-text">${t}</div>
      <button class="pg-use-btn" data-p="${encodeURIComponent(t)}">Use ↵</button>
    </div>`).join('');
  document.body.appendChild(popup);

  const close = () => { popup.remove(); overlay.remove(); };
  overlay.addEventListener('click', close);
  popup.querySelectorAll('.pg-use-btn').forEach(btn =>
    btn.addEventListener('click', () => { fillInput(decodeURIComponent(btn.dataset.p)); close(); }));
}

// ── Badge ─────────────────────────────────────────────────────────────────────

function injectBadge(el, s, prompt, isNew) {
  if (el.querySelector('.pg-badge')) return;
  const { level, pct } = s;
  const badge = document.createElement('div');
  badge.className = `pg-badge pg-badge-${level}`;
  badge.innerHTML = `
    <span class="pg-badge-icon">${level === 'low' ? '✓' : level === 'medium' ? '⚡' : '⚠'}</span>
    <span class="pg-badge-label">Hallucination Risk</span>
    <span class="pg-badge-bar"><span class="pg-badge-fill" style="width:${pct}%"></span></span>
    <span class="pg-badge-pct">${pct}%</span>
    <span class="pg-badge-level">${level.toUpperCase()}</span>
    ${level !== 'low' ? `<button class="pg-fix-btn">✦ Better prompts</button>` : ''}
  `;
  el.appendChild(badge);

  if (level !== 'low') {
    badge.querySelector('.pg-fix-btn').addEventListener('click', () => showPopup(prompt));
    // Only auto-show popup for NEW responses, never for ones that existed on page load
    if (isNew) setTimeout(() => showPopup(prompt), 500);
  }

  chrome.storage.local.get(['pg_history','pg_stats'], data => {
    const h = data.pg_history || [];
    h.unshift({ prompt, pct, level, ts: Date.now() });
    if (h.length > 100) h.splice(100);
    const st = data.pg_stats || { total:0, high:0, totalRisk:0 };
    st.total++; if (level === 'high') st.high++; st.totalRisk += pct;
    chrome.storage.local.set({ pg_history: h, pg_stats: st });
  });
}

// ── Text helpers ──────────────────────────────────────────────────────────────

function getText(el) {
  const textSel = SELECTORS[PLATFORM].text;
  const inner = el.querySelector(textSel);
  const t = (inner || el).innerText?.trim() || '';
  return t;
}

function getPrompt(el) {
  let cur = el;
  while (cur) {
    cur = cur.previousElementSibling;
    if (!cur) break;
    if (cur.getAttribute('data-message-author-role') === 'user') return cur.innerText?.trim() || '';
    if (cur.classList.contains('human-turn')) return cur.innerText?.trim() || '';
  }
  const all = document.querySelectorAll('[data-message-author-role="user"]');
  return all.length ? all[all.length-1].innerText?.trim() || '' : 'this topic';
}

function fillInput(text) {
  const el = document.querySelector(SELECTORS[PLATFORM].input);
  if (!el) return;
  el.focus();
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
    if (setter) setter.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  } else if (el.isContentEditable) {
    el.innerText = text;
    el.dispatchEvent(new InputEvent('input', { bubbles: true }));
  }
}

// ── Process a response element ────────────────────────────────────────────────

function processEl(el) {
  if (el.dataset.pgDone) return;
  // Don't start a second poll if one is already running for this element
  if (el.dataset.pgPolling === '1') return;
  el.dataset.pgPolling = '1';
  const isNew = !el.dataset.pgOld;

  let last = '', stable = 0;

  function poll() {
    // Element may have been removed from DOM
    if (!document.contains(el)) return;
    if (el.dataset.pgDone) return;

    const text = el.innerText?.trim() || '';
    if (!text || text.length < 30) { setTimeout(poll, 500); return; }

    if (text === last) {
      stable++;
      if (stable >= 2) {
        el.dataset.pgDone = '1';
        el.dataset.pgPolling = '0';
        injectBadge(el, score(text), getPrompt(el), isNew);
        return;
      }
    } else {
      stable = 0;
      last = text;
    }
    setTimeout(poll, 600);
  }

  setTimeout(poll, 300);
}

// ── Observe ───────────────────────────────────────────────────────────────────

function scan() {
  document.querySelectorAll(sel).forEach(el => {
    // Reset stale polling state if element has text but polling got stuck
    if (el.dataset.pgPolling === '1' && !el.dataset.pgDone) {
      const text = el.innerText?.trim() || '';
      if (text.length > 30 && !el.querySelector('.pg-badge')) {
        el.dataset.pgPolling = '0'; // allow re-entry
      }
    }
    processEl(el);
  });
}

new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
setInterval(scan, 1500);

// SPA navigation detection
let lastUrl = location.href;
setInterval(() => {
  if (location.href === lastUrl) return;
  lastUrl = location.href;
  // Mark any currently visible responses as old
  setTimeout(() => {
    document.querySelectorAll(sel).forEach(el => {
      if (el.dataset.pgDone) el.dataset.pgOld = '1';
    });
    scan();
  }, 800);
}, 500);

} // end setup()
