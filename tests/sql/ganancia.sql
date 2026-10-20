-- Ejecutar sólo en una base temporal vacía.
\set ON_ERROR_STOP on
create role anon;
create role authenticated;
create role service_role;
create table pagos_cadete(id uuid primary key);
\ir ../../supabase/migrations/20261020_ganancia.sql
select * from capturar_ganancia_costos('00000000-0000-0000-0000-000000000001','{"Equipo":"400"}','primera');
select * from capturar_ganancia_costos('00000000-0000-0000-0000-000000000001','{"Equipo":"450","Funda":"5"}','segunda');
insert into ganancia_movimientos(id,fuente_tipo,fuente_id,fecha_operacion,tipo,concepto,ingreso_usd,costo_usd,comision_usd,gasto_usd,estado_evidencia)
values('00000000-0000-0000-0000-000000000002','manual','uno','2026-10-20','ingreso','Servicio',35,0,0,0,'confirmado'),
('00000000-0000-0000-0000-000000000003','venta','dos','2026-10-20','venta','Recibo',500,null,null,0,'pendiente');
select * from editar_ganancia_manual('00000000-0000-0000-0000-000000000002',1,'{"ingreso_usd":"50"}');
select * from completar_ganancia('00000000-0000-0000-0000-000000000003',1,'{"ingreso_usd":"500","costo_usd":"400","comision_usd":"5","gasto_usd":"0","estado_evidencia":"estimado","motivo":"Lista aproximada"}');
do $$ begin
 if (select count(*) from ganancia_revisiones)!=2 then raise exception 'Auditoría incorrecta'; end if;
 if exists(select * from editar_ganancia_manual('00000000-0000-0000-0000-000000000002',1,'{"ingreso_usd":"60"}')) then raise exception 'Permite versión vieja'; end if;
 if (select costos->>'Equipo' from ganancia_costos limit 1)!='400' then raise exception 'Costo original perdido'; end if;
 if not (select conflictos ? 'Equipo' from ganancia_costos limit 1) then raise exception 'Conflicto no registrado'; end if;
 if has_table_privilege('anon','ganancia_movimientos','select') or has_function_privilege('authenticated','completar_ganancia(uuid,integer,jsonb)','execute') then raise exception 'Exposición pública'; end if;
end $$;
