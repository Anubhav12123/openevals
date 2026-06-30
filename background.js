// PromptGuard — background service worker
// Minimal — all logic runs in content.js

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ pg_history: [], pg_stats: { total: 0, high: 0, totalRisk: 0 } });
});
