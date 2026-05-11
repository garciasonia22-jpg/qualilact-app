"""Login persistente entre fallas de conexión usando sessionStorage del navegador.

Diseño:
- Tras el login se emite un token firmado con HMAC-SHA256 (clave derivada de
  SUPABASE_KEY) que contiene usuario, rol, nombre y expiración (30 días).
- El token se guarda en sessionStorage del navegador. sessionStorage es
  per-pestaña: se borra automáticamente cuando el usuario cierra la ventana
  o pestaña, lo cual cumple el requisito de "cerrar al cerrar la ventana".
- Si Streamlit pierde el estado de la sesión (caída de internet, reinicio del
  servidor, recarga de la página), un bridge JS recarga la página con el token
  en un query param efímero. Python valida la firma del token y restaura el
  estado de sesión sin pedir credenciales otra vez.
- Cerrar sesión manualmente borra sessionStorage explícitamente.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

import streamlit as st


_TOKEN_KEY = "ql_session_token"
_QPARAM    = "_ql_s"
_TTL_DAYS  = 30


def _secret_key() -> bytes:
    raw = (os.environ.get("SUPABASE_KEY") or "qualilact-default-secret-change-me").encode("utf-8")
    return hashlib.sha256(raw).digest()


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _make_token(usuario: str, rol: str, nombre: str) -> str:
    payload = {
        "u": usuario, "r": rol, "n": nombre,
        "exp": int(time.time()) + _TTL_DAYS * 86400,
    }
    body = _b64u(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig  = _b64u(hmac.new(_secret_key(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def _parse_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        expected = _b64u(hmac.new(_secret_key(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_b64u_dec(body))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return data
    except Exception:
        return None


def _inject_js(js_body: str):
    st.html(
        f"<script>(function(){{try{{{js_body}}}catch(e){{console.warn('ql_sess',e);}}}})();</script>",
        unsafe_allow_javascript=True,
    )


def issue_token(usuario: str, rol: str, nombre: str):
    """Llamar después de un login exitoso. El token se persistirá en
    sessionStorage del navegador en el siguiente render (sobrevive el rerun)."""
    st.session_state["_pending_token"] = _make_token(usuario, rol, nombre)


def request_logout():
    """Cerrar sesión: limpia session_state y marca un flag para que el próximo
    render borre sessionStorage del navegador."""
    keep_keys = set()  # nada que conservar
    for k in list(st.session_state.keys()):
        if k not in keep_keys:
            del st.session_state[k]
    st.session_state["_pending_logout"] = True


def restore_or_sync_session():
    """Punto único llamado al inicio de cada render, ANTES del guard de auth.

    Maneja cuatro escenarios en orden:
      1. _pending_logout = True  → limpia sessionStorage + URL en el navegador.
      2. _pending_token presente  → guarda el token recién emitido en sessionStorage.
      3. URL trae el token        → valida firma, restaura session_state, limpia URL.
      4. No logueado + sin token   → bridge JS recarga la página con el token
         desde sessionStorage si lo hay (rehidratación tras caída de conexión).
    """
    # ── 1. Logout pendiente ───────────────────────────────────────────────
    if st.session_state.pop("_pending_logout", False):
        _inject_js(
            f'var u=new URL(window.location.href);'
            f'window.sessionStorage.removeItem("{_TOKEN_KEY}");'
            f'u.searchParams.delete("{_QPARAM}");'
            f'window.history.replaceState({{}},"",u.toString());'
        )
        return

    # ── 2. Token recién emitido por el login ──────────────────────────────
    pending_tok = st.session_state.pop("_pending_token", None)
    if pending_tok:
        _inject_js(
            f'window.sessionStorage.setItem("{_TOKEN_KEY}",{json.dumps(pending_tok)});'
        )

    # ── 3. Restaurar desde query param si la URL trae token ───────────────
    try:
        qp_tok = st.query_params.get(_QPARAM)
    except Exception:
        qp_tok = None

    if qp_tok and not st.session_state.get("_logged_in"):
        data = _parse_token(qp_tok)
        if data:
            st.session_state["_logged_in"]      = True
            st.session_state["_rol_usuario"]    = data.get("r", "")
            st.session_state["_nombre_usuario"] = data.get("n", "")
            st.session_state["_usuario_login"]  = data.get("u", "")
        else:
            # token inválido/expirado: borra también sessionStorage
            _inject_js(
                f'window.sessionStorage.removeItem("{_TOKEN_KEY}");'
            )
        # Limpia el query param de la URL (visual + evita re-trigger)
        try:
            del st.query_params[_QPARAM]
        except Exception:
            pass
        # También limpiamos la URL del navegador por si Streamlit no lo hizo
        _inject_js(
            f'var u=new URL(window.location.href);'
            f'u.searchParams.delete("{_QPARAM}");'
            f'window.history.replaceState({{}},"",u.toString());'
        )

    # ── 4. Bridge: rehidratar desde sessionStorage si hay token guardado ──
    if not st.session_state.get("_logged_in"):
        _inject_js(
            f'var u=new URL(window.location.href);'
            f'if (u.searchParams.get("{_QPARAM}")) return;'
            f'var t=window.sessionStorage.getItem("{_TOKEN_KEY}");'
            f'if (!t) return;'
            f'u.searchParams.set("{_QPARAM}", t);'
            f'window.location.replace(u.toString());'
        )
