import test from 'node:test';
import assert from 'node:assert/strict';
import { dateKey, monthDays, taskPayload } from '../src/utils/planner.js';

test('calendar starts Monday and covers a leap month without duplicate dates', () => {
  const days = monthDays('2024-02');
  assert.equal(days[0], '2024-01-29');
  assert.equal(days.length, 42);
  assert.equal(new Set(days).size, 42);
  assert.ok(days.includes('2024-02-29'));
});

test('calendar handles year boundaries and local dates', () => {
  assert.equal(monthDays('2026-01')[0], '2025-12-29');
  assert.equal(dateKey(new Date(2026, 0, 1, 0, 5)), '2026-01-01');
});

test('task edits do not send server-owned IDs and timestamps', () => {
  const payload = taskPayload({ id: 'server-id', created_at: 'yesterday', title: 'Bài', archived: false });
  assert.equal(payload.title, 'Bài');
  assert.equal(payload.archived, false);
  assert.equal('id' in payload, false);
  assert.equal('created_at' in payload, false);
});
