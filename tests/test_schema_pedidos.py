from pathlib import Path


SCHEMA = Path(__file__).parents[1] / "supabase" / "schema.sql"


def test_schema_define_rpc_atomica_para_pedido_con_codigo_mailing():
    sql = SCHEMA.read_text(encoding="utf-8")
    inicio = sql.index(
        "create or replace function public.guardar_pedido_con_descuento_mailing"
    )
    fin = sql.index("$$;", inicio)
    funcion = sql[inicio:fin]

    assert "usado_en is null" in funcion
    assert "for update" in funcion
    assert "insert into pedidos" in funcion
    assert "update pedidos" in funcion
    assert "update codigos_descuento" in funcion
    assert "p_descuento_mailing_usd" in funcion
    assert "grant execute" in sql[fin:]


def test_schema_rpc_atomica_regalo_y_mailing_con_grant_solo_service_role():
    """Catches non-transactional gift use or an RPC callable by browser roles."""
    sql = SCHEMA.read_text(encoding="utf-8")
    tabla_promo = sql.index("create table if not exists codigos_promo")
    inicio = sql.index(
        "create or replace function public.guardar_pedido_con_descuento_mailing"
    )
    fin = sql.index("$$;", inicio)
    funcion = sql[inicio:fin]
    privilegios = sql[fin:sql.index("-- Al borrar auth.users", fin)]

    assert tabla_promo < inicio
    assert "p_codigo_promo text" in funcion
    assert "from codigos_promo" in funcion
    assert "for update" in funcion
    assert "'tipo', 'regalo_promocional'" in funcion
    assert "'codigo_promo', v_codigo_promo.code" in funcion
    assert "usos_actuales = usos_actuales + 1" in funcion
    assert "usos_actuales < usos_maximos" in funcion
    assert "revoke all on function" in privilegios
    assert "from public, anon, authenticated" in privilegios
    assert "to service_role" in privilegios


def test_schema_rpc_migracion_es_idempotente_y_retira_firma_anterior():
    sql = SCHEMA.read_text(encoding="utf-8")

    assert "drop function if exists public.guardar_pedido_con_descuento_mailing" in sql
    assert "create or replace function public.guardar_pedido_con_descuento_mailing" in sql
