import pytest
from web.comparativa import product_id, resolve_pair, public_product, spec_key, validate_sheet

PHONE = {'nombre': 'iPhone 13 128GB (Usado)', 'categoria': 'Apple - iPhone Usado', 'usd': 500, 'costo': 400, 'proveedor': 'private'}
OTHER = {'nombre': 'Samsung Galaxy S24 256GB', 'categoria': 'Samsung'}
TABLET = {'nombre': 'iPad Pro 256GB', 'categoria': 'Apple - iPad'}


def test_pair_enforces_catalog_identity_and_section():
    assert resolve_pair([PHONE, OTHER], product_id(PHONE['nombre']), product_id(OTHER['nombre'])) == (PHONE, OTHER)
    for a, b in [(PHONE, TABLET), (PHONE, PHONE)]:
        with pytest.raises(ValueError):
            resolve_pair([PHONE, OTHER, TABLET], product_id(a['nombre']), product_id(b['nombre']))
    with pytest.raises(ValueError):
        resolve_pair([PHONE], 'missing', 'unknown')
    with pytest.raises(ValueError):
        resolve_pair([PHONE, PHONE, OTHER], product_id(PHONE['nombre']), product_id(OTHER['nombre']))


def test_public_projection_and_configuration_keys():
    assert 'costo' not in public_product(PHONE) and 'proveedor' not in public_product(PHONE)
    assert spec_key(PHONE) == spec_key({**PHONE, 'nombre': 'IPHONE 13 128GB'})
    for name in ['iPhone 13 Pro 128GB', 'iPhone 13 256GB', 'iPhone 14 128GB']:
        assert spec_key(PHONE) != spec_key({**PHONE, 'nombre': name})


def test_facts_require_real_search_sources():
    url = 'https://www.apple.com/iphone/specs/'
    data = {'model': PHONE['nombre'], 'attributes': [{'key': 'pantalla', 'value': 'OLED', 'source_urls': [url]}]}
    result = validate_sheet(data, {url: 'Apple'}, PHONE)
    assert result['attributes'][0]['value'] == 'OLED'
    assert result['sources'] == [{'url': url, 'title': 'Apple'}]
    for bad in ['javascript:alert(1)', 'https://invented.example/spec', 'http://localhost/private']:
        with pytest.raises(ValueError):
            validate_sheet({**data, 'attributes': [{'key': 'pantalla', 'value': 'OLED', 'source_urls': [bad]}]}, {url: 'Apple'}, PHONE)
    with pytest.raises(ValueError):
        validate_sheet({**data, 'model': 'different model'}, {url: 'Apple'}, PHONE)



def test_model_echo_ignores_case_and_spacing_only():
    # El modelo suele devolver el nombre con otra capitalización ("5g" -> "5G");
    # eso no es otro modelo, pero un número o calificador distinto sí lo es.
    moto = {'nombre': 'MOTO Edge 70 FUSION 5g 256/8gb', 'categoria': 'Motorola'}
    url = 'https://www.motorola.com/specs'
    data = {'model': 'MOTO Edge 70  FUSION 5G 256/8GB', 'attributes': [{'key': 'pantalla', 'value': 'pOLED', 'source_urls': [url]}]}
    assert validate_sheet(data, {url: 'Motorola'}, moto)['model'] == moto['nombre']
    for other in ['MOTO Edge 60 FUSION 5g 256/8gb', 'MOTO Edge 70 FUSION 5g 512/8gb', 'MOTO Edge 70 5g 256/8gb']:
        with pytest.raises(ValueError):
            validate_sheet({**data, 'model': other}, {url: 'Motorola'}, moto)

def test_source_links_reject_browser_normalized_local_hosts():
    from web.comparativa import safe_source_url
    for url in ['http://127.1/private', 'http://0x7f.0.0.1/private', 'https://localhost./private', 'https://foo.local./private', 'https://example.com:99999/specs']:
        assert not safe_source_url(url)
    assert safe_source_url('https://support.apple.com/specs')
