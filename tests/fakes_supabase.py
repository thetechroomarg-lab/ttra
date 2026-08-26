"""Doble de prueba mínimo del cliente de supabase-py: solo implementa lo que
usa web/cuentas.py (auth.sign_up, auth.sign_in_with_password,
auth.admin.delete_user, table().select/insert/update().eq().execute())."""
import copy
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal


class _FakeAuthUser:
    def __init__(self, id_, email):
        self.id = id_
        self.email = email
        self.email_confirmed_at = None


class _FakeAuthResponse:
    def __init__(self, user, session=None):
        self.user = user
        self.session = session


class _FakeAdminAuth:
    def __init__(self, usuarios_por_email, passwords):
        self._usuarios_por_email = usuarios_por_email
        self._passwords = passwords

    def delete_user(self, user_id):
        for email, user in list(self._usuarios_por_email.items()):
            if user.id == user_id:
                del self._usuarios_por_email[email]
                if hasattr(self, "_on_delete_user"):
                    self._on_delete_user(user_id)
                return
        raise Exception("User not found")

    def create_user(self, credenciales):
        email = credenciales["email"].strip().lower()
        if email in self._usuarios_por_email:
            raise Exception("User already registered")
        user = _FakeAuthUser(id_=str(uuid.uuid4()), email=email)
        self._usuarios_por_email[email] = user
        self._passwords[email] = credenciales.get("password")
        return _FakeAuthResponse(user)

    def update_user_by_id(self, user_id, atributos):
        for email, user in self._usuarios_por_email.items():
            if user.id == user_id:
                if "password" in atributos:
                    self._passwords[email] = atributos["password"]
                return _FakeAuthResponse(user)
        raise Exception("User not found")


class FakeAuth:
    def __init__(self):
        self._usuarios_por_email = {}
        self._passwords = {}
        self.admin = _FakeAdminAuth(self._usuarios_por_email, self._passwords)
        self.emails_con_reset_pedido = []
        self.last_sign_up_payload = None
        self.next_sign_up_session = object()

    def reset_password_for_email(self, email):
        self.emails_con_reset_pedido.append(email.strip().lower())

    def sign_up(self, credenciales):
        self.last_sign_up_payload = credenciales
        email = credenciales["email"].strip().lower()
        if email in self._usuarios_por_email:
            raise Exception("User already registered")
        user = _FakeAuthUser(id_=str(uuid.uuid4()), email=email)
        self._usuarios_por_email[email] = user
        self._passwords[email] = credenciales["password"]
        return _FakeAuthResponse(user, session=self.next_sign_up_session)

    def sign_in_with_password(self, credenciales):
        email = credenciales["email"].strip().lower()
        user = self._usuarios_por_email.get(email)
        if not user or self._passwords.get(email) != credenciales["password"]:
            raise Exception("Invalid login credentials")
        return _FakeAuthResponse(user)


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeRpcResult:
    def __init__(self, data):
        self.data = data

    def execute(self):
        return self


class _FakeRpcCall:
    def __init__(self, callback):
        self._callback = callback

    def execute(self):
        return _FakeRpcResult(self._callback())


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
        if self._operacion == "delete":
            objetivo = self._filtrar(self._tabla._filas)
            self._tabla._filas[:] = [fila for fila in self._tabla._filas if fila not in objetivo]
            return _FakeExecuteResult(objetivo)
        raise ValueError(self._operacion)


class _FakeTable:
    def __init__(self, nombre):
        self._nombre = nombre
        self._filas = []

    def select(self, *_args, **_kwargs):
        return _FakeQuery(self, "select")

    def insert(self, payload):
        if self._nombre == "pedidos":
            payload = {
                "modo_precio": "minorista",
                "descuento_mayorista_usd": 0,
                **payload,
            }
        return _FakeQuery(self, "insert", payload)

    def update(self, payload):
        return _FakeQuery(self, "update", payload)

    def delete(self):
        return _FakeQuery(self, "delete")


class FakeSupabaseClient:
    def __init__(self):
        self.auth = FakeAuth()
        self._tablas = {}
        self.rpc_calls = []
        self.atomic_order_failure_stage = None
        self.auth.admin._on_delete_user = self._eliminar_perfil_por_auth_id

    def table(self, nombre):
        return self._tablas.setdefault(nombre, _FakeTable(nombre))

    def rpc(self, nombre, parametros=None):
        self.rpc_calls.append((nombre, parametros))
        if nombre == "siguiente_numero_recibo":
            self._ultimo_recibo = getattr(self, "_ultimo_recibo", 1992) + 1
            return _FakeRpcResult(f"0001-{self._ultimo_recibo}")
        if nombre == "guardar_pedido_con_descuento_mailing":
            return _FakeRpcCall(
                lambda: self._guardar_pedido_con_descuento_mailing(parametros or {})
            )
        raise ValueError(nombre)

    def _guardar_pedido_con_descuento_mailing(self, parametros):
        """Simula el RPC transaccional, incluyendo rollback ante excepciones."""
        from web import pedidos

        instantanea = {
            nombre: copy.deepcopy(tabla._filas)
            for nombre, tabla in self._tablas.items()
        }
        tablas_anteriores = set(self._tablas)
        try:
            if self.atomic_order_failure_stage == "before_order":
                raise RuntimeError("Fallo simulado antes de guardar")

            codigo = next(
                (
                    fila
                    for fila in self.table("codigos_descuento")._filas
                    if fila.get("cliente_id") == parametros.get("p_cliente_id")
                    and fila.get("code") == parametros.get("p_codigo")
                    and fila.get("activo")
                    and not fila.get("usado_en")
                ),
                None,
            )
            if not codigo:
                return {"ok": False, "error": "codigo_no_disponible"}

            elegibles = set(codigo.get("productos") or [])
            descuento_unitario = pedidos.decimal_monetario(
                codigo.get("descuento_usd") or 5
            )
            descuento_mailing = Decimal("0")
            bruto = Decimal("0")
            cantidad = 0
            for item in parametros.get("p_detalle") or []:
                unitario = pedidos.decimal_monetario(item.get("usd_unitario"))
                subtotal = pedidos.decimal_monetario(item.get("usd_subtotal"))
                unidades = int(item.get("cantidad") or 0)
                if unidades <= 0 or subtotal != unitario * unidades:
                    return {"ok": False, "error": "montos_invalidos"}
                bruto += subtotal
                cantidad += unidades
                if item.get("nombre") in elegibles and unitario > 0:
                    descuento_mailing += min(descuento_unitario, unitario) * unidades

            descuento_cantidad = Decimal("0")
            if cantidad >= 6:
                descuento_cantidad = Decimal("7.5") * cantidad
            elif cantidad >= 2:
                descuento_cantidad = Decimal("5") * cantidad
            descuento_total = min(descuento_cantidad + descuento_mailing, bruto)
            if (
                descuento_mailing <= 0
                or pedidos.decimal_monetario(
                    parametros.get("p_descuento_mailing_usd")
                ) != descuento_mailing
                or pedidos.decimal_monetario(parametros.get("p_descuento_usd"))
                != descuento_total
                or pedidos.decimal_monetario(parametros.get("p_total_usd"))
                != bruto - descuento_total
                or parametros.get("p_modo_precio") != "minorista"
                or pedidos.decimal_monetario(
                    parametros.get("p_descuento_mayorista_usd")
                ) != 0
            ):
                return {"ok": False, "error": "montos_invalidos"}

            fecha_entrega = date.fromisoformat(parametros["p_fecha_entrega"])
            pedido = pedidos.guardar_pedido(
                self,
                parametros["p_cliente_id"],
                parametros["p_productos"],
                fecha_entrega,
                direccion_entrega=parametros.get("p_direccion_entrega"),
                detalle=parametros["p_detalle"],
                total_usd=parametros["p_total_usd"],
                descuento_usd=parametros["p_descuento_usd"],
                modo_precio=parametros["p_modo_precio"],
                descuento_mayorista_usd=parametros[
                    "p_descuento_mayorista_usd"
                ],
                origen=parametros.get("p_origen") or "whatsapp",
            )
            if self.atomic_order_failure_stage == "after_order":
                raise RuntimeError("Fallo simulado al consumir")

            if codigo.get("usado_en"):
                raise RuntimeError("El codigo fue consumido concurrentemente")
            codigo["usado_en"] = datetime.now(timezone.utc).isoformat()
            if self.atomic_order_failure_stage == "after_consume":
                raise RuntimeError("Fallo simulado despues de consumir")
            return {"ok": True, "pedido": pedido}
        except Exception:
            for nombre in list(self._tablas):
                if nombre not in tablas_anteriores:
                    del self._tablas[nombre]
            for nombre, filas in instantanea.items():
                self._tablas[nombre]._filas[:] = filas
            raise

    def _eliminar_perfil_por_auth_id(self, auth_id):
        """Simula el trigger que borra el perfil y sus registros en cascada."""
        clientes = self.table("clientes")._filas
        cliente_ids = {fila["id"] for fila in clientes if fila.get("auth_id") == auth_id}
        self.table("clientes")._filas[:] = [fila for fila in clientes if fila.get("id") not in cliente_ids]
        for nombre in ("pedidos", "interacciones_cliente", "codigos_descuento", "domicilios_cliente"):
            tabla = self.table(nombre)
            tabla._filas[:] = [fila for fila in tabla._filas if fila.get("cliente_id") not in cliente_ids]
