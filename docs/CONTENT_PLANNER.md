# Content Planner

Objective: manage a multi-week marketing plan from ideas to recorded publication,
connected to the existing generation pipeline and immutable content library.

## Delivery checklist

- [x] Transactional plan/task storage with optimistic concurrency and API auth.
- [x] Plan creation, editing, weekly cadence template and reversible task archival.
- [x] Board, monthly calendar, filters, progress and task editor.
- [x] Library attachment, review gates and publication URL tracking.
- [x] Explicit brief handoff to generation; no automatic paid calls.
- [x] CSV handoff and activity timeline.
- [x] Regression tests, frontend checks and browser walkthrough.

## Product rules

- Shared workspace, using the application's existing API-key access model.
- A scheduled date is a planning date, not an automatic social-media publishing job.
- Ready requires a linked snapshot whose AI review passed and is available.
- Marking a task published is a human record and requires a publication URL.
- Changes include a plan revision. Stale clients receive 409 instead of overwriting.
- Store data in outputs/planner.sqlite3 on the existing outputs volume.
- No external scheduler, social-media API, model call or new dependency is required.


## Using the feature

1. Open **Kế hoạch nội dung** in the sidebar, or `/plans`.
2. Create a plan with its brand label, objective and date range.
3. Add individual tasks or use **Dựng lịch mẫu** to fill selected weekdays and
   channels with editable ideas. Existing active date/channel slots are preserved.
4. Switch between board and calendar. Search matches titles, briefs and owners;
   channel filtering and the archived-task view work in both modes.
5. Open a task to edit its brief, owner, planned date or status. **Lưu và chuẩn bị
   brief AI** saves the task and opens the existing generation form with its brief.
   Select the real knowledge-base brand there; the plan's brand is a display label.
6. Review generated content, save a library snapshot, then attach the snapshot and
   a matching-channel piece to the task. Ready requires an available, passing review.
7. After publishing externally, record its HTTP(S) URL and mark the task published.
8. Export CSV for a handoff. Archived tasks stay recoverable and are excluded from CSV.

## Storage and concurrency

SQLite transactions persist each complete plan in `outputs/planner.sqlite3`.
No new package or manual schema setup is required. Every update supplies the last
observed plan revision; the database compares that revision during the write,
including when requests come from separate workers. A conflict returns 409 without
changing the stored plan. Close the editor, reload the latest plan using the refresh
button and review the changes before editing again.

Keep `/app/outputs` on persistent storage. Back up SQLite using its backup API or
while the server is stopped; copying a live database file is not a safe backup.
This is a shared-workspace application, not a tenant-isolated collaboration system.
There are no assignments to user accounts, outgoing notifications, automatic social
publishing or automatic paid AI calls. Owner names are organizational labels.

Plans support at most 500 tasks (including archived tasks), up to a 366-day period,
and retain the latest 100 activity entries. AI handoff is explicit and library
attachment is manual. The board uses accessible edit controls, not drag-and-drop.

## API

All routes use the existing API-key dependency:

- `GET/POST /api/plans`: list summaries / create a plan.
- `GET/PUT /api/plans/{id}`: get / update plan fields.
- `POST /api/plans/{id}/tasks`: add a task.
- `PUT /api/plans/{id}/tasks/{task_id}`: edit or archive/restore a task.
- `POST /api/plans/{id}/cadence`: create a weekday/channel cadence.
- `GET /api/plans/{id}/export`: UTF-8 CSV with formula-triggering cells neutralized.

## Validation completed

- Backend: 330 tests passed, including 22 planner cases (concurrent writes, review
  gates, publication transitions, archive/restore, validation, CSV and authentication).
- Frontend: 3 deterministic calendar/payload tests; lint and production build pass.
- Retrieval evaluation: 4/4 cases pass; no regression.
- Browser: plan creation, 24 ideas across two channels, library attachment,
  ready-to-published transition, progress, calendar and brief handoff verified.
- Mobile viewport: 390px layout checked; page itself has no horizontal overflow;
  the board/calendar scroll inside their own regions.
- Browser walkthroughs used temporary planner databases and synthetic content.
  No live model calls or social-media publication were performed.
