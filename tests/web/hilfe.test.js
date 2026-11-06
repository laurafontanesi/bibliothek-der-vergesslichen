// Escaping and links (web/js/hilfe.js).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { esc, h, raw, html, safeUrl } from '../../web/js/hilfe.js';

test('esc escapes the five HTML characters', () => {
  assert.equal(esc(`<a href="x">'&'</a>`), '&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;');
  assert.equal(esc(null), '');
  assert.equal(esc(3), '3');
});

test('h escapes values, keeps markup made by h and raw', () => {
  const bad = '<img src=x onerror=alert(1)>';
  assert.equal(html(h`<b>${bad}</b>`), '<b>&lt;img src=x onerror=alert(1)&gt;</b>');
  assert.equal(html(h`<p>${h`<i>${'x'}</i>`}</p>`), '<p><i>x</i></p>');
  assert.equal(html(h`<p>${raw('<br>')}</p>`), '<p><br></p>');
  assert.equal(html(h`<ul>${['<a>', h`<li>b</li>`]}</ul>`), '<ul>&lt;a&gt;<li>b</li></ul>');
});

test('data cannot pass for markup', () => {
  // an object from JSON with a marker property, or with the shape of the Markup class
  for (const fake of [{ __raw: '<script>' }, { s: '<script>' }, JSON.parse('{"s":"<script>"}')])
    assert.ok(!html(h`${fake}`).includes('<script>'));
  assert.equal(html('<b>'), '&lt;b&gt;');
});

test('safeUrl keeps only https and links within the site', () => {
  assert.equal(safeUrl('https://www.dwds.de/wb/Tisch'), 'https://www.dwds.de/wb/Tisch');
  assert.equal(safeUrl('  HTTPS://example.org '), 'HTTPS://example.org');
  assert.equal(safeUrl('#wort/nehmen'), '#wort/nehmen');
  for (const u of ['javascript:alert(1)', ' JavaScript:alert(1)', 'data:text/html,<b>', 'http://example.org', '//example.org', '', null, undefined])
    assert.equal(safeUrl(u), '#', String(u));
});
