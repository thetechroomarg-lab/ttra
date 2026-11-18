-- Cuentas propias del cadete (email + contraseña con hash scrypt). Reemplazan,
-- de a poco, a la contraseña única CADETE_PASSWORD. Se crean con
-- scripts/crear_cadete.py; baja individual con activo = false.
create table if not exists cadetes (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  email text not null unique,
  password_hash text not null,
  rol text not null default 'cadete' check (rol = 'cadete'),
  activo boolean not null default true,
  creado_en timestamptz not null default now()
);
alter table cadetes enable row level security;
