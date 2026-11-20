"""La pizarra de la home mostraba siempre los mismos 6 productos (el primero de
cada sección). La selección corre en el navegador: se prueba con node."""
import json
import shutil
import subprocess
import textwrap

import pytest

import web.app as appmod

ESTATICOS = appmod.BASE / "static"
RUTA = ESTATICOS / "pizarra-seleccion.js"
node = shutil.which("node")

pytestmark = pytest.mark.skipif(node is None, reason="node no está instalado")


def _correr(cuerpo):
    guion = textwrap.dedent(f"""
        const {{ armarMazo, familiaDe, leerVistos, marcarVisto }} = require({json.dumps(str(RUTA))});
        const semilla = (s) => () => {{ s |= 0; s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s);
          t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }};
        class Almacen {{ constructor() {{ this.d = {{}}; }} getItem(k) {{ return this.d[k] ?? null; }} setItem(k, v) {{ this.d[k] = String(v); }} }}
        const mk = (pref, n, extra = {{}}) => Array.from({{ length: n }}, (_, i) => ({{ nombre: pref + " " + i, usd: 100 + i, pesos: 165000 + i, marca: extra.marca || "X", ...extra }}));
        const secciones = {{
          "Celulares": [...mk("IPHONE", 20, {{ marca: "Apple" }}), ...mk("GALAXY", 20, {{ marca: "Samsung" }}), ...mk("MOTO", 20, {{ marca: "Motorola" }})],
          "Tablets": mk("TAB", 15),
          "Notebooks y Macbooks": [...mk("MACBOOK AIR", 8), ...mk("LENOVO", 20)],
          "Accesorios Celulares": mk("CARGADOR", 30),
          "Gaming": mk("JOYSTICK", 12),
          "Electro": mk("ASPIRADORA", 25),
        }};
        const nombres = (m) => m.map((x) => x.producto.nombre);
        {cuerpo}
    """)
    r = subprocess.run([node, "-e", guion], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_cada_visita_arranca_con_otros_productos_y_no_siempre_los_mismos():
    salida = _correr("""
        const primeros = new Set(), conjuntos = new Set();
        for (let i = 1; i <= 40; i++) {
          const m = armarMazo({ secciones, azar: semilla(i) });
          primeros.add(m[0].producto.nombre);
          conjuntos.add(nombres(m).slice(0, 6).join("|"));
        }
        console.log(JSON.stringify({ primeros: primeros.size, conjuntos: conjuntos.size }));
    """)
    assert salida["conjuntos"] >= 35
    assert salida["primeros"] >= 15


def test_ya_no_devuelve_el_primero_de_cada_seccion_en_orden_de_catalogo():
    salida = _correr("""
        const fijos = new Set(["IPHONE 0", "TAB 0", "MACBOOK AIR 0", "CARGADOR 0", "JOYSTICK 0", "ASPIRADORA 0", "GALAXY 0", "LENOVO 0"]);
        let siempre = 0;
        for (let i = 1; i <= 40; i++) {
          const n = nombres(armarMazo({ secciones, azar: semilla(i) }));
          if (n.slice(0, 6).every((x) => fijos.has(x))) siempre++;
        }
        console.log(JSON.stringify(siempre));
    """)
    assert salida <= 1


def test_mezcla_categorias_y_nunca_dos_seguidos_de_la_misma_familia():
    salida = _correr("""
        let seguidos = 0, minFamilias = 99;
        for (let i = 1; i <= 40; i++) {
          const m = armarMazo({ secciones, azar: semilla(i) });
          for (let k = 1; k < m.length; k++) if (m[k].familia === m[k - 1].familia) seguidos++;
          minFamilias = Math.min(minFamilias, new Set(m.slice(0, 8).map((x) => x.familia)).size);
        }
        console.log(JSON.stringify({ seguidos, minFamilias }));
    """)
    assert salida["seguidos"] == 0
    assert salida["minFamilias"] >= 6


def test_familias_separan_iphone_android_mac_y_notebooks():
    salida = _correr("""
        const m = armarMazo({ secciones, azar: semilla(3), tamano: 80 });
        const f = (pref) => [...new Set(m.filter((x) => x.producto.nombre.startsWith(pref)).map((x) => x.familia))];
        console.log(JSON.stringify({ iphone: f("IPHONE"), galaxy: f("GALAXY"), mac: f("MACBOOK"), nb: f("LENOVO") }));
    """)
    assert salida == {"iphone": ["iPhone"], "galaxy": ["Android"], "mac": ["Mac"], "nb": ["Notebooks"]}


def test_nunca_incluye_usados_cpo_ni_productos_sin_foto_ni_sin_precio():
    salida = _correr("""
        const s = JSON.parse(JSON.stringify(secciones));
        s.Celulares.push({ nombre: "IPHONE 14 128GB USADO 86%", usd: 400, pesos: 660000, marca: "Apple" },
                         { nombre: "IPHONE 13 CPO", usd: 300, pesos: 495000, marca: "Apple" },
                         { nombre: "IPHONE 99", categoria: "Celulares Usados", usd: 250, pesos: 400000, marca: "Apple" },
                         { nombre: "SIN PRECIO", usd: null, pesos: null });
        s.Gaming.push({ nombre: "CONSOLA SIN FOTO", usd: 1, pesos: 1 });
        let malos = 0;
        for (let i = 1; i <= 30; i++) {
          const m = armarMazo({ secciones: s, tamano: 200, azar: semilla(i), tieneImagen: (p) => p.nombre !== "CONSOLA SIN FOTO" });
          malos += nombres(m).filter((n) => /USADO|CPO|IPHONE 99|SIN PRECIO|SIN FOTO/.test(n)).length;
        }
        console.log(JSON.stringify(malos));
    """)
    assert salida == 0


def test_lo_ya_mostrado_en_visitas_anteriores_va_al_final_del_mazo():
    salida = _correr("""
        const a = new Almacen();
        for (let i = 0; i < 1; i++) {
          const vistos = leerVistos(a);
          const m = armarMazo({ secciones, vistos, azar: semilla(10 + i), tamano: 24 });
          m.forEach((x) => marcarVisto(a, x.producto.nombre));
        }
        const previos = leerVistos(a);
        const m = armarMazo({ secciones, vistos: previos, azar: semilla(99), tamano: 16 });
        console.log(JSON.stringify({ repetidos: nombres(m).filter((n) => previos.has(n)).length, vistos: previos.size }));
    """)
    assert salida["vistos"] == 24
    assert salida["repetidos"] == 0


def test_sin_localstorage_sigue_funcionando():
    salida = _correr("""
        const roto = { getItem() { throw new Error("x"); }, setItem() { throw new Error("x"); } };
        marcarVisto(roto, "A");
        console.log(JSON.stringify([...leerVistos(roto)].length + armarMazo({ secciones }).length));
    """)
    assert salida == 24


def test_home_tiene_flechas_fuera_del_enlace_y_pizarra_las_usa():
    html = (ESTATICOS / "index.html").read_text(encoding="utf-8")
    js = (ESTATICOS / "pizarra.js").read_text(encoding="utf-8")
    assert html.index("pizarra-seleccion.js") < html.index('src="pizarra.js"')
    assert 'data-pz-paso="-1"' in html and 'data-pz-paso="1"' in html
    assert 'aria-label="Producto anterior"' in html and 'aria-label="Producto siguiente"' in html
    # Un botón dentro de un <a> es HTML inválido: las flechas van después de cerrarlo.
    assert html.index("</a>", html.index("ttra-pz-destacado")) < html.index("ttra-pz-nav")
    assert "data-pz-paso" in js and "ArrowLeft" in js and "ArrowRight" in js
    assert "TTRAPizarraSeleccion" in js
    assert "pickProducts" not in js
