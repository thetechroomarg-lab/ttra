import html
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _formatear_usd(valor):
    return f"U$D {int(valor or 0):,}".replace(",", ".")


def _garantia_producto(nombre):
    producto = (nombre or "").lower()
    if any(palabra in producto for palabra in ("iphone", "ipad", "macbook", "imac", "airpods", "apple watch")):
        return (
            "Apple: 1 año de garantía oficial mundial desde la activación. Cubre fallas de fábrica o "
            "funcionamiento interno; no cubre golpes, líquidos, mal uso ni desgaste. La gestión se realiza "
            "directamente con Apple, por ejemplo en One Click (Córdoba Shopping) o MacStation. Apple define "
            "reparación o reemplazo. Los equipos son nuevos y sellados; una preactivación excepcional puede "
            "reducir la vigencia. Se recomienda usar cargadores originales."
        )
    if any(palabra in producto for palabra in ("notebook", "laptop")):
        return (
            "Notebooks: 6 meses por fallas de funcionamiento. Requiere verificación técnica previa, de hasta "
            "5 días hábiles; la resolución puede demorar hasta 30 días. No cubre golpes, líquidos, negligencia "
            "ni software que afecte el rendimiento. Si corresponde, se repone el mismo modelo; sin stock se "
            "coordina uno equivalente con ajuste de diferencia."
        )
    if "samsung" in producto:
        return (
            "Samsung: 3 meses desde la entrega por fallas de fábrica. No cubre caídas, rayones, humedad, apps "
            "no confiables, mal uso, sobrecargas o cortocircuitos; tampoco hay reembolso por disconformidad. "
            "Retirar films, etiquetas o números de serie anula la garantía. Display y accesorios: 7 días. "
            "Presentar caja, accesorios, sin cuentas activas y nota con la falla. Diagnóstico: hasta 5 días hábiles; "
            "resolución estimada: hasta 1 mes. Si falla dentro de 2 días de la revisión, corresponde cambio directo. "
            "The Tech Room Arg intermedia con el importador."
        )
    elif "motorola" in producto or producto.startswith("moto "):
        return (
            "Motorola: 3 meses desde la entrega por defectos de fábrica. No cubre golpes, rayaduras, humedad, "
            "apps no seguras, mal manejo, variaciones de voltaje ni cortocircuitos; tampoco hay devolución por "
            "disconformidad. Remover films, etiquetas de garantía o números de serie anula la garantía. Display y "
            "accesorios: 7 días. Presentar caja, accesorios, sin cuentas activas y nota con la falla. Diagnóstico: "
            "hasta 5 días hábiles; resolución estimada: hasta 1 mes. Si falla dentro de 2 días de la revisión, "
            "corresponde cambio directo. The Tech Room Arg intermedia con el importador."
        )
    elif any(palabra in producto for palabra in ("xiaomi", "redmi", "poco")):
        return (
            "Xiaomi: 3 meses desde la entrega por desperfectos de fábrica. No cubre golpes, rayaduras, humedad, "
            "apps inseguras, mal uso, variaciones eléctricas ni manipulación indebida; tampoco hay devolución por "
            "disconformidad. Remover etiquetas, films o el número de serie anula la garantía. Display y accesorios: "
            "7 días. Presentar caja, accesorios, sin cuentas activas y nota con la falla. Diagnóstico: hasta 5 días "
            "hábiles; resolución estimada: hasta 1 mes. Si falla dentro de 2 días de la revisión, corresponde cambio "
            "directo. The Tech Room Arg intermedia con el importador."
        )
    return (
        "Accesorios, consolas y parlantes no Apple: 1 mes desde la entrega. No cubre golpes, caídas, humedad, "
        "mala conexión, sobrecargas, uso indebido, modificaciones, intentos de reparación ni fuentes no originales; "
        "no hay devolución por disconformidad. Presentar embalaje, caja, accesorios y nota con la falla. Revisión: "
        "hasta 5 días hábiles; reparación o reposición: hasta 1 mes. No hay cambios inmediatos sin revisión previa. "
        "The Tech Room Arg intermedia con el importador."
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
        f"<td style='padding:10px 8px;vertical-align:top;word-break:break-word;overflow-wrap:anywhere'>{html.escape(item.get('nombre') or '')}{(' · ' + html.escape(item['color'])) if item.get('color') else ''}</td>"
        f"<td style='padding:10px 6px;text-align:center;vertical-align:top'>{int(item.get('cantidad') or 0)}</td>"
        f"<td style='padding:10px 6px;text-align:right;vertical-align:top;white-space:nowrap'>{_formatear_usd(item.get('usd_unitario'))}</td>"
        f"<td style='padding:10px 6px;text-align:right;vertical-align:top;white-space:nowrap'>{_formatear_usd(item.get('usd_subtotal'))}</td>"
        "</tr>"
        for item in detalle
    )
    descuento = int(pedido.get("descuento_usd") or 0)
    descuento_html = (
        f"<p style='margin:4px 0'>Descuentos aplicados: -{_formatear_usd(descuento)}</p>"
        if descuento else ""
    )
    garantias = "".join(f"<li>{html.escape(garantia)}</li>" for garantia in garantias_para_detalle(detalle))
    nombres = str(cliente.get("nombre") or "").strip().split()
    primer_nombre = html.escape(nombres[0] if nombres else "Cliente")
    recibo_id = html.escape(pedido.get("recibo_id") or "")
    fecha_emision = html.escape(_formatear_fecha_emision(pedido.get("recibo_emitido_en")))
    entregado_por_alejo_html = (
        "<p style='margin:14px 0 0;font-weight:700'>Entregado por Alejo</p>"
        if pedido.get("entregado_por_cadete") else ""
    )
    return f"""<!doctype html><html lang='es'><body style='margin:0;background:#f2f2f2;font-family:Arial,sans-serif;color:#161616'>
<main style='max-width:680px;margin:24px auto;background:#fff;padding:32px;box-sizing:border-box'>
  <header style='border-bottom:3px solid #c8102e;padding-bottom:18px;margin-bottom:24px'>
    <strong style='font-size:22px;letter-spacing:-1px'>THE TECH ROOM ARG<span style='color:#c8102e'>.</span></strong>
    <p style='margin:14px 0 0;color:#555'>Recibo interno {recibo_id}<br>Emitido el {fecha_emision}</p>
    {entregado_por_alejo_html}
  </header>
  <p>Hola {primer_nombre},</p><p>Este comprobante resume tu compra.</p>
  <table role='presentation' style='width:100%;border-collapse:collapse;table-layout:fixed;margin:20px 0'>
    <colgroup><col style='width:52%'><col style='width:10%'><col style='width:19%'><col style='width:19%'></colgroup>
    <thead><tr style='background:#161616;color:#fff'><th style='text-align:left;padding:10px 8px'>Producto</th><th style='padding:10px 6px'>Cant.</th><th style='text-align:right;padding:10px 6px'>Unitario</th><th style='text-align:right;padding:10px 6px'>Subtotal</th></tr></thead>
    <tbody>{filas}</tbody>
  </table>
  {descuento_html}
  <p style='font-size:20px;font-weight:700;text-align:right'>Total: {_formatear_usd(pedido.get('total_usd'))}</p>
  <section style='border-top:1px solid #ddd;margin-top:24px;padding-top:18px'><h2 style='font-size:17px'>Garantía</h2><ul>{garantias}</ul>
    <p style='font-size:13px;color:#555'>Para gestionar una garantía, conservá caja y accesorios. Soy intermediario con el importador y te mantendré informado durante el proceso.</p>
  </section>
</main></body></html>"""


def _parrafo_celda(valor, estilo):
    return Paragraph(html.escape(str(valor or "")), estilo)


def _estilo_celda_encabezado():
    return ParagraphStyle(
        "EncabezadoRecibo", fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, textColor=colors.white, wordWrap="CJK",
    )


def _fotos_para_pdf(fotos):
    imagenes = []
    for foto in fotos or []:
        try:
            imagen = Image(BytesIO(foto))
            imagen._restrictSize(8 * cm, 8 * cm)
            imagenes.append(imagen)
        except Exception:
            continue
    return imagenes


def pdf_recibo(cliente, pedido, fotos=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    titulo = estilos["Title"]
    titulo.fontName = "Helvetica-Bold"
    titulo.fontSize = 20
    normal = estilos["BodyText"]
    normal.leading = 16
    celda = ParagraphStyle("CeldaRecibo", parent=normal, fontSize=8.5, leading=11, wordWrap="CJK")
    encabezado = _estilo_celda_encabezado()
    nombre_cliente = html.escape(
        f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip() or "Cliente"
    )
    elementos = [
        Paragraph('THE TECH ROOM ARG<font color="#c8102e">.</font>', titulo),
        Paragraph(f"Recibo interno {html.escape(pedido.get('recibo_id') or '')}", normal),
        Paragraph(f"Emitido el {_formatear_fecha_emision(pedido.get('recibo_emitido_en'))}", normal),
    ]
    if pedido.get("entregado_por_cadete"):
        elementos.append(Paragraph("<b>Entregado por Alejo</b>", normal))
    elementos.extend([
        Spacer(1, 14),
        Paragraph(f"Cliente: {nombre_cliente}", normal),
        Spacer(1, 12),
    ])
    filas = [[_parrafo_celda("Producto", encabezado), _parrafo_celda("Cant.", encabezado),
              _parrafo_celda("Unitario", encabezado), _parrafo_celda("Subtotal", encabezado)]]
    for item in pedido.get("detalle") or []:
        nombre = item.get("nombre") or ""
        if item.get("color"):
            nombre = f"{nombre} - {item['color']}"
        filas.append([
            _parrafo_celda(nombre, celda),
            _parrafo_celda(item.get("cantidad") or 0, celda),
            _parrafo_celda(_formatear_usd(item.get("usd_unitario")), celda),
            _parrafo_celda(_formatear_usd(item.get("usd_subtotal")), celda),
        ])
    tabla = Table(filas, colWidths=[8.0 * cm, 1.3 * cm, 3.25 * cm, 3.25 * cm], repeatRows=1)
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
    imagenes = _fotos_para_pdf(fotos)
    if imagenes:
        elementos.extend([Spacer(1, 16), Paragraph("Fotos de entrega", estilos["Heading2"])])
        filas_fotos = [imagenes[indice:indice + 2] for indice in range(0, len(imagenes), 2)]
        elementos.append(Table(filas_fotos, colWidths=[8.0 * cm, 8.0 * cm], hAlign="LEFT"))
    doc.build(elementos)
    return buffer.getvalue()
