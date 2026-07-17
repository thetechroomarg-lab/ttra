import openpyxl


def escribir_xlsx(lista, reporte, ruta):
    wb = openpyxl.Workbook()

    hoja = wb.active
    hoja.title = "Lista"
    hoja.append(["Nombre", "Link Google Imágenes", "País", "Precio"])
    for fila in lista:
        hoja.append([fila["nombre"], fila["link"], fila["pais"], fila["precio"]])

    rep = wb.create_sheet("Reporte")

    rep.append(["Filtrados"])
    rep.append(["Nombre", "Motivo"])
    for f in reporte.get("filtrados", []):
        rep.append([f.get("nombre", ""), f.get("motivo", "")])
    rep.append([])

    rep.append(["Posibles duplicados (revisar)"])
    rep.append(["Nombre A", "Nombre B", "Similitud"])
    for d in reporte.get("duplicados_posibles", []):
        rep.append([d.get("nombre_a", ""), d.get("nombre_b", ""), d.get("similitud", "")])
    rep.append([])

    rep.append(["Dudas de precio"])
    rep.append(["Texto", "Motivo"])
    for x in reporte.get("dudas_precio", []):
        rep.append([x.get("texto", ""), x.get("motivo", "")])

    wb.save(ruta)
