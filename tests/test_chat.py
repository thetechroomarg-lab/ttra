# tests/test_chat.py
from web.reglas import construir_system
from web.chat import responder, _extraer_texto


class _Bloque:
    def __init__(self, tipo, text=None):
        self.type = tipo
        if text is not None:
            self.text = text


class _RespThinking:
    # simula Sonnet 5: primero un bloque de "thinking", luego el texto
    content = [_Bloque("thinking"), _Bloque("text", "hola precios")]


def test_extraer_texto_ignora_bloque_thinking():
    assert _extraer_texto(_RespThinking()) == "hola precios"


class _FakeContent:
    def __init__(self, text): self.text = text


class _FakeResp:
    def __init__(self, text): self.content = [_FakeContent(text)]


class _FakeMessages:
    def __init__(self, parent): self.parent = parent
    def create(self, **kwargs):
        self.parent.ultimo_kwargs = kwargs
        return _FakeResp("iPhone 13 128GB\n🇺🇸 U$D 660 · 🇦🇷 $ 1.016.400 · 🏦 $ 1.047.835")


class FakeClient:
    def __init__(self): self.messages = _FakeMessages(self)


def test_system_incluye_reglas_y_catalogo_sin_proveedor():
    productos = [{"nombre": "iPhone 13 128GB", "categoria": "Apple - iPhone",
                  "usd": 660, "pesos": 1016400, "transferencia": 1047835,
                  "link_imagen": "x"}]
    system = construir_system(productos)
    assert "WhatsApp" in system
    assert "proveedor" in system.lower()          # la regla de NO mostrar proveedor
    assert "iPhone 13 128GB" in system            # el catálogo está embebido
    assert "wa.me/543512145217" in system


def test_responder_llama_al_cliente_y_devuelve_texto():
    productos = [{"nombre": "iPhone 13 128GB", "categoria": "Apple - iPhone",
                  "usd": 660, "pesos": 1016400, "transferencia": 1047835,
                  "link_imagen": "x"}]
    client = FakeClient()
    out = responder("tenes iphone 13?", [], productos, client)
    assert "U$D 660" in out
    # se le pasó el mensaje del usuario al modelo
    msgs = client.ultimo_kwargs["messages"]
    assert msgs[-1] == {"role": "user", "content": "tenes iphone 13?"}
    # el system prompt viaja aparte
    assert "system" in client.ultimo_kwargs
