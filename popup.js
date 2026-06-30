// PromptGuard — popup.js

function render(stats, history) {
  const total = stats.total || 0;
  const high  = stats.high  || 0;
  const avg   = total > 0 ? Math.round(stats.totalRisk / total) : 0;
  const prot  = total > 0 ? Math.max(0, 100 - avg) : 0;

  // Numbers
  document.getElementById('stat-total').textContent = total || '0';
  document.getElementById('stat-high').textContent  = high  || '0';
  document.getElementById('stat-safe').textContent  = total > 0 ? `${prot}%` : '—';
  document.getElementById('ring-num').textContent   = total > 0 ? `${avg}%` : '—';

  // Ring — r=46, circumference = 2π×46 ≈ 289
  const C = 289;
  const arc = document.getElementById('ring-arc');
  const filled = (avg / 100) * C;
  const colour = avg >= 35 ? '#f87171' : avg >= 15 ? '#facc15' : '#4ade80';
  arc.style.stroke = colour;
  arc.style.filter = `drop-shadow(0 0 6px ${colour}99)`;
  setTimeout(() => {
    arc.setAttribute('stroke-dasharray', `${filled} ${C}`);
  }, 60);

  // Protection bar
  document.getElementById('pbar-pct').textContent = total > 0 ? `${prot}%` : '—';
  setTimeout(() => {
    document.getElementById('pbar-fill').style.width = `${prot}%`;
  }, 60);

  // History
  const el = document.getElementById('history');
  if (!history.length) return;
  el.innerHTML = history.slice(0, 20).map(h => `
    <div class="hi">
      <div class="hi-dot ${h.level}"></div>
      <div class="hi-text">${esc(h.prompt)}</div>
      <div class="hi-badge ${h.level}">${h.pct}%</div>
    </div>`).join('');
}

const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

chrome.storage.local.get(['pg_history','pg_stats'], d =>
  render(d.pg_stats||{}, d.pg_history||[]));
