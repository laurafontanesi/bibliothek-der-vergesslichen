// The scheduler (web/js/fsrs.js): FSRS-6 with its default parameters, days starting at 4 in the
// morning. Times are tested in Berlin, also across the change to summer time.
process.env.TZ = 'Europe/Berlin';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { W, recall, interval, step, replay, day, dueMs, dueDays } from '../../web/js/fsrs.js';

const close = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} is not ${b}`);
const at = s => new Date(s).getTime();          // local time (no Z): Berlin
const D = 86400000;

test('stability is the time until recall drops to 90 %', () => {
  for (const s of [0.5, 2.3, 10, 400]) { close(recall(s, s), 0.9); close(interval(s), s); }
  close(recall(0, 5), 1);
  assert.ok(interval(10, 0.95) < 10 && interval(10, 0.8) > 10);
});

test('the first answer sets stability and difficulty from the parameters', () => {
  for (const g of [1, 2, 3, 4]) close(step(null, g, 0).s, W[g - 1]);
  close(step(null, 1, 0).d, W[4]);                                  // 6.4133
  close(step(null, 3, 0).d, W[4] - Math.exp(W[5] * 2) + 1);         // about 2.12
  assert.equal(step(null, 1, 0).lapses, 1);
  assert.equal(step(null, 3, 0).lapses, 0);
});

test('a later answer: Again lowers stability, Hard < Good < Easy', () => {
  const t0 = at('2030-11-02T10:00'), st = step(null, 3, t0), later = t0 + 3 * D;
  const [again, hard, good, easy] = [1, 2, 3, 4].map(g => step(st, g, later));
  assert.ok(again.s < st.s);
  assert.ok(st.s < hard.s && hard.s < good.s && good.s < easy.s);
  assert.equal(again.lapses, 1);
  assert.equal(good.reps, 2);
  assert.ok(again.d > st.d && easy.d < st.d);
});

test('difficulty stays between 1 and 10, stability stays positive', () => {
  for (const g of [1, 4]) {
    let st = null;
    for (let i = 0; i < 60; i++) st = step(st, g, at('2030-01-01T10:00') + i * 2 * D);
    assert.ok(st.d >= 1 && st.d <= 10 && st.s > 0, JSON.stringify(st));
  }
});

test('a second Good on the same day does not lower stability', () => {
  const t0 = at('2030-11-02T09:00'), st = step(null, 3, t0);
  assert.ok(step(st, 3, t0 + 3600e3).s >= st.s);
  assert.ok(step(st, 1, t0 + 3600e3).s < st.s);
});

test('replay skips grades outside 1 to 4', () => {
  const t0 = at('2030-11-02T09:00');
  assert.deepEqual(replay([[t0, 3], [t0 + D, 0], [t0 + 2 * D, 5]]), replay([[t0, 3]]));
  assert.equal(replay([]), null);
});

test('the day starts at 4 in the morning', () => {
  assert.equal(day(at('2030-11-06T03:59')), day(at('2030-11-05T12:00')));
  assert.equal(day(at('2030-11-06T04:00')), day(at('2030-11-05T12:00')) + 1);
  assert.equal(day(at('2030-03-31T12:00')) - day(at('2030-03-30T12:00')), 1);   // the 23-hour day
});

test('due at 4 in the morning local time, also across summer time; Again after 10 minutes', () => {
  const t0 = at('2030-11-02T18:30'), st = step(null, 3, t0);
  assert.equal(dueDays(st), 2);
  assert.equal(dueMs(st), at('2030-11-04T04:00'));
  const spring = step(null, 3, at('2030-03-30T12:00'));                       // CET, due in CEST
  assert.equal(dueMs(spring), at('2030-04-01T04:00'));
  const autumn = step(null, 3, at('2030-10-26T12:00'));                       // CEST, due in CET
  assert.equal(dueMs(autumn), at('2030-10-28T04:00'));
  const again = step(null, 1, t0);
  assert.equal(dueMs(again), t0 + 10 * 60e3);
  assert.equal(dueMs(null), 0);
  assert.equal(dueDays(null), 0);
});
