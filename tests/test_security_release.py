"""Regression checks for the September security audit (fictitious data only)."""
from fastapi.testclient import TestClient
import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_shipping_document_is_not_public():
    with TestClient(appmod.app, base_url='https://testserver') as c:
        assert c.get('/ciudad/paquetes_18_08_2026.pdf').status_code == 404


def test_registration_cannot_claim_unverified_existing_phone(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, 'get_client', lambda: fake)
    original = {'id': 'previous-client', 'auth_id': None, 'nombre': 'Original',
                'apellido': 'Cliente', 'celular': '3510000000', 'email': 'original@example.com'}
    fake.table('clientes').insert(original.copy()).execute()
    fake.table('domicilios_cliente').insert({'id': 'private-address', 'cliente_id': 'previous-client',
                                            'direccion': 'Domicilio ficticio privado'}).execute()
    with TestClient(appmod.app, base_url='https://testserver') as c:
        r = c.post('/registro', json={'nombre': 'Otra', 'apellido': 'Persona', 'celular': '3510000000',
                                     'email': 'other@example.com', 'password': 'test-password',
                                     'provincia': 'Córdoba', 'direccion': 'Otro domicilio 123'})
        assert r.status_code == 400
        assert c.get('/api/me').status_code == 401
        assert c.get('/api/domicilios').status_code == 401
    row = fake.table('clientes').select('*').eq('id', 'previous-client').execute().data[0]
    assert row['auth_id'] is None and row['email'] == original['email']


def test_forwarded_header_cannot_reset_admin_login_limit(monkeypatch):
    monkeypatch.setattr(appmod, 'ADMIN_CLIENTES_PASSWORD', 'test-admin-password')
    appmod._intentos_login_fallidos.clear()
    with TestClient(appmod.app, base_url='https://testserver') as c:
        for i in range(appmod._LOGIN_MAX_INTENTOS):
            assert c.post('/admin/clientes/login', json={'password': 'wrong'},
                          headers={'X-Forwarded-For': f'192.0.2.{i}'}).status_code == 401
        assert c.post('/admin/clientes/login', json={'password': 'wrong'},
                      headers={'X-Forwarded-For': '198.51.100.99'}).status_code == 429


def test_private_responses_and_safe_frame_policy(monkeypatch):
    monkeypatch.setattr(appmod, 'get_client', lambda: FakeSupabaseClient())
    with TestClient(appmod.app, base_url='https://testserver') as c:
        for path in ['/api/me', '/api/domicilios', '/admin/cadete', '/login']:
            r = c.get(path)
            assert 'no-store' in r.headers.get('cache-control', '')
            assert r.headers['x-content-type-options'] == 'nosniff'
            assert r.headers['x-frame-options'] == 'SAMEORIGIN'
            assert "frame-ancestors 'self'" in r.headers['content-security-policy']
            assert r.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
            assert 'max-age=' in r.headers['strict-transport-security']


def test_private_files_are_blocked_even_if_copied_to_static(tmp_path):
    from fastapi import FastAPI
    from web.public_static import PublicStaticFiles
    for name in ['receipt.pdf', 'backup.csv', 'data.sqlite3', '.env', 'certificate.pem', 'public.css']:
        (tmp_path / name).write_text('fictitious content')
    app = FastAPI()
    app.mount('/', PublicStaticFiles(directory=tmp_path))
    with TestClient(app) as c:
        for name in ['receipt.pdf', 'backup.csv', 'data.sqlite3', '.env', 'certificate.pem']:
            assert c.get('/' + name).status_code == 404
        assert c.get('/public.css').status_code == 200


def test_login_budget_survives_new_store_and_is_shared(tmp_path):
    from web.login_rate_limit import LoginAttemptStore
    first = LoginAttemptStore(tmp_path / 'shared.sqlite3')
    second = LoginAttemptStore(tmp_path / 'shared.sqlite3')
    key = ('peer', 'admin')
    assert first.reserve(key, 2, 900)
    assert second.reserve(key, 2, 900)
    assert not first.reserve(key, 2, 900)
    assert not LoginAttemptStore(tmp_path / 'shared.sqlite3').reserve(key, 2, 900)
    second.pop(key)
    assert first.reserve(key, 2, 900)


def test_cadete_password_rotation_invalidates_existing_sessions(monkeypatch):
    monkeypatch.setattr(appmod, 'get_client', lambda: FakeSupabaseClient())
    monkeypatch.setattr(appmod, 'CADETE_PASSWORD', 'old-fictitious-password')
    monkeypatch.setenv('CADETE_PASSWORD', 'old-fictitious-password')
    with TestClient(appmod.app, base_url='https://testserver') as c:
        assert c.post('/admin/cadete/login', json={'password': 'old-fictitious-password'}).status_code == 200
        monkeypatch.setattr(appmod, 'CADETE_PASSWORD', 'new-fictitious-password')
        monkeypatch.setenv('CADETE_PASSWORD', 'new-fictitious-password')
        assert 'type="password"' in c.get('/admin/cadete').text
        assert c.post('/admin/tareas-entrega/missing/completar').status_code == 401
        assert c.post('/admin/cadete/login', json={'password': 'new-fictitious-password'}).status_code == 200
        assert 'type="password"' not in c.get('/admin/cadete').text


def test_https_redirects_without_trusting_forwarded_headers(monkeypatch):
    from starlette.requests import Request
    from starlette.responses import RedirectResponse
    from starlette.routing import Route

    async def redirect_to_self(request: Request):
        return RedirectResponse(str(request.url))

    monkeypatch.setattr(appmod, '_session_https_only', True)
    monkeypatch.setattr(appmod.app.router, 'routes', [
        Route('/security-test-scheme', redirect_to_self),
        *appmod.app.router.routes,
    ])
    with TestClient(appmod.app, base_url='http://testserver', follow_redirects=False) as c:
        r = c.get('/security-test-scheme')
        assert r.status_code == 307
        assert r.headers['location'] == 'https://testserver/security-test-scheme'
