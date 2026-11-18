import pytest


@pytest.fixture(autouse=True)
def isolated_login_attempt_store(tmp_path, monkeypatch):
    import web.app as appmod
    from web.login_rate_limit import LoginAttemptStore
    monkeypatch.setattr(appmod, '_intentos_login_fallidos', LoginAttemptStore(tmp_path / 'login.sqlite3'))


@pytest.fixture(autouse=True)
def cadete_sin_cuenta_obligatoria(monkeypatch):
    """Los tests viejos del panel entran con la contraseña única; los de
    tests/test_cadetes_cuentas.py prenden la exigencia de cuenta a propósito."""
    import web.app as appmod
    monkeypatch.setattr(appmod, '_CADETE_EXIGIR_CUENTA', False)
