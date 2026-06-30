const input  = document.getElementById('api-key');
const btn    = document.getElementById('save-btn');
const status = document.getElementById('status');

chrome.storage.local.get('groq_key', ({ groq_key }) => {
  if (groq_key) input.value = groq_key;
});

btn.addEventListener('click', () => {
  const key = input.value.trim();
  chrome.storage.local.set({ groq_key: key || null }, () => {
    status.textContent = key ? 'Key saved.' : 'Key removed.';
    setTimeout(() => { status.textContent = ''; }, 2000);
  });
});
