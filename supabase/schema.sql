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
  nota text,
  direccion text,
  orden integer not null default 0,
  creada_en timestamptz not null default now()
);
create index if not exists tareas_entrega_fecha_orden_idx
  on tareas_entrega (fecha_entrega, orden);

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
alter table interacciones_cliente enable row level security;
alter table codigos_descuento enable row level security;
