import re

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
