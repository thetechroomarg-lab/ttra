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
  origen text not null default 'whatsapp',
  fecha timestamptz not null default now()
);

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
alter table interacciones_cliente enable row level security;
alter table codigos_descuento enable row level security;
