// PromptGuard — content.js
// Injected into ChatGPT, Claude, and Gemini pages

const PLATFORM = detectPlatform();
const processed = new WeakSet();

// ── Platform detection ────────────────────────────────────────────────────────

function detectPlatform() {
  const h = location.hostname;
  if (h.includes('chatgpt.com')) return 'chatgpt';
  if (h.includes('claude.ai')) return 'claude';
  if (h.includes('gemini.google.com')) return 'gemini';
  return null;
}

// Selectors for each platform
const SELECTORS = {
  chatgpt: {
    response: '[data-message-author-role="assistant"]',
    text: '.markdown, .whitespace-pre-wrap',
    input: '#prompt-textarea',
  },
  claude: {
    response: '[data-testid="assistant-message"]',
    text: '.font-claude-message',
    input: '.ProseMirror',
  },
  gemini: {
    response: 'model-response',
    text: '.response-content, .markdown, p',
    input: '.ql-editor, rich-textarea .ql-editor',
  },
};

// ── Hallucination scoring ─────────────────────────────────────────────────────

function scoreHallucination(text) {
  if (!text || text.length < 30) return { risk: 0.5, level: 'medium', pct: 50 };

  const lower = text.toLowerCase();
  let risk = 0;

  const HIGH_RISK = [
    /i('m| am) not (sure|certain|aware)/g,
    /i (think|believe|suppose|guess)\b/g,
    /it('s| is) (possible|likely) that/g,
    /\bmight be\b/g,
    /\bcould be\b/g,
    /i may be wrong/g,
    /if i recall correctly/g,
    /to (my|the best of my) knowledge/g,
    /as far as i know/g,
    /i('m| am) not 100/g,
    /i cannot (verify|confirm|guarantee)/g,
    /my (knowledge|training) cutoff/g,
    /i don't have (access|information) (to|about)/g,
  ];

  const MED_RISK = [
    /\bapproximately\b/g,
    /\baround \d/g,
    /\broughly\b/g,
    /\bseems? (to|like)\b/g,
    /\bappears? (to|like)\b/g,
    /\bgenerally\b/g,
    /\btypically\b/g,
    /\busually\b/g,
    /\bsomething like\b/g,
    /\bi'm not 100% sure\b/g,
  ];

  const CONFIDENT = [
    /according to (studies|research|data|reports)/g,
    /\bspecifically\b/g,
    /research (shows|indicates|demonstrates|confirms)/g,
    /it (is|was|has been) (proven|established|confirmed)/g,
    /\bthe (fact|answer) is\b/g,
    /\bexactly\b/g,
  ];

  HIGH_RISK.forEach(p => {
    const m = lower.match(p);
    if (m) risk += m.length * 0.14;
  });
  MED_RISK.forEach(p => {
    const m = lower.match(p);
    if (m) risk += m.length * 0.06;
  });
  CONFIDENT.forEach(p => {
    const m = lower.match(p);
    if (m) risk -= m.length * 0.05;
  });

  risk = Math.max(0, Math.min(1, risk));

  const level = risk >= 0.35 ? 'high' : risk >= 0.15 ? 'medium' : 'low';
  const pct = Math.round(risk * 100);
  return { risk, level, pct };
}

// ── Prompt suggestions ────────────────────────────────────────────────────────

function generateSuggestions(originalPrompt) {
  const p = originalPrompt.trim().replace(/\?$/, '');
  return [
    `${p}? Please only include facts you are certain about and explicitly say "I'm not sure" for anything uncertain.`,
    `Can you walk me through step by step: ${p.toLowerCase()}? Cite specific sources if you can, and skip anything you can't verify.`,
    `Give me a precise, factual answer to: ${p.toLowerCase()}. Keep it concise and avoid any guessing or speculation.`,
  ];
}

// ── Badge injection ───────────────────────────────────────────────────────────

function injectBadge(container, scoreData, originalPrompt) {
  if (container.querySelector('.pg-badge')) return;

  const { level, pct } = scoreData;

  const badge = document.createElement('div');
  badge.className = `pg-badge pg-badge-${level}`;
  badge.innerHTML = `
    <span class="pg-badge-icon">${level === 'low' ? '✓' : level === 'medium' ? '⚡' : '⚠'}</span>
    <span class="pg-badge-label">Hallucination Risk</span>
    <span class="pg-badge-bar"><span class="pg-badge-fill" style="width:${pct}%"></span></span>
    <span class="pg-badge-pct">${pct}%</span>
    <span class="pg-badge-level">${level.toUpperCase()}</span>
    ${level === 'high' ? '<button class="pg-fix-btn">✦ Better prompts</button>' : ''}
  `;

  container.appendChild(badge);

  if (level === 'high') {
    badge.querySelector('.pg-fix-btn').addEventListener('click', () => {
      showSuggestionPopup(originalPrompt, container);
    });
    // Auto-show popup for high risk
    setTimeout(() => showSuggestionPopup(originalPrompt, container), 400);
  }

  // Save to history
  saveToHistory({ prompt: originalPrompt, pct, level, ts: Date.now() });
}

// ── Suggestion popup ──────────────────────────────────────────────────────────

function showSuggestionPopup(originalPrompt, anchor) {
  // Remove any existing popup
  document.querySelectorAll('.pg-popup').forEach(el => el.remove());

  const suggestions = generateSuggestions(originalPrompt);

  const popup = document.createElement('div');
  popup.className = 'pg-popup';
  popup.innerHTML = `
    <div class="pg-popup-header">
      <div class="pg-popup-title-row">
        <span class="pg-popup-icon">⚠</span>
        <div>
          <div class="pg-popup-title">High Hallucination Risk Detected</div>
          <div class="pg-popup-sub">This response may contain uncertain or inaccurate information</div>
        </div>
      </div>
      <button class="pg-popup-close">✕</button>
    </div>
    <div class="pg-popup-divider"></div>
    <div class="pg-popup-body">
      <div class="pg-popup-hint">✦ Try one of these clearer prompts:</div>
      ${suggestions.map((s, i) => `
        <div class="pg-suggestion" data-index="${i}">
          <div class="pg-suggestion-num">${i + 1}</div>
          <div class="pg-suggestion-text">${s}</div>
          <button class="pg-use-btn" data-prompt="${encodeURIComponent(s)}">Use this ↵</button>
        </div>
      `).join('')}
    </div>
    <div class="pg-popup-footer">PromptGuard · Click "Use this" to auto-fill the chatbox</div>
  `;

  document.body.appendChild(popup);

  // Position near the anchor
  const rect = anchor.getBoundingClientRect();
  const top = Math.min(rect.bottom + window.scrollY + 12, window.scrollY + window.innerHeight - 420);
  popup.style.top = `${top}px`;

  // Close button
  popup.querySelector('.pg-popup-close').addEventListener('click', () => popup.remove());

  // Use this buttons
  popup.querySelectorAll('.pg-use-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = decodeURIComponent(btn.dataset.prompt);
      fillInput(prompt);
      popup.remove();
    });
  });
}

// ── Fill input on target platform ─────────────────────────────────────────────

function fillInput(text) {
  const sel = SELECTORS[PLATFORM]?.input;
  if (!sel) return;

  const el = document.querySelector(sel);
  if (!el) return;

  el.focus();

  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set
      || Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
    if (nativeSetter) nativeSetter.call(el, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  } else if (el.isContentEditable) {
    el.innerText = text;
    el.dispatchEvent(new InputEvent('input', { bubbles: true }));
  }
}

// ── Extract text from response ────────────────────────────────────────────────

function extractText(container) {
  const sel = SELECTORS[PLATFORM]?.text;
  const inner = sel ? container.querySelector(sel) : null;
  return (inner || container).innerText?.trim() || '';
}

function extractUserPrompt(responseEl) {
  // Walk backwards through siblings/cousins to find the preceding user message
  let el = responseEl;
  while (el) {
    el = el.previousElementSibling;
    if (!el) break;
    const role = el.getAttribute('data-message-author-role');
    if (role === 'user') {
      return el.innerText?.trim() || '';
    }
    // Claude / Gemini: look for human-turn markers
    if (el.classList.contains('human-turn') || el.querySelector('[data-testid="human-turn"]')) {
      return el.innerText?.trim() || '';
    }
  }
  return '';
}

// ── Storage helpers ───────────────────────────────────────────────────────────

function saveToHistory(entry) {
  chrome.storage.local.get(['pg_history', 'pg_stats'], data => {
    const history = data.pg_history || [];
    history.unshift(entry);
    if (history.length > 100) history.splice(100);

    const stats = data.pg_stats || { total: 0, high: 0, totalRisk: 0 };
    stats.total += 1;
    if (entry.level === 'high') stats.high += 1;
    stats.totalRisk += entry.pct;

    chrome.storage.local.set({ pg_history: history, pg_stats: stats });
  });
}

// ── Observer ──────────────────────────────────────────────────────────────────

function processResponse(el) {
  if (processed.has(el)) return;

  const text = extractText(el);
  if (!text || text.length < 40) return;

  // Wait a beat to make sure streaming is done
  const waitForDone = () => {
    const currentText = extractText(el);
    setTimeout(() => {
      const laterText = extractText(el);
      if (laterText !== currentText) {
        // Still streaming — check again
        setTimeout(waitForDone, 800);
        return;
      }
      // Text settled — score and inject
      if (processed.has(el)) return;
      processed.add(el);

      const score = scoreHallucination(laterText);
      const prompt = extractUserPrompt(el) || 'your question';
      injectBadge(el, score, prompt);
    }, 800);
  };

  waitForDone();
}

function observe() {
  if (!PLATFORM) return;

  const sel = SELECTORS[PLATFORM].response;

  // Process any already-existing responses
  document.querySelectorAll(sel).forEach(processResponse);

  const observer = new MutationObserver(mutations => {
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches(sel)) {
          processResponse(node);
        }
        node.querySelectorAll(sel).forEach(processResponse);
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

observe();
