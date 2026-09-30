---
name: pedido
description: Carga un cliente nuevo (si no existe) y un pedido en la base de producción de The Tech Room Arg (Supabase) directo desde el chat — cuenta, domicilio, pedido con fecha de entrega y mail de credenciales. Usar cuando Vladimir pide "inyectar", "cargar", "meter" o "sumar" un cliente y/o un pedido con nombre, contacto, dirección y producto.
---

# Cargar cliente + pedido

Escribe DIRECTO en la base de producción (Supabase) — no hay ambiente de
prueba separado (ver `web/supabase_client.py`, una sola URL/key por variables
de entorno). Es una acción real e irreversible sin borrar a mano
(`web/cuentas.py::eliminar_cliente`, `web/pedidos.py::eliminar_pedido`).

## Quick start

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/pedido/scripts/cargar_pedido.py \
  --nombre "Inti Nahuel" --apellido "Algarbe" \
  --email intialgarbe@gmail.com --celular "+54 9 3516 09-8597" \
  --direccion "Bv. Quinta Sta. Ana 162, X5000 Córdoba" \
  --producto "s26 ultra 256gb" --fecha manana   # opcional: --piso 3 --depto B
```

- `--producto` es un término de búsqueda (como en `/precios`): debe matchear
  **exactamente un** producto de `web/productos.json`, si no el script corta
  y lista los candidatos para que se afine la búsqueda.
- `--fecha` acepta `YYYY-MM-DD`, o `hoy` / `manana` / `pasado manana`
  (default: `manana`).
- `--cantidad` (default 1).

## Qué hace, paso a paso (replica el flujo real de `/registro` y `/api/pedidos` de la web)

1. Busca el producto en `productos.json` (falla si no matchea exactamente uno).
2. Busca si el **celular** ya existe en `clientes`:
   - **Si existe**: reusa ese `cliente_id`, NO crea cuenta nueva, NO manda mail de
     credenciales — solo agrega el pedido.
   - **Si no existe**: valida que el email tampoco esté usado por otro
     celular (si lo está, corta con error — hay que revisarlo a mano), crea
     la cuenta con `client.auth.admin.create_user` (`email_confirm: True`,
     salteando la confirmación por mail ya que la creó un admin de
     confianza — mismo patrón que `web/cuentas.py::resetear_password_cliente`),
     inserta la fila en `clientes` con `debe_cambiar_password: True`, y crea
     el domicilio "Principal" con `domicilios.crear`.
3. Arma el `detalle` del pedido (nombre, cantidad, usd_unitario/subtotal,
   proveedor interno vía `resolver_proveedor`) y llama a
   `pedidos.guardar_pedido` con `modo_precio="minorista"`, `origen="manual"`.
4. Si el cliente es nuevo, manda un mail (vía `web/email_util.enviar_email`,
   Resend) con el email y la contraseña temporal — por
   [[feedback-mail-al-inyectar-cliente]].

## Gotchas

- El catálogo NO trackea color por separado para productos con varios
  colores en el mismo nombre (ej. Samsung: `"S26 Ultra ... (Black, Cobalt
  Violet, ...)"`) — el pedido no guarda qué color pidió el cliente. Si el
  cliente pidió un color puntual, anotalo aparte (no queda en la DB).
- Precio siempre **minorista** — este script no arma pedidos mayoristas
  (la lógica de verificación de precio mayorista del checkout real es más
  compleja; si hace falta, avisar para extenderlo en vez de improvisarlo).
- Sin código de descuento ni promoción — es la carga simple sin esos flujos.
- Si el celular existe pero es un "lead" sin cuenta (`auth_id` nulo), el
  script igual reusa ese `cliente_id` para el pedido, sin crear cuenta — si
  hace falta que tenga login, avisar aparte para dar de alta la cuenta.
- El campo interno `proveedor` puede salir "Proveedor no identificado" si el
  nombre del producto no matchea `web/proveedores.json` (pasa con productos
  que tienen colores embebidos en el nombre, como los Samsung de arriba —
  es un problema real de nombres, no del script).
