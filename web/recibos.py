import html
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _formatear_usd(valor):
    return f"U$D {int(valor or 0):,}".replace(",", ".")


def _garantia_producto(nombre):
    producto = (nombre or "").lower()
    if any(palabra in producto for palabra in ("iphone", "ipad", "macbook", "imac", "airpods", "apple watch")):
        return (
            "Apple nuevo: 12 meses desde la entrega. La garantía se gestiona directamente "
            "en One Click (Córdoba Shopping) o MacStation (Nuevocentro Shopping)."
        )
    if any(palabra in producto for palabra in ("notebook", "laptop")):
        return (
            "Notebooks: 6 meses desde la entrega. Cubre solo fallas de fábrica; no cubre "
            "caídas, rayones, humedad, mal uso ni software no confiable."
        )
    if "samsung" in producto:
        marca = "Samsung"
    elif "motorola" in producto or producto.startswith("moto "):
        marca = "Motorola"
    elif any(palabra in producto for palabra in ("xiaomi", "redmi", "poco")):
        marca = "Xiaomi"
    else:
        marca = "Productos electrónicos"
    return (
        f"{marca}: 3 meses desde la entrega. Cubre solo fallas de fábrica; no cubre "
        "caídas, rayones, humedad, mal uso ni software no confiable."
    )


def garantias_para_detalle(detalle):
    garantias = []
    for item in detalle or []:
        garantia = _garantia_producto(item.get("nombre"))
        if garantia not in garantias:
            garantias.append(garantia)
    return garantias


def _formatear_fecha_emision(fecha):
    if not fecha:
        return "-"
    try:
        return datetime.fromisoformat(fecha.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return fecha


def html_recibo(cliente, pedido, logo_url=""):
    detalle = pedido.get("detalle") or []
    filas = "".join(
        "<tr>"
        f"<td>{html.escape(item.get('nombre') or '')}{(' · ' + html.escape(item['color'])) if item.get('color') else ''}</td>"
        f"<td style='text-align:center'>{int(item.get('cantidad') or 0)}</td>"
        f"<td style='text-align:right'>{_formatear_usd(item.get('usd_unitario'))}</td>"
        f"<td style='text-align:right'>{_formatear_usd(item.get('usd_subtotal'))}</td>"
        "</tr>"
        for item in detalle
    )
    descuento = int(pedido.get("descuento_usd") or 0)
    descuento_html = (
        f"<p style='margin:4px 0'>Descuentos aplicados: -{_formatear_usd(descuento)}</p>"
        if descuento else ""
    )
    garantias = "".join(f"<li>{html.escape(garantia)}</li>" for garantia in garantias_para_detalle(detalle))
    nombre_cliente = html.escape(f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip() or "Cliente")
    recibo_id = html.escape(pedido.get("recibo_id") or "")
    fecha_emision = html.escape(_formatear_fecha_emision(pedido.get("recibo_emitido_en")))
    return f"""<!doctype html><html lang='es'><body style='margin:0;background:#f2f2f2;font-family:Arial,sans-serif;color:#161616'>
<main style='max-width:680px;margin:24px auto;background:#fff;padding:32px;box-sizing:border-box'>
  <header style='border-bottom:3px solid #c8102e;padding-bottom:18px;margin-bottom:24px'>
    <strong style='font-size:22px;letter-spacing:-1px'>THE TECH ROOM ARG<span style='color:#c8102e'>.</span></strong>
    <p style='margin:14px 0 0;color:#555'>Recibo interno {recibo_id}<br>Emitido el {fecha_emision}</p>
  </header>
  <p>Hola {nombre_cliente},</p><p>Este comprobante resume tu compra.</p>
  <table style='width:100%;border-collapse:collapse;margin:20px 0'>
    <thead><tr style='background:#161616;color:#fff'><th style='text-align:left;padding:10px'>Producto</th><th>Cant.</th><th style='text-align:right'>Unitario</th><th style='text-align:right'>Subtotal</th></tr></thead>
    <tbody>{filas}</tbody>
  </table>
  {descuento_html}
  <p style='font-size:20px;font-weight:700;text-align:right'>Total: {_formatear_usd(pedido.get('total_usd'))}</p>
  <section style='border-top:1px solid #ddd;margin-top:24px;padding-top:18px'><h2 style='font-size:17px'>Garantía</h2><ul>{garantias}</ul>
    <p style='font-size:13px;color:#555'>Para gestionar una garantía, conservá caja y accesorios. Soy intermediario con el importador y te mantendré informado durante el proceso.</p>
  </section>
</main></body></html>"""


def pdf_recibo(cliente, pedido):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    titulo = estilos["Title"]
    titulo.fontName = "Helvetica-Bold"
    titulo.fontSize = 20
    normal = estilos["BodyText"]
    normal.leading = 16
    nombre_cliente = html.escape(
        f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip() or "Cliente"
    )
    elementos = [
        Paragraph('THE TECH ROOM ARG<font color="#c8102e">.</font>', titulo),
        Paragraph(f"Recibo interno {html.escape(pedido.get('recibo_id') or '')}", normal),
        Paragraph(f"Emitido el {_formatear_fecha_emision(pedido.get('recibo_emitido_en'))}", normal),
        Spacer(1, 14),
        Paragraph(f"Cliente: {nombre_cliente}", normal),
        Spacer(1, 12),
    ]
    filas = [["Producto", "Cant.", "Unitario", "Subtotal"]]
    for item in pedido.get("detalle") or []:
        nombre = item.get("nombre") or ""
        if item.get("color"):
            nombre = f"{nombre} - {item['color']}"
        filas.append([nombre, str(item.get("cantidad") or 0), _formatear_usd(item.get("usd_unitario")), _formatear_usd(item.get("usd_subtotal"))])
    tabla = Table(filas, colWidths=[8.1 * cm, 1.4 * cm, 3.2 * cm, 3.2 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#161616")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d0d0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elementos.extend([tabla, Spacer(1, 12)])
    descuento = int(pedido.get("descuento_usd") or 0)
    if descuento:
        elementos.append(Paragraph(f"Descuentos aplicados: -{_formatear_usd(descuento)}", normal))
    elementos.append(Paragraph(f"<b>Total: {_formatear_usd(pedido.get('total_usd'))}</b>", normal))
    elementos.extend([Spacer(1, 16), Paragraph("Garantía", estilos["Heading2"])])
    for garantia in garantias_para_detalle(pedido.get("detalle")):
        elementos.append(Paragraph(f"- {html.escape(garantia)}", normal))
    doc.build(elementos)
    return buffer.getvalue()
