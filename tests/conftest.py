import pytest


@pytest.fixture(autouse=True)
def isolated_login_attempt_store(tmp_path, monkeypatch):
    import web.app as appmod
    from web.login_rate_limit import LoginAttemptStore
    monkeypatch.setattr(appmod, '_intentos_login_fallidos', LoginAttemptStore(tmp_path / 'login.sqlite3'))
