#!/usr/bin/env python3
"""Sube arte generado y crea una versión previsualizada; nunca envía correo."""
import argparse
import json
import mimetypes
import shutil
import sys
import uuid
from pathlib import Path

from api_mailing import MailingApi


PROJECT_DIR = Path(__file__).resolve().parents[4]


def guardar_previsualizacion(resultado, imagen, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    asset = resultado["asset"]
    manifest = {key: value for key, value in resultado.items() if key not in {
        "preview_path", "manifest_path", "hero_path",
    }}
    html_preview = (resultado.get("manifest") or {}).get("html")
    if not html_preview:
        raise RuntimeError("La web no devolvió el HTML de vista previa")
    preview_path = output_dir / "preview.html"
    manifest_path = output_dir / "manifest.json"
    extension = Path(asset.get("filename") or imagen).suffix or Path(imagen).suffix
    hero_path = output_dir / f"hero{extension}"
    preview_path.write_text(html_preview, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(imagen, hero_path)
    return {
        **resultado,
        "preview_path": str(preview_path),
        "manifest_path": str(manifest_path),
        "hero_path": str(hero_path),
    }


def ejecutar(api, imagen, productos, brief, asunto, preheader, alt, nota=None,
             parent_id=None, output_dir=None):
    if not productos:
        raise ValueError("Seleccioná al menos un producto")
    if parent_id:
        padre = api.get(f"/admin/mailing/campanias/{parent_id}")
        campaign_id = padre["campaign_id"]
    else:
        campaign_id = str(uuid.uuid4())
    asset = api.post_file(f"/admin/mailing/assets/{campaign_id}", Path(imagen))
    payload = {
        "campaign_id": campaign_id,
        "parent_id": parent_id,
        "brief": brief,
        "asunto": asunto,
        "preheader": preheader,
        "nota": nota,
        "productos": productos,
        "hero": {
            "url": asset["url"],
            "sha256": asset["sha256"],
            "alt": alt,
            "width": asset["width"],
            "height": asset["height"],
        },
    }
    version = api.post("/admin/mailing/campanias", json=payload)
    resultado = {
        **version, "campaign_id": campaign_id, "asset": asset, "asset_url": asset["url"]
    }
    if output_dir is not None:
        return guardar_previsualizacion(resultado, imagen, output_dir)
    return resultado


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imagen", required=True, type=Path)
    parser.add_argument("--producto", action="append", required=True)
    parser.add_argument("--brief", default="")
    parser.add_argument("--asunto", required=True)
    parser.add_argument("--preheader", default="")
    parser.add_argument("--alt", required=True)
    parser.add_argument("--nota")
    parser.add_argument("--parent-id")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args(argv)
    if not args.imagen.is_file():
        parser.error("--imagen debe apuntar a un archivo existente")
    api = MailingApi()
    try:
        resultado = ejecutar(
            api, args.imagen, args.producto, args.brief, args.asunto,
            args.preheader, args.alt, args.nota, args.parent_id,
        )
        if args.salida is None:
            args.salida = PROJECT_DIR / "outputs" / "mailing" / resultado["campaign_id"] / resultado["id"]
        resultado = guardar_previsualizacion(resultado, args.imagen, args.salida)
        resumen = {campo: resultado.get(campo) for campo in (
            "id", "campaign_id", "estado", "asset_url", "preview_path", "manifest_path", "hero_path"
        )}
        print(json.dumps(resumen, ensure_ascii=False))
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
