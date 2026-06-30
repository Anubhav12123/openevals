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

// Mark responses already on page as old — no auto-popup for these
document.querySelectorAll(sel).forEach(el => {
  el.dataset.pgOld = '1';
  el.dataset.pgDone = '1';
});

// ── Scoring ───────────────────────────────────────────────────────────────────

const HIGH_RISK_PATTERNS = [
  { re: /i('m| am) not (sure|certain|aware)/g,         label: "uncertainty phrase" },
  { re: /i (think|believe|suppose|guess)\b/g,           label: "hedged claim" },
  { re: /it('s| is) (possible|likely) that/g,           label: "speculative statement" },
  { re: /\bmight\b/g,                                    label: "'might'" },
  { re: /\bcould be\b/g,                                 label: "'could be'" },
  { re: /i may be wrong/g,                               label: "self-doubt" },
  { re: /if i recall correctly/g,                        label: "memory caveat" },
  { re: /to (my|the best of my) knowledge/g,             label: "knowledge caveat" },
  { re: /as far as i know/g,                             label: "knowledge caveat" },
  { re: /i cannot (verify|confirm|guarantee)/g,          label: "unverifiable claim" },
  { re: /my (knowledge|training) (cutoff|data)/g,        label: "training cutoff" },
  { re: /i don't have (access|information)/g,            label: "missing info" },
  { re: /\buncertain\b/g,                                label: "'uncertain'" },
  { re: /\bpossibly\b/g,                                 label: "'possibly'" },
  { re: /\bperhaps\b/g,                                  label: "'perhaps'" },
  { re: /\bprobably\b/g,                                 label: "'probably'" },
  { re: /\bi'd (guess|say|estimate)\b/g,                 label: "hedged estimate" },
  { re: /\bspeculat/g,                                   label: "speculation" },
  { re: /\bhypothet/g,                                   label: "hypothesis" },
];

const MED_RISK_PATTERNS = [
  { re: /\bapproximately\b/g,   label: "'approximately'" },
  { re: /\baround \d/g,         label: "vague number" },
  { re: /\broughly\b/g,         label: "'roughly'" },
  { re: /\bseems?\b/g,          label: "'seems'" },
  { re: /\bappears?\b/g,        label: "'appears'" },
  { re: /\bgenerally\b/g,       label: "'generally'" },
  { re: /\btypically\b/g,       label: "'typically'" },
  { re: /\busually\b/g,         label: "'usually'" },
  { re: /\boften\b/g,           label: "'often'" },
  { re: /\bmay\b/g,             label: "'may'" },
  { re: /\bsomewhat\b/g,        label: "'somewhat'" },
  { re: /\blikely\b/g,          label: "'likely'" },
  { re: /\bpotentially\b/g,     label: "'potentially'" },
];

const CONFIDENT_PATTERNS = [
  { re: /according to (studies|research|data|reports)/g },
  { re: /research (shows|indicates|demonstrates|confirms)/g },
  { re: /it (is|was|has been) (proven|established|confirmed)/g },
  { re: /\bdefinitely\b/g },
  { re: /\bcertainly\b/g },
  { re: /\bconfirmed\b/g },
  { re: /\bproven\b/g },
];

function scoreHallucination(text) {
  const lower = text.toLowerCase();
  let risk = 0.10;
  const triggers = [];

  HIGH_RISK_PATTERNS.forEach(({ re, label }) => {
    const m = lower.match(re);
    if (m) { risk += m.length * 0.15; triggers.push(label); }
  });
  MED_RISK_PATTERNS.forEach(({ re, label }) => {
    const m = lower.match(re);
    if (m) { risk += m.length * 0.06; triggers.push(label); }
  });
  CONFIDENT_PATTERNS.forEach(({ re }) => {
    const m = lower.match(re);
    if (m) risk -= m.length * 0.05;
  });

  risk = Math.max(0, Math.min(1, risk));
  const level = risk >= 0.35 ? 'high' : risk >= 0.20 ? 'medium' : 'low';
  const uniqueTriggers = [...new Set(triggers)].slice(0, 3);
  return { level, pct: Math.round(risk * 100), triggers: uniqueTriggers };
}

const API_URL = 'https://openevals-api.onrender.com';

function templateSuggestions(p) {
  p = p.trim().replace(/\?$/, '');
  return [
    `${p}? Only include facts you are certain about — say "I don't know" for anything uncertain.`,
    `Walk me through step by step: ${p.toLowerCase()}? Cite sources where possible, skip what you can't verify.`,
    `Give me a precise, factual answer to: ${p.toLowerCase()}. No speculation or guessing.`,
  ];
}

async function getSuggestions(originalPrompt, responseText) {
  try {
    const res = await fetch(`${API_URL}/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: originalPrompt, response: responseText }),
    });
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    if (Array.isArray(data.suggestions) && data.suggestions.length === 3) {
      return data.suggestions;
    }
    throw new Error('Bad response');
  } catch {
    return templateSuggestions(originalPrompt);
  }
}

// ── Popup ─────────────────────────────────────────────────────────────────────

async function showPopup(originalPrompt, responseText) {
  if (document.querySelector('.pg-popup')) return;

  const overlay = document.createElement('div');
  overlay.className = 'pg-overlay';
  document.body.appendChild(overlay);

  const popup = document.createElement('div');
  popup.className = 'pg-popup';
  popup.innerHTML = `<div class="pg-loading">Generating smarter prompts…</div>`;
  document.body.appendChild(popup);

  const close = () => { popup.remove(); overlay.remove(); };
  overlay.addEventListener('click', close);

  const suggestions = await getSuggestions(originalPrompt, responseText);

  popup.innerHTML = suggestions.map((s, i) => `
    <div class="pg-suggestion">
      <div class="pg-suggestion-num">${i + 1}</div>
      <div class="pg-suggestion-text">${s}</div>
      <div class="pg-suggestion-actions">
        <button class="pg-copy-btn" data-p="${encodeURIComponent(s)}">Copy</button>
        <button class="pg-use-btn" data-p="${encodeURIComponent(s)}">Use ↵</button>
      </div>
    </div>`).join('');

  popup.querySelectorAll('.pg-use-btn').forEach(btn =>
    btn.addEventListener('click', () => { fillInput(decodeURIComponent(btn.dataset.p)); close(); }));

  popup.querySelectorAll('.pg-copy-btn').forEach(btn =>
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(decodeURIComponent(btn.dataset.p));
      btn.textContent = '✓';
      setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
    }));
}

// ── Badge ─────────────────────────────────────────────────────────────────────

function injectBadge(el, scoreData, prompt, responseText, isNew) {
  if (el.querySelector('.pg-badge')) return;
  const { level, pct, triggers } = scoreData;

  const badge = document.createElement('div');
  badge.className = `pg-badge pg-badge-${level}`;
  const icon = level === 'low' ? '✓' : level === 'medium' ? '⚡' : '⚠';
  const triggerHtml = triggers.length
    ? `<span class="pg-badge-triggers">Detected: ${triggers.join(', ')}</span>`
    : '';
  badge.innerHTML = `
    <span class="pg-badge-icon">${icon}</span>
    <span class="pg-badge-label">Hallucination Risk</span>
    <span class="pg-badge-bar"><span class="pg-badge-fill" style="width:${pct}%"></span></span>
    <span class="pg-badge-pct">${pct}%</span>
    <span class="pg-badge-level">${level.toUpperCase()}</span>
    ${triggerHtml}
    ${level !== 'low' ? `<button class="pg-fix-btn">✦ Better prompts</button>` : ''}
  `;
  el.appendChild(badge);

  if (level !== 'low') {
    badge.querySelector('.pg-fix-btn').addEventListener('click', () => showPopup(prompt, responseText));
    if (isNew) setTimeout(() => showPopup(prompt, responseText), 500);
  }

  chrome.storage.local.get(['pg_history', 'pg_stats'], data => {
    const h = data.pg_history || [];
    h.unshift({ prompt, pct, level, ts: Date.now() });
    if (h.length > 100) h.splice(100);
    const st = data.pg_stats || { total: 0, high: 0, totalRisk: 0 };
    st.total++;
    if (level === 'high') st.high++;
    st.totalRisk += pct;
    chrome.storage.local.set({ pg_history: h, pg_stats: st });
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getText(el) {
  const inner = el.querySelector(SELECTORS[PLATFORM].text);
  return (inner || el).innerText?.trim() || '';
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
  return all.length ? all[all.length - 1].innerText?.trim() || '' : 'this topic';
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

// ── Process element ───────────────────────────────────────────────────────────

function processEl(el) {
  if (el.dataset.pgDone) return;
  if (el.dataset.pgPolling === '1') return;
  el.dataset.pgPolling = '1';
  const isNew = !el.dataset.pgOld;

  let last = '', stable = 0;

  function poll() {
    if (!document.contains(el) || el.dataset.pgDone) return;
    const text = el.innerText?.trim() || '';
    if (!text || text.length < 30) { setTimeout(poll, 500); return; }
    if (text === last) {
      if (++stable >= 2) {
        el.dataset.pgDone = '1';
        el.dataset.pgPolling = '0';
        const s = scoreHallucination(text);
        injectBadge(el, s, getPrompt(el), text, isNew);
        return;
      }
    } else { stable = 0; last = text; }
    setTimeout(poll, 600);
  }

  setTimeout(poll, 300);
}

// ── Observe ───────────────────────────────────────────────────────────────────

function scan() {
  document.querySelectorAll(sel).forEach(el => {
    if (el.dataset.pgPolling === '1' && !el.dataset.pgDone) {
      if ((el.innerText?.trim() || '').length > 30 && !el.querySelector('.pg-badge')) {
        el.dataset.pgPolling = '0';
      }
    }
    processEl(el);
  });
}

new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
setInterval(scan, 1500);

let lastUrl = location.href;
setInterval(() => {
  if (location.href === lastUrl) return;
  lastUrl = location.href;
  setTimeout(() => {
    document.querySelectorAll(sel).forEach(el => { if (el.dataset.pgDone) el.dataset.pgOld = '1'; });
    scan();
  }, 800);
}, 500);

} // end setup()
