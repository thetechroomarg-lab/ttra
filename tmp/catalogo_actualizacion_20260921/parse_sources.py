import json
import re
import sys
from pathlib import Path


BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parents[1]))
from normalize import separar_variantes, variantes_usadas_desde_detalles


def money(value):
    value = value.strip().replace("$", "").replace("US", "").replace("USD", "")
    if re.search(r"[.,]\d{3}$", value):
        value = value.replace(".", "").replace(",", "")
    else:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def clean_name(value):
    value = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF🇺🇸🇰🇷]", "", value)
    value = value.replace("▪️", "").replace("▪", "").replace("️", "")
    value = re.sub(r"\s+", " ", value).strip(" -\t")
    return value


def colors(value):
    return separar_variantes(value)


def add(items, name, cost, provider, item_colors=None):
    row = {"nombre": clean_name(name), "costo": round(float(cost), 2), "proveedor": provider}
    if item_colors:
        row["colores"] = list(dict.fromkeys(item_colors))
    items.append(row)


def parse_az():
    text = (BASE / "az.txt").read_text(encoding="utf-8")
    items, filtered, doubts = [], [], []
    pattern = re.compile(
        r"(?m)^([^\n]+)\nColores:\s*([^\n]*)\n\$([\d.]+)(?:\s*[–-]\s*\$([\d.]+))?\s+\$[\d.]+"
    )
    for m in pattern.finditer(text):
        name = clean_name(m.group(1))
        if re.search(r"(?i)caja\s+(?:abollada|manchada)|sin stock", name):
            filtered.append({"nombre": name, "motivo": "caja dañada o sin stock"})
            continue
        if m.group(4):
            # Las bandas corresponden a colores; se usa el costo mínimo disponible.
            cost = min(money(m.group(3)), money(m.group(4)))
        else:
            cost = money(m.group(3))
        if re.search(r"(?i)\bslim\b", name) and re.search(
            r"(?i)^(?:note|poco|redmi|xiaomi|moto|motorola|samsung|a\d{2}|s\d{2})", name
        ):
            name = re.sub(r"(?i)\bslim\b", "(s/ cargador)", name)
        add(items, name, cost, "az", colors(m.group(2)))
    return items, filtered, doubts


def parse_oh():
    items, filtered, doubts = [], [], []
    for line in (BASE / "oh.txt").read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 4:
            continue
        category, name, price, stock = parts[:4]
        color = parts[4] if len(parts) > 4 else ""
        if stock.upper() not in {"SI", "SÍ"}:
            filtered.append({"nombre": clean_name(name), "motivo": "sin stock"})
            continue
        try:
            cost = money(price) / 1520
        except ValueError:
            doubts.append({"texto": line, "motivo": "sin costo numérico"})
            continue
        add(items, name, cost, "oh", colors(color))
    return items, filtered, doubts


def parse_va():
    text = (BASE / "va.txt").read_text(encoding="utf-8")
    items, filtered, doubts = [], [], []
    pattern = re.compile(r"(?m)^\s*(.+?)\s+US\$([\d.,]+)\s*$")
    for m in pattern.finditer(text):
        name = clean_name(m.group(1))
        tail = text[m.end():].splitlines()
        color_line = ""
        # Primera línea no vacía después del renglón en pesos.
        skipped_pesos = False
        for line in tail[:5]:
            val = clean_name(line)
            if not val:
                continue
            if not skipped_pesos and re.fullmatch(r"\$?\s*[\d.]+", val):
                skipped_pesos = True
                continue
            color_line = val
            break
        if re.search(r"(?i)\bslim\b", name):
            name = re.sub(r"(?i)\bslim\b", "(s/ cargador)", name)
        add(items, name, money(m.group(2)), "va", colors(color_line))
    return items, filtered, doubts


def parse_fr():
    items, filtered, doubts = [], [], []
    used = False
    raw_lines = (BASE / "fr.txt").read_text(encoding="utf-8").splitlines()
    lines = []
    index = 0
    while index < len(raw_lines):
        line = raw_lines[index]
        if line.startswith('"') and line.count('"') == 1 and index + 1 < len(raw_lines):
            line = line.lstrip('"') + raw_lines[index + 1].lstrip('"')
            index += 1
        lines.append(line)
        index += 1
    for pos, line in enumerate(lines):
        upper = line.upper()
        if "IPHONE USADO" in upper:
            used = True
            continue
        if used and re.search(r"MACBOOK|PERFUME|REPUESTOS|M[ÓO]DULOS", upper):
            used = False
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) < 2:
            continue
        name = clean_name(parts[0])
        if not name or re.search(r"(?i)iphone nuevos|iphone cpo|airpods y audio|apple watch", name):
            continue
        nums = []
        for p in parts[1:]:
            if re.fullmatch(r"\d+(?:[.,]\d+)?", p):
                nums.append(p)
        if re.search(r"(?i)sin stock", name) or (parts[-1].replace("$", "").replace(",", "").strip() == "0"):
            filtered.append({"nombre": name, "motivo": "sin stock"})
            continue
        if not nums:
            continue
        cost = money(nums[0])
        if re.search(r"(?i)^caja vac|perfume|m[oó]dulo|bater[ií]a|vaper", name):
            filtered.append({"nombre": name, "motivo": "no corresponde al catálogo de productos"})
            continue
        item_colors = []
        mt = re.search(r"\s*\(([^()]*)\)\s*$", name)
        if mt and not re.search(r"\d+%|caja|garant|usad", mt.group(1), re.I):
            item_colors = colors(mt.group(1))
            name = name[:mt.start()].strip()
        if used and "IPHONE" in name.upper():
            details = []
            for detail in lines[pos + 1:]:
                if re.search(r"\t\s*\d+(?:[.,]\d+)?\s*\t", detail):
                    break
                details.append(detail)
            item_colors = variantes_usadas_desde_detalles(details)
        add(items, name, cost, "fr", item_colors)
    return items, filtered, doubts


def parse_em():
    items, filtered, doubts = [], [], []
    for line in (BASE / "em.txt").read_text(encoding="utf-8").splitlines():
        if "USD" not in line:
            continue
        status = "Disponible" if re.search(r"\bDisponible\s*$", line) and "No Disponible" not in line else "otro"
        price_m = re.search(r"USD([\d.]+,\d{2})", line)
        if not price_m:
            doubts.append({"texto": clean_name(line), "motivo": "sin costo numérico"})
            continue
        left = line[:price_m.start()].strip()
        cols = [x.strip() for x in re.split(r"\s{2,}", left) if x.strip()]
        if not cols:
            continue
        product = cols[0]
        size = cols[1] if len(cols) >= 2 else ""
        color = cols[2] if len(cols) >= 3 else ""
        color_words = re.compile(r"(?i)^(?:black|silver|blue|purple|midnight|blanco|white|negro|rojo|azul|gold|rose gold)$")
        if len(cols) == 2 and color_words.match(size):
            color, size = size, ""
        name = f"{product} {size}".strip()
        if status != "Disponible":
            filtered.append({"nombre": clean_name(name), "motivo": "no disponible o en tránsito"})
            continue
        add(items, name, money(price_m.group(1)), "em", colors(color))
    return items, filtered, doubts


def parse_ba():
    lines = (BASE / "ba.txt").read_text(encoding="utf-8").splitlines()
    items, filtered, doubts = [], [], []
    pending = ""
    row_re = re.compile(r"^(.*?)\s+(\d+)\s+\$(\d+)\s*$")
    for line in lines:
        m = row_re.match(line)
        stripped = line.strip()
        if not m:
            if stripped and not re.search(r"Codigo|NOTEBOOK|CANTIDAD|DOLARES|ENTRANTE|Columna|VARIOS PRODUCTOS", stripped, re.I):
                pending = stripped
            continue
        left, qty, cost = m.group(1).strip(), int(m.group(2)), float(m.group(3))
        # El texto puede venir en la línea anterior cuando la celda quedó envuelta.
        if not left and pending:
            left = pending
        # Quitar códigos de inventario iniciales sin tocar el nombre comercial.
        left = re.sub(r"^(?:[A-Z0-9][A-Z0-9.\-]*|\d{6}|JBL)\s{2,}", "", left).strip()
        name = clean_name(left)
        if not name:
            doubts.append({"texto": line, "motivo": "producto no extraído del PDF"})
            continue
        if qty == 0:
            filtered.append({"nombre": name, "motivo": "stock 0"})
            continue
        add(items, name, cost, "ba")
    return items, filtered, doubts


def merge_same_source(items):
    grouped = {}
    for row in items:
        key = re.sub(r"\s+", " ", row["nombre"]).casefold()
        if key not in grouped or row["costo"] < grouped[key]["costo"]:
            grouped[key] = row
        elif row.get("colores"):
            grouped[key].setdefault("colores", [])
            grouped[key]["colores"] = list(dict.fromkeys(grouped[key]["colores"] + row["colores"]))
    return list(grouped.values())


all_items, all_filtered, all_doubts = [], [], []
for provider, parser in [("az", parse_az), ("em", parse_em), ("oh", parse_oh), ("ba", parse_ba), ("va", parse_va), ("fr", parse_fr)]:
    items, filtered, doubts = parser()
    items = merge_same_source(items)
    payload = {"items": items, "filtrados": filtered, "dudas_precio": doubts}
    (BASE / f"entrada_{provider}_nueva.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(provider, len(items), len(filtered), len(doubts))
    all_items.extend(items)
    all_filtered.extend(filtered)
    all_doubts.extend(doubts)

master = {"items": all_items, "filtrados": all_filtered, "dudas_precio": all_doubts}
(BASE / "entrada_master_nueva.json").write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
print("master", len(all_items), len(all_filtered), len(all_doubts))
