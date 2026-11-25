-- Listado WhatsApp (mayoristas): cuánto quiere ganar la cuenta en cada franja de
-- precio. Clave = número de rango de US$ 300 (0 = 0 a 300, 1 = 301 a 600...),
-- valor = dólares de ganancia. Vacío = sin ganancia elegida.
alter table clientes add column if not exists listado_ganancias jsonb not null default '{}'::jsonb;
