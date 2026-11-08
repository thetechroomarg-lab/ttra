-- Códigos de descuento públicos: sin cliente, los puede aplicar cualquiera y son
-- de un solo uso (el primer pedido que lo reserva lo deja tomado).
alter table codigos_descuento alter column cliente_id drop not null;

create or replace function public.guardar_pedido_con_descuento_mailing(
  p_cliente_id uuid,
  p_codigo text,
  p_productos jsonb,
  p_detalle jsonb,
  p_total_usd numeric,
  p_descuento_usd numeric,
  p_descuento_mailing_usd numeric,
  p_fecha_entrega date,
  p_direccion_entrega text,
  p_modo_precio text,
  p_descuento_mayorista_usd numeric,
  p_origen text default 'whatsapp',
  p_codigo_promo text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_codigo codigos_descuento%rowtype;
  v_codigo_promo codigos_promo%rowtype;
  v_pedido pedidos%rowtype;
  v_item jsonb;
  v_cantidad_item integer;
  v_cantidad_total integer := 0;
  v_unitario numeric;
  v_subtotal numeric;
  v_total_bruto numeric := 0;
  v_descuento_cantidad numeric := 0;
  v_descuento_mailing numeric := 0;
  v_descuento_total numeric;
  v_detalle_nuevo jsonb;
  v_detalle_consolidado jsonb;
  v_productos_nuevos jsonb;
  v_productos_consolidados jsonb;
  v_consolidar boolean;
begin
  p_codigo := nullif(upper(trim(p_codigo)), '');
  p_codigo_promo := nullif(upper(trim(p_codigo_promo)), '');
  if p_modo_precio is null
     or p_modo_precio not in ('minorista', 'mayorista')
     or p_descuento_mayorista_usd is null
     or p_descuento_mayorista_usd < 0
     or (p_modo_precio = 'minorista' and p_descuento_mayorista_usd <> 0)
     or p_fecha_entrega is null
     or jsonb_typeof(p_productos) is distinct from 'array'
     or jsonb_typeof(p_detalle) is distinct from 'array'
     or jsonb_array_length(p_detalle) = 0 then
    return jsonb_build_object('ok', false, 'error', 'pedido_invalido');
  end if;

  if p_codigo is not null then
    select * into v_codigo
    from codigos_descuento
    where (cliente_id = p_cliente_id or cliente_id is null)
      and code = p_codigo
      and activo = true
      and usado_en is null
      and (
        reservado_pedido_id is null
        or not exists (
          select 1 from pedidos reservado
          where reservado.id = codigos_descuento.reservado_pedido_id
            and reservado.borrado_en is null
        )
      )
    for update;
    if not found then
      return jsonb_build_object('ok', false, 'error', 'codigo_no_disponible');
    end if;
  end if;

  if p_codigo_promo is not null then
    select * into v_codigo_promo
    from codigos_promo
    where code = p_codigo_promo
      and activo = true
      and usos_actuales < usos_maximos
    for update;
    if not found then
      return jsonb_build_object('ok', false, 'error', 'codigo_promo_no_disponible');
    end if;
  end if;

  for v_item in select value from jsonb_array_elements(p_detalle)
  loop
    begin
      v_cantidad_item := (v_item ->> 'cantidad')::integer;
      v_unitario := (v_item ->> 'usd_unitario')::numeric;
      v_subtotal := (v_item ->> 'usd_subtotal')::numeric;
    exception when others then
      return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
    end;
    if v_cantidad_item <= 0 or v_unitario <= 0
       or v_subtotal is distinct from v_unitario * v_cantidad_item then
      return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
    end if;
    v_cantidad_total := v_cantidad_total + v_cantidad_item;
    v_total_bruto := v_total_bruto + v_subtotal;
    if p_codigo is not null and (v_codigo.tope_total_usd is not null or exists (
      select 1
      from jsonb_array_elements_text(coalesce(v_codigo.productos, '[]'::jsonb)) elegible(nombre)
      where elegible.nombre = v_item ->> 'nombre'
    )) then
      v_descuento_mailing := v_descuento_mailing
        + least(coalesce(nullif(v_codigo.descuento_usd, 0), 5)::numeric, v_unitario)
          * v_cantidad_item;
    end if;
  end loop;
  -- Código con tope (premio de fidelidad): vale para cualquier producto y
  -- descuenta como máximo el tope en total, no por unidad.
  if p_codigo is not null and v_codigo.tope_total_usd is not null then
    v_descuento_mailing := least(v_descuento_mailing, v_codigo.tope_total_usd);
  end if;

  if p_modo_precio = 'minorista' then
    if v_cantidad_total >= 6 then
      v_descuento_cantidad := 7.5 * v_cantidad_total;
    elsif v_cantidad_total >= 2 then
      v_descuento_cantidad := 5 * v_cantidad_total;
    end if;
  end if;
  v_descuento_total := least(
    v_descuento_cantidad + v_descuento_mailing,
    v_total_bruto
  );
  if (p_codigo is not null and (p_modo_precio <> 'minorista' or v_descuento_mailing <= 0))
     or (p_codigo is null and p_descuento_mailing_usd is distinct from 0)
     or p_descuento_mailing_usd is distinct from v_descuento_mailing
     or p_descuento_usd is distinct from v_descuento_total
     or p_total_usd is distinct from v_total_bruto - v_descuento_total then
    return jsonb_build_object('ok', false, 'error', 'montos_invalidos');
  end if;

  v_productos_nuevos := p_productos;
  v_detalle_nuevo := p_detalle;
  if p_codigo_promo is not null then
    v_productos_nuevos := v_productos_nuevos || jsonb_build_array(
      format('%s (regalo código %s)', v_codigo_promo.producto_regalo, v_codigo_promo.code)
    );
    v_detalle_nuevo := v_detalle_nuevo || jsonb_build_array(jsonb_build_object(
      'nombre', v_codigo_promo.producto_regalo,
      'color', null,
      'cantidad', 1,
      'usd_unitario', 0,
      'usd_subtotal', 0,
      'tipo', 'regalo_promocional',
      'codigo_promo', v_codigo_promo.code
    ));
  end if;

  select * into v_pedido
  from pedidos
  where cliente_id = p_cliente_id
    and fecha_entrega = p_fecha_entrega
    and modo_precio = p_modo_precio
    and direccion_entrega is not distinct from p_direccion_entrega
    and recibo_enviado_en is null
    and detalle is not null
    and total_usd is not null
  order by fecha
  limit 1
  for update;
  v_consolidar := found;

  if v_consolidar then
    select coalesce(jsonb_agg(valor order by primera_pos), '[]'::jsonb)
    into v_productos_consolidados
    from (
      select valor, min(posicion) as primera_pos
      from jsonb_array_elements(
        coalesce(v_pedido.productos, '[]'::jsonb) || v_productos_nuevos
      ) with ordinality elemento(valor, posicion)
      group by valor
    ) unicos;

    select coalesce(jsonb_agg(item_final order by primera_pos), '[]'::jsonb)
    into v_detalle_consolidado
    from (
      select
        ((array_agg(item order by posicion))[1] - 'cantidad' - 'usd_subtotal')
          || jsonb_build_object(
            'cantidad', sum((item ->> 'cantidad')::integer),
            'usd_subtotal', sum((item ->> 'usd_subtotal')::numeric)
          ) as item_final,
        min(posicion) as primera_pos
      from (
        select item, posicion::bigint
        from jsonb_array_elements(coalesce(v_pedido.detalle, '[]'::jsonb))
          with ordinality existente(item, posicion)
        union all
        select item, 1000000 + posicion::bigint
        from jsonb_array_elements(v_detalle_nuevo)
          with ordinality nuevo(item, posicion)
      ) items
      group by item ->> 'nombre', item ->> 'color',
        (item ->> 'usd_unitario')::numeric, item ->> 'tipo', item ->> 'codigo_promo'
    ) agrupados;

    update pedidos
    set productos = v_productos_consolidados,
        detalle = v_detalle_consolidado,
        total_usd = v_pedido.total_usd + p_total_usd,
        descuento_usd = coalesce(v_pedido.descuento_usd, 0) + p_descuento_usd,
        descuento_mayorista_usd = coalesce(v_pedido.descuento_mayorista_usd, 0)
          + p_descuento_mayorista_usd,
        direccion_entrega = p_direccion_entrega
    where id = v_pedido.id
    returning * into v_pedido;
  else
    insert into pedidos (
      cliente_id, productos, detalle, total_usd, descuento_usd,
      modo_precio, descuento_mayorista_usd, fecha_entrega,
      direccion_entrega, origen
    ) values (
      p_cliente_id, v_productos_nuevos, v_detalle_nuevo, p_total_usd, p_descuento_usd,
      p_modo_precio, p_descuento_mayorista_usd, p_fecha_entrega,
      p_direccion_entrega, coalesce(p_origen, 'whatsapp')
    ) returning * into v_pedido;
  end if;

  if p_codigo is not null then
    -- Se reserva para este pedido; se consume al enviar el recibo.
    update codigos_descuento
    set reservado_pedido_id = v_pedido.id,
        reservado_en = now()
    where id = v_codigo.id and usado_en is null;
    if not found then
      raise exception 'El codigo fue consumido concurrentemente';
    end if;
  end if;

  if p_codigo_promo is not null then
    update codigos_promo
    set usos_actuales = usos_actuales + 1
    where id = v_codigo_promo.id
      and activo = true
      and usos_actuales < usos_maximos;
    if not found then
      raise exception 'El regalo fue consumido concurrentemente';
    end if;
  end if;

  return jsonb_build_object('ok', true, 'pedido', to_jsonb(v_pedido));
end;
$$;

revoke all on function public.guardar_pedido_con_descuento_mailing(
  uuid, text, jsonb, jsonb, numeric, numeric, numeric, date, text, text, numeric, text, text
) from public, anon, authenticated;
grant execute on function public.guardar_pedido_con_descuento_mailing(
  uuid, text, jsonb, jsonb, numeric, numeric, numeric, date, text, text, numeric, text, text
) to service_role;
