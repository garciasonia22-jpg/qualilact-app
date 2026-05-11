import os

import streamlit as st
from supabase import create_client


def _get_secret(name: str) -> str | None:
    """Lee primero de st.secrets (si hay secrets.toml) y luego de os.environ."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


@st.cache_resource
def init_connection():
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key:
        st.error("Error: No se encontraron SUPABASE_URL / SUPABASE_KEY en variables de entorno ni secrets.")
        return None
    return create_client(url, key)
