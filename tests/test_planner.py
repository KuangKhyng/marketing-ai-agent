from concurrent.futures import ThreadPoolExecutor
import csv
import io
from threading import Barrier

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from api.main import app
from api import planner
from api.routes import plans
from api.routes.library import Snapshot
from api.schemas import PipelineStatus


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(planner, "DB_PATH", tmp_path / "planner.sqlite3")
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.delenv("APP_API_KEY", raising=False)
    return TestClient(app)


@pytest.fixture
def plan(client):
    response = client.post('/api/plans', json={"title": "Kế hoạch tháng 9", "brand": "Cà phê",
        "objective": "Giới thiệu sản phẩm", "start_date": "2026-09-01", "end_date": "2026-09-28"})
    assert response.status_code == 201
    return response.json()


def add(client, plan, **fields):
    return client.post(f'/api/plans/{plan["id"]}/tasks', json={"revision": plan["revision"], "title": "Ý tưởng", **fields})


def edit(client, plan, **fields):
    task = plan['tasks'][0]
    payload = {key: value for key, value in task.items() if key not in ('id', 'created_at', 'updated_at')}
    return client.put(f'/api/plans/{plan["id"]}/tasks/{task["id"]}', json={**payload, "revision": plan["revision"], **fields})


def attach_review(monkeypatch, passed=True, unavailable=False):
    snapshot = Snapshot(id='a' * 64, title='Approved copy', saved_at='2026-09-01T00:00:00Z',
        campaign=PipelineStatus(run_id='source', phase='final_review',
            content={"pieces": [{"channel": "facebook", "body": "Bài đã duyệt"}]},
            review_result={"overall_passed": passed, "review_unavailable": unavailable}))
    monkeypatch.setattr(plans, 'get_snapshot', lambda _: snapshot)


def test_plan_persists_and_list_has_counts(client, plan):
    result = add(client, plan, due_date='2026-09-03', owner='Linh').json()
    assert result['revision'] == 2
    assert client.get(f'/api/plans/{plan["id"]}').json() == result
    summary = client.get('/api/plans').json()[0]
    assert summary['task_count'] == 1
    assert summary['published_count'] == 0
    assert 'tasks' not in summary
    assert planner.DB_PATH.exists()


def test_stale_tab_cannot_overwrite(client, plan):
    assert add(client, plan).status_code == 200
    assert add(client, plan, title='Stale').status_code == 409
    assert len(client.get(f'/api/plans/{plan["id"]}').json()['tasks']) == 1


def test_concurrent_process_style_cas_commits_only_one(client, plan):
    barrier = Barrier(2)
    def update(title):
        def operation(current):
            barrier.wait(timeout=5)
            current.title = title
        try:
            return planner.change(plan['id'], 1, operation).revision
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ['A', 'B']))
    assert sorted(results) == [2, 409]


@pytest.mark.parametrize('fields', [
    {'title': '   '}, {'channel': 'unknown'}, {'status': 'not-a-stage'},
    {'due_date': '2026-08-01'}, {'due_date': '2026-09-31'},
    {'snapshot_id': 'a' * 64}, {'piece_index': 0}, {'publication_url': 'javascript:alert(1)'},
])
def test_invalid_task_rejected_without_mutation(client, plan, fields):
    assert add(client, plan, **fields).status_code == 422
    assert client.get(f'/api/plans/{plan["id"]}').json()['revision'] == 1


def test_cadence_is_deterministic_deduplicated_and_preserves_existing(client, plan):
    updated = add(client, plan, title='Custom brief', due_date='2026-09-02').json()
    url = f'/api/plans/{plan["id"]}/cadence'
    first = client.post(url, json={"revision": updated['revision'], "channels": ['facebook'], "weekdays": [0, 2, 4]}).json()
    assert len(first['tasks']) == 12
    assert first['tasks'][0]['title'] == 'Custom brief'
    second = client.post(url, json={"revision": first['revision'], "channels": ['facebook'], "weekdays": [0, 2, 4]}).json()
    assert second['tasks'] == first['tasks']
    assert all(task['status'] == 'idea' for task in second['tasks'])


def test_cadence_validation(client, plan):
    url = f'/api/plans/{plan["id"]}/cadence'
    assert client.post(url, json={"revision": 1, "channels": []}).status_code == 422
    assert client.post(url, json={"revision": 1, "channels": ['facebook'], "weekdays": [7]}).status_code == 422


@pytest.mark.parametrize('passed,unavailable', [(False, False), (True, True)])
def test_review_gate_fails_closed(client, plan, monkeypatch, passed, unavailable):
    attach_review(monkeypatch, passed, unavailable)
    assert add(client, plan, snapshot_id='a' * 64, piece_index=0, status='ready').status_code == 422
    assert add(client, plan, status='ready').status_code == 422


def test_publication_requires_ready_content_and_url(client, plan, monkeypatch):
    attach_review(monkeypatch)
    assert add(client, plan, snapshot_id='a' * 64, piece_index=0, status='published', publication_url='https://example.com/post').status_code == 422
    ready = add(client, plan, snapshot_id='a' * 64, piece_index=0, status='ready').json()
    assert edit(client, ready, status='published').status_code == 422
    done = edit(client, ready, status='published', publication_url='https://example.com/post').json()
    assert done['tasks'][0]['status'] == 'published'
    assert client.get('/api/plans').json()[0]['published_count'] == 1
    assert edit(client, done, snapshot_id='b' * 64).status_code == 422


def test_link_validates_channel_piece_and_existence(client, plan, monkeypatch):
    attach_review(monkeypatch)
    assert add(client, plan, snapshot_id='a' * 64, piece_index=1).status_code == 422
    assert add(client, plan, snapshot_id='a' * 64, piece_index=0, channel='tiktok').status_code == 422
    def missing(_):
        raise HTTPException(404, 'missing')
    monkeypatch.setattr(plans, 'get_snapshot', missing)
    assert add(client, plan, snapshot_id='a' * 64, piece_index=0).status_code == 404


def test_archive_is_reversible_and_not_exported(client, plan):
    added = add(client, plan).json()
    archived = edit(client, added, archived=True).json()
    assert client.get('/api/plans').json()[0]['task_count'] == 0
    assert len(list(csv.reader(io.StringIO(client.get(f'/api/plans/{plan["id"]}/export').text.lstrip('\ufeff'))))) == 1
    restored = edit(client, archived, archived=False).json()
    assert restored['tasks'][0]['id'] == added['tasks'][0]['id']
    assert client.get('/api/plans').json()[0]['task_count'] == 1


def test_csv_preserves_vietnamese_and_neutralizes_formulas(client, plan):
    add(client, plan, title='=HYPERLINK("evil")', owner='@SUM(1)', brief='Cà phê,\nxuống dòng')
    response = client.get(f'/api/plans/{plan["id"]}/export')
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert rows[1][0].startswith("'=")
    assert rows[1][3].startswith("'@")
    assert rows[1][5] == 'Cà phê,\nxuống dòng'


def test_plan_date_edit_cannot_orphan_tasks(client, plan):
    updated = add(client, plan, due_date='2026-09-01').json()
    fields = {key: updated[key] for key in ('title', 'brand', 'objective', 'start_date', 'end_date', 'revision')}
    assert client.put(f'/api/plans/{plan["id"]}', json={**fields, 'start_date': '2026-09-02'}).status_code == 422
    assert client.put(f'/api/plans/{plan["id"]}', json={**fields, 'title': 'Tên mới'}).status_code == 200


def test_api_auth_and_missing_plan(client, monkeypatch):
    assert client.get('/api/plans/missing').status_code == 404
    monkeypatch.setenv('APP_API_KEY', 'planner-test-key')
    assert client.get('/api/plans').status_code == 401
    assert client.get('/api/plans/missing/export').status_code == 401
    assert client.post('/api/plans', json={}).status_code == 401


def test_disk_unavailable_reports_503(client, monkeypatch, tmp_path):
    file = tmp_path / 'not-a-directory'
    file.write_text('x')
    monkeypatch.setattr(planner, 'DB_PATH', file / 'planner.sqlite3')
    assert client.get('/api/plans').status_code == 503
