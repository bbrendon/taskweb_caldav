from datetime import date, timedelta


def test_crud_and_versioning(authed):
    v0 = authed.get('/api/tasks').json()['version']
    r = authed.post('/api/tasks', json={'title': 'Buy milk', 'due': '2026-10-01', 'tags': ['home', 'Home']})
    assert r.status_code == 201
    t = r.json()
    assert t['due'] == '2026-10-01' and t['tags'] == ['home']
    assert 'PENDING' in t['virtual_tags'] and t['priority_band'] == 'none'

    listing = authed.get('/api/tasks').json()
    assert listing['version'] > v0 and [x['uid'] for x in listing['tasks']] == [t['uid']]
    assert authed.get(f"/api/tasks?since={listing['version']}").json()['unchanged'] is True

    u = authed.patch(f"/api/tasks/{t['uid']}", json={'priority': 1, 'starred': True}).json()
    assert u['priority_band'] == 'high' and 'STARRED' in u['virtual_tags'] and u['title'] == 'Buy milk'

    assert authed.delete(f"/api/tasks/{t['uid']}").json() == {'deleted': [t['uid']]}
    assert authed.patch(f"/api/tasks/{t['uid']}", json={'title': 'gone'}).status_code == 404


def test_validation(authed):
    assert authed.post('/api/tasks', json={'title': 'x', 'recur_after': 'monthly'}).status_code == 422
    assert authed.post('/api/tasks', json={'title': 'x', 'rrule': 'FREQ=SOMETIMES'}).status_code == 422
    assert authed.post('/api/tasks', json={'title': 'x', 'due': '2026-13-01'}).status_code == 422
    assert authed.post('/api/tasks', json={'title': 'x', 'uid': 'mine'}).status_code == 422
    assert authed.post('/api/tasks', json={'title': 'x', 'parent_uid': 'missing'}).status_code == 422
    r = authed.post('/api/tasks', json={'title': 'x', 'recur_after': 'P1D', 'rrule': 'FREQ=DAILY'})
    assert r.status_code == 422


def test_repeat_kinds_are_exclusive(authed):
    t = authed.post('/api/tasks', json={'title': 'x', 'rrule': 'FREQ=WEEKLY'}).json()
    u = authed.patch(f"/api/tasks/{t['uid']}", json={'recur_after': 'P10D'}).json()
    assert u['recur_after'] == 'P10D' and u['rrule'] is None


def test_no_parent_cycles(authed):
    a = authed.post('/api/tasks', json={'title': 'a'}).json()
    b = authed.post('/api/tasks', json={'title': 'b', 'parent_uid': a['uid']}).json()
    assert authed.patch(f"/api/tasks/{a['uid']}", json={'parent_uid': b['uid']}).status_code == 422
    assert authed.patch(f"/api/tasks/{a['uid']}", json={'parent_uid': a['uid']}).status_code == 422
    tasks = {t['uid']: t for t in authed.get('/api/tasks').json()['tasks']}
    assert 'HAS_SUBTASKS' in tasks[a['uid']]['virtual_tags']


def test_complete_recurring_and_skip(authed):
    t = authed.post('/api/tasks', json={'title': 'Filter', 'due': '2026-01-01', 'recur_after': 'P30D'}).json()
    r = authed.post(f"/api/tasks/{t['uid']}/complete").json()
    assert r['status'] == 'NEEDS-ACTION' and len(r['completions']) == 1
    assert date.fromisoformat(r['due']) >= date.today() + timedelta(days=29)
    s = authed.post(f"/api/tasks/{t['uid']}/skip").json()
    assert len(s['completions']) == 1
    plain = authed.post('/api/tasks', json={'title': 'p'}).json()
    assert authed.post(f"/api/tasks/{plain['uid']}/skip").status_code == 422
    done = authed.post(f"/api/tasks/{plain['uid']}/complete").json()
    assert done['status'] == 'COMPLETED'
    assert authed.post(f"/api/tasks/{plain['uid']}/reopen").json()['status'] == 'NEEDS-ACTION'


def test_location_and_alarm(authed):
    t = authed.post('/api/tasks', json={
        'title': 'Take out bins', 'location': 'Home',
        'location_alarm': {'title': 'Home', 'lat': 37.33, 'lon': -122.03, 'radius': 120, 'proximity': 'ARRIVE'},
        'alarms': [{'at': '2026-10-01T08:00:00-07:00'}],
    }).json()
    assert t['location_alarm']['proximity'] == 'ARRIVE' and t['alarms'] == [{'at': '2026-10-01T08:00:00-07:00'}]
    bad = {'title': 'x', 'location_alarm': {'lat': 99, 'lon': 0}}
    assert authed.post('/api/tasks', json=bad).status_code == 422


def test_delete_cascade(authed):
    p = authed.post('/api/tasks', json={'title': 'p'}).json()
    c = authed.post('/api/tasks', json={'title': 'c', 'parent_uid': p['uid']}).json()
    r = authed.delete(f"/api/tasks/{p['uid']}?children=delete").json()
    assert set(r['deleted']) == {p['uid'], c['uid']}


def test_config_and_settings(authed):
    cfg = authed.get('/api/config').json()
    assert cfg['timezone'] == 'America/Los_Angeles' and cfg['places'][0]['name'] == 'Home'
    assert cfg['priorities'] == {'none': 0, 'high': 1, 'medium': 5, 'low': 9}
    assert authed.get('/api/settings').json() == {}
    doc = {'saved_searches': [{'id': 's1', 'name': 'Errands', 'filter': {'match': 'all', 'conditions': []}}]}
    assert authed.put('/api/settings', json=doc).json() == doc
    assert authed.get('/api/settings').json() == doc


def test_spa_fallback_without_build(authed):
    r = authed.get('/some/client/route')
    assert r.status_code in (200, 404)
    assert authed.get('/api/nope').status_code in (401, 404)
