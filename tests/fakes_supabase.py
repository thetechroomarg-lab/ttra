"""Doble de prueba mínimo del cliente de supabase-py: solo implementa lo que
usa web/cuentas.py (auth.sign_up, auth.sign_in_with_password,
auth.admin.delete_user, table().select/insert/update().eq().execute())."""
import uuid


class _FakeAuthUser:
    def __init__(self, id_, email):
        self.id = id_
        self.email = email


class _FakeAuthResponse:
    def __init__(self, user):
        self.user = user


class _FakeAdminAuth:
    def __init__(self, usuarios_por_email):
        self._usuarios_por_email = usuarios_por_email

    def delete_user(self, user_id):
        for email, user in list(self._usuarios_por_email.items()):
            if user.id == user_id:
                del self._usuarios_por_email[email]


class FakeAuth:
    def __init__(self):
        self._usuarios_por_email = {}
        self._passwords = {}
        self.admin = _FakeAdminAuth(self._usuarios_por_email)

    def sign_up(self, credenciales):
        email = credenciales["email"].strip().lower()
        if email in self._usuarios_por_email:
            raise Exception("User already registered")
        user = _FakeAuthUser(id_=str(uuid.uuid4()), email=email)
        self._usuarios_por_email[email] = user
        self._passwords[email] = credenciales["password"]
        return _FakeAuthResponse(user)

    def sign_in_with_password(self, credenciales):
        email = credenciales["email"].strip().lower()
        user = self._usuarios_por_email.get(email)
        if not user or self._passwords.get(email) != credenciales["password"]:
            raise Exception("Invalid login credentials")
        return _FakeAuthResponse(user)


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, tabla, operacion, payload=None):
        self._tabla = tabla
        self._operacion = operacion
        self._payload = payload
        self._filtros = []

    def eq(self, campo, valor):
        self._filtros.append((campo, valor))
        return self

    def _filtrar(self, filas):
        for campo, valor in self._filtros:
            filas = [f for f in filas if f.get(campo) == valor]
        return filas

    def execute(self):
        if self._operacion == "select":
            return _FakeExecuteResult(self._filtrar(list(self._tabla._filas)))
        if self._operacion == "insert":
            fila = dict(self._payload)
            self._tabla._filas.append(fila)
            return _FakeExecuteResult([fila])
        if self._operacion == "update":
            objetivo = self._filtrar(self._tabla._filas)
            for fila in objetivo:
                fila.update(self._payload)
            return _FakeExecuteResult(objetivo)
        raise ValueError(self._operacion)


class _FakeTable:
    def __init__(self):
        self._filas = []

    def select(self, *_args, **_kwargs):
        return _FakeQuery(self, "select")

    def insert(self, payload):
        return _FakeQuery(self, "insert", payload)

    def update(self, payload):
        return _FakeQuery(self, "update", payload)


class FakeSupabaseClient:
    def __init__(self):
        self.auth = FakeAuth()
        self._tablas = {}

    def table(self, nombre):
        return self._tablas.setdefault(nombre, _FakeTable())
