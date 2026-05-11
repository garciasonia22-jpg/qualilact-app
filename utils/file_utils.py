import io
import json
import re
import zipfile

import pandas as pd
import requests

from db.supabase_repo import upload_imagen, get_imagen_url
from utils.time_utils import now_col


def save_fotos_to_disk(uploaded_files: list, prefix: str) -> list:
    """Sube las imágenes al bucket de Supabase Storage y devuelve la lista de
    paths internos (sin prefijo de bucket). El nombre 'save_fotos_to_disk' se
    conserva por compatibilidad con los componentes existentes."""
    saved = []
    if not uploaded_files:
        return saved
    ts = now_col().strftime("%Y%m%d_%H%M%S")
    safe_prefix = re.sub(r"[^A-Z0-9_\-]", "_", (prefix or "X").upper())
    for i, uf in enumerate(uploaded_files, start=1):
        ext = uf.name.rsplit(".", 1)[-1].lower() if "." in uf.name else "jpg"
        ext = ext if ext in ("jpg", "jpeg", "png") else "jpg"
        path = f"{safe_prefix}/{ts}_{i}.{ext}"
        ctype = "image/png" if ext == "png" else "image/jpeg"
        uf.seek(0)
        data = uf.read()
        uf.seek(0)
        try:
            upload_imagen(path, data, content_type=ctype)
            saved.append(path)
        except Exception:
            # Si falla la subida, omite la imagen pero continúa con el resto.
            continue
    return saved


def get_image_url(path: str):
    """Wrapper directo para get_imagen_url (URL firmada, cache 30 min)."""
    return get_imagen_url(path)


# ─────────────────────────────────────────────────────────────────────
# Generación de ZIP con evidencias fotográficas (en memoria)
# ─────────────────────────────────────────────────────────────────────
_INVALID_FN_RE = re.compile(r'[\\/:*?"<>|\s]+')


def _safe_name(s) -> str:
    """Sanitiza un valor para usarlo como segmento de nombre de archivo."""
    if s is None:
        return ""
    if isinstance(s, float) and pd.isna(s):
        return ""
    out = _INVALID_FN_RE.sub("_", str(s).strip())
    return out.strip("._-") or ""


def _parse_fotos(raw) -> list[str]:
    """Convierte fotos_json (str/list/None) en lista de paths del bucket."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [p for p in raw if p]
    s = str(raw).strip()
    if not s or s == "[]":
        return []
    try:
        data = json.loads(s)
        return [p for p in data if p] if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _ext_from_path(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "jpg"
    return ext if ext in ("jpg", "jpeg", "png", "webp") else "jpg"


def _build_filename(row: dict, idx: int, ext: str) -> tuple[str, str]:
    """Devuelve (carpeta_por_fecha, nombre_archivo) para una imagen.

    Patrón:
      RUTAS        → {Fecha}_{Ruta}_{Placa}[_{n}].{ext}
      TRANSUIZA    → {Fecha}_Transuiza_{Placa}[_{n}].{ext}
      SEGUIMIENTOS → {Fecha}_{SubTipo}_{Codigo|Ruta}[_{n}].{ext}
    """
    fecha = _safe_name(row.get("fecha")) or "SIN_FECHA"
    folder = fecha

    tipo = str(row.get("tipo_seguimiento") or "").upper()
    if not tipo and "sub_tipo_seguimiento" in row:
        tipo = "SEGUIMIENTOS"

    if tipo == "TRANSUIZA":
        partes = [fecha, "Transuiza", _safe_name(row.get("placa"))]
    elif tipo == "SEGUIMIENTOS" or row.get("sub_tipo_seguimiento"):
        sub = _safe_name(row.get("sub_tipo_seguimiento")) or "SEG"
        ident = (_safe_name(row.get("seg_codigo"))
                 or _safe_name(row.get("ruta"))
                 or _safe_name(row.get("seg_id_muestra"))
                 or "REG")
        partes = [fecha, sub, ident]
    else:  # RUTAS por defecto
        partes = [fecha,
                  _safe_name(row.get("ruta")),
                  _safe_name(row.get("placa"))]

    base = "_".join(p for p in partes if p) or "evidencia"
    if idx > 1:
        base = f"{base}_{idx}"
    return folder, f"{base}.{ext}"


def _download_bytes(path: str, timeout: int = 15) -> bytes | None:
    """Descarga el binario de una imagen del bucket vía URL firmada."""
    if not path:
        return None
    url = get_imagen_url(path)
    if not url:
        return None
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        return None
    return None


def generar_zip_imagenes(datos_filtrados) -> tuple[bytes, int]:
    """Genera un ZIP en memoria con todas las evidencias fotográficas.

    Args:
        datos_filtrados: pd.DataFrame o lista de dicts con los registros
            actualmente filtrados en la vista del historial. Debe contener al
            menos `fotos_json` y los campos descriptivos (fecha, ruta, placa,
            tipo_seguimiento, sub_tipo_seguimiento, seg_codigo, etc.).

    Returns:
        (zip_bytes, num_imagenes_incluidas). Si no hay imágenes, num=0 y los
        bytes corresponden a un ZIP vacío (el caller decide si mostrarlo).
    """
    if datos_filtrados is None:
        return b"", 0

    if isinstance(datos_filtrados, pd.DataFrame):
        rows = datos_filtrados.to_dict(orient="records")
    else:
        rows = list(datos_filtrados)

    buf = io.BytesIO()
    incluidas = 0
    nombres_usados: set[str] = set()

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            paths = _parse_fotos(row.get("fotos_json"))
            if not paths:
                continue
            for i, path in enumerate(paths, start=1):
                data = _download_bytes(path)
                if not data:
                    continue
                folder, fname = _build_filename(row, i, _ext_from_path(path))
                ruta_zip = f"{folder}/{fname}"
                # Evita colisiones entre registros con misma fecha/ruta/placa
                base_zip = ruta_zip
                col = 1
                while ruta_zip in nombres_usados:
                    col += 1
                    name, ext = base_zip.rsplit(".", 1)
                    ruta_zip = f"{name}_{col}.{ext}"
                nombres_usados.add(ruta_zip)
                try:
                    zf.writestr(ruta_zip, data)
                    incluidas += 1
                except Exception:
                    continue

    buf.seek(0)
    return buf.read(), incluidas
