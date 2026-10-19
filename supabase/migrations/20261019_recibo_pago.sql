-- Aplicar antes de desplegar la selección de pagos de entregas.
-- NULL conserva el significado de los recibos históricos (medio no registrado).
alter table public.pedidos add column if not exists recibo_pago jsonb;
comment on column public.pedidos.recibo_pago is 'Snapshot del cobro: métodos, importes recibidos, factores y cotización al emitir. No recalcular en reenvíos.';
