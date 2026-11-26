"""Saldo a favor del cliente (en dólares).

Si un cliente paga de más, esa plata queda a su favor para siempre. Se
descuenta recién cuando se envía el recibo de una compra nueva (igual que los
descuentos de cupones: ver cupones.py), nunca antes.

El saldo no es una columna: es la suma de movimientos de la tabla
`saldo_favor_movimientos` (solo se agregan filas, nunca se editan). Así no hay
lecturas-y-escrituras que se pisen y cada peso tiene su origen anotado.

    create table saldo_favor_movimientos (
      id uuid primary key default gen_random_uuid(),
      cliente_id uuid not null references clientes(id),
      monto_usd numeric(12,2) not null,   -- + acredita, - consume
      motivo text,
      pedido_id uuid,                      -- compra que lo consumió
      creado_por text,
      creado_en timestamptz not null default now()
    );
    create index on saldo_favor_movimientos (cliente_id);
    create unique index on saldo_favor_movimientos (pedido_id) where monto_usd < 0;
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TABLA = "saldo_favor_movimientos"
CENTAVO = Decimal("0.01")
TOPE_MOVIMIENTO_USD = Decimal("1000000")


def _monto(valor):
    try:
        n = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValueError("Ingresá un monto válido.") from None
    if not n.is_finite():
        raise ValueError("Ingresá un monto válido.")
    return n.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _filas(client, cliente_id):
    if not cliente_id:
        return []
    return client.table(TABLA).select("*").eq("cliente_id", cliente_id).execute().data or []


def saldo(client, cliente_id):
    """Saldo disponible en USD (nunca negativo)."""
    try:
        total = sum((Decimal(str(f.get("monto_usd") or 0)) for f in _filas(client, cliente_id)), Decimal(0))
    except (InvalidOperation, ValueError):
        return Decimal(0)
    return max(total, Decimal(0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def movimientos(client, cliente_id):
    """Historial, el más nuevo primero."""
    return sorted(_filas(client, cliente_id), key=lambda f: str(f.get("creado_en") or ""), reverse=True)


def acreditar(client, cliente_id, monto_usd, motivo, por=None):
    """Suma (monto > 0) o corrige a la baja (monto < 0) el saldo. Devuelve el
    saldo nuevo. Una corrección no puede dejar el saldo por debajo de cero."""
    monto = _monto(monto_usd)
    if monto == 0 or abs(monto) > TOPE_MOVIMIENTO_USD:
        raise ValueError("Ingresá un monto distinto de cero.")
    motivo = " ".join(str(motivo or "").split())[:200]
    if not motivo:
        raise ValueError("Anotá el motivo del saldo.")
    actual = saldo(client, cliente_id)
    if actual + monto < 0:
        raise ValueError("No se puede restar más de lo que el cliente tiene a favor.")
    client.table(TABLA).insert({
        "cliente_id": cliente_id, "monto_usd": str(monto), "motivo": motivo, "creado_por": por,
    }).execute()
    return actual + monto


def aplicable(client, cliente_id, total_usd):
    """Cuánto del saldo se usa en una compra de `total_usd`: lo que tenga, hasta
    cubrir el total. El resto sigue a favor del cliente."""
    try:
        total = max(_monto(total_usd), Decimal(0))
    except ValueError:
        return Decimal(0)
    return min(saldo(client, cliente_id), total)


def consumir(client, cliente_id, pedido_id, monto_usd):
    """Descuenta el saldo usado por un pedido. Seguro de repetir: un pedido
    consume una sola vez (el reenvío del recibo no vuelve a descontar)."""
    monto = _monto(monto_usd)
    if monto <= 0 or not pedido_id:
        return False
    ya = [f for f in _filas(client, cliente_id)
          if f.get("pedido_id") == pedido_id and Decimal(str(f.get("monto_usd") or 0)) < 0]
    if ya:
        return False
    client.table(TABLA).insert({
        "cliente_id": cliente_id, "monto_usd": str(-monto), "pedido_id": pedido_id,
        "motivo": "Usado en una compra", "creado_por": "recibo",
    }).execute()
    return True


def formatear(monto):
    """US$ 1.250 / US$ 1.250,50 (sin decimales si es entero)."""
    valor = f"{_monto(monto):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if valor.endswith(",00"):
        valor = valor[:-3]
    return f"US$ {valor}"
