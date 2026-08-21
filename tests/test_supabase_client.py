import pytest

from web import supabase_client


def test_get_client_sin_variables_de_entorno_da_error_claro(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        supabase_client.get_client()


def test_get_client_con_variables_crea_cliente(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "clave-de-prueba")
    cliente = supabase_client.get_client()
    assert cliente is not None
