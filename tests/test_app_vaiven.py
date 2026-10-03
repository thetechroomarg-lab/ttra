import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _logueado(monkeypatch, celular="3511234567", email="juan@x.com"):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    client = TestClient(appmod.app, base_url="https://testserver")
    r = client.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": celular,
        "email": email, "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    assert r.status_code == 200
    return client


def test_vaiven_unlocked_album_serves_the_six_attached_photos(monkeypatch):
    client = _logueado(monkeypatch)
    access = client.post('/vaiven/acceso').json()['access']
    response = client.get('/vaiven', params={'access': access})
    assert response.status_code == 200
    assert 'Hola,' in response.text and 'Vaivén' in response.text
    assert 'mi papi Vlad y mi mami' in response.text
    assert 'Volver a la Tienda' in response.text
    assert response.text.count('<img ') == 6
    assert '<header' not in response.text
    assert '/site-header.js' not in response.text
    assert 'id="vaiven-mascot"' in response.text
    for number in range(1, 7):
        photo = client.get(f'/vaiven/vaiven-{number}.webp')
        assert photo.status_code == 200
        assert photo.headers['content-type'] == 'image/webp'
        assert len(photo.content) > 10000


def test_vaiven_rejects_direct_html_and_manual_routes(monkeypatch):
    client = _logueado(monkeypatch)
    client.post('/vaiven/acceso')
    for path in ['/vaiven', '/vaiven/', '/vaiven.html', '/vaiven?access=inventado', '/vaiven?access=gatito🐱']:
        response = client.get(path)
        assert response.status_code == 403
        assert '¡Tramposo! ¡Eso no se vale!' in response.text
        assert '/vaiven/vaiven-1.webp' not in response.text


def test_vaiven_access_is_single_use_and_bound_to_the_browser(monkeypatch):
    client = _logueado(monkeypatch)
    other = TestClient(appmod.app, base_url="https://testserver")
    access = client.post('/vaiven/acceso').json()['access']
    assert other.get('/vaiven', params={'access': access}).status_code == 403
    assert client.get('/vaiven', params={'access': access}).status_code == 200
    assert client.get('/vaiven', params={'access': access}).status_code == 403
    assert client.get('/vaiven').status_code == 403


@pytest.mark.parametrize("gato", ["vaiven", "bitu", "fendi"])
def test_album_access_requires_a_logged_in_client(gato):
    guest = TestClient(appmod.app, base_url="https://testserver")
    r = guest.post(f'/{gato}/acceso')
    assert r.status_code == 401
    assert 'access' not in r.json()


@pytest.mark.parametrize("gato", ["vaiven", "bitu", "fendi"])
def test_album_access_is_lost_after_logout(monkeypatch, gato):
    client = _logueado(monkeypatch)
    access = client.post(f'/{gato}/acceso').json()['access']
    client.post('/logout')
    assert client.get(f'/{gato}', params={'access': access}).status_code == 403


@pytest.mark.parametrize("gato", ["bitu", "fendi"])
def test_companion_albums_open_for_logged_in_clients(monkeypatch, gato):
    client = _logueado(monkeypatch)
    access = client.post(f'/{gato}/acceso').json()['access']
    response = client.get(f'/{gato}', params={'access': access})
    assert response.status_code == 200
    assert response.text.count('<img ') == 6
    for number in range(1, 7):
        assert client.get(f'/{gato}/{gato}-{number}.webp').status_code == 200
