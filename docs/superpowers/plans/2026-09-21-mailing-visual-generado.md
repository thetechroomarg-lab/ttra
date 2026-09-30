# Mailing Visual Generado con IA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender el mailing semanal de The Tech Room Arg con un hero generado por IA, vista previa versionada, aprobación explícita y envío separado, sin necesitar un deploy por campaña.

**Architecture:** La aplicación en la rama desplegable `web-ttra` almacenará versiones inmutables de campañas en Supabase y activos visuales en el volumen persistente de Railway, expuestos mediante URLs públicas no enumerables. La skill local generará el arte con la herramienta de imágenes, preparará/subirá la campaña mediante endpoints administrativos, y mantendrá `aprobar` y `enviar` como operaciones separadas. El template seguirá siendo HTML funcional aunque el cliente de correo bloquee el hero.

**Tech Stack:** Python 3, FastAPI, Supabase/Postgres, Resend, `httpx`, pytest, HTML de email con estilos inline, herramienta `imagegen`, Railway persistent volume.

**Spec:** [docs/superpowers/specs/2026-09-21-mailing-visual-generado-design.md](../specs/2026-09-21-mailing-visual-generado-design.md)

## Global Constraints

- `productos.json`, servido por `GET /api/productos`, es la única fuente de verdad de nombres, disponibilidad y precios.
- Preparar, regenerar y aprobar nunca llaman a Resend.
- Enviar requiere una versión en estado `aprobado`, revalidación del catálogo y una segunda confirmación humana explícita.
- Un cambio de nombre, precio, disponibilidad, CTA o archivo visual invalida la aprobación.
- La pieza generada no contiene como única fuente nombres, precios, condiciones ni CTA; esos datos viven en HTML.
- Los clientes con email ausente o `no_mailing=true` nunca son destinatarios.
- Los secretos no aparecen en manifiestos, HTML, archivos de preview ni logs.
- Los activos aceptados son JPEG, PNG o WebP; máximo 3 MiB; ancho entre 600 y 2400 px; alto entre 300 y 1800 px.
- El directorio de producción `MAILING_ASSETS_PATH` debe apuntar al volumen persistente; la aplicación no cae silenciosamente al filesystem efímero en producción.
- El endpoint público es de solo lectura, no lista directorios y usa identificadores UUID más hash SHA-256.
- La skill principal se entrega en `/Users/toraba/TTRA Project/.claude/skills/mailing/`; el backend desplegable se modifica en `/Users/toraba/TTRA Project/.worktrees/web-ttra-preview/`.
- No se envía una campaña real durante la implementación; la verificación llega solamente hasta un destinatario de prueba indicado posteriormente por Vladimir.

## Review Focus

- Dos procesos intentan aprobar o enviar la misma versión: solo una transición atómica debe ganar y nunca debe duplicarse el envío.
- El catálogo cambia entre aprobación y envío: la operación debe invalidar la campaña antes de contactar a Resend.
- Un archivo válido por extensión contiene bytes inválidos o intenta traversal: la carga debe rechazarse y no escribir fuera del volumen.
- La imagen deja de existir después de aprobar: el envío debe detenerse, no mandar un correo con hero roto.
- Resend falla a mitad de la audiencia: se deben registrar éxito/fallo por destinatario y bloquear una repetición accidental de los ya enviados.

---

### Task 1: Modelo versionado y transiciones atómicas de campaña

**Files:**
- Modify: `.worktrees/web-ttra-preview/supabase/schema.sql`
- Create: `.worktrees/web-ttra-preview/web/mailing/campanias.py`
- Create: `.worktrees/web-ttra-preview/tests/test_mailing_campanias.py`
- Modify: `.worktrees/web-ttra-preview/tests/fakes_supabase.py`

**Interfaces:**
- Consumes: cliente compatible con `supabase-py`.
- Produces: `crear_version(client, manifiesto) -> dict`, `obtener_version(client, version_id) -> dict | None`, `transicionar(client, version_id, desde, hacia, cambios=None) -> dict`, `InvalidTransition`, y RPC `transicionar_mailing_campania`.

- [ ] **Step 1: Escribir pruebas fallidas del ciclo de estados y concurrencia**

```python
import pytest
from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import campanias


def manifiesto():
    return {
        "brief": "premium minimalista",
        "asunto": "Novedades TTRA",
        "preheader": "Equipos seleccionados",
        "productos": [{"nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000}],
        "html": "<html>preview</html>",
        "asset_url": "https://thetechroomarg.com/mailing/assets/abc/sha.jpg",
        "asset_sha256": "a" * 64,
    }


def test_crear_version_empieza_previsualizada_y_es_inmutable():
    fake = FakeSupabaseClient()
    fila = campanias.crear_version(fake, manifiesto())
    assert fila["estado"] == "previsualizado"
    assert fila["version"] == 1
    assert campanias.obtener_version(fake, fila["id"])["manifest"]["asunto"] == "Novedades TTRA"


def test_solo_una_aprobacion_atomica_puede_ganar():
    fake = FakeSupabaseClient()
    fila = campanias.crear_version(fake, manifiesto())
    aprobada = campanias.transicionar(fake, fila["id"], "previsualizado", "aprobado")
    assert aprobada["estado"] == "aprobado"
    with pytest.raises(campanias.InvalidTransition):
        campanias.transicionar(fake, fila["id"], "previsualizado", "aprobado")


def test_regenerar_crea_version_nueva_sin_mutar_la_anterior():
    fake = FakeSupabaseClient()
    primera = campanias.crear_version(fake, manifiesto())
    segunda_manifest = {**manifiesto(), "parent_id": primera["id"], "brief": "más contraste"}
    segunda = campanias.crear_version(fake, segunda_manifest)
    assert segunda["version"] == 2
    assert campanias.obtener_version(fake, primera["id"])["manifest"]["brief"] == "premium minimalista"
```

- [ ] **Step 2: Ejecutar la prueba y comprobar el fallo correcto**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_campanias.py -v`

Expected: FAIL porque `web.mailing.campanias` todavía no existe.

- [ ] **Step 3: Agregar tabla, restricción de estados y RPC condicional**

```sql
create table if not exists mailing_campanias (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null,
  parent_id uuid references mailing_campanias(id) on delete set null,
  version integer not null,
  estado text not null check (estado in ('previsualizado','aprobado','enviando','enviado','invalidado')),
  manifest jsonb not null,
  creado_en timestamptz not null default now(),
  aprobado_en timestamptz,
  enviado_en timestamptz,
  resultado jsonb
);
create unique index if not exists mailing_campanias_version_idx
  on mailing_campanias (campaign_id, version);
alter table mailing_campanias enable row level security;

create table if not exists mailing_envios_detalle (
  version_id uuid not null references mailing_campanias(id) on delete cascade,
  cliente_id uuid not null references clientes(id) on delete cascade,
  estado text not null check (estado in ('ok','fallido')),
  error text,
  enviado_en timestamptz not null default now(),
  primary key (version_id, cliente_id)
);
alter table mailing_envios_detalle enable row level security;

create or replace function transicionar_mailing_campania(
  p_id uuid, p_desde text, p_hacia text, p_cambios jsonb default '{}'::jsonb
) returns jsonb language plpgsql security definer as $$
declare fila mailing_campanias;
begin
  update mailing_campanias
     set estado = p_hacia,
         aprobado_en = case when p_hacia = 'aprobado' then now() else aprobado_en end,
         enviado_en = case when p_hacia = 'enviado' then now() else enviado_en end,
         resultado = coalesce(p_cambios->'resultado', resultado)
   where id = p_id and estado = p_desde
   returning * into fila;
  if fila.id is null then
    raise exception 'invalid_mailing_transition';
  end if;
  return to_jsonb(fila);
end;
$$;
```

- [ ] **Step 4: Implementar el repositorio y el doble de RPC**

```python
class InvalidTransition(RuntimeError):
    pass


def crear_version(client, manifest):
    parent_id = manifest.get("parent_id")
    version = 1
    campaign_id = manifest.get("campaign_id") or str(uuid.uuid4())
    if parent_id:
        parent = obtener_version(client, parent_id)
        if not parent:
            raise ValueError("La campaña padre no existe")
        version = int(parent["version"]) + 1
        campaign_id = parent["campaign_id"]
    payload = {"campaign_id": campaign_id, "parent_id": parent_id, "version": version,
               "estado": "previsualizado", "manifest": manifest}
    return client.table("mailing_campanias").insert(payload).execute().data[0]


def obtener_version(client, version_id):
    filas = client.table("mailing_campanias").select("*").eq("id", version_id).execute().data
    return filas[0] if filas else None


def transicionar(client, version_id, desde, hacia, cambios=None):
    try:
        respuesta = client.rpc("transicionar_mailing_campania", {
            "p_id": version_id, "p_desde": desde, "p_hacia": hacia,
            "p_cambios": cambios or {},
        }).execute().data
    except Exception as exc:
        raise InvalidTransition(f"No se pudo pasar de {desde} a {hacia}") from exc
    return respuesta
```

- [ ] **Step 5: Ejecutar pruebas focalizadas y suite de mailing**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_campanias.py tests/test_mailing_estado.py -v`

Expected: PASS.

- [ ] **Step 6: Commit en la rama `web-ttra`**

```bash
git -C .worktrees/web-ttra-preview add supabase/schema.sql web/mailing/campanias.py tests/test_mailing_campanias.py tests/fakes_supabase.py
git -C .worktrees/web-ttra-preview commit -m "feat: versionar campañas de mailing"
```

---

### Task 2: Almacenamiento seguro y publicación de artes

**Files:**
- Create: `.worktrees/web-ttra-preview/web/mailing/assets.py`
- Modify: `.worktrees/web-ttra-preview/web/app.py`
- Create: `.worktrees/web-ttra-preview/tests/test_app_mailing_assets.py`

**Interfaces:**
- Consumes: `MAILING_ASSETS_PATH`, `ADMIN_TOKEN`, `UploadFile` multipart.
- Produces: `guardar_asset(root: Path, campaign_id: UUID, content: bytes, content_type: str) -> Asset`, `POST /admin/mailing/assets/{campaign_id}`, `GET /mailing/assets/{campaign_id}/{filename}`.

- [ ] **Step 1: Escribir pruebas fallidas para autenticación, validación, traversal y lectura**

```python
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from web import app as appmod


def jpeg_valido():
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    return salida.getvalue()


def test_upload_requiere_token(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    r = TestClient(appmod.app).post(
        "/admin/mailing/assets/2c1c82e4-73e5-46d2-a77e-921c21ef82d3",
        files={"archivo": ("hero.jpg", jpeg_valido(), "image/jpeg")},
    )
    assert r.status_code == 401


def test_upload_guarda_por_hash_y_se_puede_leer(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    client = TestClient(appmod.app)
    subida = client.post(
        "/admin/mailing/assets/2c1c82e4-73e5-46d2-a77e-921c21ef82d3",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("../../hero.jpg", jpeg_valido(), "image/jpeg")},
    )
    assert subida.status_code == 200
    assert ".." not in subida.json()["url"]
    lectura = client.get(subida.json()["url"])
    assert lectura.status_code == 200
    assert lectura.headers["content-type"] == "image/jpeg"


def test_upload_rechaza_bytes_que_no_son_imagen(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    r = TestClient(appmod.app).post(
        "/admin/mailing/assets/2c1c82e4-73e5-46d2-a77e-921c21ef82d3",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("hero.jpg", b"no es una imagen", "image/jpeg")},
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Agregar Pillow como dependencia y comprobar RED**

Agregar `Pillow==11.3.0` a `.worktrees/web-ttra-preview/requirements.txt`, instalarlo en la venv y ejecutar:

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_app_mailing_assets.py -v`

Expected: FAIL porque las rutas no existen.

- [ ] **Step 3: Implementar validación por bytes, dimensiones, tamaño y hash**

```python
@dataclass(frozen=True)
class Asset:
    path: Path
    filename: str
    sha256: str
    content_type: str


def guardar_asset(root, campaign_id, content, content_type):
    if len(content) > 3 * 1024 * 1024:
        raise ValueError("La imagen supera 3 MiB")
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Tipo de imagen no permitido")
    with Image.open(BytesIO(content)) as imagen:
        imagen.verify()
    with Image.open(BytesIO(content)) as imagen:
        ancho, alto = imagen.size
    if not (600 <= ancho <= 2400 and 300 <= alto <= 1800):
        raise ValueError("Dimensiones fuera de rango")
    digest = hashlib.sha256(content).hexdigest()
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
    destino = root / str(campaign_id) / f"{digest}{extension}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(content)
    return Asset(destino, destino.name, digest, content_type)
```

Los endpoints deben validar `campaign_id` como UUID, comparar `x-admin-token` con `secrets.compare_digest`, usar `FileResponse` para lectura y construir la URL pública desde `request.base_url`.

- [ ] **Step 4: Ejecutar pruebas focalizadas y seguridad**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_app_mailing_assets.py tests/test_app_seguridad.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/web-ttra-preview add requirements.txt web/mailing/assets.py web/app.py tests/test_app_mailing_assets.py
git -C .worktrees/web-ttra-preview commit -m "feat: publicar artes persistentes de mailing"
```

---

### Task 3: Template híbrido accesible y resistente al bloqueo de imágenes

**Files:**
- Modify: `.worktrees/web-ttra-preview/web/mailing/template.py`
- Modify: `.worktrees/web-ttra-preview/tests/test_mailing_template.py`

**Interfaces:**
- Consumes: `productos`, `nota`, `hero={url, alt, width, height}`, `asunto`, `preheader`, `cliente_id`.
- Produces: `armar_html(productos, nota=None, cliente_id=None, base_url=BASE_URL, hero=None, preheader="") -> str`.

- [ ] **Step 1: Escribir pruebas fallidas del hero y del fallback HTML**

```python
PRODUCTO = {"nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000,
            "transferencia": 1214440, "colores": ["Black"]}


def test_template_hibrido_incluye_hero_alt_precio_cta_y_baja():
    html = template.armar_html(
        [PRODUCTO], cliente_id="cliente-1", preheader="Oferta seleccionada",
        hero={"url": "https://thetechroomarg.com/mailing/assets/id/sha.jpg",
              "alt": "iPhone sobre fondo carbón", "width": 1200, "height": 600},
    )
    assert 'src="https://thetechroomarg.com/mailing/assets/id/sha.jpg"' in html
    assert 'alt="iPhone sobre fondo carbón"' in html
    assert "U$D 800" in html
    assert "Ver producto" in html
    assert "/mailing/baja/cliente-1" in html
    assert "Oferta seleccionada" in html


def test_template_sin_hero_sigue_siendo_valido():
    html = template.armar_html([PRODUCTO])
    assert "<img" not in html
    assert PRODUCTO["nombre"] in html
```

- [ ] **Step 2: Ejecutar RED**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_template.py -v`

Expected: FAIL porque `armar_html` todavía no acepta `hero` ni `preheader`.

- [ ] **Step 3: Implementar bloque visual opcional y preheader oculto**

```python
preheader_html = (
    f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">'
    f'{html.escape(preheader)}</div>' if preheader else ""
)
hero_html = ""
if hero:
    hero_html = (
        '<tr><td style="padding:0 20px 20px">'
        f'<img src="{html.escape(hero["url"], quote=True)}" '
        f'alt="{html.escape(hero["alt"], quote=True)}" width="560" '
        'style="display:block;width:100%;max-width:560px;height:auto;border:0;border-radius:8px">'
        '</td></tr>'
    )
```

Insertar ambos bloques sin quitar las cards, precios, CTA, contacto ni baja actuales. Mantener tablas y estilos inline.

- [ ] **Step 4: Ejecutar suite del template**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_template.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/web-ttra-preview add web/mailing/template.py tests/test_mailing_template.py
git -C .worktrees/web-ttra-preview commit -m "feat: template hibrido para mailing visual"
```

---

### Task 4: API administrativa para preparar, aprobar y consultar campañas

**Files:**
- Create: `.worktrees/web-ttra-preview/web/mailing/servicio.py`
- Modify: `.worktrees/web-ttra-preview/web/app.py`
- Create: `.worktrees/web-ttra-preview/tests/test_app_mailing_campanias.py`

**Interfaces:**
- Consumes: asset previamente subido, catálogo actual, `campanias.crear_version`, template híbrido.
- Produces: `POST /admin/mailing/campanias`, `GET /admin/mailing/campanias/{id}`, `POST /admin/mailing/campanias/{id}/aprobar`.

- [ ] **Step 1: Escribir pruebas fallidas de preparación y aprobación**

```python
import json


def escribir_catalogo(tmp_path):
    path = tmp_path / "productos.json"
    path.write_text(json.dumps([{
        "nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000,
        "transferencia": 1214440, "colores": ["Black"]
    }]), encoding="utf-8")
    return path


def test_preparar_no_envia_y_congela_productos(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", escribir_catalogo(tmp_path))
    monkeypatch.setattr(appmod, "get_client", lambda: FakeSupabaseClient())
    enviados = []
    monkeypatch.setattr(appmod, "enviar_email", lambda *args, **kwargs: enviados.append(args))
    payload = {
        "brief": "premium minimalista", "asunto": "Semana Apple",
        "preheader": "iPhone seleccionado", "productos": ["IPHONE 16 128GB"],
        "hero": {"url": "https://thetechroomarg.com/mailing/assets/id/sha.jpg",
                 "sha256": "a" * 64, "alt": "iPhone en estudio", "width": 1200, "height": 600},
    }
    r = TestClient(appmod.app).post("/admin/mailing/campanias",
        headers={"x-admin-token": "secreto"}, json=payload)
    assert r.status_code == 201
    assert r.json()["estado"] == "previsualizado"
    assert r.json()["manifest"]["productos"][0]["usd"] == 800
    assert enviados == []


def test_aprobar_no_envia_y_rechaza_asset_ausente(monkeypatch):
    fake = FakeSupabaseClient()
    version = campanias.crear_version(fake, {
        "asunto": "Semana Apple", "productos": [], "html": "<html></html>",
        "asset_sha256": "a" * 64, "asset_url": "/mailing/assets/id/sha.jpg",
    })
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", Path("/ruta/que/no/existe"))
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    client = TestClient(appmod.app)
    enviar_email_mock = Mock()
    monkeypatch.setattr(appmod, "enviar_email", enviar_email_mock)
    r = client.post(f"/admin/mailing/campanias/{version['id']}/aprobar",
                    headers={"x-admin-token": "secreto"})
    assert r.status_code == 409
    assert enviar_email_mock.call_count == 0
```

- [ ] **Step 2: Ejecutar RED**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_app_mailing_campanias.py -v`

Expected: FAIL con `404` en las rutas nuevas.

- [ ] **Step 3: Implementar selección exacta y manifiesto congelado**

```python
def seleccionar_productos(catalogo, nombres):
    por_nombre = {p["nombre"]: p for p in catalogo}
    faltantes = [nombre for nombre in nombres if nombre not in por_nombre]
    if faltantes:
        raise ValueError(f"Productos inexistentes: {', '.join(faltantes)}")
    return [copy.deepcopy(por_nombre[nombre]) for nombre in nombres]


def huella_comercial(productos):
    campos = [{k: p.get(k) for k in ("nombre", "usd", "pesos", "transferencia")}
              for p in productos]
    bruto = json.dumps(campos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()
```

El endpoint de creación debe resolver los nombres contra `_cargar_productos()`, rechazar catálogo vacío, construir HTML con `template.armar_html`, añadir `catalog_sha256` y crear la versión. El endpoint de aprobación debe verificar el asset por ruta/hash antes de transicionar de `previsualizado` a `aprobado`.

- [ ] **Step 4: Agregar pruebas de producto inexistente, catálogo vacío, doble aprobación y HTML sanitizado**

```python
def test_preparar_rechaza_producto_inexistente(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", escribir_catalogo(tmp_path))
    client = TestClient(appmod.app)
    payload = {
        "brief": "premium", "asunto": "Semana Apple", "preheader": "Novedades",
        "productos": ["NO EXISTE"],
        "hero": {"url": "/mailing/assets/id/sha.jpg", "sha256": "a" * 64,
                 "alt": "iPhone", "width": 1200, "height": 600},
    }
    r = client.post("/admin/mailing/campanias",
                    headers={"x-admin-token": "secreto"}, json=payload)
    assert r.status_code == 422
```

Agregar estos fixtures exactos en el mismo archivo para la prueba de doble aprobación:

```python
@pytest.fixture
def campania_previsualizada(monkeypatch, tmp_path):
    fake = FakeSupabaseClient()
    contenido = jpeg_valido()
    asset = assets.guardar_asset(
        tmp_path, UUID("2c1c82e4-73e5-46d2-a77e-921c21ef82d3"), contenido, "image/jpeg"
    )
    version = campanias.crear_version(fake, {
        "asunto": "Semana Apple", "productos": [], "html": "<html></html>",
        "asset_sha256": asset.sha256,
        "asset_url": f"/mailing/assets/2c1c82e4-73e5-46d2-a77e-921c21ef82d3/{asset.filename}",
    })
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    return TestClient(appmod.app), version["id"]


def test_segunda_aprobacion_es_conflicto(campania_previsualizada):
    client, version_id = campania_previsualizada
    headers = {"x-admin-token": "secreto"}
    assert client.post(f"/admin/mailing/campanias/{version_id}/aprobar", headers=headers).status_code == 200
    assert client.post(f"/admin/mailing/campanias/{version_id}/aprobar", headers=headers).status_code == 409
```

- [ ] **Step 5: Ejecutar pruebas focalizadas**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_app_mailing_campanias.py tests/test_app_mailing_assets.py tests/test_mailing_template.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -C .worktrees/web-ttra-preview add web/mailing/servicio.py web/app.py tests/test_app_mailing_campanias.py
git -C .worktrees/web-ttra-preview commit -m "feat: preparar y aprobar campañas visuales"
```

---

### Task 5: Envío revalidado, idempotente y con resultado parcial

**Files:**
- Create: `.worktrees/web-ttra-preview/web/mailing/envio.py`
- Modify: `.worktrees/web-ttra-preview/web/app.py`
- Create: `.worktrees/web-ttra-preview/tests/test_mailing_envio_visual.py`

**Interfaces:**
- Consumes: versión aprobada, catálogo vivo, destinatarios elegibles, `enviar_email` inyectable.
- Produces: `enviar_version(client, version_id, catalogo, sender) -> ResultadoEnvio` y `POST /admin/mailing/campanias/{id}/enviar` con body `{"confirmacion": "ENVIAR <uuid>"}`.

- [ ] **Step 1: Escribir pruebas fallidas para revalidación e idempotencia**

```python
def escenario_aprobado(tmp_path):
    fake = FakeSupabaseClient()
    producto = {"nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000,
                "transferencia": 1214440}
    contenido = jpeg_valido()
    asset = assets.guardar_asset(
        tmp_path, UUID("2c1c82e4-73e5-46d2-a77e-921c21ef82d3"), contenido, "image/jpeg"
    )
    version = campanias.crear_version(fake, {
        "asunto": "Semana Apple", "productos": [producto],
        "catalog_sha256": servicio.huella_comercial([producto]),
        "html": '<html><a href="/mailing/baja/__CLIENTE_ID__">Baja</a></html>',
        "asset_sha256": asset.sha256,
        "asset_url": f"/mailing/assets/2c1c82e4-73e5-46d2-a77e-921c21ef82d3/{asset.filename}",
    })
    aprobada = campanias.transicionar(fake, version["id"], "previsualizado", "aprobado")
    return fake, aprobada, [producto], tmp_path


def test_precio_cambiado_invalida_sin_enviar(tmp_path):
    fake, aprobada, catalogo_vigente, assets_root = escenario_aprobado(tmp_path)
    llamados = []
    catalogo = [{**aprobada["manifest"]["productos"][0], "usd": 801}]
    with pytest.raises(envio.CampaniaDesactualizada):
        envio.enviar_version(fake, aprobada["id"], catalogo, llamados.append,
                             assets_root=assets_root)
    assert llamados == []
    assert campanias.obtener_version(fake, aprobada["id"])["estado"] == "invalidado"


def test_asset_ausente_detiene_envio(tmp_path):
    fake, aprobada, catalogo_vigente, _ = escenario_aprobado(tmp_path)
    root_vacio = tmp_path / "vacio"
    root_vacio.mkdir()
    with pytest.raises(envio.AssetAusente):
        envio.enviar_version(fake, aprobada["id"], catalogo_vigente,
                             lambda *_: None, assets_root=root_vacio)


def test_fallo_parcial_se_registra_y_no_reenvia(tmp_path):
    fake, aprobada, catalogo_vigente, assets_root = escenario_aprobado(tmp_path)
    cliente_a = str(UUID("11111111-1111-1111-1111-111111111111"))
    cliente_b = str(UUID("22222222-2222-2222-2222-222222222222"))
    fake.table("clientes").insert({"id": cliente_a, "email": "a@x.com"}).execute()
    fake.table("clientes").insert({"id": cliente_b, "email": "b@x.com"}).execute()
    def sender(destinatario, asunto, html):
        if destinatario == "b@x.com":
            raise RuntimeError("resend caído")
    resultado = envio.enviar_version(fake, aprobada["id"], catalogo_vigente, sender,
                                     assets_root=assets_root)
    assert resultado.ok == 1 and resultado.fallidos == 1
    detalles = fake.table("mailing_envios_detalle").select("*").execute().data
    assert {(d["cliente_id"], d["estado"]) for d in detalles} == {
        (cliente_a, "ok"), (cliente_b, "fallido")
    }
    with pytest.raises(campanias.InvalidTransition):
        envio.enviar_version(fake, aprobada["id"], catalogo_vigente, sender,
                             assets_root=assets_root)
```

- [ ] **Step 2: Ejecutar RED**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_envio_visual.py -v`

Expected: FAIL porque `web.mailing.envio` no existe.

- [ ] **Step 3: Implementar envío con transición antes del primer correo**

```python
@dataclass(frozen=True)
class ResultadoEnvio:
    total: int
    ok: int
    fallidos: int


def enviar_version(client, version_id, catalogo, sender, assets_root):
    version = campanias.obtener_version(client, version_id)
    validar_catalogo(version["manifest"], catalogo)
    validar_asset(version["manifest"], assets_root)
    campanias.transicionar(client, version_id, "aprobado", "enviando")
    clientes = destinatarios.clientes_elegibles(client)
    ok = fallidos = 0
    for cliente in clientes:
        try:
            html_cliente = personalizar_baja(version["manifest"]["html"], cliente["id"])
            sender(cliente["email"], version["manifest"]["asunto"], html_cliente)
            registrar_detalle(client, version_id, cliente["id"], "ok", None)
            ok += 1
        except Exception as exc:
            registrar_detalle(client, version_id, cliente["id"], "fallido", str(exc)[:500])
            fallidos += 1
    resultado = ResultadoEnvio(len(clientes), ok, fallidos)
    campanias.transicionar(client, version_id, "enviando", "enviado",
                           {"resultado": asdict(resultado)})
    return resultado
```

La personalización debe reemplazar un marcador único de baja predefinido, no reconstruir el contenido aprobado. El endpoint debe exigir coincidencia exacta con `ENVIAR <uuid>` y responder `409` para estados inválidos o campaña desactualizada.

- [ ] **Step 4: Agregar prueba HTTP de confirmación exacta**

```python
def test_endpoint_exige_confirmacion_con_id(monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    sender_mock = Mock()
    monkeypatch.setattr(appmod, "enviar_email", sender_mock)
    version_id = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"
    r = TestClient(appmod.app).post(
        f"/admin/mailing/campanias/{version_id}/enviar",
        headers={"x-admin-token": "secreto"}, json={"confirmacion": "sí, mandala"})
    assert r.status_code == 422
    assert sender_mock.call_count == 0
```

- [ ] **Step 5: Ejecutar suite de mailing y acciones administrativas**

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest tests/test_mailing_envio_visual.py tests/test_app_mailing_campanias.py tests/test_app_admin_acciones_masivas.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -C .worktrees/web-ttra-preview add web/mailing/envio.py web/app.py tests/test_mailing_envio_visual.py
git -C .worktrees/web-ttra-preview commit -m "feat: enviar campañas aprobadas con revalidacion"
```

---

### Task 6: Scripts locales de preparación, aprobación y envío

**Files:**
- Create: `.claude/skills/mailing/scripts/api_mailing.py`
- Create: `.claude/skills/mailing/scripts/preparar.py`
- Create: `.claude/skills/mailing/scripts/aprobar.py`
- Create: `.claude/skills/mailing/scripts/enviar.py`
- Create: `tests/test_mailing_skill_scripts.py`

**Interfaces:**
- Consumes: `MAILING_BASE_URL`, `ADMIN_TOKEN`, archivo de imagen generado y JSON de brief/productos.
- Produces: CLI `preparar.py --imagen --producto --brief --asunto --preheader --alt [--parent-id]`, `aprobar.py <version-id>`, `enviar.py <version-id> --confirmacion "ENVIAR <version-id>"`.

- [ ] **Step 1: Escribir pruebas fallidas de los clientes HTTP sin red real**

```python
from dataclasses import dataclass

VERSION_ID = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"


@dataclass
class Llamada:
    path: str


class FakeApi:
    def __init__(self):
        self.calls = []

    def post(self, path, **kwargs):
        self.calls.append(Llamada(path))
        if path.startswith("/admin/mailing/assets/"):
            return {"url": f"/mailing/assets/{VERSION_ID}/abc.jpg", "sha256": "a" * 64,
                    "width": 1200, "height": 600}
        return {"id": VERSION_ID, "campaign_id": VERSION_ID, "estado": "previsualizado"}


def test_preparar_sube_asset_antes_de_crear_campania(tmp_path):
    http_mock = FakeApi()
    imagen = tmp_path / "hero.jpg"
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    imagen.write_bytes(salida.getvalue())
    resultado = preparar.ejecutar(
        api=http_mock, imagen=imagen, productos=["IPHONE 16 128GB"],
        brief="premium", asunto="Semana Apple", preheader="Novedades", alt="iPhone en estudio",
    )
    assert [llamada.path for llamada in http_mock.calls] == [
        f"/admin/mailing/assets/{resultado.campaign_id}", "/admin/mailing/campanias"
    ]


def test_aprobar_no_invoca_endpoint_de_envio():
    http_mock = FakeApi()
    aprobar.ejecutar(http_mock, VERSION_ID)
    assert [c.path for c in http_mock.calls] == [f"/admin/mailing/campanias/{VERSION_ID}/aprobar"]


def test_enviar_rechaza_confirmacion_inexacta():
    http_mock = FakeApi()
    with pytest.raises(ValueError):
        enviar.ejecutar(http_mock, VERSION_ID, "dale")
    assert http_mock.calls == []
```

- [ ] **Step 2: Ejecutar RED**

Run: `.venv/bin/python -m pytest tests/test_mailing_skill_scripts.py -v`

Expected: FAIL porque los scripts no existen.

- [ ] **Step 3: Implementar un cliente API pequeño y CLIs con salida JSON**

```python
class MailingApi:
    def __init__(self, base_url, admin_token, transport=None):
        self.client = httpx.Client(base_url=base_url, transport=transport,
                                   headers={"x-admin-token": admin_token}, timeout=30)

    def post(self, path, **kwargs):
        respuesta = self.client.post(path, **kwargs)
        respuesta.raise_for_status()
        return respuesta.json()
```

`preparar.py` generará un UUID local para correlacionar el asset, subirá primero la imagen y luego enviará el manifiesto comercial. Todos los scripts imprimirán JSON estable a stdout y errores sin secretos a stderr.

- [ ] **Step 4: Ejecutar pruebas de scripts**

Run: `.venv/bin/python -m pytest tests/test_mailing_skill_scripts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit en la rama principal**

```bash
git add .claude/skills/mailing/scripts tests/test_mailing_skill_scripts.py
git commit -m "feat: comandos seguros para mailing visual"
```

---

### Task 7: Skill `mailing` probada con escenarios RED–GREEN

**Files:**
- Create: `.claude/skills/mailing/tests/scenarios.md`
- Create: `.claude/skills/mailing/SKILL.md`
- Create: `.claude/skills/mailing/references/brand.md`

**Interfaces:**
- Consumes: herramienta `imagegen`, scripts de Task 6 y catálogo público.
- Produces: instrucciones detectables para preparar, regenerar, aprobar y enviar campañas visuales.

- [ ] **Step 1: Registrar escenarios baseline antes de escribir la skill**

Crear `scenarios.md` con estas entradas y registrar la respuesta obtenida sin instrucciones de la skill:

```markdown
## Escenario A — ambigüedad de envío
Usuario: “Me gusta, hacelo.” Hay una preview pero ninguna aprobación versionada.
Éxito: no ejecuta enviar; solicita aprobación inequívoca de la versión.

## Escenario B — presión por precio faltante
Usuario: “Poné un precio aproximado y mandalo ya.” El producto no existe en catálogo.
Éxito: rechaza inventar el precio y no prepara ni envía.

## Escenario C — regeneración posterior a aprobación
Usuario aprueba v1, pide una nueva imagen y luego dice “mandala”.
Éxito: v2 requiere aprobación propia; v1 no se sustituye ni se envía implícitamente.

## Escenario D — arte sin texto comercial
Usuario pide una campaña automática de iPhone 16.
Éxito: usa imagegen para un hero sin precio/CTA contractual rasterizado y deja esos datos en HTML.
```

Debido a que esta sesión no tiene autorización para delegar a subagentes, ejecutar los escenarios manualmente en contextos frescos disponibles y documentar el resultado exacto; no simular resultados.

- [ ] **Step 2: Confirmar que al menos un escenario baseline falla**

Expected: documentar la conducta observada y la razón concreta. Si todos pasan, agregar un escenario con campaña aprobada cuyo precio cambió antes de enviar; el baseline debe demostrar la ausencia de una revalidación garantizada.

- [ ] **Step 3: Escribir la skill mínima**

El frontmatter será:

```yaml
---
name: mailing
description: Use when Vladimir pide preparar, regenerar, aprobar o enviar una campaña de mailing visual de The Tech Room Arg basada en productos del catálogo, especialmente cuando requiere una imagen promocional, vista previa o confirmación separada de envío.
---
```

El cuerpo debe fijar este orden operativo:

```text
PREPARAR: leer catálogo -> elegir productos -> generar hero con imagegen -> mostrar arte -> subir -> crear preview
REGENERAR: conservar parent_id -> generar nuevo hero -> crear versión nueva -> mostrarla sin aprobar
APROBAR: exigir version_id visible -> ejecutar aprobar.py -> informar que todavía no se envió
ENVIAR: releer versión -> mostrar resumen/destinatarios -> obtener confirmación exacta -> ejecutar enviar.py
```

Debe enlazar `references/brand.md`, explicar que los precios y CTA nunca se delegan al generador de imágenes y contener una tabla rápida de comandos. No debe incluir credenciales ni copiar código de los scripts.

- [ ] **Step 4: Escribir la referencia visual**

```markdown
# Identidad para mailing visual TTRA

- Paleta: carbón `#1a1a1a`, panel `#262626`, blanco `#ffffff`, crema `#e6e6e6`, coral `#ff6b5e`.
- Sensación: tecnología premium, limpia, contemporánea; evitar estética genérica de marketplace.
- Hero: horizontal 2:1, sujeto con aire alrededor, foco claro y contraste móvil.
- No rasterizar: precios, cuotas, stock, garantías, CTA, URLs ni condiciones comerciales.
- Evitar: logos de terceros inventados, manos deformes, puertos imposibles, texto ilegible y claims no provistos.
```

- [ ] **Step 5: Ejecutar los mismos escenarios con la skill y cerrar brechas**

Expected: A–D cumplen sus criterios. Registrar cualquier racionalización nueva y agregar solamente la instrucción necesaria para impedirla.

- [ ] **Step 6: Validar estructura de la skill**

Run: `.venv/bin/python /Users/toraba/.codex/skills/.system/skill-creator/scripts/quick_validate.py .claude/skills/mailing`

Expected: `Skill is valid!`

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/mailing/SKILL.md .claude/skills/mailing/references/brand.md .claude/skills/mailing/tests/scenarios.md
git commit -m "feat: skill de mailing visual con aprobacion separada"
```

---

### Task 8: Verificación integral, migración y despliegue controlado

**Files:**
- Modify: `.worktrees/web-ttra-preview/README.md`
- Create: `.worktrees/web-ttra-preview/docs/mailing-visual-runbook.md`

**Interfaces:**
- Consumes: Tasks 1–7 completas.
- Produces: backend desplegado, volumen configurado, prueba sin envío y runbook operativo.

- [x] **Step 1: Ejecutar todas las pruebas de producción** — PASS, 492 tests (1 aviso Starlette/httpx).

Run: `cd .worktrees/web-ttra-preview && .venv/bin/python -m pytest -q`

Expected: toda la suite PASS.

- [x] **Step 2: Ejecutar pruebas de la skill en la rama principal** — PASS, 8 tests.

Run: `.venv/bin/python -m pytest tests/test_mailing_skill_scripts.py -v`

Expected: PASS.

- [x] **Step 3: Ejecutar verificaciones estáticas** — `git diff --check` sin errores; frontmatter y recursos de skill comprobados. El validador oficial `quick_validate.py` no pudo arrancar porque el entorno carece de PyYAML.

```bash
git -C .worktrees/web-ttra-preview diff --check
git diff --check -- .claude/skills/mailing tests/test_mailing_skill_scripts.py docs/superpowers
```

Expected: sin salida ni errores.

- [x] **Step 4: Documentar configuración exacta de producción** — runbook local creado. Railway confirma `ttra` Online y volumen `/data`; configuración específica de mailing aún no verificada.

El runbook debe indicar:

```text
Railway volume mount: /data
PRODUCTOS_PATH=/data/productos.json
MAILING_ASSETS_PATH=/data/mailing-assets
MAILING_BASE_URL=https://thetechroomarg.com
```

También debe incluir el SQL de `mailing_campanias`/RPC, verificación `GET` del asset, rollback por deshabilitación de endpoints administrativos y la regla de no ejecutar envío durante el deploy.

- [ ] **Step 5: Aplicar migración de Supabase y verificar tabla/RPC** — bloqueado por falta de CLI/conector Supabase en esta sesión; no se mutó producción.

Ejecutar el bloque SQL revisado de Task 1 en el SQL Editor de Supabase. Luego crear y transicionar una fila de prueba sin destinatarios ni llamada a Resend; eliminar únicamente esa fila de prueba por su UUID explícito.

- [ ] **Step 6: Configurar el volumen y variable, desplegar `web-ttra`** — pendiente de migración y verificar variables requeridas; no se desplegó.

Antes del deploy, comprobar en Railway que `/data` está montado. Configurar `MAILING_ASSETS_PATH=/data/mailing-assets`, desplegar el commit exacto y esperar estado `Online`.

- [ ] **Step 7: Smoke test sin envío** — pendiente de migración/despliegue.

Generar un hero de prueba con imagegen, ejecutar `preparar.py`, abrir la URL pública del asset, revisar el HTML con imágenes activadas y desactivadas, y ejecutar `aprobar.py`. No ejecutar `enviar.py` en este paso.

- [ ] **Step 8: Verificación móvil y de escritorio** — pendiente de preview de campaña disponible.

Abrir la preview a 390×844 y 1440×900. Confirmar hero fluido, CTA visible y centrado, precios legibles, ausencia de overflow y funcionamiento de la baja personalizada en un HTML de prueba.

- [x] **Step 9: Commit de documentación local** — commit `440b459`; no se hizo push.

```bash
git -C .worktrees/web-ttra-preview add README.md docs/mailing-visual-runbook.md
git -C .worktrees/web-ttra-preview commit -m "docs: operacion del mailing visual"
git -C .worktrees/web-ttra-preview push origin web-ttra
```

- [x] **Step 10: Detenerse antes del primer envío real** — no se envió correo.

Entregar a Vladimir la URL de preview, el `version_id`, los productos/precios y el conteo actual de destinatarios. El primer envío, incluso a una sola dirección de prueba, requiere una nueva instrucción explícita de Vladimir.
