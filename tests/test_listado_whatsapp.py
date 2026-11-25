"""LISTADO WHATSAPP: sección exclusiva para mayoristas.

Los datos y el acceso se prueban contra la app; el formato del texto corre en el
navegador, así que se prueba con node si está instalado.
"""
import json
import shutil
import subprocess
import textwrap

import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from web import listado_whatsapp

RUTA_JS = appmod.BASE / "static" / "listado-whatsapp.js"
node = shutil.which("node")


# ---------- Datos ----------

def _prod(nombre, categoria, usd, publico):
    return {"nombre": nombre, "categoria": categoria, "usd": usd, "usd_publico": publico}


def test_recargo_es_10_hasta_499_y_15_desde_500():
    """Catches a markup outside the 10 to 15 USD range the wholesaler asked for."""
    assert listado_whatsapp.recargo_usd(120) == 10
    assert listado_whatsapp.recargo_usd(499) == 10
    assert listado_whatsapp.recargo_usd(500) == 15
    assert listado_whatsapp.recargo_usd(1800) == 15


def test_tres_columnas_en_dolares_mayorista_publico_y_con_ganancia():
    secciones = listado_whatsapp.secciones_listado([_prod("Elegible", "Apple - iPhone", 740, 800)])

    assert secciones[0]["seccion"] == "Celulares"
    assert secciones[0]["grupos"][0]["titulo"] == "Apple"
    assert secciones[0]["grupos"][0]["items"] == [{"n": "Elegible", "a": 740, "b": 800, "c": 815}]


def test_no_incluye_iphones_usados_ni_productos_sin_precio_publico():
    productos = [
        _prod("Usado", "Apple - iPhone Usado", 380, 400),
        {"nombre": "Sin publico", "categoria": "Apple - iPhone", "usd": 100},
        _prod("Nuevo", "Apple - iPhone", 380, 400),
    ]

    nombres = [i["n"] for s in listado_whatsapp.secciones_listado(productos)
               for g in s["grupos"] for i in g["items"]]

    assert nombres == ["Nuevo"]


def test_agrupa_por_seccion_y_marca_con_apple_primero():
    productos = [
        _prod("Galaxy A16", "Samsung", 150, 180),
        _prod("iPhone 15", "Apple - iPhone", 700, 760),
        _prod("iPad 10", "Apple - iPad", 400, 450),
    ]

    secciones = listado_whatsapp.secciones_listado(productos)

    assert [s["seccion"] for s in secciones] == ["Celulares", "Tablets"]
    assert [g["titulo"] for g in secciones[0]["grupos"]] == ["Apple", "Samsung"]


# ---------- Acceso ----------

def _cliente(monkeypatch, mayorista):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave123",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    if mayorista:
        cliente = fake.table("clientes").select("*").execute().data[0]
        fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", cliente["id"]).execute()
    monkeypatch.setattr(appmod, "_cargar_snapshot_mayorista", lambda: ([
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 800, "pesos": 1376000,
         "transferencia": 1418000, "costo": 700, "margen": 100, "proveedor": "privado"},
    ], {"Elegible": 700}))
    monkeypatch.setattr(appmod, "_cargar_cotizacion_catalogo", lambda: 1720)
    return c


def test_api_sin_sesion_es_401(monkeypatch):
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    assert c.get("/api/listado-whatsapp").status_code == 401


def test_api_minorista_es_403_y_no_filtra_datos(monkeypatch):
    c = _cliente(monkeypatch, mayorista=False)
    r = c.get("/api/listado-whatsapp")
    assert r.status_code == 403
    assert "Elegible" not in r.text


def test_api_mayorista_devuelve_listado_sin_datos_privados(monkeypatch):
    c = _cliente(monkeypatch, mayorista=True)

    r = c.get("/api/listado-whatsapp")

    assert r.status_code == 200
    datos = r.json()
    assert datos["cotizacion"] == 1720
    assert datos["secciones"][0]["grupos"][0]["items"] == [{"n": "Elegible", "a": 750, "b": 800, "c": 815}]
    for privado in ("costo", "margen", "proveedor", "privado"):
        assert privado not in r.text


def test_pagina_redirige_segun_el_tipo_de_cliente(monkeypatch):
    anonimo = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    assert anonimo.get("/listado-whatsapp").headers["location"] == "/login.html"

    minorista = _cliente(monkeypatch, mayorista=False)
    assert minorista.get("/listado-whatsapp").headers["location"] == "/"


def test_pagina_para_mayorista_responde_html(monkeypatch):
    c = _cliente(monkeypatch, mayorista=True)
    r = c.get("/listado-whatsapp")
    assert r.status_code == 200
    assert "Listado WhatsApp" in r.text


# ---------- Formato del texto (node) ----------

pytestmark_js = pytest.mark.skipif(node is None, reason="node no está instalado")


def _js(cuerpo):
    guion = textwrap.dedent(f"""
        const L = require({json.dumps(str(RUTA_JS))});
        const fecha = new Date("2026-11-25T15:00:00Z");
        const secciones = [{{ seccion: "Celulares", grupos: [
          {{ titulo: "Apple", items: [{{ n: "iPhone 15 128GB", a: 740, b: 800, c: 815 }}] }},
          {{ titulo: "Samsung", items: [{{ n: "*Galaxy* A16_5G ~4GB~", a: 150, b: 180, c: 190 }}] }},
        ] }}];
        {cuerpo}
    """)
    r = subprocess.run([node, "-e", guion], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytestmark_js
def test_pesos_y_transferencia_siguen_el_dolar_elegido():
    """Catches pesos that ignore the wholesaler's own dollar."""
    r = _js('console.log(JSON.stringify([L.precios(800, 1720), L.precios(800, 1800)]))')
    assert r[0] == {"usd": 800, "pesos": 1376000, "transferencia": 1418557}
    assert r[1]["pesos"] == 1440000


@pytestmark_js
def test_lee_el_dolar_en_formatos_argentinos_y_rechaza_basura():
    casos = ['1800', '1.800', '$ 1.800', '1800,50', '', 'abc', '0']
    r = _js(f'console.log(JSON.stringify({json.dumps(casos)}.map(L.leerDolar)))')
    assert r == [1800, 1800, 1800, 1800.5, None, None, None]


@pytestmark_js
def test_el_texto_no_rompe_whatsapp():
    """Catches *, _, ~ or list prefixes in product names that WhatsApp would format."""
    r = _js("""
      const m = L.armarMensajes(secciones, "c", 1720, { nombre: "Tecno *Sur*", fecha });
      console.log(JSON.stringify(m));
    """)
    assert len(r) == 1
    texto = r[0]
    assert "Galaxy A165G 4GB" in texto
    assert "\t" not in texto
    asteriscos = [ln for ln in texto.split("\n") if "*" in ln]
    # Solo el nombre y los títulos de marca van en negrita, cada uno con un par de *.
    assert all(ln.startswith("*") and ln.endswith("*") and ln.count("*") == 2 for ln in asteriscos)
    assert "_" not in texto and "~" not in texto
    assert "*TECNO SUR*" in texto
    assert "🇺🇸 US$ 815 · 🇦🇷 $1.401.800 · 🏦 $1.445.155" in texto


@pytestmark_js
def test_sin_nombre_no_deja_linea_vacia_ni_negrita_vacia():
    r = _js('console.log(JSON.stringify(L.armarMensajes(secciones, "a", 1720, { nombre: "  ", fecha })[0]))')
    assert not r.startswith("*")
    assert "**" not in r
    assert "📅 25 de noviembre de 2026" in r


@pytestmark_js
def test_cada_columna_usa_su_precio_en_dolares():
    r = _js("""
      console.log(JSON.stringify(["a", "b", "c"].map((c) => L.armarMensajes(secciones, c, 1720, { nombre: "", fecha })[0])))
    """)
    assert "US$ 740" in r[0] and "US$ 800" in r[1] and "US$ 815" in r[2]


@pytestmark_js
def test_listados_largos_se_parten_entre_marcas_bajo_el_limite():
    """Catches a message over WhatsApp's character limit or a brand cut in half."""
    r = _js("""
      const items = Array.from({ length: 400 }, (_, i) => ({ n: "Producto de prueba numero " + i + " 256GB negro", a: 100 + i, b: 120 + i, c: 130 + i }));
      const grande = [{ seccion: "Celulares", grupos: [{ titulo: "A", items }, { titulo: "B", items }, { titulo: "C", items }] }];
      const m = L.armarMensajes(grande, "c", 1720, { nombre: "Tienda", fecha });
      console.log(JSON.stringify({ n: m.length, max: Math.max(...m.map((x) => x.length)), partes: m.map((x) => /\\(parte \\d de \\d\\)/.test(x)) }));
    """)
    assert r["n"] > 1
    assert r["max"] <= 55000
    assert all(r["partes"])


@pytestmark_js
def test_rangos_de_300_dolares_segun_el_precio_mayorista():
    """Catches wrong range edges: 300 belongs to the first range, 301 to the second."""
    r = _js("""
      const edges = [0, 1, 300, 301, 600, 601, 1500].map(L.rangoDe);
      const lista = [{ seccion: "X", grupos: [{ titulo: "Y", items: [
        { n: "a", a: 120, b: 1, c: 1 }, { n: "b", a: 300, b: 1, c: 1 }, { n: "c", a: 301, b: 1, c: 1 }, { n: "d", a: 1500, b: 1, c: 1 }] }] }];
      console.log(JSON.stringify({ edges, rangos: L.rangos(lista), e0: L.etiquetaRango(0), e1: L.etiquetaRango(1) }));
    """)
    assert r["edges"] == [0, 0, 0, 1, 1, 2, 4]
    assert [(x["etiqueta"], x["cantidad"]) for x in r["rangos"]] == [
        ("US$ 0 a 300", 2), ("US$ 301 a 600", 1), ("US$ 1.201 a 1.500", 1)]
    assert r["e1"] == "US$ 301 a 600"


@pytestmark_js
def test_la_ganancia_elegida_se_suma_solo_a_su_rango_y_solo_a_la_primera_columna():
    r = _js("""
      const m = L.conGanancias(secciones, { 0: 25, 2: 100 });
      console.log(JSON.stringify(m[0].grupos.map((g) => g.items[0])));
    """)
    # iPhone 15 (a=740) cae en el rango 601 a 900 (índice 2, +100); Galaxy (a=150) en el 0 a 300 (+25).
    assert r[0] == {"n": "iPhone 15 128GB", "a": 840, "b": 800, "c": 815}
    assert r[1] == {"n": "*Galaxy* A16_5G ~4GB~", "a": 175, "b": 180, "c": 190}


@pytestmark_js
def test_lee_la_ganancia_y_nunca_devuelve_negativos_ni_basura():
    casos = ["150", "US$ 150", "", "abc", "-30", "99999"]
    r = _js(f'console.log(JSON.stringify({json.dumps(casos)}.map(L.leerGanancia)))')
    assert r == [150, 150, 0, 0, 30, 5000]


@pytestmark_js
def test_el_texto_lleva_la_fecha_de_hoy_y_el_dolar_que_puso_el_usuario():
    """Catches a hardcoded date or a dollar that ignores the user's own value."""
    r = _js("""
      const hoy = new Date();
      const esperada = new Intl.DateTimeFormat("es-AR", { timeZone: "America/Argentina/Buenos_Aires", day: "numeric", month: "long", year: "numeric" }).format(hoy);
      const t = L.armarMensajes(secciones, "b", 1850, { nombre: "", fecha: hoy })[0];
      console.log(JSON.stringify({ t, esperada }));
    """)
    assert "📅 " + r["esperada"] in r["t"]
    assert "💵 Dólar: $1.850" in r["t"]
    assert "🇦🇷 $1.480.000" in r["t"]  # 800 USD x 1850


# ---------- Ganancias guardadas en la cuenta ----------

def test_limpiar_ganancias_descarta_lo_invalido_y_los_ceros():
    """Catches junk or out-of-range values reaching the clientes table."""
    crudo = {"0": 50, "1": 0, "2": -5, "3": 9999, "x": 10, "4": "20", "5": True, "6": 12.5, "300": 10, 7: 10, "08": 40}
    assert listado_whatsapp.limpiar_ganancias(crudo) == {"0": 50, "8": 40}
    assert listado_whatsapp.limpiar_ganancias("no es un dict") == {}
    assert listado_whatsapp.limpiar_ganancias(None) == {}


def _fila_cliente(monkeypatch):
    return appmod.get_client().table("clientes").select("*").execute().data[0]


def test_ganancias_se_guardan_en_la_cuenta_y_vuelven_en_la_proxima_visita(monkeypatch):
    c = _cliente(monkeypatch, mayorista=True)

    r = c.put("/api/listado-whatsapp/ganancias", json={"ganancias": {"0": 50, "2": 120, "1": 0, "9": -4}})

    assert r.status_code == 200
    assert r.json()["ganancias"] == {"0": 50, "2": 120}
    assert _fila_cliente(monkeypatch)["listado_ganancias"] == {"0": 50, "2": 120}
    assert c.get("/api/listado-whatsapp").json()["ganancias"] == {"0": 50, "2": 120}


def test_cada_cuenta_guarda_sus_propias_ganancias(monkeypatch):
    c = _cliente(monkeypatch, mayorista=True)
    c.put("/api/listado-whatsapp/ganancias", json={"ganancias": {"0": 50}})
    otra = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    otra.post("/registro", json={
        "nombre": "Ana", "apellido": "Gómez", "celular": "3519999999",
        "email": "ana@x.com", "password": "clave123",
        "provincia": "Córdoba", "direccion": "Av. Colón 456, Córdoba",
    })
    fake = appmod.get_client()
    ana = [f for f in fake.table("clientes").select("*").execute().data if f["email"] == "ana@x.com"][0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", ana["id"]).execute()

    assert otra.get("/api/listado-whatsapp").json()["ganancias"] == {}


def test_guardar_ganancias_exige_sesion_y_ser_mayorista(monkeypatch):
    anonimo = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    assert anonimo.put("/api/listado-whatsapp/ganancias", json={"ganancias": {"0": 5}}).status_code == 401

    minorista = _cliente(monkeypatch, mayorista=False)
    assert minorista.put("/api/listado-whatsapp/ganancias", json={"ganancias": {"0": 5}}).status_code == 403
    assert "listado_ganancias" not in _fila_cliente(monkeypatch) or _fila_cliente(monkeypatch)["listado_ganancias"] in (None, {})


def test_si_falla_la_base_guardar_responde_503_y_leer_devuelve_vacio(monkeypatch):
    c = _cliente(monkeypatch, mayorista=True)
    real = appmod.get_client()

    class Roto:
        def table(self, nombre):
            if nombre == "clientes":
                raise RuntimeError("base caída")
            return real.table(nombre)

    # Primero resuelve el tipo de cliente con la base buena, después se cae.
    monkeypatch.setattr(appmod, "_tipo_cliente_sesion", lambda request: "mayorista")
    monkeypatch.setattr(appmod, "get_client", lambda: Roto())

    assert c.put("/api/listado-whatsapp/ganancias", json={"ganancias": {"0": 5}}).status_code == 503
    assert appmod._ganancias_listado_guardadas("cualquiera") == {}


def test_la_opcion_3_aclara_que_sirve_para_revender_en_el_interior():
    assert "Ideal para revender en el interior" in RUTA_JS.read_text(encoding="utf-8")
