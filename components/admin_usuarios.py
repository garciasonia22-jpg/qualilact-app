import streamlit as st
import pandas as pd

from db.supabase_client import init_connection
from utils.auth_utils import hashear_contrasena


_ROL_OPTS = ["ADMINISTRADOR", "OPERARIO"]
_ROL_LABELS = {"ADMINISTRADOR": "Administrador", "OPERARIO": "Operario"}
_ROL_LABELS_INV = {"Administrador": "ADMINISTRADOR", "Operario": "OPERARIO"}


def _get_supabase():
    return init_connection()


def _load_usuarios() -> list[dict]:
    try:
        resp = _get_supabase().table("usuarios_app").select("nombre_usuario, rol").order("nombre_usuario").execute()
        return resp.data or []
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return []


def render_admin_usuarios():
    st.markdown(
        "<h3 style='color:#0056A3;font-weight:800;margin-bottom:4px;'>👥 Gestión de Usuarios</h3>"
        "<p style='color:#6B7280;font-size:0.82rem;margin-bottom:22px;'>Panel exclusivo para administradores. "
        "Crea, modifica o elimina usuarios del sistema.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("_rol_usuario") != "ADMINISTRADOR":
        st.warning("⛔ Acceso restringido. Solo los administradores pueden gestionar usuarios.")
        return

    usuarios = _load_usuarios()

    # ── Tabla de usuarios actuales ──────────────────────────────────────────
    st.markdown("#### Usuarios registrados")
    if usuarios:
        df = pd.DataFrame(usuarios)
        df = df.rename(columns={"nombre_usuario": "Usuario", "rol": "Rol"})
        df["Rol"] = df["Rol"].map(lambda r: _ROL_LABELS.get(r, r))
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay usuarios registrados.")

    st.markdown("<hr style='border-color:#E5E7EB;margin:18px 0;'>", unsafe_allow_html=True)

    # ── Crear nuevo usuario ─────────────────────────────────────────────────
    st.markdown("#### Agregar usuario")
    with st.form("_form_add_user", clear_on_submit=True):
        _nu_col1, _nu_col2, _nu_col3 = st.columns([2, 2, 1])
        with _nu_col1:
            _nu_usuario = st.text_input("👤 Usuario", placeholder="nombre_usuario")
        with _nu_col2:
            _nu_contrasena = st.text_input("🔒 Contraseña", type="password", placeholder="contraseña")
        with _nu_col3:
            _nu_rol_label = st.selectbox("Rol", options=["Administrador", "Operario"])
        _nu_submit = st.form_submit_button("➕ Agregar Usuario", type="primary", use_container_width=True)

    if _nu_submit:
        _nu_usuario = (_nu_usuario or "").strip()
        _nu_contrasena = (_nu_contrasena or "").strip()
        if not _nu_usuario or not _nu_contrasena:
            st.error("El usuario y la contraseña son obligatorios.")
        else:
            _nu_rol = _ROL_LABELS_INV.get(_nu_rol_label, "OPERARIO")
            _nombres_existentes = [u["nombre_usuario"] for u in usuarios]
            if _nu_usuario in _nombres_existentes:
                st.error(f"El usuario «{_nu_usuario}» ya existe.")
            else:
                try:
                    _get_supabase().table("usuarios_app").insert({
                        "nombre_usuario": _nu_usuario,
                        "contrasena": hashear_contrasena(_nu_contrasena),
                        "rol": _nu_rol,
                    }).execute()
                    st.success(f"✅ Usuario «{_nu_usuario}» creado con rol **{_nu_rol_label}**.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al crear usuario: {e}")

    st.markdown("<hr style='border-color:#E5E7EB;margin:18px 0;'>", unsafe_allow_html=True)

    # ── Modificar / Eliminar usuario ────────────────────────────────────────
    st.markdown("#### Modificar o eliminar usuario")

    if not usuarios:
        st.info("No hay usuarios disponibles para modificar.")
        return

    _nombres = [u["nombre_usuario"] for u in usuarios]
    _me_usuario = st.selectbox("Seleccionar usuario", options=_nombres, key="_me_sel_usuario")

    if _me_usuario:
        _me_data = next((u for u in usuarios if u["nombre_usuario"] == _me_usuario), None)
        _me_rol_actual = _me_data["rol"] if _me_data else "OPERARIO"
        _me_rol_actual_label = _ROL_LABELS.get(_me_rol_actual, "Operario")

        _me_col1, _me_col2 = st.columns([2, 1])
        with _me_col1:
            _me_nuevo_rol_label = st.selectbox(
                "Nuevo rol",
                options=["Administrador", "Operario"],
                index=0 if _me_rol_actual_label == "Administrador" else 1,
                key="_me_rol_select",
            )
        with _me_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            _me_btn_cambiar = st.button("💾 Cambiar Rol", key="_me_btn_rol", use_container_width=True)

        if _me_btn_cambiar:
            _me_nuevo_rol = _ROL_LABELS_INV.get(_me_nuevo_rol_label, "OPERARIO")
            if _me_nuevo_rol == _me_rol_actual:
                st.info(f"El usuario «{_me_usuario}» ya tiene el rol **{_me_nuevo_rol_label}**.")
            else:
                try:
                    _get_supabase().table("usuarios_app").update(
                        {"rol": _me_nuevo_rol}
                    ).eq("nombre_usuario", _me_usuario).execute()
                    st.success(f"✅ Rol de «{_me_usuario}» actualizado a **{_me_nuevo_rol_label}**.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar rol: {e}")

        st.markdown("<br>", unsafe_allow_html=True)

        _me_propio = _me_usuario == st.session_state.get("_usuario_login", "")
        if _me_propio:
            st.warning("⚠️ No puedes eliminar tu propia cuenta mientras estás activo.")
        else:
            with st.expander("🗑️ Zona de eliminación (acción irreversible)"):
                st.warning(
                    f"Estás a punto de eliminar al usuario **{_me_usuario}**. "
                    "Esta acción no se puede deshacer."
                )
                _me_confirm_key = f"_me_confirm_{_me_usuario}"
                _me_confirm = st.checkbox(
                    f"Confirmo que quiero eliminar a «{_me_usuario}»",
                    key=_me_confirm_key,
                )
                if st.button("🗑️ Eliminar Usuario", key="_me_btn_del", type="primary", disabled=not _me_confirm):
                    try:
                        _get_supabase().table("usuarios_app").delete().eq(
                            "nombre_usuario", _me_usuario
                        ).execute()
                        st.success(f"✅ Usuario «{_me_usuario}» eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar usuario: {e}")
