from contextlib import nullcontext
from fastapi.testclient import TestClient
import pytest
import web.app as appmod
from web.comparativa import product_id, spec_key
from web.comparativa_specs import SpecStore
from web.login_rate_limit import LoginAttemptStore
from tests.test_comparativa import PHONE, OTHER, TABLET


@pytest.fixture
def setup_comparison(tmp_path, monkeypatch):
    monkeypatch.setenv('COMPARISON_AI_PROVIDER', 'anthropic')
    monkeypatch.setattr(appmod, '_catalogo_autorizado', lambda request: ([PHONE, OTHER, TABLET], 'public'))
    monkeypatch.setattr(appmod.app.state, 'comparison_store', SpecStore(tmp_path / 'spec.sqlite3'))
    monkeypatch.setattr(appmod.app.state, 'comparison_budget', LoginAttemptStore(tmp_path / 'limits.sqlite3'))
    monkeypatch.setattr(appmod.app.state, 'comparison_global_budget', LoginAttemptStore(tmp_path / 'global.sqlite3'))
    return {'a': product_id(PHONE['nombre']), 'b': product_id(OTHER['nombre']), 'product': product_id(PHONE['nombre'])}


def test_pair_api_excludes_private_and_rejects_cross_category(setup_comparison):
    with TestClient(appmod.app) as c:
        r = c.get('/api/comparativa', params=setup_comparison)
        assert r.status_code == 200
        assert 'costo' not in r.text and 'private' not in r.text
        r = c.get('/api/comparativa', params={**setup_comparison, 'b': product_id(TABLET['nombre'])})
        assert r.status_code == 400
        assert c.get('/comparativa').status_code == 200


def test_missing_provider_key_and_cross_site_are_safe(setup_comparison, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    with TestClient(appmod.app) as c:
        r = c.post('/api/comparativa/ficha', json=setup_comparison)
        assert r.status_code == 503
        assert 'ANTHROPIC' not in r.text
        assert c.post('/api/comparativa/ficha', json=setup_comparison, headers={'Origin': 'https://evil.example'}).status_code == 403
        assert c.post('/api/comparativa/ficha', json={**setup_comparison, 'product': product_id(TABLET['nombre'])}).status_code == 400


def test_generation_is_cached_and_private_data_never_leaves(setup_comparison, monkeypatch):
    import web.comparativa_routes as routes
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'fictitious')
    monkeypatch.setattr(appmod, '_comparison_client', lambda: nullcontext(object()))
    calls = []
    def research(product, client):
        calls.append(product)
        return {'model': product['nombre'], 'attributes': [], 'sources': [], 'fetched_at': 123}
    monkeypatch.setattr(routes, 'research', research)
    with TestClient(appmod.app) as c:
        for _ in range(2):
            r = c.post('/api/comparativa/ficha', json=setup_comparison)
            assert r.status_code == 200 and r.json()['status'] == 'ready'
    assert calls == [{'nombre': PHONE['nombre'], 'categoria': PHONE['categoria']}]


def test_failures_and_limits_do_not_expose_provider_errors(setup_comparison, monkeypatch):
    import web.comparativa_routes as routes
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'fictitious')
    monkeypatch.setattr(appmod, '_comparison_client', lambda: nullcontext(object()))
    def fail(*args):
        raise RuntimeError('private-api-key')
    monkeypatch.setattr(routes, 'research', fail)
    with TestClient(appmod.app) as c:
        r = c.post('/api/comparativa/ficha', json=setup_comparison)
        assert r.status_code == 503 and 'private-api-key' not in r.text
        assert c.post('/api/comparativa/ficha', json=setup_comparison).status_code == 202


def test_limits_are_enforced_without_calling_provider(setup_comparison, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'fictitious')
    monkeypatch.setattr(appmod.app.state.comparison_global_budget, 'reserve', lambda *args: False)
    monkeypatch.setattr(appmod, '_comparison_client', lambda: pytest.fail('Provider must not be called'))
    with TestClient(appmod.app) as c:
        assert c.post('/api/comparativa/ficha', json=setup_comparison).status_code == 429


def test_cached_sheets_work_without_provider_configuration(setup_comparison, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    store = appmod.app.state.comparison_store
    key = spec_key(PHONE)
    assert store.claim(key, 'test')
    store.save(key, 'test', {'model': PHONE['nombre'], 'attributes': [], 'sources': [], 'fetched_at': 123})
    with TestClient(appmod.app) as c:
        assert c.post('/api/comparativa/ficha', json=setup_comparison).json()['status'] == 'ready'
