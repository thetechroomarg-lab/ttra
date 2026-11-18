-- Varios cadetes: cada cuenta tiene un slug (el valor que se guarda en
-- asignado_a), entra "pendiente" y Vlad la aprueba desde su panel. La cuenta
-- que ya existe (la de Alejo) queda aprobada con slug 'alejo'.
alter table cadetes add column if not exists slug text unique;
alter table cadetes add column if not exists aprobado boolean not null default false;
update cadetes set aprobado = true, slug = 'alejo' where slug is null;

-- Saldo, pagos y avisos push por cadete. Las filas viejas (cadete null) son de Alejo.
alter table movimientos_cadete add column if not exists cadete text;
alter table pagos_cadete add column if not exists cadete text;
alter table cadete_push_suscripciones add column if not exists cadete text;
