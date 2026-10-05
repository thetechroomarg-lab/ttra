import html
from pathlib import Path
from urllib.parse import quote
from io import BytesIO
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import garantias

_ZONA_ARGENTINA = timezone(timedelta(hours=-3))


def _formatear_usd(valor):
    return f"U$D {int(valor or 0):,}".replace(",", ".")


def garantias_para_detalle(detalle):
    """Texto completo de cada garantía del pedido, sin repetir (misma fuente que la web)."""
    return [garantias.texto_plano(clave) for clave in garantias.claves_para_detalle(detalle)]


_ACENTO = "#c8102e"
LOGO_PATH = Path(__file__).resolve().parent / "static" / "icon-512.png"
GRACIAS = "Gracias por confiar en The Tech Room Arg."
GRACIAS_DETALLE = "Fue un gusto atenderte. Volvé cuando quieras, acá te espero."
FIRMA = "Vladimir · The Tech Room Arg"


def _garantias_html(detalle):
    datos = garantias.cargar()
    partes = []
    for clave in garantias.claves_para_detalle(detalle):
        g = datos[clave]
        bloques = []
        if g.get("alcance"):
            bloques.append(f"<p style='margin:14px 0 0;color:#444;font-size:14px;line-height:1.6'>{html.escape(g['alcance'])}</p>")
        for seccion in garantias.secciones(g):
            filas = []
            if seccion["titulo"]:
                filas.append(
                    f"<p style='margin:20px 0 8px;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase'>"
                    f"<span style='color:{_ACENTO}'>{seccion['indice']}</span>&nbsp;&nbsp;{html.escape(seccion['titulo'])}</p>"
                )
            for tipo, valor in seccion["lineas"]:
                if tipo == "item":
                    filas.append(f"<p style='margin:0 0 6px;padding-left:16px;text-indent:-16px;font-size:14px;line-height:1.55'><span style='color:{_ACENTO}'>&ndash;</span>&nbsp;&nbsp;{html.escape(valor)}</p>")
                elif tipo == "etiqueta":
                    filas.append(f"<p style='margin:10px 0 6px;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#777'>{html.escape(valor)}</p>")
                elif tipo == "destacado":
                    filas.append(f"<p style='margin:0 0 8px;padding:10px 12px;background:#f3f1ea;font-size:14px;font-weight:700'>{html.escape(valor)}</p>")
                elif tipo == "excepcion":
                    filas.append(f"<p style='margin:0 0 10px;padding:12px 14px;background:#161616;color:#fff;border-top:3px solid {_ACENTO};font-size:14px;font-weight:700'>{html.escape(valor)}</p>")
                elif tipo == "nota":
                    filas.append(f"<p style='margin:8px 0 0;padding:10px 12px;background:#f3f1ea;font-size:13px;color:#444'>{html.escape(valor)}</p>")
                elif tipo == "enlace":
                    texto, url = valor
                    filas.append(f"<p style='margin:0 0 6px;font-size:13px'><a href='{html.escape(url)}' style='color:{_ACENTO};font-weight:700'>{html.escape(texto)}</a></p>")
                elif tipo == "fuerte":
                    filas.append(f"<p style='margin:10px 0 4px;font-size:14px;font-weight:700'>{html.escape(valor)}</p>")
                elif tipo == "firma":
                    filas.append(f"<p style='margin:8px 0 0;font-family:Georgia,serif;font-style:italic;color:#666'>{html.escape(valor)}</p>")
                else:
                    filas.append(f"<p style='margin:0 0 8px;font-size:14px;line-height:1.6'>{html.escape(valor)}</p>")
            bloques.append("".join(filas))
        partes.append(
            "<article style='margin:22px 0 0;border:1px solid #e2e0d8'>"
            f"<div style='background:#161616;color:#fff;padding:16px 18px'>"
            f"<p style='margin:0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#bbb'>Garantía</p>"
            f"<p style='margin:4px 0 0;font-size:22px;font-weight:700'>{html.escape(g['titulo'])}"
            f"<span style='float:right;color:#ff715b'>{html.escape(garantias.plazo_texto(g))}</span></p>"
            f"<p style='margin:6px 0 0;font-size:12px;color:#bbb'>{html.escape(g['desde'])}</p></div>"
            f"<div style='padding:4px 18px 18px'>{''.join(bloques)}</div></article>"
        )
    return "".join(partes)


def _formatear_fecha_emision(fecha):
    if not fecha:
        return "-"
    try:
        momento = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        return momento.astimezone(_ZONA_ARGENTINA).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return fecha


def _link_whatsapp(link):
    texto = f"Te paso la tienda donde compro tecnología, registrate con mi link: {link}"
    return f"https://wa.me/?text={quote(texto)}"


def _beneficios_html(beneficios):
    """Sellos de fidelidad y link de referido. Sin datos, no hay sección."""
    if not beneficios:
        return ""
    total = int(beneficios.get("sellos_para_premio") or 0)
    sellos = min(int(beneficios.get("sellos") or 0), total)
    premio = _formatear_usd(beneficios.get("premio_fidelidad_usd"))
    puntos = "".join(
        f"<span style='display:inline-block;width:22px;height:22px;border-radius:50%;margin-right:6px;"
        f"background:{_ACENTO if i < sellos else '#e4e4e4'}'></span>"
        for i in range(total)
    )
    if sellos >= total:
        texto_sellos = (f"Completaste las {total} compras: tenés {premio} de descuento para tu próxima compra. "
                        "Lo ves en tu perfil de la web.")
    else:
        texto_sellos = f"Llevás {sellos} de {total} compras. Al llegar a {total} te ganás {premio} de descuento."
    link = beneficios.get("link_referido")
    referido_html = (
        "<p style='margin:16px 0 6px;font-weight:700'>Invitá a tus amigos</p>"
        f"<p style='margin:0 0 10px;font-size:14px;color:#555'>Por cada amigo que se registre con tu link y compre, "
        f"ganás {_formatear_usd(beneficios.get('premio_referido_usd'))} para tu próxima compra.</p>"
        f"<a href='{html.escape(_link_whatsapp(link), quote=True)}' style='display:inline-block;background:{_ACENTO};color:#fff;"
        "text-decoration:none;font-weight:700;padding:10px 16px'>Compartir por WhatsApp</a>"
        f"<p style='margin:8px 0 0;font-size:12px;color:#888;word-break:break-all'>{html.escape(link)}</p>"
    ) if link else ""
    return f"""<section style='border-top:1px solid #ddd;margin-top:24px;padding-top:18px'><h2 style='font-size:17px;margin:0 0 10px'>Tus beneficios</h2>
    <div>{puntos}</div>
    <p style='margin:10px 0 0;font-size:14px'>{texto_sellos}</p>
    {referido_html}
  </section>"""


def html_recibo(cliente, pedido, logo_url="", beneficios=None):
    # El logo del mail se dibuja con HTML (sin imágenes externas): muchos
    # clientes de correo bloquean imágenes y quedaría un recuadro roto.
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
    garantias_html = _garantias_html(detalle)
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
    <table role='presentation' cellpadding='0' cellspacing='0' style='border-collapse:collapse'><tr>
      <td style='background:#000;width:84px;height:84px;padding:0 0 0 12px;vertical-align:middle'>
        <div style='width:62px;color:#fff;font:900 17px/0.92 Arial,Helvetica,sans-serif;letter-spacing:-1px'>THE TECH ROOM ARG<span style='color:#c8102e'>.</span></div>
      </td></tr></table>
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
  <section style='border-top:1px solid #ddd;margin-top:24px;padding-top:18px'><h2 style='font-size:17px;margin:0'>Garantía de tu compra</h2>
    <p style='font-size:13px;color:#555;margin:6px 0 0'>Estas son las condiciones de garantía de los productos que compraste.</p>
    {garantias_html}
  </section>
  {_beneficios_html(beneficios)}
  <footer style='margin-top:28px;padding:22px 20px;background:#161616;color:#fff;border-top:3px solid #c8102e'>
    <p style='margin:0;font-size:18px;font-weight:700'>{GRACIAS}</p>
    <p style='margin:8px 0 0;font-size:14px;color:#ddd'>{GRACIAS_DETALLE}</p>
    <p style='margin:12px 0 0;font-family:Georgia,serif;font-style:italic;color:#bbb'>{FIRMA}</p>
  </footer>
  <p style='font-size:12px;color:#888;margin-top:14px'>Documento no válido como factura.</p>
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


def _garantias_pdf(detalle, normal):
    """Una ficha por garantía: cabecera oscura con el plazo y bloques numerados."""
    claves = garantias.claves_para_detalle(detalle)
    if not claves:
        return []
    acento = colors.HexColor(_ACENTO)
    gris = colors.HexColor("#666666")
    base = ParagraphStyle("GarBase", parent=normal, fontSize=9.5, leading=13.5)
    titulo_seccion = ParagraphStyle("GarSeccion", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=11,
                                    spaceBefore=11, spaceAfter=5)
    item = ParagraphStyle("GarItem", parent=base, leftIndent=12, firstLineIndent=-12, spaceAfter=3)
    etiqueta = ParagraphStyle("GarEtiqueta", parent=base, fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                              textColor=gris, spaceBefore=4, spaceAfter=3)
    parrafo = ParagraphStyle("GarParrafo", parent=base, spaceAfter=4)
    fuerte = ParagraphStyle("GarFuerte", parent=base, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=3)
    firma = ParagraphStyle("GarFirma", parent=base, fontName="Times-Italic", fontSize=10.5, textColor=gris, spaceBefore=4)
    caja = ParagraphStyle("GarCaja", parent=base, fontSize=9)
    caja_invertida = ParagraphStyle("GarCajaInv", parent=caja, textColor=colors.white)
    cab_titulo = ParagraphStyle("GarCabTitulo", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18,
                                textColor=colors.white)
    cab_plazo = ParagraphStyle("GarCabPlazo", parent=cab_titulo, alignment=2, textColor=colors.HexColor("#ff715b"))
    cab_desde = ParagraphStyle("GarCabDesde", parent=base, fontSize=8, leading=10, textColor=colors.HexColor("#bbbbbb"))

    def recuadro(contenido, fondo="#f3f1ea"):
        tabla = Table([[contenido]], colWidths=[17.9 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fondo)),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tabla

    elementos = [
        CondPageBreak(6 * cm),
        Spacer(1, 18),
        Paragraph("Garantía de tu compra", ParagraphStyle("GarH", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=18)),
        Paragraph("Estas son las condiciones de garantía de los productos que compraste.",
                  ParagraphStyle("GarIntro", parent=base, textColor=gris)),
    ]
    datos = garantias.cargar()
    for clave in claves:
        g = datos[clave]
        cabecera = Table([
            [Paragraph(f"Garantía {html.escape(g['titulo'])}", cab_titulo),
             Paragraph(html.escape(garantias.plazo_texto(g)), cab_plazo)],
            [Paragraph(html.escape(g["desde"]), cab_desde), ""],
        ], colWidths=[12.4 * cm, 5.5 * cm])
        cabecera.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#161616")),
            ("SPAN", (0, 1), (1, 1)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
            ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ("LINEBELOW", (0, -1), (-1, -1), 2, acento),
        ]))
        ficha = [Spacer(1, 4)]
        if g.get("alcance"):
            ficha.append(Paragraph(html.escape(g["alcance"]), ParagraphStyle("GarAlcance", parent=parrafo, textColor=gris)))
        for seccion in garantias.secciones(g):
            if seccion["titulo"]:
                ficha.append(Paragraph(
                    f'<font color="{_ACENTO}">{seccion["indice"]}</font>&nbsp;&nbsp;&nbsp;{html.escape(seccion["titulo"].upper())}',
                    titulo_seccion))
            for tipo, valor in seccion["lineas"]:
                if tipo == "item":
                    ficha.append(Paragraph(f'<font color="{_ACENTO}">–</font>&nbsp;&nbsp;{html.escape(valor)}', item))
                elif tipo == "etiqueta":
                    ficha.append(Paragraph(html.escape(valor.upper()), etiqueta))
                elif tipo == "destacado":
                    ficha.append(recuadro(Paragraph(f"<b>{html.escape(valor)}</b>", caja)))
                    ficha.append(Spacer(1, 3))
                elif tipo == "excepcion":
                    ficha.append(recuadro(Paragraph(f"<b>{html.escape(valor)}</b>", caja_invertida), "#161616"))
                    ficha.append(Spacer(1, 4))
                elif tipo == "nota":
                    ficha.append(Spacer(1, 3))
                    ficha.append(recuadro(Paragraph(html.escape(valor), caja)))
                elif tipo == "enlace":
                    texto, url = valor
                    # La dirección se imprime solo si es corta; si no, queda el enlace.
                    visible = f' <font color="#888888" size="8">{html.escape(url)}</font>' if len(url) <= 45 else ""
                    ficha.append(Paragraph(
                        f'&nbsp;&nbsp;&nbsp;<link href="{html.escape(url)}"><font color="{_ACENTO}"><u>{html.escape(texto)}</u></font></link>{visible}',
                        base))
                elif tipo == "fuerte":
                    ficha.append(Paragraph(html.escape(valor), fuerte))
                elif tipo == "firma":
                    ficha.append(Paragraph(html.escape(valor), firma))
                else:
                    ficha.append(Paragraph(html.escape(valor), parrafo))
        elementos.extend([Spacer(1, 14), KeepTogether([cabecera, *ficha[:3]]), *ficha[3:]])
    return elementos


def _cierre_pdf(normal):
    """Bloque final de agradecimiento, siempre presente."""
    blanco = ParagraphStyle("CierreTitulo", parent=normal, fontName="Helvetica-Bold", fontSize=14, leading=18,
                            textColor=colors.white)
    detalle = ParagraphStyle("CierreDetalle", parent=normal, fontSize=10, leading=14, textColor=colors.HexColor("#dddddd"))
    firma = ParagraphStyle("CierreFirma", parent=normal, fontName="Times-Italic", fontSize=11, textColor=colors.HexColor("#bbbbbb"))
    tabla = Table([[[Paragraph(GRACIAS, blanco), Spacer(1, 4), Paragraph(GRACIAS_DETALLE, detalle),
                     Spacer(1, 6), Paragraph(FIRMA, firma)]]], colWidths=[17.9 * cm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#161616")),
        ("LINEABOVE", (0, 0), (-1, 0), 3, colors.HexColor(_ACENTO)),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return KeepTogether([tabla])


def _pie_de_pagina(canvas, doc):
    """En cada página: agradecimiento a la izquierda y número de página a la derecha."""
    canvas.saveState()
    ancho = doc.pagesize[0]
    y = 0.9 * cm
    canvas.setStrokeColor(colors.HexColor("#dddddd"))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, y + 10, ancho - doc.rightMargin, y + 10)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(doc.leftMargin, y, f"{GRACIAS} Volvé cuando quieras.")
    canvas.drawRightString(ancho - doc.rightMargin, y, f"thetechroomarg.com  ·  {doc.page}")
    canvas.restoreState()


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
    datos_recibo = [
        Paragraph(f"<b>Recibo interno {html.escape(pedido.get('recibo_id') or '')}</b>", normal),
        Paragraph(f"Emitido el {_formatear_fecha_emision(pedido.get('recibo_emitido_en'))}", normal),
    ]
    if LOGO_PATH.exists():
        cabecera = Table([[Image(str(LOGO_PATH), width=2.6 * cm, height=2.6 * cm), datos_recibo]],
                         colWidths=[3.2 * cm, 14.7 * cm], hAlign="LEFT")
        cabecera.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(_ACENTO)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elementos = [cabecera]
    else:
        elementos = [Paragraph('THE TECH ROOM ARG<font color="#c8102e">.</font>', titulo), *datos_recibo]
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
    elementos.extend(_garantias_pdf(pedido.get("detalle"), normal))
    elementos.extend([Spacer(1, 22), _cierre_pdf(normal), Spacer(1, 10),
        Paragraph("Documento no válido como factura.", ParagraphStyle("Leyenda", parent=normal, fontSize=8, textColor=colors.HexColor("#888888"))),
    ])
    imagenes = _fotos_para_pdf(fotos)
    if imagenes:
        elementos.extend([Spacer(1, 16), Paragraph("Fotos de entrega", estilos["Heading2"])])
        filas_fotos = [imagenes[indice:indice + 2] for indice in range(0, len(imagenes), 2)]
        elementos.append(Table(filas_fotos, colWidths=[8.0 * cm, 8.0 * cm], hAlign="LEFT"))
    doc.build(elementos, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()
