from .conftest import PASSWORD


def test_api_requires_login(client):
    assert client.get('/api/tasks').status_code == 401
    assert client.get('/api/session').json() == {'authenticated': False}
    assert client.get('/api/health').status_code == 200


def test_login_sets_httponly_cookie(client):
    r = client.post('/api/login', json={'password': PASSWORD})
    assert r.status_code == 200
    cookie = r.headers['set-cookie']
    assert 'tw_session=' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert 'Max-Age=15552000' in cookie
    assert client.get('/api/session').json() == {'authenticated': True}


def test_wrong_password(client):
    assert client.post('/api/login', json={'password': 'nope'}).status_code == 401


def test_rate_limit(client):
    codes = [client.post('/api/login', json={'password': 'nope'}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    # even the right password is refused while limited
    assert client.post('/api/login', json={'password': PASSWORD}).status_code == 429


def test_tampered_cookie_rejected(client):
    client.cookies.set('tw_session', 'user.forged.sig')
    assert client.get('/api/tasks').status_code == 401


def test_mutations_need_csrf_header(client):
    client.post('/api/login', json={'password': PASSWORD})
    assert client.post('/api/tasks', json={'title': 'x'}).status_code == 403
    r = client.post('/api/tasks', json={'title': 'x'}, headers={'X-Requested-With': 'taskweb'})
    assert r.status_code == 201


def test_logout(client):
    client.post('/api/login', json={'password': PASSWORD})
    client.post('/api/logout')
    assert client.get('/api/session').json() == {'authenticated': False}
