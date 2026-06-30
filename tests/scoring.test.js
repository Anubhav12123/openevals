// OpenEvals — scoring unit tests
// Run with: node tests/scoring.test.js

// ── Inline the scoring logic (mirrors content.js) ────────────────────────────

const HIGH_RISK = [
  /i('m| am) not (sure|certain|aware)/g,
  /i (think|believe|suppose|guess)\b/g,
  /it('s| is) (possible|likely) that/g,
  /\bmight\b/g, /\bcould be\b/g, /i may be wrong/g,
  /if i recall correctly/g, /to (my|the best of my) knowledge/g,
  /as far as i know/g, /i cannot (verify|confirm|guarantee)/g,
  /my (knowledge|training) (cutoff|data)/g, /i don't have (access|information)/g,
  /\buncertain\b/g, /\bpossibly\b/g, /\bperhaps\b/g, /\bprobably\b/g,
  /\bi'd (guess|say|estimate)\b/g, /\bspeculat/g, /\bhypothet/g,
];

const MED_RISK = [
  /\bapproximately\b/g, /\baround \d/g, /\broughly\b/g,
  /\bseems?\b/g, /\bappears?\b/g, /\bgenerally\b/g,
  /\btypically\b/g, /\busually\b/g, /\boften\b/g,
  /\bmay\b/g, /\bsomewhat\b/g, /\blikely\b/g, /\bpotentially\b/g,
];

const CONFIDENT = [
  /according to (studies|research|data|reports)/g,
  /research (shows|indicates|demonstrates|confirms)/g,
  /it (is|was|has been) (proven|established|confirmed)/g,
  /\bdefinitely\b/g, /\bcertainly\b/g, /\bconfirmed\b/g, /\bproven\b/g,
];

function scoreHallucination(text) {
  const lower = text.toLowerCase();
  let risk = 0.10;
  HIGH_RISK.forEach(p => { const m = lower.match(p); if (m) risk += m.length * 0.15; });
  MED_RISK.forEach(p => { const m = lower.match(p); if (m) risk += m.length * 0.06; });
  CONFIDENT.forEach(p => { const m = lower.match(p); if (m) risk -= m.length * 0.05; });
  risk = Math.max(0, Math.min(1, risk));
  const level = risk >= 0.35 ? 'high' : risk >= 0.20 ? 'medium' : 'low';
  return { level, pct: Math.round(risk * 100) };
}

// ── Test runner ───────────────────────────────────────────────────────────────

let passed = 0, failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.log(`  ✗ ${name}`);
    console.log(`    ${e.message}`);
    failed++;
  }
}

function expect(actual) {
  return {
    toBe(expected) {
      if (actual !== expected) throw new Error(`Expected "${expected}" but got "${actual}"`);
    },
    toBeGreaterThan(n) {
      if (actual <= n) throw new Error(`Expected ${actual} > ${n}`);
    },
    toBeLessThan(n) {
      if (actual >= n) throw new Error(`Expected ${actual} < ${n}`);
    },
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

console.log('\nOpenEvals — Hallucination Scoring Tests\n');

test('confident factual response scores LOW', () => {
  const { level } = scoreHallucination(
    'The Eiffel Tower is 330 metres tall. It was completed in 1889. Research confirms it is the tallest structure in Paris.'
  );
  expect(level).toBe('low');
});

test('hedged response with "I think" scores MEDIUM or HIGH', () => {
  const { level } = scoreHallucination(
    'I think the answer might be around 42, but I am not entirely certain about the exact figure.'
  );
  expect(level !== 'low').toBe(true);
});

test('highly uncertain response scores HIGH', () => {
  const { level } = scoreHallucination(
    'I\'m not sure about this. I think it might possibly be the case, but I cannot verify it. Perhaps it could be true, but I may be wrong. As far as I know, this is speculative.'
  );
  expect(level).toBe('high');
});

test('response with "probably" and "might" scores above 20%', () => {
  const { pct } = scoreHallucination(
    'This will probably work, and it might be the best approach, though it could be different.'
  );
  expect(pct).toBeGreaterThan(20);
});

test('confident signals reduce score', () => {
  const withConfidence = scoreHallucination('Research confirms this is definitely proven and confirmed by studies.');
  const withoutConfidence = scoreHallucination('This might possibly be the case perhaps.');
  expect(withoutConfidence.pct).toBeGreaterThan(withConfidence.pct);
});

test('baseline score is above 0 for any text', () => {
  const { pct } = scoreHallucination('The sky is blue.');
  expect(pct).toBeGreaterThan(0);
});

test('score never exceeds 100', () => {
  const { pct } = scoreHallucination(
    'I think I believe I might possibly perhaps probably guess estimate speculate hypothetically I\'m not sure I cannot verify I may be wrong as far as I know I don\'t have information'
  );
  expect(pct).toBeLessThan(101);
});

test('score never goes below 0', () => {
  const { pct } = scoreHallucination(
    'Research definitely confirms this is proven. Studies show it is established. Certainly confirmed.'
  );
  expect(pct).toBeGreaterThan(-1);
});

test('short text still returns a result', () => {
  const { level, pct } = scoreHallucination('Maybe.');
  expect(typeof level).toBe('string');
  expect(typeof pct).toBe('number');
});

test('level is always one of low/medium/high', () => {
  const texts = ['definitely true', 'I think maybe', 'I have no idea possibly perhaps might'];
  texts.forEach(t => {
    const { level } = scoreHallucination(t);
    expect(['low','medium','high'].includes(level)).toBe(true);
  });
});

// ── Summary ───────────────────────────────────────────────────────────────────

console.log(`\n${passed + failed} tests — ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
