-- Libro privado: nunca accesible desde anon/authenticated.
create table if not exists ganancia_movimientos (
 id uuid primary key default gen_random_uuid(),
 fuente_tipo text not null, fuente_id text not null,
 fecha_operacion date not null, tipo text not null check (tipo in ('venta','ingreso','gasto')),
 concepto text not null check (length(concepto) between 1 and 300),
 ingreso_usd numeric(20,2), costo_usd numeric(20,2), comision_usd numeric(20,2), gasto_usd numeric(20,2),
 estado_evidencia text not null check (estado_evidencia in ('confirmado','estimado','pendiente')),
 evidencia jsonb not null default '{}', version_calculo int not null default 1,
 version int not null default 1, anulado_en timestamptz, creado_en timestamptz not null default now(),
 unique(fuente_tipo,fuente_id)
);
create index if not exists ganancia_fecha_idx on ganancia_movimientos(fecha_operacion);
create table if not exists ganancia_costos (
 id uuid primary key, costos jsonb not null, conflictos jsonb not null default '{}',
 fuente text not null, creado_en timestamptz not null default now()
);
create table if not exists ganancia_revisiones (
 id uuid primary key default gen_random_uuid(), movimiento_id uuid not null references ganancia_movimientos(id),
 anterior jsonb not null, nuevo jsonb not null, creado_en timestamptz not null default now()
);
alter table ganancia_movimientos enable row level security;
alter table ganancia_costos enable row level security;
alter table ganancia_revisiones enable row level security;
revoke all on ganancia_movimientos,ganancia_costos,ganancia_revisiones from anon,authenticated;
grant all on ganancia_movimientos,ganancia_costos,ganancia_revisiones to service_role;
alter table pagos_cadete add column if not exists cotizacion_ars_usd numeric;
create or replace function editar_ganancia_manual(p_id uuid,p_version int,p_cambios jsonb)
returns setof ganancia_movimientos language plpgsql security invoker set search_path=public as $$
declare anterior ganancia_movimientos; nuevo ganancia_movimientos;
begin
 select * into anterior from ganancia_movimientos where id=p_id and fuente_tipo='manual' and version=p_version and anulado_en is null for update;
 if not found then return; end if;
 update ganancia_movimientos set
  concepto=coalesce(p_cambios->>'concepto',concepto),
  fecha_operacion=coalesce((p_cambios->>'fecha_operacion')::date,fecha_operacion),
  ingreso_usd=coalesce((p_cambios->>'ingreso_usd')::numeric,ingreso_usd),
  gasto_usd=coalesce((p_cambios->>'gasto_usd')::numeric,gasto_usd),
  anulado_en=case when p_cambios->>'anular'='true' then now() else null end,
  version=version+1 where id=p_id returning * into nuevo;
 insert into ganancia_revisiones(movimiento_id,anterior,nuevo) values(p_id,to_jsonb(anterior),to_jsonb(nuevo));
 return next nuevo;
end $$;
revoke all on function editar_ganancia_manual(uuid,int,jsonb) from public,anon,authenticated;
grant execute on function editar_ganancia_manual(uuid,int,jsonb) to service_role;

-- Los valores anteriores (incluidos costos ausentes) prevalecen al agregar productos.
create or replace function capturar_ganancia_costos(p_id uuid,p_costos jsonb,p_fuente text)
returns setof ganancia_costos language sql security invoker set search_path=public as $$
 insert into ganancia_costos(id,costos,fuente) values(p_id,p_costos,p_fuente)
 on conflict(id) do update set costos=excluded.costos || ganancia_costos.costos,
 conflictos=ganancia_costos.conflictos || coalesce((
 select jsonb_object_agg(n.key,jsonb_build_object('anterior',ganancia_costos.costos->n.key,'nuevo',n.value))
 from jsonb_each(excluded.costos) n where ganancia_costos.costos ? n.key
 and ganancia_costos.costos->n.key is distinct from n.value
 ),'{}'::jsonb)
 returning *;
$$;
revoke all on function capturar_ganancia_costos(uuid,jsonb,text) from public,anon,authenticated;
grant execute on function capturar_ganancia_costos(uuid,jsonb,text) to service_role;

create or replace function completar_ganancia(p_id uuid,p_version int,p_cambios jsonb)
returns setof ganancia_movimientos language plpgsql security invoker set search_path=public as $$
declare anterior ganancia_movimientos; nuevo ganancia_movimientos;
begin
 select * into anterior from ganancia_movimientos where id=p_id and fuente_tipo!='manual'
 and version=p_version and anulado_en is null for update;
 if not found then return; end if;
 update ganancia_movimientos set
 ingreso_usd=(p_cambios->>'ingreso_usd')::numeric, costo_usd=(p_cambios->>'costo_usd')::numeric,
 comision_usd=(p_cambios->>'comision_usd')::numeric, gasto_usd=(p_cambios->>'gasto_usd')::numeric,
 estado_evidencia=p_cambios->>'estado_evidencia',
 evidencia=evidencia || jsonb_build_object('faltantes','[]'::jsonb,'correccion_admin',p_cambios->>'motivo'),
 version=version+1 where id=p_id returning * into nuevo;
 insert into ganancia_revisiones(movimiento_id,anterior,nuevo) values(p_id,to_jsonb(anterior),to_jsonb(nuevo));
 return next nuevo;
end $$;
revoke all on function completar_ganancia(uuid,int,jsonb) from public,anon,authenticated;
grant execute on function completar_ganancia(uuid,int,jsonb) to service_role;
