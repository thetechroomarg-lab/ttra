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
