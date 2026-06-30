# PromptGuard

**Real-time hallucination detection and smarter prompt suggestions for AI chatbots.**

PromptGuard is a Chrome extension that sits on top of ChatGPT, Claude, and Gemini. It automatically scores every AI response for hallucination risk and — when the risk is high — shows you three better ways to ask your question so you get a more accurate answer.

---

## What it does

- **Hallucination score badge** — appears under every AI response showing risk level (LOW / MEDIUM / HIGH) with a percentage
- **Smart prompt suggestions** — when risk is high, a popup slides in with 3 rewritten versions of your question designed to reduce hallucination
- **One-click refill** — click "Use this" on any suggestion and it auto-fills the chatbox
- **Session stats** — click the extension icon to see how many responses were evaluated, how many were high risk, and your full history

---

## Works on

| Platform | URL |
|---|---|
| ChatGPT | chatgpt.com |
| Claude | claude.ai |
| Gemini | gemini.google.com |

---

## How to install (Chrome)

1. Clone or download this repo
2. Open Chrome and go to `chrome://extensions`
3. Enable **Developer mode** (toggle in the top right)
4. Click **Load unpacked**
5. Select the folder containing `manifest.json`
6. The 🛡 PromptGuard icon appears in your toolbar

---

## How hallucination is scored

PromptGuard uses a client-side heuristic analyser — no API calls, no data sent anywhere. It scans each response for:

- **High-risk signals** — "I think", "I believe", "I'm not sure", "to my knowledge", "if I recall correctly", "I may be wrong"
- **Medium-risk signals** — "approximately", "roughly", "seems like", "generally", "typically"
- **Confidence signals** — "according to research", "studies show", "specifically", "it is confirmed" (these reduce the score)

A weighted sum produces a risk percentage. Above 35% triggers the suggestion popup.

---

## How prompt suggestions work

When high risk is detected, PromptGuard rewrites your original question three ways:
1. Asks the AI to flag anything it is uncertain about
2. Asks for a step-by-step breakdown with sources
3. Asks for a precise, factual answer with no speculation

All suggestions are generated locally — no external API required.

---

## Project structure

```
promptguard/
├── manifest.json     — Chrome extension config (Manifest V3)
├── content.js        — Injected into chatbot pages; scoring + UI logic
├── content.css       — Styles for the badge and suggestion popup
├── popup.html        — Extension icon popup (stats dashboard)
├── popup.js          — Popup data rendering
├── popup.css         — Popup styles
├── background.js     — Service worker (initialises storage on install)
└── icons/            — Extension icons (16px, 48px, 128px)
```

---

## Built by

Anubhav Dixit · Michigan State University  
[github.com/Anubhav12123](https://github.com/Anubhav12123)
