"""Exercise storefront/admin data flow without touching real customers or orders."""
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_catalogo_registro_pedido_y_administracion_conectados(tmp_path, monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, 'get_client', lambda: fake)
    monkeypatch.setattr(appmod, 'ADMIN_TOKEN', 'integration-token')
    monkeypatch.setattr(appmod, 'ADMIN_CLIENTES_PASSWORD', 'integration-password')
    monkeypatch.setattr(appmod, 'PRODUCTOS_PATH', tmp_path / 'productos.json')
    monkeypatch.setattr(appmod, 'COSTOS_PATH', tmp_path / 'costos.json')
    monkeypatch.setattr(appmod, 'CATALOGO_MANIFEST_PATH', tmp_path / 'catalogo-manifest.json')
    monkeypatch.setattr(appmod.entregas, 'ahora_argentina', lambda: datetime(
        2026, 9, 22, 10, tzinfo=ZoneInfo('America/Argentina/Cordoba')))
    customer = TestClient(appmod.app, base_url='https://testserver')
    admin = TestClient(appmod.app, base_url='https://testserver')
    product = {'nombre': 'Teléfono integración', 'categoria': 'Apple - iPhone',
               'usd': 180, 'pesos': 270000, 'transferencia': 280000, 'colores': ['Negro']}
    assert admin.post('/admin/productos', json=[product], headers={'X-Admin-Token': 'integration-token'}).status_code == 200
    catalog = customer.get('/api/catalogo').json()['secciones']['Celulares']
    assert catalog[0]['nombre'] == product['nombre']
    assert catalog[0]['usd'] == 180
    anon_headers = {'X-TTRA-ANON-ID': 'catalog-integration-visitor'}
    assert customer.post('/api/interacciones', headers=anon_headers, json={
        'tipo_evento': 'view_item', 'producto_nombre': product['nombre'],
    }).status_code == 200
    assert customer.post('/registro', headers=anon_headers, json={
        'nombre': 'Integración', 'apellido': 'Verificada', 'celular': '3510000000',
        'email': 'integracion@example.com', 'password': 'test-password',
        'provincia': 'Córdoba', 'direccion': 'Av. Colón 123, Córdoba',
    }).status_code == 200
    assert customer.get('/api/me').status_code == 200
    client_id = fake.table('clientes').select('*').execute().data[0]['id']
    assert fake.table('interacciones_cliente').select('*').execute().data[0]['cliente_id'] == client_id
    payload = {
        'productos': ['Teléfono integración (Negro)'], 'fecha_entrega': '2026-09-22',
        'direccion_entrega': 'Av. Colón 123, Córdoba',
        'detalle': [{'nombre': product['nombre'], 'color': 'Negro', 'cantidad': 1,
                     'usd_unitario': 180, 'usd_subtotal': 180}], 'total_usd': 180,
    }
    response = customer.post('/api/pedidos', json=payload)
    assert response.status_code == 200, response.text
    order = fake.table('pedidos').select('*').execute().data[0]
    assert order['total_usd'] == 180
    assert customer.put(f"/admin/pedidos/{order['id']}/fecha-entrega", json={'fecha_entrega': '2026-09-23'}).status_code == 401
    assert admin.post('/admin/clientes/login', json={'password': 'integration-password'}).status_code == 200
    panel = admin.get('/admin/clientes')
    assert panel.status_code == 200
    assert order['id'] in panel.text and 'Teléfono integración' in panel.text
    clients = admin.get('/admin/clientes/lista')
    assert clients.status_code == 200 and 'Integración Verificada' in clients.text
    history = admin.get(f'/admin/clientes/{client_id}/historial')
    assert history.status_code == 200
    assert 'data-campaign-source="vista"' in history.text and 'Teléfono integración' in history.text
    assert admin.put(f"/admin/pedidos/{order['id']}/fecha-entrega", json={'fecha_entrega': '2026-09-23'}).status_code == 200
    assert fake.table('pedidos').select('*').execute().data[0]['fecha_entrega'] == '2026-09-23'
    # A changed admin price reaches the public catalog; an old cart is rejected.
    product['usd'] = 220
    assert admin.post('/admin/productos', json=[product], headers={'X-Admin-Token': 'integration-token'}).status_code == 200
    assert customer.get('/api/catalogo').json()['secciones']['Celulares'][0]['usd'] == 220
    assert customer.post('/api/pedidos', json=payload).status_code == 409
    assert len(fake.table('pedidos').select('*').execute().data) == 1
