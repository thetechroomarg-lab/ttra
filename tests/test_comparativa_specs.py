import json
from types import SimpleNamespace
import pytest
from web.comparativa_specs import SpecStore, research
from tests.test_comparativa import PHONE


def test_persistent_cache_lease_and_expiry(tmp_path):
    path = tmp_path / 'specs.sqlite3'
    a, b = SpecStore(path), SpecStore(path)
    assert a.claim('phone', 'a', now=100)
    assert not b.claim('phone', 'b', now=101)
    assert b.claim('phone', 'b', now=221)
    assert not a.save('phone', 'a', {'data': 'stale'}, now=222)
    assert b.save('phone', 'b', {'data': 'fresh'}, now=223)
    assert a.get('phone', now=224) == {'data': 'fresh'}
    # TTL prácticamente permanente (un modelo lanzado no cambia de specs):
    # sigue disponible mucho después de lo que antes era el vencimiento a 30 días.
    assert b.get('phone', now=223 + 31 * 86400) == {'data': 'fresh'}


def test_global_concurrency_and_failure_backoff(tmp_path):
    store = SpecStore(tmp_path / 'specs.sqlite3')
    assert store.claim('one', 'a', now=100)
    assert store.claim('two', 'b', now=100)
    assert not store.claim('three', 'c', now=100)
    store.fail('one', 'a', now=101)
    assert not store.claim('one', 'd', now=102)
    assert store.claim('three', 'c', now=102)


def test_research_accepts_only_sources_returned_by_search_and_sends_no_private_fields():
    url = 'https://www.apple.com/iphone/specs/'
    payload = {'model': PHONE['nombre'], 'attributes': [{'key': 'pantalla', 'value': 'OLED', 'source_urls': [url]}]}
    calls = []
    class Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(stop_reason='end_turn', content=[
                SimpleNamespace(type='web_search_tool_result', content=[SimpleNamespace(type='web_search_result', url=url, title='Apple')]),
                SimpleNamespace(type='text', text=json.dumps(payload))])
    research(PHONE, SimpleNamespace(messages=Messages()))
    sent = json.dumps(calls)
    assert 'private' not in sent and 'costo' not in sent and 'proveedor' not in sent
    payload['attributes'][0]['source_urls'] = ['https://invented.example/spec']
    with pytest.raises(ValueError):
        research(PHONE, SimpleNamespace(messages=Messages()))


def test_incomplete_provider_response_is_never_cached_or_resumed():
    class Messages:
        def create(self, **kwargs):
            return SimpleNamespace(stop_reason='pause_turn', content=[])
    with pytest.raises(ValueError, match='incompleta'):
        research(PHONE, SimpleNamespace(messages=Messages()))


def test_provider_timeout_bubbles_to_safe_route_handler():
    class Messages:
        def create(self, **kwargs):
            raise TimeoutError('internal detail')
    with pytest.raises(TimeoutError):
        research(PHONE, SimpleNamespace(messages=Messages()))
