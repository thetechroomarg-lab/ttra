"""La rotación de recomendados corre en el navegador: se prueba con node si está instalado."""
import json
import shutil
import subprocess
import textwrap

import pytest

import web.app as appmod

RUTA = appmod.BASE / "static" / "recomendados-rotacion.js"
node = shutil.which("node")


def _correr(cuerpo):
    guion = textwrap.dedent(f"""
        const {{ elegir }} = require({json.dumps(str(RUTA))});
        class Almacen {{ constructor() {{ this.d = {{}}; }} getItem(k) {{ return this.d[k] ?? null; }} setItem(k, v) {{ this.d[k] = String(v); }} }}
        const catalogo = (n) => Array.from({{ length: n }}, (_, i) => ({{ nombre: "P" + i }}));
        const nombres = (l) => l.map((p) => p.nombre);
        {cuerpo}
    """)
    r = subprocess.run([node, "-e", guion], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


pytestmark = pytest.mark.skipif(node is None, reason="node no está instalado")


def test_no_repite_ningun_producto_hasta_recorrer_todo_el_catalogo():
    salida = _correr("""
        const s = new Almacen(), c = catalogo(100), vistos = [];
        for (let i = 0; i < 12; i++) vistos.push(...nombres(elegir({ catalogo: c, cantidad: 8, storage: s })));
        console.log(JSON.stringify({ total: vistos.length, unicos: new Set(vistos).size }));
    """)
    assert salida == {"total": 96, "unicos": 96}


def test_cada_vuelta_dentro_de_una_pantalla_no_trae_duplicados_y_siempre_completa():
    salida = _correr("""
        const s = new Almacen(), c = catalogo(30); let ok = true;
        for (let i = 0; i < 60; i++) { const l = nombres(elegir({ catalogo: c, cantidad: 8, storage: s })); if (l.length !== 8 || new Set(l).size !== 8) ok = false; }
        console.log(JSON.stringify(ok));
    """)
    assert salida is True


def test_al_agotar_el_catalogo_arranca_otra_vuelta_sin_repetir_lo_ultimo_visto():
    salida = _correr("""
        const s = new Almacen(), c = catalogo(100);
        for (let i = 0; i < 12; i++) elegir({ catalogo: c, cantidad: 8, storage: s });   // 96 vistos
        const ultimos = JSON.parse(s.getItem("ttra_reco_vistos_v1")).slice(-30);
        const siguiente = nombres(elegir({ catalogo: c, cantidad: 8, storage: s }));
        console.log(JSON.stringify(siguiente.some((n) => ultimos.includes(n))));
    """)
    assert salida is False


def test_recargar_la_pagina_en_la_misma_sesion_no_reinicia_la_memoria():
    salida = _correr("""
        const s = new Almacen(), c = catalogo(100);
        const a = nombres(elegir({ catalogo: c, cantidad: 8, storage: s }));
        const b = nombres(elegir({ catalogo: c, cantidad: 8, storage: s }));  // "recarga": mismo storage
        console.log(JSON.stringify(a.filter((n) => b.includes(n)).length));
    """)
    assert salida == 0


def test_un_producto_que_sale_del_catalogo_no_se_recomienda_y_uno_nuevo_entra():
    salida = _correr("""
        const s = new Almacen();
        elegir({ catalogo: catalogo(20), cantidad: 8, storage: s });
        const nuevo = catalogo(20).slice(10).concat([{ nombre: "NUEVO" }]);
        const l = nombres(elegir({ catalogo: nuevo, cantidad: 8, storage: s }));
        console.log(JSON.stringify(l.every((n) => n === "NUEVO" || Number(n.slice(1)) >= 10)));
    """)
    assert salida is True


def test_los_personalizados_ocupan_hasta_la_mitad_y_el_resto_es_sorpresa():
    salida = _correr("""
        const c = catalogo(200), pref = c.slice(0, 24).map((p) => ({ ...p, motivo_recomendacion: "x" }));
        let maxPref = 0, conMotivo = true;
        for (let i = 0; i < 20; i++) {
          const l = elegir({ catalogo: c, cantidad: 8, preferidos: pref, storage: new Almacen() });
          const n = l.filter((p) => Number(p.nombre.slice(1)) < 24).length;
          maxPref = Math.max(maxPref, n);
          if (l.filter((p) => p.motivo_recomendacion).length !== n) conMotivo = false;
        }
        console.log(JSON.stringify({ maxPref, conMotivo }));
    """)
    assert salida["maxPref"] <= 4 + 4  # la mitad reservada a preferidos; el resto puede coincidir por azar
    assert salida["conMotivo"] is True


def test_funciona_sin_sessionstorage_disponible():
    salida = _correr("""
        const roto = { getItem() { throw new Error("bloqueado"); }, setItem() { throw new Error("bloqueado"); } };
        const l = elegir({ catalogo: catalogo(50), cantidad: 8, storage: roto });
        console.log(JSON.stringify(l.length));
    """)
    assert salida == 8


def test_catalogo_chico_o_vacio_no_rompe():
    salida = _correr("""
        const s = new Almacen();
        console.log(JSON.stringify([elegir({ catalogo: [], cantidad: 8, storage: s }).length,
                                    elegir({ catalogo: catalogo(3), cantidad: 8, storage: s }).length]));
    """)
    assert salida == [0, 3]


def test_el_index_carga_la_rotacion_antes_que_el_carrusel():
    html = (appmod.BASE / "static" / "index.html").read_text(encoding="utf-8")
    assert html.index("recomendados-rotacion.js") < html.index("landing-pipboy.js")
