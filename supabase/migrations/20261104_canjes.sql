-- Plan Canje: solicitudes de clientes que quieren entregar un iPhone usado como
-- parte de pago. Las fotos viven en el bucket privado recibos-series, bajo
-- canjes/<id>/. Al aprobar se emite un código de descuento de una sola vez
-- (codigos_descuento) por el valor de la tabla; el código queda en `codigo`.
create table if not exists canjes (
  id uuid primary key,
  cliente_id uuid not null references clientes(id) on delete cascade,
  equipo_id text not null,
  modelo text not null,
  capacidad text not null,
  valor_usd integer not null,
  fotos jsonb not null default '[]'::jsonb,
  estado text not null default 'pendiente' check (estado in ('pendiente', 'aprobado', 'rechazado')),
  codigo text,
  motivo_rechazo text,
  creado_en timestamptz not null default now(),
  resuelto_en timestamptz
);
create index if not exists canjes_estado_idx on canjes(estado, creado_en desc);
create index if not exists canjes_cliente_idx on canjes(cliente_id);
alter table canjes enable row level security;
revoke all on canjes from anon, authenticated;
