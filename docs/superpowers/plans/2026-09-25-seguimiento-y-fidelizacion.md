# Seguimiento post-entrega y programa de fidelización Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** al completarse una entrega, sumar un sello de fidelización a la cuenta del cliente (emitiendo un código de descuento de US$20 al 5to) y, 7 días después, mandarle un mail de seguimiento automático preguntando qué le pareció.

**Architecture:** dos módulos Python puros nuevos (`web/fidelidad.py`, `web/mailing/seguimiento.py`) que siguen el patrón ya usado por `web/entregas.py`/`web/pedidos.py`: funciones que reciben el cliente de Supabase como parámetro, sin estado propio. `web/fidelidad.py` se invoca en el momento exacto en que hoy se marca una entrega como completada (envío de recibo en `web/app.py`, y el punto donde se consume un `codigos_descuento` dentro del flujo de `/api/pedidos`). `web/mailing/seguimiento.py` es un script aparte que corre por cron diario (fuera del repo, vía la skill `schedule`), igual que el borrador semanal de mailing ya planeado.

**Tech Stack:** FastAPI (`web/app.py`), Supabase vía `supabase-py`, Resend vía `web/email_util.enviar_email`, pytest con `tests/fakes_supabase.py`.

**Spec:** [docs/superpowers/specs/2026-09-25-seguimiento-y-fidelizacion-design.md](../specs/2026-09-25-seguimiento-y-fidelizacion-design.md)

## Global Constraints

- "Entrega completada" para un pedido significa que se envió su recibo (`pedidos.recibo_enviado_en` se marca en `web/app.py::admin_pedido_enviar_recibo`) — es el único punto de entrega que ya existe en el repo; las tareas de `tareas_entrega` (notas del cadete) NO suman sello ni disparan seguimiento, porque no son pedidos con productos.
- Solo pedidos con `cliente_id` (cuenta con login) participan de fidelización y seguimiento — un pedido cargado a mano sin cuenta no suma ni se le manda mail.
- El sello sube de a 1 por cada entrega completada, sin monto mínimo (ya definido).
- Al llegar a 5 sellos se genera un código en la tabla `codigos_descuento` ya existente (US$20, aplicable a cualquier producto del catálogo vigente), y **no** se resetea `sellos_fidelidad` hasta que ese código se use en un pedido.
- El mail de seguimiento se envía automático, sin preview de Vladimir, con reply-to a su casilla real (a diferencia del mailing masivo de novedades que si necesita su aprobación).
- No enviar el mail de seguimiento dos veces para el mismo pedido, ni dejar de reintentar si el envío falla.
- Nunca `git push` a `web-ttra` sin permiso explícito puntual.

## Review Focus

1. Un pedido histórico sin `cliente_id` (cargado a mano por WhatsApp) se marca con recibo enviado: no debe sumar sello ni intentar mandar mail de seguimiento — el pedido no tiene cuenta a la que asociarle nada.
2. Dos entregas completadas el mismo día para el mismo cliente deben sumar dos sellos independientes, y si la segunda hace que llegue a 5, ahí se emite el código — no antes ni con un off-by-one.
3. Si el cliente ya tiene un código de fidelidad pendiente (llegó a 5 y no lo usó) y se le completa una entrega nueva, el sello no debe seguir sumando de largo — se mantiene en 5 hasta que use el código existente.
4. El cron de seguimiento corriendo dos veces el mismo día sobre el mismo pedido no debe mandar el mail dos veces.
5. Si `enviar_email` tira `EnvioEmailError` (Resend caído), el cron de seguimiento no debe marcar el pedido como notificado — tiene que reintentar al día siguiente.

---

## Task 1: Columnas nuevas en el schema

**Files:**
- Modify: `supabase/schema.sql` (después del bloque de `pedidos`, línea ~100, y después del bloque de `clientes`, buscar con `grep -n "create table if not exists clientes" supabase/schema.sql`)

**Interfaces:**
- Produces: `pedidos.seguimiento_enviado_en timestamptz`, `clientes.sellos_fidelidad integer not null default 0`, `clientes.fidelidad_ultimo_codigo text`.

No hay ambiente de prueba separado para Supabase (`tests/fakes_supabase.py` no lee este archivo) — hay que correr estas líneas a mano en el SQL Editor de Supabase antes de que el código de las tareas siguientes corra contra producción, igual que se documenta para `no_mailing` en el plan de mailing.

- [ ] **Step 1: Agregar las columnas al schema**

En `supabase/schema.sql`, dentro del bloque de `alter table pedidos add column if not exists ...` (junto a `lat`/`lng`, línea ~100), agregar:

```sql
-- Marca cuándo se mandó el mail de seguimiento post-entrega (7 días después
-- de enviar el recibo). Null hasta que el envío tiene éxito.
alter table pedidos add column if not exists seguimiento_enviado_en timestamptz;
```

Dentro del bloque de `alter table clientes add column if not exists ...` (buscar con `grep -n "alter table clientes add column" supabase/schema.sql`), agregar:

```sql
-- Programa de fidelización: sube de a 1 por cada entrega completada de un
-- pedido con cuenta. Llega a 5 y se congela ahí hasta que el cliente use el
-- código de fidelidad_ultimo_codigo; recién entonces vuelve a 0.
alter table clientes add column if not exists sellos_fidelidad integer not null default 0;
alter table clientes add column if not exists fidelidad_ultimo_codigo text;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat: schema para seguimiento post-entrega y fidelización"
```

---

## Task 2: Módulo `web/fidelidad.py`

**Files:**
- Create: `web/fidelidad.py`
- Test: `tests/test_fidelidad.py`

**Interfaces:**
- Consumes: cliente de Supabase con `.table(nombre).select("*").eq(...).execute().data` / `.insert(...)` / `.update(...)`, igual que `web/pedidos.py`.
- Produces: `registrar_entrega_completada(client, cliente_id, nombres_catalogo) -> dict | None` (info del sello nuevo, o del código emitido si llegó a 5); `marcar_codigo_fidelidad_usado(client, cliente_id, codigo) -> bool` (True si el código coincidía y se resetió el ciclo).

- [ ] **Step 1: Escribir los tests, empezando por sumar sello sin llegar a 5**

```python
# tests/test_fidelidad.py
from tests.fakes_supabase import FakeSupabaseClient
from web import fidelidad


def _cliente(fake, sellos=0, codigo=None):
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez",
        "sellos_fidelidad": sellos, "fidelidad_ultimo_codigo": codigo,
    }).execute()
    return "cliente-1"


def test_suma_un_sello_sin_llegar_a_cinco():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=1)

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13"])

    cliente = fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
    assert cliente["sellos_fidelidad"] == 2
    assert cliente["fidelidad_ultimo_codigo"] is None
    assert resultado == {"sellos_fidelidad": 2, "codigo_emitido": None}


def test_al_llegar_a_cinco_emite_codigo_de_veinte_dolares_y_no_resetea():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=4)

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13", "iPhone 14"])

    cliente = fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == resultado["codigo_emitido"]
    codigos = fake.table("codigos_descuento").select("*").eq("code", resultado["codigo_emitido"]).execute().data
    assert codigos[0] == {
        "cliente_id": cliente_id,
        "code": resultado["codigo_emitido"],
        "productos": ["iPhone 13", "iPhone 14"],
        "descuento_usd": 20,
        "activo": True,
    }


def test_no_suma_de_largo_si_ya_tiene_un_codigo_pendiente():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-PENDIENTE")

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13"])

    cliente = fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == "TTRA-PENDIENTE"
    assert resultado is None


def test_marcar_codigo_usado_resetea_el_ciclo_si_coincide():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-ABC123")

    reseteo = fidelidad.marcar_codigo_fidelidad_usado(fake, cliente_id, "TTRA-ABC123")

    cliente = fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
    assert reseteo is True
    assert cliente["sellos_fidelidad"] == 0
    assert cliente["fidelidad_ultimo_codigo"] is None


def test_marcar_codigo_usado_ignora_codigos_que_no_son_de_fidelidad():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-ABC123")

    reseteo = fidelidad.marcar_codigo_fidelidad_usado(fake, cliente_id, "TTRA-OTRO-CODIGO-DE-MAILING")

    cliente = fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]
    assert reseteo is False
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == "TTRA-ABC123"
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_fidelidad.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.fidelidad'`

- [ ] **Step 3: Implementar `web/fidelidad.py`**

```python
import secrets
import string

DESCUENTO_FIDELIDAD_USD = 20
SELLOS_PARA_PREMIO = 5


def _generar_codigo_fidelidad(client):
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(12):
        codigo = "TTRA-" + "".join(secrets.choice(alfabeto) for _ in range(8))
        existe = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
        if not existe:
            return codigo
    raise RuntimeError("No se pudo generar un código de fidelidad único")


def registrar_entrega_completada(client, cliente_id, nombres_catalogo):
    """Suma un sello de fidelidad a la cuenta del cliente. Si llega a
    SELLOS_PARA_PREMIO, emite un código de descuento y lo deja pendiente de
    uso (no resetea el contador hasta que se consuma, ver
    marcar_codigo_fidelidad_usado). Devuelve None si el cliente ya tenía un
    código pendiente sin usar (no sigue sumando de largo)."""
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return None
    cliente = filas[0]
    if cliente.get("fidelidad_ultimo_codigo"):
        return None

    sellos = int(cliente.get("sellos_fidelidad") or 0) + 1
    actualizacion = {"sellos_fidelidad": sellos}
    codigo_emitido = None
    if sellos >= SELLOS_PARA_PREMIO:
        codigo_emitido = _generar_codigo_fidelidad(client)
        client.table("codigos_descuento").insert({
            "cliente_id": cliente_id,
            "code": codigo_emitido,
            "productos": list(nombres_catalogo),
            "descuento_usd": DESCUENTO_FIDELIDAD_USD,
            "activo": True,
        }).execute()
        actualizacion["fidelidad_ultimo_codigo"] = codigo_emitido

    client.table("clientes").update(actualizacion).eq("id", cliente_id).execute()
    return {"sellos_fidelidad": sellos, "codigo_emitido": codigo_emitido}


def marcar_codigo_fidelidad_usado(client, cliente_id, codigo):
    """Si `codigo` es el código de fidelidad pendiente de este cliente,
    resetea el ciclo a 0 y libera fidelidad_ultimo_codigo. Devuelve True si
    reseteó algo, False si el código no era el de fidelidad de ese cliente
    (ej. un código de descuento de mailing) — no toca nada en ese caso."""
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return False
    cliente = filas[0]
    if not codigo or cliente.get("fidelidad_ultimo_codigo") != codigo:
        return False
    client.table("clientes").update({
        "sellos_fidelidad": 0, "fidelidad_ultimo_codigo": None,
    }).eq("id", cliente_id).execute()
    return True
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_fidelidad.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add web/fidelidad.py tests/test_fidelidad.py
git commit -m "feat: programa de fidelización (sellos y código de premio)"
```

---

## Task 3: Enganchar la suma de sello al enviar el recibo

**Files:**
- Modify: `web/app.py` (import al inicio, y `admin_pedido_enviar_recibo` — buscar con `grep -n "def admin_pedido_enviar_recibo" web/app.py`)
- Test: `tests/test_app_admin_clientes.py` (agregar test nuevo al lado de `test_admin_envia_recibo_y_marca_el_pedido`)

**Interfaces:**
- Consumes: `fidelidad.registrar_entrega_completada(client, cliente_id, nombres_catalogo)` (Task 2).

- [ ] **Step 1: Escribir el test**

En `tests/test_app_admin_clientes.py`, agregar después de `test_admin_envia_recibo_y_marca_el_pedido`:

```python
def test_enviar_recibo_suma_un_sello_de_fidelidad(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("clientes").update({"sellos_fidelidad": 1}).eq("id", cliente["id"]).execute()
    fake.table("pedidos").insert({
        "id": "pedido-fidelidad", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{
            "nombre": "iPhone 13", "color": "Negro", "cantidad": 1,
            "usd_unitario": 500, "usd_subtotal": 500,
        }],
        "total_usd": 500,
        "descuento_usd": 0,
    }).execute()
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)

    r = c.post("/admin/pedidos/pedido-fidelidad/recibo")

    assert r.status_code == 200
    actualizado = fake.table("clientes").select("*").eq("id", cliente["id"]).execute().data[0]
    assert actualizado["sellos_fidelidad"] == 2
```

El caso de un pedido sin `cliente_id` no necesita un test HTTP aparte: `admin_pedido_enviar_recibo` ya devuelve 400 antes de llegar al envío cuando no encuentra el cliente por `cliente_id` (valida el email del cliente antes), y el guard `if pedido.get("cliente_id"):` del Step 3 de abajo queda cubierto por `test_no_suma_de_largo_si_ya_tiene_un_codigo_pendiente` y el resto de `tests/test_fidelidad.py` (Task 2), que ya ejercitan `registrar_entrega_completada` directamente.

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_app_admin_clientes.py::test_enviar_recibo_suma_un_sello_de_fidelidad -v`
Expected: FAIL (`sellos_fidelidad` sigue en 1, nadie lo incrementó todavía)

- [ ] **Step 3: Enganchar `fidelidad.registrar_entrega_completada` en el envío de recibo**

En `web/app.py`, agregar el import junto a los demás módulos del proyecto (buscar con `grep -n "^from web import\|^import web" web/app.py` para ubicar el bloque):

```python
from web import fidelidad
```

Dentro de `admin_pedido_enviar_recibo`, justo después de la línea:

```python
    client.table("pedidos").update(actualizacion_pedido).eq("id", pedido_id).execute()
```

agregar:

```python
    if pedido.get("cliente_id"):
        try:
            fidelidad.registrar_entrega_completada(
                client, pedido["cliente_id"],
                [p.get("nombre") for p in _cargar_productos() if p.get("nombre")],
            )
        except Exception:
            logger.exception(
                "No se pudo registrar el sello de fidelidad del pedido %s", pedido_id
            )
```

No bloquea la respuesta si falla — el recibo ya se mandó, y perder un sello por un error puntual de Supabase es preferible a que el cliente vea un error después de recibir su mail.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_app_admin_clientes.py -v`
Expected: todos PASS, incluido el nuevo.

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_admin_clientes.py
git commit -m "feat: sumar sello de fidelidad al completar una entrega"
```

---

## Task 4: Resetear el ciclo cuando se usa el código de fidelidad

**Files:**
- Modify: `web/app.py` (endpoint de `/api/pedidos`, en la rama donde se llama al RPC `guardar_pedido_con_descuento_mailing` — buscar con `grep -n "guardar_pedido_con_descuento_mailing" web/app.py`)
- Test: `tests/test_app_pedidos.py`

**Interfaces:**
- Consumes: `fidelidad.marcar_codigo_fidelidad_usado(client, cliente_id, codigo)` (Task 2).

- [ ] **Step 1: Escribir el test**

Buscar en `tests/test_app_pedidos.py` un test existente que guarde un pedido usando `codigo_descuento` (ej. `grep -n "codigo_descuento" tests/test_app_pedidos.py`) para copiar el setup de cliente + catálogo + código. Agregar:

```python
def test_usar_codigo_de_fidelidad_resetea_el_ciclo(monkeypatch):
    c = _cliente_logueado(monkeypatch)  # o el helper de login que use este archivo
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({
        "sellos_fidelidad": 5, "fidelidad_ultimo_codigo": "TTRA-PREMIO1",
    }).eq("id", cliente["id"]).execute()
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente["id"], "code": "TTRA-PREMIO1",
        "productos": ["iPhone 13"], "descuento_usd": 20, "activo": True,
    }).execute()

    r = c.post("/api/pedidos", json={
        "productos": [{"nombre": "iPhone 13", "cantidad": 1}],
        "fecha_entrega": "2026-08-24",
        "codigo_descuento": "TTRA-PREMIO1",
        "total_usd": 480,
    })

    assert r.status_code == 200
    actualizado = fake.table("clientes").select("*").eq("id", cliente["id"]).execute().data[0]
    assert actualizado["sellos_fidelidad"] == 0
    assert actualizado["fidelidad_ultimo_codigo"] is None
```

Este test es un esqueleto de guía: adaptá el payload exacto de `/api/pedidos` (nombres de campos, catálogo de prueba, helper de login) a lo que ya usan los tests vecinos en `tests/test_app_pedidos.py` — copiá el setup completo de un test existente que use `codigo_descuento` y solo cambiale el aserto final.

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_app_pedidos.py::test_usar_codigo_de_fidelidad_resetea_el_ciclo -v`
Expected: FAIL (`sellos_fidelidad` sigue en 5, nadie lo reseteó)

- [ ] **Step 3: Enganchar el reseteo tras el RPC**

En `web/app.py`, dentro de la rama `if fila_descuento or codigo_promo:` del endpoint de pedidos, justo después del bloque que ya actualiza `lat`/`lng` tras el éxito del RPC (después de la línea `logger.exception("No se pudo guardar lat/lng del pedido %s", pedido_id_rpc)` y su bloque `except`), agregar:

```python
        if fila_descuento:
            try:
                fidelidad.marcar_codigo_fidelidad_usado(
                    client, cliente_id, fila_descuento["code"],
                )
            except Exception:
                logger.exception(
                    "No se pudo resetear el ciclo de fidelidad para %s", cliente_id
                )
```

Esto corre después de que el RPC ya confirmó `resultado.get("ok")` (la rama entera está bajo ese chequeo previo), así que `fila_descuento["code"]` efectivamente se consumió. `marcar_codigo_fidelidad_usado` no hace nada si ese código no era el de fidelidad de este cliente (ej. era un código de mailing de oferta).

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_app_pedidos.py -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_pedidos.py
git commit -m "feat: resetear ciclo de fidelidad al usar el código de premio"
```

---

## Task 5: Exponer el estado de fidelidad en `/api/me` y mostrarlo en `/perfil`

**Files:**
- Modify: `web/cuentas.py:177-186` (`obtener_cliente`)
- Modify: `web/static/perfil.html:64-68`
- Modify: `web/static/perfil.js` (cerca de `mostrarSeccionCondicionesMayorista`, línea ~119, y su llamada en `cargarPerfil`, línea ~199)
- Test: `tests/test_cuentas.py`

**Interfaces:**
- Produces: `obtener_cliente(...)` ahora incluye `sellos_fidelidad` (int) y `fidelidad_ultimo_codigo` (str | None) en el dict que devuelve, y por lo tanto en la respuesta JSON de `GET /api/me`.

- [ ] **Step 1: Escribir el test de `obtener_cliente`**

En `tests/test_cuentas.py`, buscar el test existente de `obtener_cliente` (ej. `grep -n "def test.*obtener_cliente" tests/test_cuentas.py`) y agregar al lado:

```python
def test_obtener_cliente_incluye_estado_de_fidelidad():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez",
        "sellos_fidelidad": 3, "fidelidad_ultimo_codigo": None,
    }).execute()

    perfil = cuentas.obtener_cliente(fake, "cliente-1")

    assert perfil["sellos_fidelidad"] == 3
    assert perfil["fidelidad_ultimo_codigo"] is None
```

(Ajustá el import de `FakeSupabaseClient` y `cuentas` a como ya se importan en el resto del archivo.)

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_cuentas.py::test_obtener_cliente_incluye_estado_de_fidelidad -v`
Expected: FAIL con `KeyError: 'sellos_fidelidad'`

- [ ] **Step 3: Agregar los campos a `obtener_cliente`**

En `web/cuentas.py`, reemplazar:

```python
    return {"id": perfil["id"], "nombre": perfil["nombre"], "apellido": perfil["apellido"],
            "celular": perfil.get("celular"), "email": perfil.get("email"),
            "direccion": perfil.get("direccion"),
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password")),
            "condiciones_mayorista_aceptadas_en": perfil.get("condiciones_mayorista_aceptadas_en")}
```

por:

```python
    return {"id": perfil["id"], "nombre": perfil["nombre"], "apellido": perfil["apellido"],
            "celular": perfil.get("celular"), "email": perfil.get("email"),
            "direccion": perfil.get("direccion"),
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password")),
            "condiciones_mayorista_aceptadas_en": perfil.get("condiciones_mayorista_aceptadas_en"),
            "sellos_fidelidad": int(perfil.get("sellos_fidelidad") or 0),
            "fidelidad_ultimo_codigo": perfil.get("fidelidad_ultimo_codigo")}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_cuentas.py -v`
Expected: todos PASS.

- [ ] **Step 5: Agregar la tarjeta de fidelidad al HTML de `/perfil`**

En `web/static/perfil.html`, reemplazar:

```html
    <section id="seccion-condiciones-mayorista" class="oculto">
      <h2>Condiciones mayoristas</h2>
      <p id="condiciones-mayorista-fecha" class="ok"></p>
      <button type="button" id="btn-ver-condiciones-mayorista">Ver condiciones mayoristas</button>
    </section>
    </section>
```

por:

```html
    <section id="seccion-condiciones-mayorista" class="oculto">
      <h2>Condiciones mayoristas</h2>
      <p id="condiciones-mayorista-fecha" class="ok"></p>
      <button type="button" id="btn-ver-condiciones-mayorista">Ver condiciones mayoristas</button>
    </section>

    <section id="seccion-fidelidad">
      <h2>Tarjeta de fidelidad</h2>
      <div id="fidelidad-sellos" class="fidelidad-sellos"></div>
      <p id="fidelidad-premio" class="ok oculto"></p>
    </section>
    </section>
```

- [ ] **Step 6: Renderizar la tarjeta en `perfil.js`**

En `web/static/perfil.js`, agregar después de la función `mostrarSeccionCondicionesMayorista` (línea ~141):

```javascript
function mostrarTarjetaFidelidad(datos) {
  const contenedorSellos = document.getElementById("fidelidad-sellos");
  const mensajePremio = document.getElementById("fidelidad-premio");
  if (!contenedorSellos || !mensajePremio) return;
  if (datos.fidelidad_ultimo_codigo) {
    contenedorSellos.textContent = "";
    mensajePremio.textContent =
      `¡Tenés un premio disponible! Código ${datos.fidelidad_ultimo_codigo} — ` +
      "US$20 de descuento en tu próxima compra.";
    mensajePremio.classList.remove("oculto");
    return;
  }
  mensajePremio.classList.add("oculto");
  const sellos = Number(datos.sellos_fidelidad) || 0;
  contenedorSellos.textContent = "";
  for (let i = 0; i < 5; i++) {
    const sello = document.createElement("span");
    sello.className = "fidelidad-sello" + (i < sellos ? " lleno" : "");
    sello.textContent = i < sellos ? "★" : "☆";
    contenedorSellos.append(sello);
  }
}
```

Y en `cargarPerfil()`, después de la línea `mostrarSeccionCondicionesMayorista(datos);` (línea ~199), agregar:

```javascript
    mostrarTarjetaFidelidad(datos);
```

- [ ] **Step 7: Levantar la app y verificar visualmente**

Usar la skill `run-ttra-web` para levantar la app y sacar un screenshot de `/perfil` logueado con un cliente que tenga `sellos_fidelidad` en 2 y en 5 (con código pendiente), confirmando que la tarjeta se ve razonable en ambos estados antes de seguir. No hace falta CSS elaborado — un `.fidelidad-sello.lleno { color: ... }` simple alcanza; si el review visual pide ajustarlo, hacelo en este mismo paso.

- [ ] **Step 8: Commit**

```bash
git add web/cuentas.py tests/test_cuentas.py web/static/perfil.html web/static/perfil.js
git commit -m "feat: mostrar tarjeta de fidelidad en el perfil del cliente"
```

---

## Task 6: Reply-to en `enviar_email`

**Files:**
- Modify: `web/email_util.py`
- Test: `tests/test_email_util.py` (crear si no existe — verificar con `ls tests/test_email_util.py`)

**Interfaces:**
- Produces: `enviar_email(destinatario, asunto, html, adjuntos=None, reply_to=None)`.

- [ ] **Step 1: Escribir el test**

```python
# tests/test_email_util.py
import pytest

from web.email_util import EnvioEmailError, enviar_email


def test_enviar_email_bloqueado_en_test():
    with pytest.raises(EnvioEmailError):
        enviar_email("cliente@x.com", "Asunto", "<p>hola</p>")


def test_enviar_email_con_reply_to_arma_el_payload(monkeypatch):
    import httpx
    import web.email_util as email_util

    capturado = {}

    class RespuestaFalsa:
        status_code = 200
        text = ""

    def post_falso(url, headers, json, timeout):
        capturado["json"] = json
        return RespuestaFalsa()

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(httpx, "post", post_falso)
    monkeypatch.setattr(email_util.os.environ, "get", lambda k, default=None: (
        "fake-key" if k == "RESEND_API_KEY" else default
    ))

    enviar_email("cliente@x.com", "Asunto", "<p>hola</p>", reply_to="contacto@thetechroomarg.com")

    assert capturado["json"]["reply_to"] == ["contacto@thetechroomarg.com"]
```

El primer test (`test_enviar_email_bloqueado_en_test`) ya debería pasar hoy — confirma que el bloqueo de test sigue intacto. El segundo es el que ejercita `reply_to` y va a fallar hasta el Step 3.

- [ ] **Step 2: Correr los tests para verificar que el segundo falla**

Run: `.venv/bin/python -m pytest tests/test_email_util.py -v`
Expected: el primero PASS, el segundo FAIL (`KeyError: 'reply_to'`)

- [ ] **Step 3: Agregar `reply_to` a `enviar_email`**

En `web/email_util.py`, reemplazar la firma y el payload:

```python
def enviar_email(destinatario, asunto, html, adjuntos=None, reply_to=None):
```

y en el `json=` del `httpx.post`, agregar la clave `reply_to` solo si se pasó:

```python
        json={
            "from": REMITENTE, "to": [destinatario], "subject": asunto, "html": html,
            **({"reply_to": [reply_to]} if reply_to else {}),
            "attachments": [
                {"filename": adjunto["filename"], "content": base64.b64encode(adjunto["content"]).decode("ascii")}
                for adjunto in (adjuntos or [])
            ],
        },
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_email_util.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add web/email_util.py tests/test_email_util.py
git commit -m "feat: soportar reply-to en enviar_email"
```

---

## Task 7: Módulo `web/mailing/seguimiento.py`

**Files:**
- Create: `web/mailing/__init__.py` (vacío)
- Create: `web/mailing/seguimiento.py`
- Test: `tests/test_seguimiento.py`

**Interfaces:**
- Consumes: `web.email_util.enviar_email(destinatario, asunto, html, adjuntos=None, reply_to=None)` (Task 6).
- Produces: `pedidos_para_notificar(client, hoy) -> list[dict]`; `enviar_seguimientos(client, hoy=None, enviar_email_fn=enviar_email) -> dict` (resumen: cuántos se enviaron, cuántos fallaron).

- [ ] **Step 1: Escribir los tests**

```python
# tests/test_seguimiento.py
from datetime import date, timedelta

from tests.fakes_supabase import FakeSupabaseClient
from web import email_util
from web.mailing import seguimiento


def _pedido_entregado(fake, hace_dias, cliente_id="cliente-1", seguimiento_enviado_en=None, id_="pedido-1"):
    entregado_en = (date(2026, 9, 25) - timedelta(days=hace_dias)).isoformat() + "T12:00:00+00:00"
    fake.table("pedidos").insert({
        "id": id_, "cliente_id": cliente_id,
        "productos": ["iPhone 13"],
        "recibo_enviado_en": entregado_en,
        "seguimiento_enviado_en": seguimiento_enviado_en,
    }).execute()


def _cliente(fake, id_="cliente-1", email="juan@x.com"):
    fake.table("clientes").insert({"id": id_, "nombre": "Juan", "apellido": "Pérez", "email": email}).execute()


def test_pedidos_para_notificar_incluye_entregas_de_hace_siete_dias():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido_entregado(fake, hace_dias=7)

    resultado = seguimiento.pedidos_para_notificar(fake, hoy=date(2026, 9, 25))

    assert len(resultado) == 1
    assert resultado[0]["id"] == "pedido-1"


def test_pedidos_para_notificar_excluye_los_ya_notificados():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido_entregado(fake, hace_dias=7, seguimiento_enviado_en="2026-09-25T09:00:00+00:00")

    resultado = seguimiento.pedidos_para_notificar(fake, hoy=date(2026, 9, 25))

    assert resultado == []


def test_pedidos_para_notificar_excluye_entregas_sin_cliente():
    fake = FakeSupabaseClient()
    _pedido_entregado(fake, hace_dias=7, cliente_id=None)

    resultado = seguimiento.pedidos_para_notificar(fake, hoy=date(2026, 9, 25))

    assert resultado == []


def test_enviar_seguimientos_marca_el_pedido_tras_el_envio_exitoso():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido_entregado(fake, hace_dias=7)
    enviados = []

    resultado = seguimiento.enviar_seguimientos(
        fake, hoy=date(2026, 9, 25),
        enviar_email_fn=lambda *args, **kwargs: enviados.append((args, kwargs)),
    )

    assert resultado == {"enviados": 1, "fallidos": 0}
    assert enviados[0][0][0] == "juan@x.com"
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["seguimiento_enviado_en"]


def test_enviar_seguimientos_no_marca_el_pedido_si_el_envio_falla():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido_entregado(fake, hace_dias=7)

    def enviar_que_falla(*_args, **_kwargs):
        raise email_util.EnvioEmailError("Resend caído")

    resultado = seguimiento.enviar_seguimientos(
        fake, hoy=date(2026, 9, 25), enviar_email_fn=enviar_que_falla,
    )

    assert resultado == {"enviados": 0, "fallidos": 1}
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["seguimiento_enviado_en"] is None
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_seguimiento.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.mailing'`

- [ ] **Step 3: Implementar `web/mailing/seguimiento.py`**

```python
import html
import os
from datetime import date, datetime, timedelta, timezone

from web.email_util import enviar_email as _enviar_email_default

VENTANA_DIAS_SEGUIMIENTO = 7
REPLY_TO_SEGUIMIENTO = os.environ.get(
    "MAIL_SEGUIMIENTO_REPLY_TO", "contacto@thetechroomarg.com"
)


def pedidos_para_notificar(client, hoy=None):
    """Pedidos con recibo enviado hace exactamente VENTANA_DIAS_SEGUIMIENTO
    días (ventana de un día para no depender de la hora exacta del cron),
    con cuenta de cliente y sin seguimiento ya enviado."""
    hoy = hoy or date.today()
    objetivo = (hoy - timedelta(days=VENTANA_DIAS_SEGUIMIENTO)).isoformat()
    pedidos = client.table("pedidos").select("*").execute().data
    resultado = []
    for pedido in pedidos:
        if not pedido.get("cliente_id") or pedido.get("seguimiento_enviado_en"):
            continue
        entregado_en = pedido.get("recibo_enviado_en")
        if not entregado_en:
            continue
        if datetime.fromisoformat(entregado_en).date().isoformat() != objetivo:
            continue
        resultado.append(pedido)
    return resultado


def _descripcion_pedido(pedido):
    detalle = pedido.get("detalle") or []
    if detalle:
        return ", ".join(item.get("nombre", "") for item in detalle)
    return ", ".join(pedido.get("productos") or [])


def enviar_seguimientos(client, hoy=None, enviar_email_fn=_enviar_email_default):
    enviados = 0
    fallidos = 0
    for pedido in pedidos_para_notificar(client, hoy=hoy):
        filas_cliente = (
            client.table("clientes").select("*").eq("id", pedido["cliente_id"]).execute().data
        )
        if not filas_cliente or not (filas_cliente[0].get("email") or "").strip():
            continue
        cliente = filas_cliente[0]
        nombre = cliente.get("nombre") or ""
        producto = _descripcion_pedido(pedido) or "tu compra"
        html_mail = (
            f"<p>Hola {html.escape(nombre)},</p>"
            f"<p>Hace una semana te entregamos {html.escape(producto)}. "
            "¿Qué te pareció todo? Respondé este mail y contame, me sirve "
            "mucho tu opinión.</p>"
            "<p>Saludos,<br>The Tech Room Arg</p>"
        )
        try:
            enviar_email_fn(
                cliente["email"],
                "¿Qué te pareció tu compra? — The Tech Room Arg",
                html_mail,
                reply_to=REPLY_TO_SEGUIMIENTO,
            )
        except Exception:
            fallidos += 1
            continue
        client.table("pedidos").update({
            "seguimiento_enviado_en": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pedido["id"]).execute()
        enviados += 1
    return {"enviados": enviados, "fallidos": fallidos}
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_seguimiento.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add web/mailing/__init__.py web/mailing/seguimiento.py tests/test_seguimiento.py
git commit -m "feat: mail automático de seguimiento a los 7 días de la entrega"
```

---

## Task 8: Script de cron diario

**Files:**
- Create: `.claude/skills/pedido/scripts/seguimiento_diario.py` (reusa el patrón y la carpeta de scripts operativos ya existente en la skill `pedido`, no crea una skill nueva)

**Interfaces:**
- Consumes: `web.mailing.seguimiento.enviar_seguimientos(client)` (Task 7), `web.supabase_client.get_client` (mismo patrón que `cargar_pedido.py`).

- [ ] **Step 1: Escribir el script**

```python
#!/usr/bin/env python3
"""Corre el mail automático de seguimiento post-entrega (7 días después de
enviar el recibo). Pensado para correr una vez por día vía la skill
`schedule` — no imprime nada si no hay pedidos para notificar.

Uso:
    ./.venv/bin/python .claude/skills/pedido/scripts/seguimiento_diario.py

Escribe DIRECTO en la base de producción, igual que cargar_pedido.py.
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.supabase_client import get_client
from web.mailing import seguimiento


def main():
    resultado = seguimiento.enviar_seguimientos(get_client())
    print(f"Seguimientos enviados: {resultado['enviados']}, fallidos: {resultado['fallidos']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/pedido/scripts/seguimiento_diario.py
git commit -m "feat: script de cron para el mail de seguimiento post-entrega"
```

- [ ] **Step 3: Nota para Vladimir (no es un paso de código)**

Después de mergear esto, hay que dar de alta la rutina diaria con la skill `schedule` para que corra `seguimiento_diario.py` una vez por día (por ejemplo, a la mañana). Esto vive fuera del repo — no hay nada más que ejecutar acá, pero sin darla de alta el mail de seguimiento no se dispara solo.

---

## Task 9: Corrida completa de la suite

- [ ] **Step 1: Correr toda la suite de tests**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: todos los tests pasan (los 399 anteriores + los nuevos de esta feature), sin warnings nuevos.

- [ ] **Step 2: Si algo rompió, arreglarlo antes de dar la feature por terminada**

No hay commit en este paso — es el gate final antes de pedir revisión de rama.
