-- supabase/schema.sql
-- Correr esto una sola vez en el SQL Editor del proyecto de Supabase.

create extension if not exists pgcrypto;

create table if not exists clientes (
  id uuid primary key default gen_random_uuid(),
  auth_id uuid unique references auth.users(id) on delete set null,
  nombre text not null,
  apellido text not null,
  celular text not null unique,
  email text not null unique,
  provincia text,
  username text unique,
  tipo_cliente text not null default 'minorista',
  debe_cambiar_password boolean not null default false,
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

-- Los clientes existentes quedan sin provincia; las altas nuevas la
-- completan obligatoriamente desde la aplicación.
alter table clientes add column if not exists provincia text;

-- Contactos tipo "proveedor" (sin cuenta web, sin mail) pueden quedar
-- cargados solo con dirección, para autocompletar el botón "Vamos" del
-- panel de entregas sin tener que tipearla cada vez.
alter table clientes alter column email drop not null;
alter table clientes add column if not exists direccion text;

-- Fecha en que una cuenta mayorista aceptó las condiciones comerciales
-- para revendedores (popup obligatorio en la landing). Null = no aceptadas.
alter table clientes add column if not exists condiciones_mayorista_aceptadas_en timestamptz;

-- Domicilios guardados por cliente para el checkout (hasta 5, uno
-- predeterminado). La columna clientes.direccion se mantiene aparte: la
-- sigue usando el panel admin para el "Vamos" de contactos-proveedor.
create table if not exists domicilios_cliente (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id) on delete cascade,
  alias text not null,
  direccion text not null,
  predeterminado boolean not null default false,
  creado_en timestamptz not null default now()
);
create index if not exists domicilios_cliente_cliente_id_idx on domicilios_cliente (cliente_id);
alter table domicilios_cliente enable row level security;

-- Migra el domicilio único que ya tenían las cuentas de clientes reales
-- (columna clientes.direccion) como su primer domicilio guardado,
-- predeterminado. No toca a los contactos-proveedor (sin auth_id).
insert into domicilios_cliente (cliente_id, alias, direccion, predeterminado)
select id, 'Principal', direccion, true
from clientes
where auth_id is not null
  and direccion is not null and trim(direccion) <> ''
  and not exists (select 1 from domicilios_cliente d where d.cliente_id = clientes.id);

create table if not exists pedidos (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id) on delete cascade,
  productos jsonb not null,
  detalle jsonb,
  total_usd numeric,
  descuento_usd numeric,
  modo_precio text not null default 'minorista',
  descuento_mayorista_usd numeric not null default 0,
  recibo_id text,
  recibo_emitido_en timestamptz,
  recibo_enviado_en timestamptz,
  fecha_entrega date,
  origen text not null default 'whatsapp',
  fecha timestamptz not null default now()
);

alter table pedidos add column if not exists fecha_entrega date;
alter table pedidos add column if not exists detalle jsonb;
alter table pedidos add column if not exists total_usd numeric;
alter table pedidos add column if not exists descuento_usd numeric;
alter table pedidos add column if not exists modo_precio text not null default 'minorista';
alter table pedidos add column if not exists descuento_mayorista_usd numeric not null default 0;
alter table pedidos add column if not exists recibo_id text;
alter table pedidos add column if not exists recibo_emitido_en timestamptz;
alter table pedidos add column if not exists recibo_enviado_en timestamptz;
alter table pedidos add column if not exists direccion_entrega text;
alter table pedidos add column if not exists orden_entrega integer;
alter table pedidos add column if not exists fotos_series jsonb not null default '[]'::jsonb;
create unique index if not exists pedidos_recibo_id_unico
  on pedidos (recibo_id) where recibo_id is not null;
create index if not exists pedidos_fecha_orden_entrega_idx
  on pedidos (fecha_entrega, orden_entrega);

-- Tareas operativas creadas desde el panel de entregas. No generan recibos
-- ni se muestran al cliente.
create table if not exists tareas_entrega (
  id uuid primary key default gen_random_uuid(),
  fecha_entrega date not null,
  titulo text not null,
  cliente_id uuid references clientes(id) on delete set null,
  nota text,
  direccion text,
  orden integer not null default 0,
  creada_en timestamptz not null default now()
);
create index if not exists tareas_entrega_fecha_orden_idx
  on tareas_entrega (fecha_entrega, orden);
alter table tareas_entrega add column if not exists completada_en timestamptz;
alter table tareas_entrega add column if not exists cliente_id uuid references clientes(id) on delete set null;
-- Nombre del cliente tal cual lo escribió el admin al crear la tarea: puede
-- coincidir con un cliente real (cliente_id) o ser un nombre libre sin
-- cuenta asociada — el campo "Cliente" del formulario ya no es opcional y
-- siempre se guarda, coincida o no con la base.
alter table tareas_entrega add column if not exists cliente_nombre text;

create sequence if not exists public.recibos_numero_seq start with 1993;
create or replace function public.siguiente_numero_recibo()
returns text language sql security definer set search_path = public as $$
  select '0001-' || nextval('public.recibos_numero_seq')::text;
$$;

create table if not exists interacciones_cliente (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid references clientes(id) on delete cascade,
  anon_id text,
  session_id text,
  tipo_evento text not null,
  producto_nombre text,
  categoria text,
  marca text,
  metadata jsonb not null default '{}'::jsonb,
  fecha timestamptz not null default now()
);

create table if not exists codigos_descuento (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id) on delete cascade,
  code text not null unique,
  productos jsonb not null default '[]'::jsonb,
  descuento_usd integer not null default 5,
  activo boolean not null default false,
  usado_en timestamptz,
  creado_en timestamptz not null default now()
);

-- Códigos promo genéricos (no atados a un cliente): al aplicarse suman un
-- producto de regalo a $0 al pedido, hasta agotar usos_maximos usos totales.
create table if not exists codigos_promo (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  producto_regalo text not null,
  usos_maximos integer not null default 20,
  usos_actuales integer not null default 0,
  activo boolean not null default true,
  creado_en timestamptz not null default now()
);

-- Retira la firma anterior de forma idempotente antes de ampliar el RPC.
drop function if exists public.guardar_pedido_con_descuento_mailing(
  uuid, text, jsonb, jsonb, numeric, numeric, numeric, date, text, text, numeric, text
);

-- Mailing opcional, regalo opcional y pedido se bloquean y confirman en una
-- sola transacción. Solo service_role puede invocar este RPC.
create or replace function public.guardar_pedido_con_descuento_mailing(
  p_cliente_id uuid,
  p_codigo text,
  p_productos jsonb,
  p_detalle jsonb,
  p_total_usd numeric,
  p_descuento_usd numeric,
  p_descuento_mailing_usd numeric,
  p_fecha_entrega date,
  p_direccion_entrega text,
  p_modo_precio text,
  p_descuento_mayorista_usd numeric,
  p_origen text default 'whatsapp',
  p_codigo_promo text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_codigo codigos_descuento%rowtype;
  v_codigo_promo codigos_promo%rowtype;
  v_pedido pedidos%rowtype;
  v_item jsonb;
  v_cantidad_item integer;
  v_cantidad_total integer := 0;
  v_unitario numeric;
  v_subtotal numeric;
  v_total_bruto numeric := 0;
  v_descuento_cantidad numeric := 0;
  v_descuento_mailing numeric := 0;
  v_descuento_total numeric;
  v_detalle_nuevo jsonb;
  v_detalle_consolidado jsonb;
  v_productos_nuevos jsonb;
  v_productos_consolidados jsonb;
  v_consolidar boolean;
begin
  p_codigo := nullif(upper(trim(p_codigo)), '');
  p_codigo_promo := nullif(upper(trim(p_codigo_promo)), '');
  if p_modo_precio is null
     or p_modo_precio not in ('minorista', 'mayorista')
     or p_descuento_mayorista_usd is null
     or p_descuento_mayorista_usd < 0
     or (p_modo_precio = 'minorista' and p_descuento_mayorista_usd <> 0)
     or p_fecha_entrega is null
     or jsonb_typeof(p_productos) is distinct from 'array'
     or jsonb_typeof(p_detalle) is distinct from 'array'
     or jsonb_array_length(p_detalle) = 0 then
    return jsonb_build_object('ok', false, 'error', 'pedido_invalido');
  end if;

  if p_codigo is not null then
    select * into v_codigo
    from codigos_descuento
    where cliente_id = p_cliente_id
      and code = p_codigo
      and activo = true
      and usado_en is null
    for update;
    if not found then
      return jsonb_build_object('ok', false, 'error', 'codigo_no_disponible');
    end if;
  end if;

  if p_codigo_promo is not null then
    select * into v_codigo_promo
    from codigos_promo
    where code = p_codigo_promo
      and activo = true
      and usos_actuales < usos_maximos
    for update;
    if not found then
      return jsonb_build_object('ok', false, 'error', 'codigo_promo_no_disponible');
    end if;
  end if;

  for v_item in select value from jsonb_array_elements(p_detalle)
  loop
    begin
      v_cantidad_item := (v_item ->> 'cantidad')::integer;
      v_unitario := (v_item ->> 'usd_unitario')::numeric;
      v_subtotal := (v_item ->> 'usd_subtotal')::numeric;
    exception when others then
      return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
    end;
    if v_cantidad_item <= 0 or v_unitario <= 0
       or v_subtotal is distinct from v_unitario * v_cantidad_item then
      return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
    end if;
    v_cantidad_total := v_cantidad_total + v_cantidad_item;
    v_total_bruto := v_total_bruto + v_subtotal;
    if p_codigo is not null and exists (
      select 1
      from jsonb_array_elements_text(coalesce(v_codigo.productos, '[]'::jsonb)) elegible(nombre)
      where elegible.nombre = v_item ->> 'nombre'
    ) then
      v_descuento_mailing := v_descuento_mailing
        + least(coalesce(nullif(v_codigo.descuento_usd, 0), 5)::numeric, v_unitario)
          * v_cantidad_item;
    end if;
  end loop;

  if p_modo_precio = 'minorista' then
    if v_cantidad_total >= 6 then
      v_descuento_cantidad := 7.5 * v_cantidad_total;
    elsif v_cantidad_total >= 2 then
      v_descuento_cantidad := 5 * v_cantidad_total;
    end if;
  end if;
  v_descuento_total := least(
    v_descuento_cantidad + v_descuento_mailing,
    v_total_bruto
  );
  if (p_codigo is not null and (p_modo_precio <> 'minorista' or v_descuento_mailing <= 0))
     or (p_codigo is null and p_descuento_mailing_usd is distinct from 0)
     or p_descuento_mailing_usd is distinct from v_descuento_mailing
     or p_descuento_usd is distinct from v_descuento_total
     or p_total_usd is distinct from v_total_bruto - v_descuento_total then
    return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
  end if;

  v_productos_nuevos := p_productos;
  v_detalle_nuevo := p_detalle;
  if p_codigo_promo is not null then
    v_productos_nuevos := v_productos_nuevos || jsonb_build_array(
      format('%s (regalo código %s)', v_codigo_promo.producto_regalo, v_codigo_promo.code)
    );
    v_detalle_nuevo := v_detalle_nuevo || jsonb_build_array(jsonb_build_object(
      'nombre', v_codigo_promo.producto_regalo,
      'color', null,
      'cantidad', 1,
      'usd_unitario', 0,
      'usd_subtotal', 0,
      'tipo', 'regalo_promocional',
      'codigo_promo', v_codigo_promo.code
    ));
  end if;

  select * into v_pedido
  from pedidos
  where cliente_id = p_cliente_id
    and fecha_entrega = p_fecha_entrega
    and modo_precio = p_modo_precio
    and direccion_entrega is not distinct from p_direccion_entrega
    and recibo_enviado_en is null
    and detalle is not null
    and total_usd is not null
  order by fecha
  limit 1
  for update;
  v_consolidar := found;

  if v_consolidar then
    select coalesce(jsonb_agg(valor order by primera_pos), '[]'::jsonb)
    into v_productos_consolidados
    from (
      select valor, min(posicion) as primera_pos
      from jsonb_array_elements(
        coalesce(v_pedido.productos, '[]'::jsonb) || v_productos_nuevos
      ) with ordinality elemento(valor, posicion)
      group by valor
    ) unicos;

    select coalesce(jsonb_agg(item_final order by primera_pos), '[]'::jsonb)
    into v_detalle_consolidado
    from (
      select
        ((array_agg(item order by posicion))[1] - 'cantidad' - 'usd_subtotal')
          || jsonb_build_object(
            'cantidad', sum((item ->> 'cantidad')::integer),
            'usd_subtotal', sum((item ->> 'usd_subtotal')::numeric)
          ) as item_final,
        min(posicion) as primera_pos
      from (
        select item, posicion::bigint
        from jsonb_array_elements(coalesce(v_pedido.detalle, '[]'::jsonb))
          with ordinality existente(item, posicion)
        union all
        select item, 1000000 + posicion::bigint
        from jsonb_array_elements(v_detalle_nuevo)
          with ordinality nuevo(item, posicion)
      ) items
      group by item ->> 'nombre', item ->> 'color',
        (item ->> 'usd_unitario')::numeric, item ->> 'tipo', item ->> 'codigo_promo'
    ) agrupados;

    update pedidos
    set productos = v_productos_consolidados,
        detalle = v_detalle_consolidado,
        total_usd = v_pedido.total_usd + p_total_usd,
        descuento_usd = coalesce(v_pedido.descuento_usd, 0) + p_descuento_usd,
        descuento_mayorista_usd = coalesce(v_pedido.descuento_mayorista_usd, 0)
          + p_descuento_mayorista_usd,
        direccion_entrega = p_direccion_entrega
    where id = v_pedido.id
    returning * into v_pedido;
  else
    insert into pedidos (
      cliente_id, productos, detalle, total_usd, descuento_usd,
      modo_precio, descuento_mayorista_usd, fecha_entrega,
      direccion_entrega, origen
    ) values (
      p_cliente_id, v_productos_nuevos, v_detalle_nuevo, p_total_usd, p_descuento_usd,
      p_modo_precio, p_descuento_mayorista_usd, p_fecha_entrega,
      p_direccion_entrega, coalesce(p_origen, 'whatsapp')
    ) returning * into v_pedido;
  end if;

  if p_codigo is not null then
    update codigos_descuento
    set usado_en = now()
    where id = v_codigo.id and usado_en is null;
    if not found then
      raise exception 'El codigo fue consumido concurrentemente';
    end if;
  end if;

  if p_codigo_promo is not null then
    update codigos_promo
    set usos_actuales = usos_actuales + 1
    where id = v_codigo_promo.id
      and activo = true
      and usos_actuales < usos_maximos;
    if not found then
      raise exception 'El regalo fue consumido concurrentemente';
    end if;
  end if;

  return jsonb_build_object('ok', true, 'pedido', to_jsonb(v_pedido));
end;
$$;

revoke all on function public.guardar_pedido_con_descuento_mailing(
  uuid, text, jsonb, jsonb, numeric, numeric, numeric, date, text, text, numeric, text, text
) from public, anon, authenticated;
grant execute on function public.guardar_pedido_con_descuento_mailing(
  uuid, text, jsonb, jsonb, numeric, numeric, numeric, date, text, text, numeric, text, text
) to service_role;

alter table codigos_promo enable row level security;

insert into codigos_promo (code, producto_regalo, usos_maximos)
values ('QUIEROMISPLAY6', 'Auriculares Redmi 6 Play', 20)
on conflict (code) do nothing;

-- Al borrar auth.users se borra su perfil y, por las foreign keys en
-- cascada, pedidos, historial de vistas y códigos de descuento asociados.
create or replace function public.eliminar_cliente_al_borrar_auth()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.clientes where auth_id = old.id;
  return old;
end;
$$;

drop trigger if exists borrar_cliente_al_borrar_auth on auth.users;
create trigger borrar_cliente_al_borrar_auth
before delete on auth.users
for each row execute function public.eliminar_cliente_al_borrar_auth();

-- El backend siempre accede con la service_role key (bypassa RLS). No hay
-- llamadas a Supabase desde el browser, así que dejamos RLS activado sin
-- policies: cualquier acceso con la clave anon/pública queda bloqueado.
alter table clientes enable row level security;
alter table pedidos enable row level security;
alter table tareas_entrega enable row level security;

-- Bucket privado: las fotos comprimidas de números de serie nunca se sirven
-- públicamente y Railway no guarda archivos.
insert into storage.buckets (id, name, public)
values ('recibos-series', 'recibos-series', false)
on conflict (id) do nothing;
alter table interacciones_cliente enable row level security;
alter table codigos_descuento enable row level security;
