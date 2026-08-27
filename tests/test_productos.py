import hashlib
import json

import pytest

import web.productos as productos_mod
from web.productos import (
    generar_costos,
    generar_productos,
    generar_proveedores,
    resolver_proveedor,
    escribir_productos_json,
)


def test_genera_indice_privado_del_costo_consolidado():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    assert generar_costos(items) == {"iphone 13 128gb": 610}


def test_genera_productos_sin_proveedor_y_con_3_precios():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    prods = generar_productos(items, cotizacion=1540)
    assert len(prods) == 1                      # se consolida al más barato
    p = prods[0]
    assert "proveedor" not in p                 # NUNCA el proveedor
    assert p["usd"] == 670                      # 610 + margen iPhone 60 (601-900), redondeo a 5
    assert p["pesos"] == 670 * 1540
    assert p["transferencia"] == round(p["pesos"] / 0.97)
    assert p["link_imagen"].startswith("https://www.google.com/search?tbm=isch")
    assert p["categoria"]                       # tiene alguna categoría no vacía


def test_genera_indice_privado_del_proveedor_elegido():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]

    assert generar_proveedores(items) == {"iphone 13 128gb": "az"}


def test_resuelve_proveedor_con_la_misma_normalizacion_del_catalogo():
    proveedores = {"Xiaomi Redmi Note 14 8GB 256GB": "az"}

    assert resolver_proveedor(proveedores, "Xiaomi Redmi Note 14 8GB 256GB slim") == "az"
    assert resolver_proveedor(proveedores, "Producto inexistente") == "Proveedor no identificado"


def test_modelos_redmi_poco_mi_sin_marca_en_el_nombre_van_a_xiaomi():
    nombres = [
        "C71 3GB 64GB",
        "C81 PRO 4GB 256GB",
        "C75X 8GB 256GB",
        "F7 5G 12GB 256GB",
        "F8 ULTRA 5G 16GB 512GB",
        "M8 PRO 5g 512gb/12gb",
        "X8 PRO MAX 12GB 512GB",
        "A5 3GB 64GB",
        "NOTE 70 4GB 128GB (4gb+8gb)",
        "MI BAND 9",
        "MI BUDS 6 PLAY",
        "Mi 17T Pro 5G 12GB 512GB",
        "17 ULTRA 5G 16GB 512GB",
    ]
    items = [{"nombre": n, "costo": 200, "proveedor": "az"} for n in nombres]

    prods = generar_productos(items, cotizacion=1540)

    assert len(prods) == len(nombres)
    assert all(p["categoria"] == "Xiaomi" for p in prods)


def test_modelos_de_otras_marcas_sin_marca_en_el_nombre_no_van_a_xiaomi():
    nombres = [
        "EDGE 60 FUSION 5G 8GB 256GB slim",       # Motorola
        "G86 5G 8GB 256GB",                       # Motorola
        "HP 15-FC0037 AMD Ryzen 5 7520U 256GB SSD 8GB 15.6\" WIN11",  # notebook, no celular
        "Mi 5-Blade Electric Shaver",              # Xiaomi pero no es celular
    ]
    items = [{"nombre": n, "costo": 200, "proveedor": "az"} for n in nombres]

    prods = generar_productos(items, cotizacion=1540)

    assert all(p["categoria"] != "Xiaomi" for p in prods)


def test_escribir_productos_json(tmp_path):
    items = [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}]
    ruta = tmp_path / "productos.json"
    escribir_productos_json(items, 1540, str(ruta))
    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    assert "proveedor" not in data[0]
    assert data[0]["nombre"] == "Moto G15 128GB"
    proveedores = json.loads((tmp_path / "proveedores.json").read_text(encoding="utf-8"))
    assert proveedores == {"Moto G15 128GB": "va"}


def test_escribir_productos_json_escribe_costos_sin_exponerlos(tmp_path):
    ruta = tmp_path / "productos.json"
    escribir_productos_json(
        [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}],
        1540,
        ruta,
    )
    publico = json.loads(ruta.read_text(encoding="utf-8"))
    costos = json.loads((tmp_path / "costos.json").read_text(encoding="utf-8"))
    assert "costo" not in publico[0]
    assert costos == {"Moto G15 128GB": 150}


def test_escribir_productos_json_publica_manifest_con_hashes_y_version_al_final(
    tmp_path, monkeypatch,
):
    """Catches publishing independently-readable product/cost generations."""
    ruta = tmp_path / "productos.json"
    destinos = []
    reemplazar_real = productos_mod.os.replace

    def registrar_reemplazo(origen, destino):
        destinos.append(productos_mod.Path(destino).name)
        reemplazar_real(origen, destino)

    monkeypatch.setattr(productos_mod.os, "replace", registrar_reemplazo)

    productos_mod.escribir_productos_json(
        [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}],
        1540,
        ruta,
    )

    manifiesto_path = tmp_path / "catalogo-manifest.json"
    manifiesto = json.loads(manifiesto_path.read_text(encoding="utf-8"))
    assert destinos == [
        "productos.json", "proveedores.json", "costos.json", "catalogo-manifest.json",
    ]
    assert manifiesto["version"] == 1
    assert manifiesto["generacion"]
    assert manifiesto["productos_sha256"] == hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert manifiesto["costos_sha256"] == hashlib.sha256(
        (tmp_path / "costos.json").read_bytes()
    ).hexdigest()


def test_manifest_no_certifica_una_mezcla_de_dos_publicaciones_concurrentes(
    tmp_path, monkeypatch,
):
    """Catches hashing mutable destination files instead of this generation."""
    ruta = tmp_path / "productos.json"
    escribir_real = productos_mod._escribir_json_atomico

    def escribir_con_interferencia(destino, contenido):
        resultado = escribir_real(destino, contenido)
        if productos_mod.Path(destino).name == "costos.json":
            escribir_real(ruta, [{"nombre": "Otra generacion", "usd": 999}])
        return resultado

    monkeypatch.setattr(
        productos_mod, "_escribir_json_atomico", escribir_con_interferencia
    )

    productos_mod.escribir_productos_json(
        [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}],
        1540,
        ruta,
    )

    manifiesto = json.loads(
        (tmp_path / "catalogo-manifest.json").read_text(encoding="utf-8")
    )
    assert manifiesto["productos_sha256"] != hashlib.sha256(
        ruta.read_bytes()
    ).hexdigest()


def test_escribir_productos_json_no_trunca_un_archivo_si_falla_la_escritura(
    tmp_path, monkeypatch,
):
    """Catches direct writes destroying the last retail catalog on partial output."""
    ruta = tmp_path / "productos.json"
    anterior = '[{"nombre": "Catalogo anterior", "usd": 100}]'
    ruta.write_text(anterior, encoding="utf-8")

    def fallar_despues_de_escribir_parcial(*args, **kwargs):
        args[1].write("[")
        raise OSError("corte simulado")

    monkeypatch.setattr(productos_mod.json, "dump", fallar_despues_de_escribir_parcial)

    with pytest.raises(OSError, match="corte simulado"):
        productos_mod.escribir_productos_json(
            [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}],
            1540,
            ruta,
        )

    assert ruta.read_text(encoding="utf-8") == anterior
    assert json.loads(ruta.read_text(encoding="utf-8"))[0]["nombre"] == "Catalogo anterior"
