#!/usr/bin/env python3
"""Ficha financiera de un producto u operación.

Lee un JSON (ver ejemplo.json) y imprime en Markdown: ficha de costos,
márgenes, niveles de precio, descuento máximo sostenible, break-even,
retorno sobre capital, escenarios de dólar y sensibilidad.

Uso:  python3 ficha.py datos.json

Campos del JSON (todo monto puede ir en "USD" o "ARS"; se convierte a USD
con "cotizacion"):
  producto          nombre
  cotizacion        ARS por USD (tipo de cambio efectivo)
  precio_venta      {"monto": 1000, "moneda": "USD"}
  costos            lista de {"concepto", "monto", "moneda", "tipo", "fuente"}
                    tipo: "producto" | "landed" (entran al landed cost)
                          "variable" (entrega, regalos, garantía esperada, CAC...)
                          "fijo"     (fijo asignado por operación)
  cobro_pct         fracción del precio que se pierde al cobrar (0.012 = 1,2%)
  cobro_fijo        costo fijo de cobro por operación, en USD (opcional)
  margen_objetivo   margen neto deseado sobre precio (0.15 = 15%)
  colchon_riesgo    colchón sobre el precio objetivo (default 0.03)
  ganancia_minima   ganancia neta mínima aceptable por operación, USD (default 0)
  fijos_mensuales   costos fijos del mes en USD, para break-even (opcional)
  dias_hasta_vender días de capital inmovilizado (opcional)
  capital           capital invertido por unidad en USD (default: landed cost)
  escenarios_dolar  lista de cotizaciones a simular (opcional)
"""
import copy
import json
import sys


def ar(n, dec=2):
    s = f"{abs(n):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{s}" if n < 0 else s


def pct(x):
    return f"{ar(x * 100, 1)}%" if x is not None else "—"


def usd(item, cot):
    monto = float(item["monto"])
    return monto / cot if item.get("moneda", "USD").upper() == "ARS" else monto


def calcular(d):
    cot = float(d["cotizacion"])
    precio = usd(d["precio_venta"], cot)
    c_pct = float(d.get("cobro_pct", 0))
    c_fijo = float(d.get("cobro_fijo", 0))
    suma = {"landed": 0.0, "variable": 0.0, "fijo": 0.0}
    for c in d.get("costos", []):
        tipo = c.get("tipo", "variable")
        suma["landed" if tipo in ("producto", "landed") else tipo] += usd(c, cot)
    landed, otros_var, fijo = suma["landed"], suma["variable"], suma["fijo"]

    cobro = precio * c_pct + c_fijo
    variable = landed + otros_var + cobro
    bruto = precio - landed
    contrib = precio - variable
    neta = contrib - fijo
    base_var = landed + otros_var + c_fijo
    obj = float(d.get("margen_objetivo", 0))
    supervivencia = base_var / (1 - c_pct)
    equilibrio = (base_var + fijo) / (1 - c_pct)
    objetivo = (base_var + fijo) / (1 - c_pct - obj) if c_pct + obj < 1 else None
    minimo = float(d.get("ganancia_minima", 0))
    desc_max = precio - (base_var + fijo + minimo) / (1 - c_pct)
    return {
        "precio": precio, "cobro": cobro, "neto": precio - cobro,
        "landed": landed, "otros_var": otros_var, "variable": variable,
        "fijo": fijo, "costo_total": variable + fijo,
        "bruto": bruto, "contrib": contrib, "neta": neta,
        "m_bruto": bruto / precio, "markup": bruto / landed if landed else None,
        "m_contrib": contrib / precio, "m_neto": neta / precio,
        "supervivencia": supervivencia, "equilibrio": equilibrio,
        "objetivo": objetivo,
        "recomendado": objetivo * (1 + float(d.get("colchon_riesgo", 0.03))) if objetivo else None,
        "promo": (supervivencia + equilibrio) / 2,
        "desc_max": desc_max,
    }


def con(d, **cambios):
    """Copia del escenario con cambios aplicados."""
    e = copy.deepcopy(d)
    if "cotizacion" in cambios:
        e["cotizacion"] = cambios["cotizacion"]
    if "precio_mult" in cambios:
        e["precio_venta"]["monto"] *= cambios["precio_mult"]
    if "precio_menos_usd" in cambios:
        p = e["precio_venta"]
        delta = cambios["precio_menos_usd"]
        p["monto"] -= delta * e["cotizacion"] if p.get("moneda", "USD").upper() == "ARS" else delta
    for c in e["costos"]:
        if "producto_mult" in cambios and c.get("tipo") == "producto":
            c["monto"] *= cambios["producto_mult"]
        if "variable_mult" in cambios and c.get("tipo") == "variable":
            c["monto"] *= cambios["variable_mult"]
    if "cobro_mas" in cambios:
        e["cobro_pct"] = e.get("cobro_pct", 0) + cambios["cobro_mas"]
    return e


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    cot = float(d["cotizacion"])
    r = calcular(d)
    out = [f"## {d.get('producto', 'Producto')}",
           f"Cotización usada: ARS {ar(cot)} por USD", "",
           "| Concepto | USD | Fuente |", "|---|---:|---|"]
    for c in d.get("costos", []):
        extra = f" (ARS {ar(float(c['monto']))})" if c.get("moneda", "USD").upper() == "ARS" else ""
        out.append(f"| {c['concepto']}{extra} | {ar(usd(c, cot))} | {c.get('fuente', '')} |")
    out.append(f"| Costo de cobro ({pct(d.get('cobro_pct', 0))} + fijo) | {ar(r['cobro'])} | |")
    out += [f"| **Costo total** | **{ar(r['costo_total'])}** | |",
            f"| Precio venta | {ar(r['precio'])} | |",
            f"| Dinero neto recibido | {ar(r['neto'])} | |",
            f"| **Ganancia neta estimada** | **{ar(r['neta'])}** | |", "",
            "| Métrica | USD | % |", "|---|---:|---:|",
            f"| Landed cost | {ar(r['landed'])} | |",
            f"| Margen bruto | {ar(r['bruto'])} | {pct(r['m_bruto'])} |",
            f"| Markup | | {pct(r['markup'])} |",
            f"| Costo variable total | {ar(r['variable'])} | |",
            f"| Margen de contribución | {ar(r['contrib'])} | {pct(r['m_contrib'])} |",
            f"| Fijo asignado | {ar(r['fijo'])} | |",
            f"| Margen neto | {ar(r['neta'])} | {pct(r['m_neto'])} |", "",
            "### Niveles de precio (USD)", "",
            "| Nivel | Precio |", "|---|---:|",
            f"| Supervivencia (solo variables) | {ar(r['supervivencia'])} |",
            f"| Equilibrio (+ fijo asignado) | {ar(r['equilibrio'])} |",
            f"| Objetivo ({pct(d.get('margen_objetivo', 0))} neto) | {ar(r['objetivo']) if r['objetivo'] else '—'} |",
            f"| Recomendado (+{pct(d.get('colchon_riesgo', 0.03))} colchón) | {ar(r['recomendado']) if r['recomendado'] else '—'} |",
            f"| Promocional mínimo (punto medio superv./equilibrio) | {ar(r['promo'])} |", ""]
    if r["desc_max"] > 0:
        out.append(f"**Descuento máximo sostenible:** USD {ar(r['desc_max'])} "
                   f"(deja ganancia neta de USD {ar(float(d.get('ganancia_minima', 0)))}).")
    else:
        out.append(f"**Descuento máximo sostenible:** ninguno — ya está USD {ar(-r['desc_max'])} por debajo del mínimo.")
    for dto in (10, 20):
        if r["contrib"] > 0:
            rd = calcular(con(d, precio_menos_usd=dto))
            perdida = (r["contrib"] - rd["contrib"]) / r["contrib"]
            extra = r["contrib"] / rd["contrib"] - 1 if rd["contrib"] > 0 else None
            out.append(f"- Descuento USD {dto}: se come {pct(perdida)} de la contribución; "
                       + (f"hacen falta {pct(extra)} más de ventas para compensar." if extra is not None
                          else "la contribución queda negativa."))
    if d.get("fijos_mensuales") and r["contrib"] > 0:
        fm = float(d["fijos_mensuales"])
        out += ["", "### Break-even",
                f"- Operaciones/mes: {ar(fm / r['contrib'], 1)}",
                f"- Facturación/mes: USD {ar(fm / r['m_contrib'])}"]
    if d.get("dias_hasta_vender"):
        dias = float(d["dias_hasta_vender"])
        cap = float(d.get("capital", r["landed"]))
        roc = r["neta"] / cap
        out += ["", "### Retorno sobre capital",
                f"- Capital: USD {ar(cap)} · {ar(dias, 0)} días hasta vender",
                f"- Por ciclo: {pct(roc)} · mensualizado: {pct(roc * 30 / dias)} · anualizado: {pct(roc * 365 / dias)}"]
    if d.get("escenarios_dolar"):
        out += ["", "### Escenarios de dólar", "",
                "| Cotización | Ganancia neta USD | Margen neto |", "|---:|---:|---:|"]
        for c in d["escenarios_dolar"]:
            re = calcular(con(d, cotizacion=c))
            out.append(f"| {ar(c)} | {ar(re['neta'])} | {pct(re['m_neto'])} |")
    casos = [("Dólar +5%", con(d, cotizacion=cot * 1.05)),
             ("Proveedor +5%", con(d, producto_mult=1.05)),
             ("Precio +5%", con(d, precio_mult=1.05)),
             ("Precio −5%", con(d, precio_mult=0.95)),
             ("Descuento USD 10", con(d, precio_menos_usd=10)),
             ("Descuento USD 20", con(d, precio_menos_usd=20)),
             ("Variables +20%", con(d, variable_mult=1.2)),
             ("Comisión de cobro +1 pp", con(d, cobro_mas=0.01))]
    filas = sorted(((n, calcular(e)["neta"] - r["neta"]) for n, e in casos), key=lambda x: x[1])
    out += ["", "### Sensibilidad (ganancia neta por operación)", "",
            "| Cambio | Δ USD | Ganancia neta |", "|---|---:|---:|"]
    out += [f"| {n} | {ar(delta)} | {ar(r['neta'] + delta)} |" for n, delta in filas]
    print("\n".join(out))


if __name__ == "__main__":
    main()
