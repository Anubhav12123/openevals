# OpenEvals

**Real-time hallucination detection for AI chatbots — right in your browser.**

OpenEvals is a Chrome extension that scores every AI response for hallucination risk as it streams in. When the risk is medium or high, it automatically surfaces three smarter ways to re-ask your question so you get more accurate answers.

---

## What it does

- **Live hallucination score badge** — appears under every AI response the moment it finishes, showing risk level (LOW / MEDIUM / HIGH) with a percentage
- **Smarter prompt suggestions** — when risk is detected, a popup shows 3 rewritten versions of your question designed to reduce uncertainty
- **One-click refill** — click "Use ↵" on any suggestion and it auto-fills the chatbox
- **Session stats** — click the extension icon to see responses evaluated, high-risk count, average risk score, and session protection rate

---

## Works on

| Platform | URL |
|---|---|
| ChatGPT | chatgpt.com |
| Claude | claude.ai |
| Gemini | gemini.google.com |

---

## How to install

1. Clone or download this repo
2. Open Chrome and go to `chrome://extensions`
3. Enable **Developer mode** (toggle in the top right)
4. Click **Load unpacked**
5. Select the `openevals` folder
6. The OpenEvals icon appears in your toolbar

---

## How hallucination is scored

OpenEvals uses a client-side heuristic analyser — no API calls, no data sent anywhere. It scans each response for:

- **High-risk signals** — "I think", "I believe", "might", "possibly", "perhaps", "I'm not sure", "to my knowledge", "I cannot verify"
- **Medium-risk signals** — "approximately", "roughly", "generally", "typically", "usually", "likely", "potentially"
- **Confidence signals** — "according to research", "confirmed", "proven", "definitely" (these reduce the score)

A weighted sum produces a risk percentage. Above 20% shows the badge; above 35% auto-triggers the prompt suggestions popup.

---

## How prompt suggestions work

When risk is detected, OpenEvals rewrites your original question three ways:

1. Asks the AI to flag anything it is uncertain about
2. Asks for a step-by-step breakdown with sources
3. Asks for a precise, factual answer with no speculation

All suggestions are generated locally — no external API required.

---

## Project structure

```
openevals/
├── manifest.json     — Chrome extension config (Manifest V3)
├── content.js        — Injected into chatbot pages; scoring + UI logic
├── content.css       — Styles for the badge and suggestion popup
├── popup.html        — Extension icon popup (session stats)
├── popup.js          — Popup data rendering
├── popup.css         — Popup styles
├── background.js     — Service worker (initialises storage on install)
└── icons/            — Extension icons (16px, 48px, 128px)
```

---

## Built by

Anubhav Dixit · Michigan State University  
[github.com/Anubhav12123](https://github.com/Anubhav12123)
