"""Comparison contracts; only products in the current authorized catalog qualify."""
import hashlib
import ipaddress
import re
import time
from urllib.parse import urlsplit
from web.catalogo import seccion_de

FIELDS = {
    'Celulares': [('pantalla', 'Pantalla'), ('procesador', 'Procesador'), ('ram', 'Memoria RAM'), ('almacenamiento', 'Almacenamiento'), ('camaras', 'Cámaras'), ('bateria', 'Batería nominal'), ('carga', 'Carga'), ('conectividad', 'Conectividad'), ('sistema', 'Sistema operativo')],
    'Tablets': [('pantalla', 'Pantalla'), ('procesador', 'Procesador'), ('ram', 'Memoria RAM'), ('almacenamiento', 'Almacenamiento'), ('camaras', 'Cámaras'), ('bateria', 'Batería nominal'), ('carga', 'Carga'), ('conectividad', 'Conectividad'), ('sistema', 'Sistema operativo')],
    'Notebooks y Macbooks': [('pantalla', 'Pantalla'), ('procesador', 'Procesador'), ('graficos', 'Gráficos'), ('ram', 'Memoria RAM'), ('almacenamiento', 'Almacenamiento'), ('conectividad', 'Conexiones'), ('sistema', 'Sistema operativo')],
    'Gaming': [('tipo', 'Tipo de equipo'), ('compatibilidad', 'Compatibilidad'), ('procesador', 'Procesador'), ('graficos', 'Gráficos'), ('almacenamiento', 'Almacenamiento'), ('conectividad', 'Conexiones'), ('caracteristicas', 'Características')],
    'Accesorios Celulares': [('tipo', 'Tipo de accesorio'), ('compatibilidad', 'Compatibilidad'), ('conectividad', 'Conexiones'), ('bateria', 'Autonomía'), ('caracteristicas', 'Características')],
}


def product_id(nombre):
    return hashlib.sha256(nombre.encode('utf-8')).hexdigest()


def resolve_pair(productos, a, b):
    if a == b:
        raise ValueError('Elegí dos productos distintos.')
    resolved = [[p for p in productos if product_id(p['nombre']) == value] for value in (a, b)]
    if any(len(rows) != 1 for rows in resolved):
        raise ValueError('Uno de los productos ya no está disponible. Volvé al catálogo.')
    first, second = (rows[0] for rows in resolved)
    if seccion_de(first) != seccion_de(second):
        raise ValueError('Solo podés comparar productos de la misma categoría.')
    return first, second


def public_product(producto):
    result = {key: producto[key] for key in ('nombre', 'usd', 'pesos', 'transferencia', 'colores', 'marca') if key in producto}
    return {**result, 'id': product_id(producto['nombre']), 'seccion': seccion_de(producto)}


def spec_key(producto):
    # Keep model, capacity, region and all ambiguous qualifiers. Only condition is removed.
    name = re.sub(r'\b(?:usados?|usadas?|nuevo|nueva|cpo)\b', '', producto['nombre'], flags=re.I)
    name = re.sub(r'\(\s*\)', '', name)
    name = re.sub(r'\s+', ' ', name).strip().casefold()
    return hashlib.sha256(('v1:' + seccion_de(producto) + ':' + name).encode()).hexdigest()


def safe_source_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        url = urlsplit(value)
        host = (url.hostname or '').rstrip('.').lower()
        if url.port is not None and not 1 <= url.port <= 65535:
            return False
        if url.scheme not in ('http', 'https') or url.username or url.password or not host or '.' not in host or host == 'localhost':
            return False
        if host.endswith(('.local', '.localhost', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            # Browsers interpret IPv4 abbreviations/octal/hex as numeric hosts.
            if re.fullmatch(r'(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*', host):
                return False
            return bool(re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}', host))
    except ValueError:
        return False


def validate_sheet(payload, searched_urls, producto):
    if not isinstance(payload, dict) or payload.get('model') != producto['nombre']:
        raise ValueError('Modelo no confirmado')
    raw = payload.get('attributes')
    if not isinstance(raw, list) or not raw or len(raw) > 16:
        raise ValueError('Ficha incompleta')
    labels = dict(FIELDS[seccion_de(producto)])
    attributes, seen, urls = [], set(), set()
    for row in raw:
        if not isinstance(row, dict) or row.get('key') not in labels or row['key'] in seen:
            raise ValueError('Atributo inválido')
        value, sources = row.get('value'), row.get('source_urls')
        if not isinstance(value, str) or not value.strip() or len(value) > 600 or not isinstance(sources, list) or len(sources) > 5:
            raise ValueError('Atributo inválido')
        if value != 'No confirmado' and not sources:
            raise ValueError('Dato sin fuente')
        if any(not safe_source_url(url) or url not in searched_urls for url in sources):
            raise ValueError('Fuente no verificada')
        attributes.append({'key': row['key'], 'label': labels[row['key']], 'value': value, 'source_urls': list(dict.fromkeys(sources))})
        seen.add(row['key'])
        urls.update(sources)
    if not urls:
        raise ValueError('No hay fuentes verificadas')
    return {'model': producto['nombre'], 'attributes': attributes,
            'sources': [{'url': url, 'title': str(searched_urls[url])[:180]} for url in sorted(urls)], 'fetched_at': int(time.time())}
