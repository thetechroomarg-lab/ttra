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
-- producto de regalo a $0 al carrito, hasta agotar usos_maximos usos totales.
create table if not exists codigos_promo (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  producto_regalo text not null,
  usos_maximos integer not null default 20,
  usos_actuales integer not null default 0,
  activo boolean not null default true,
  creado_en timestamptz not null default now()
);
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
