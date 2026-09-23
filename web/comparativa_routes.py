"""Route installation keeps the existing app's authorization as the source of truth."""
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from web.comparativa import FIELDS, public_product, resolve_pair, spec_key
from web.comparativa_specs import SpecStore, research
from web.login_rate_limit import LoginAttemptStore
from web.comparativa_gemini import research_gemini


class SheetRequest(BaseModel):
    a: str = Field(pattern=r'^[a-f0-9]{64}$')
    b: str = Field(pattern=r'^[a-f0-9]{64}$')
    product: str = Field(pattern=r'^[a-f0-9]{64}$')


def install(app, catalog_loader, data_path, client_factory):
    directory = Path(data_path).parent / '.security'
    store = SpecStore(directory / 'comparison-specs.sqlite3')
    budget = LoginAttemptStore(directory / 'comparison-limits.sqlite3')
    # Exposed only to application tests/configuration, never sent to browsers.
    app.state.comparison_store = store
    app.state.comparison_budget = budget
    app.state.comparison_global_budget = LoginAttemptStore(directory / 'comparison-global-limits.sqlite3')

    def pair(request, a, b):
        products, _ = catalog_loader(request)
        try:
            return resolve_pair(products, a, b)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get('/comparativa')
    def comparison_page():
        return FileResponse(Path(__file__).parent / 'static' / 'comparativa.html')

    @app.get('/api/comparativa')
    def comparison_data(request: Request, a: str, b: str):
        products = pair(request, a, b)
        return {'products': [{**public_product(p), 'sheet': app.state.comparison_store.get(spec_key(p))} for p in products],
                'fields': [{'key': key, 'label': label} for key, label in FIELDS[public_product(products[0])['seccion']]]}

    @app.post('/api/comparativa/ficha')
    def comparison_sheet(payload: SheetRequest, request: Request):
        origin = request.headers.get('origin')
        if (origin and urlsplit(origin).netloc != request.url.netloc) or request.headers.get('sec-fetch-site') == 'cross-site':
            raise HTTPException(403, 'Solicitud no permitida.')
        products = pair(request, payload.a, payload.b)
        product = next((p for p in products if public_product(p)['id'] == payload.product), None)
        if product is None:
            raise HTTPException(400, 'Producto fuera de la comparación.')
        current = app.state.comparison_store
        key = spec_key(product)
        cached = current.get(key)
        if cached:
            return {'status': 'ready', 'sheet': cached}
        provider = os.environ.get('COMPARISON_AI_PROVIDER', 'gemini').lower()
        key_name = 'GEMINI_API_KEY' if provider == 'gemini' else 'ANTHROPIC_API_KEY'
        if provider not in ('gemini', 'anthropic') or not os.environ.get(key_name):
            return JSONResponse({'status': 'unavailable', 'message': 'La consulta de especificaciones no está disponible por el momento.'}, status_code=503)
        owner = secrets.token_hex(16)
        if not current.claim(key, owner):
            cached = current.get(key)
            return {'status': 'ready', 'sheet': cached} if cached else JSONResponse({'status': 'pending', 'retry_after': 5}, status_code=202)
        try:
            limiter = app.state.comparison_budget
            peer = request.client.host if request.client else 'unknown'
            if not limiter.reserve(('comparison', peer), 12, 3600) or not app.state.comparison_global_budget.reserve(('comparison', 'global'), 100, 86400):
                current.fail(key, owner)
                return JSONResponse({'status': 'unavailable', 'message': 'Alcancé el límite de consultas. Probá más tarde.'}, status_code=429)
            # Factory creates a dedicated client; do not inherit unbounded SDK retries.
            identity = {'nombre': product['nombre'], 'categoria': product.get('categoria', '')}
            if provider == 'gemini':
                sheet = research_gemini(identity, os.environ[key_name])
            else:
                with client_factory() as client:
                    sheet = research(identity, client)
            if not current.save(key, owner, sheet):
                return JSONResponse({'status': 'pending', 'retry_after': 5}, status_code=202)
            return {'status': 'ready', 'sheet': sheet}
        except Exception:
            current.fail(key, owner)
            return JSONResponse({'status': 'unavailable', 'message': 'No pude verificar esta ficha. Podés reintentar en un minuto.'}, status_code=503)
