// PromptGuard — popup.js

const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function render(stats, history) {
  const total = stats.total || 0;
  const high  = stats.high  || 0;
  const avg   = total > 0 ? Math.round(stats.totalRisk / total) : 0;
  const prot  = total > 0 ? Math.max(0, 100 - avg) : 0;

  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-high').textContent  = high;
  document.getElementById('stat-avg').textContent   = total > 0 ? `${avg}%` : '—';
  document.getElementById('stat-safe').textContent  = total > 0 ? `${prot}%` : '—';

  const histEl = document.getElementById('history');
  if (history.length) {
    histEl.innerHTML = history.slice(0, 20).map(h => `
      <div class="hi">
        <div class="hi-dot ${h.level}"></div>
        <div class="hi-text">${esc(h.prompt)}</div>
        <div class="hi-badge ${h.level}">${h.pct}%</div>
      </div>`).join('');
  }
}

chrome.storage.local.get(['pg_history','pg_stats'], d =>
  render(d.pg_stats || {}, d.pg_history || []));

// History toggle
document.getElementById('history-toggle').addEventListener('click', () => {
  const h = document.getElementById('history');
  const link = document.getElementById('history-toggle');
  h.classList.toggle('hidden');
  link.textContent = h.classList.contains('hidden') ? 'View recent activity ›' : 'Hide recent activity ›';
});
