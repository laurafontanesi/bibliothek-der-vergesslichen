// FSRS-6 (open-spaced-repetition), with its default parameters.
// Formulas as in the official Rust implementation (docs.rs/crate/fsrs, src/model.rs); default
// parameters as listed in the Anki SRS Kai documentation (kuroahna.github.io/anki_srs_kai). A card's
// memory is two numbers: stability S (days until recall drops to 90 %) and difficulty D (1 to 10).
// The state is never stored: it is computed again from the card's answers, so the answers are the
// only truth.
export const W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
  1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542];
export const RETENTION = 0.9;            // the share of cards still remembered when they come due

const DECAY = -W[20];
const FACTOR = Math.pow(0.9, 1 / DECAY) - 1;
const clampD = d => Math.min(10, Math.max(1, d));

export const recall = (days, s) => Math.pow(1 + FACTOR * days / s, DECAY);
export const interval = (s, r = RETENTION) => s / FACTOR * (Math.pow(r, 1 / DECAY) - 1);
const initS = g => W[g - 1];
const initD = g => W[4] - Math.exp(W[5] * (g - 1)) + 1;
function nextD(d, g) {
  const delta = -W[6] * (g - 3);
  const damped = d + delta * (10 - d) / 9;                 // linear damping near 10
  return clampD(W[7] * initD(4) + (1 - W[7]) * damped);    // mean reversion towards Easy
}
function sSuccess(d, s, r, g) {
  return s * (1 + Math.exp(W[8]) * (11 - d) * Math.pow(s, -W[9]) * (Math.exp(W[10] * (1 - r)) - 1)
    * (g === 2 ? W[15] : 1) * (g === 4 ? W[16] : 1));
}
function sFail(d, s, r) {
  const f = W[11] * Math.pow(d, -W[12]) * (Math.pow(s + 1, W[13]) - 1) * Math.exp(W[14] * (1 - r));
  return Math.min(f, s / Math.exp(W[17] * W[18]));
}
function sShort(s, g) {                                    // a second answer on the same day
  let inc = Math.exp(W[17] * (g - 3 + W[18])) * Math.pow(s, -W[19]);
  if (g >= 3) inc = Math.max(inc, 1);
  return s * inc;
}

// The day of a moment, with the day starting at 4 in the morning (an answer late at night counts for the day before)
export function day(ms) {
  const t = new Date(ms - 4 * 3600 * 1000);
  return Math.round(Date.UTC(t.getFullYear(), t.getMonth(), t.getDate()) / 86400000);
}

// One answer: grade 1 Again, 2 Hard, 3 Good, 4 Easy
export function step(st, g, ms) {
  if (!st) return { s: initS(g), d: clampD(initD(g)), last: ms, lastGrade: g, reps: 1, lapses: g === 1 ? 1 : 0 };
  const days = day(ms) - day(st.last);
  const s = days <= 0 ? sShort(st.s, g) : g === 1 ? sFail(st.d, st.s, recall(days, st.s)) : sSuccess(st.d, st.s, recall(days, st.s), g);
  return { s: Math.max(0.01, s), d: nextD(st.d, g), last: ms, lastGrade: g, reps: st.reps + 1, lapses: st.lapses + (g === 1 ? 1 : 0) };
}
export function replay(answers) {
  let st = null;
  for (const [ms, g] of answers) if (g >= 1 && g <= 4) st = step(st, g, ms);
  return st;
}
// When the card is due: a forgotten card again after 10 minutes, else after its interval in days
export function dueMs(st) {
  if (!st) return 0;
  if (st.lastGrade === 1) return st.last + 10 * 60 * 1000;
  const days = Math.min(36500, Math.max(1, Math.round(interval(st.s))));
  // 4 in the morning, local time, of the due day (also across a change to or from summer time)
  const u = new Date((day(st.last) + days) * 86400000);
  return new Date(u.getUTCFullYear(), u.getUTCMonth(), u.getUTCDate(), 4).getTime();
}
export function dueDays(st) {
  return st ? Math.min(36500, Math.max(1, Math.round(interval(st.s)))) : 0;
}
