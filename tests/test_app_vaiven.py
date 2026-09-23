from fastapi.testclient import TestClient
from web.app import app


def test_vaiven_unlocked_album_serves_the_six_attached_photos():
    with TestClient(app) as client:
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


def test_vaiven_rejects_direct_html_and_manual_routes():
    with TestClient(app) as client:
        client.post('/vaiven/acceso')
        for path in ['/vaiven', '/vaiven/', '/vaiven.html', '/vaiven?access=inventado', '/vaiven?access=gatito🐱']:
            response = client.get(path)
            assert response.status_code == 403
            assert '¡Tramposo! ¡Eso no se vale!' in response.text
            assert '/vaiven/vaiven-1.webp' not in response.text


def test_vaiven_access_is_single_use_and_bound_to_the_browser():
    with TestClient(app) as client, TestClient(app) as other:
        access = client.post('/vaiven/acceso').json()['access']
        assert other.get('/vaiven', params={'access': access}).status_code == 403
        assert client.get('/vaiven', params={'access': access}).status_code == 200
        assert client.get('/vaiven', params={'access': access}).status_code == 403
        assert client.get('/vaiven').status_code == 403
