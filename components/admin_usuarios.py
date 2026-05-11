import pandas as pd
import streamlit as st

from db.supabase_client import init_connection
from utils.auth_utils import hashear_contrasena

_ROL_OPTS = ["ADMINISTRADOR", "OPERARIO"]
_ROL_LABELS = {"ADMINISTRADOR": "Administrador", "OPERARIO": "Operario"}
_ROL_LABELS_INV = {"Administrador": "ADMINISTRADOR", "Operario": "OPERARIO"}


def _get_supabase():
    return init_connection()


def _load_usuarios() -> list[dict]:
    try:
        resp = (
            _get_supabase()
            .table("usuarios_app")
            .select("id, nombre_usuario, rol")
            .order("nombre_usuario")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return []


def _banner_sesion(nombre_admin: str):
    st.markdown(
        f"""
        <div style="
            background:linear-gradient(135deg,#EAF2FB 0%,#F8FAFC 100%);
            border:1px solid #C8DBF0;border-left:5px solid #0056A3;
            border-radius:12px;padding:14px 20px;margin-bottom:22px;
            display:flex;align-items:center;justify-content:space-between;
            box-shadow:0 1px 4px rgba(0,86,163,0.06);">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="font-size:1.6rem;">🔑</div>
                <div>
                    <div style="color:#0056A3;font-weight:700;font-size:0.95rem;line-height:1.1;">
                        Sesión Administrativa Activa
                    </div>
                    <div style="color:#374151;font-size:0.82rem;margin-top:2px;">
                        Conectado como <b style="color:#0056A3;">{nombre_admin}</b>
                    </div>
                </div>
            </div>
            <div style="
                background:#0056A3;color:#fff;font-size:0.7rem;font-weight:700;
                padding:6px 12px;border-radius:999px;letter-spacing:.5px;">
                ADMIN
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tab_listado(usuarios: list[dict]):
    st.markdown(
        "<p style='color:#6B7280;font-size:0.85rem;margin:4px 0 14px;'>"
        "Visualiza todos los usuarios del sistema y sus roles asignados.</p>",
        unsafe_allow_html=True,
    )

    if not usuarios:
        st.info("No hay usuarios registrados todavía. Crea el primero en la pestaña «➕ Crear Usuario».")
        return

    total = len(usuarios)
    n_admins = sum(1 for u in usuarios if u.get("rol") == "ADMINISTRADOR")
    n_oper = total - n_admins

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Total", total)
    c2.metric("🔑 Administradores", n_admins)
    c3.metric("👤 Operarios", n_oper)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    df = pd.DataFrame(usuarios)
    df = df.rename(columns={"nombre_usuario": "Usuario", "rol": "Rol"})
    df["Rol"] = df["Rol"].map(lambda r: _ROL_LABELS.get(r, r))
    df = df[["Usuario", "Rol"]]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Usuario": st.column_config.TextColumn("👤 Usuario", width="medium"),
            "Rol": st.column_config.TextColumn("🎯 Rol", width="small"),
        },
    )


def _tab_crear(usuarios: list[dict]):
    st.markdown(
        "<p style='color:#6B7280;font-size:0.85rem;margin:4px 0 14px;'>"
        "Completa los campos para registrar un nuevo usuario en el sistema.</p>",
        unsafe_allow_html=True,
    )

    nombres_existentes = {u["nombre_usuario"].lower() for u in usuarios}

    with st.form("_form_crear_usuario", clear_on_submit=True, border=True):
        c1, c2 = st.columns(2)
        with c1:
            nu_usuario = st.text_input(
                "👤 Nombre de Usuario",
                placeholder="ej. jperez",
                help="Sin espacios. Se usará para iniciar sesión.",
            )
        with c2:
            nu_rol_label = st.selectbox(
                "🎯 Rol",
                options=["Operario", "Administrador"],
                help="Operario: registra datos. Administrador: además gestiona usuarios y catálogos.",
            )

        nu_contrasena = st.text_input(
            "🔒 Contraseña",
            type="password",
            placeholder="Mínimo 4 caracteres",
            help="Se almacena cifrada con bcrypt. Usa el ícono 👁 para revelarla mientras escribes.",
        )

        submitted = st.form_submit_button(
            "➕ Crear Usuario", type="primary", use_container_width=True
        )

    if not submitted:
        return

    nu_usuario = (nu_usuario or "").strip()
    nu_contrasena = (nu_contrasena or "").strip()

    if not nu_usuario or not nu_contrasena:
        st.error("⚠️ El nombre de usuario y la contraseña son obligatorios.")
        return
    if " " in nu_usuario:
        st.error("⚠️ El nombre de usuario no puede contener espacios.")
        return
    if len(nu_contrasena) < 4:
        st.error("⚠️ La contraseña debe tener al menos 4 caracteres.")
        return
    if nu_usuario.lower() in nombres_existentes:
        st.error(f"⚠️ El usuario «{nu_usuario}» ya existe. Elige otro nombre.")
        return

    nu_rol = _ROL_LABELS_INV.get(nu_rol_label, "OPERARIO")
    try:
        _get_supabase().table("usuarios_app").insert(
            {
                "nombre_usuario": nu_usuario,
                "contrasena": hashear_contrasena(nu_contrasena),
                "rol": nu_rol,
            }
        ).execute()
        st.success(f"✅ Usuario «{nu_usuario}» creado con rol **{nu_rol_label}**.")
        st.rerun()
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")


def _tab_modificar(usuarios: list[dict]):
    st.markdown(
        "<p style='color:#6B7280;font-size:0.85rem;margin:4px 0 14px;'>"
        "Selecciona un usuario para editar sus datos o eliminarlo del sistema.</p>",
        unsafe_allow_html=True,
    )

    if not usuarios:
        st.info("No hay usuarios disponibles para modificar.")
        return

    nombres = [u["nombre_usuario"] for u in usuarios]
    sel = st.selectbox(
        "👤 Selecciona un usuario",
        options=["— Seleccionar —"] + nombres,
        key="_me_sel_usuario",
    )

    if sel == "— Seleccionar —":
        st.caption("Elige un usuario de la lista para cargar sus datos.")
        return

    user = next((u for u in usuarios if u["nombre_usuario"] == sel), None)
    if not user:
        st.error("No se pudo cargar el usuario seleccionado.")
        return

    rol_actual = user.get("rol", "OPERARIO")
    rol_actual_label = _ROL_LABELS.get(rol_actual, "Operario")
    es_propio = sel == st.session_state.get("_usuario_login", "")

    st.markdown(
        f"""
        <div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:10px;
                    padding:12px 16px;margin:6px 0 14px;">
            <span style="color:#6B7280;font-size:0.78rem;">Datos actuales:</span>
            <div style="margin-top:4px;">
                <b style="color:#0056A3;">{sel}</b>
                <span style="color:#6B7280;"> · </span>
                <span style="color:#374151;">{rol_actual_label}</span>
                {"<span style='background:#FEF3C7;color:#92400E;font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:999px;margin-left:8px;'>TU CUENTA</span>" if es_propio else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ───── Editar datos ──────────────────────────────────────────────
    with st.form(f"_form_edit_{user['id']}", clear_on_submit=False, border=True):
        st.markdown("**✏️ Editar datos**")
        c1, c2 = st.columns(2)
        with c1:
            ed_nombre = st.text_input("👤 Nombre de Usuario", value=sel)
        with c2:
            ed_rol_label = st.selectbox(
                "🎯 Rol",
                options=["Administrador", "Operario"],
                index=0 if rol_actual_label == "Administrador" else 1,
                disabled=es_propio,
                help="Por seguridad no puedes cambiar tu propio rol." if es_propio else None,
            )

        ed_pwd = st.text_input(
            "🔒 Nueva Contraseña",
            type="password",
            placeholder="Dejar en blanco para mantener la actual",
        )

        guardar = st.form_submit_button(
            "💾 Actualizar Datos", type="primary", use_container_width=True
        )

    if guardar:
        ed_nombre = (ed_nombre or "").strip()
        ed_pwd = (ed_pwd or "").strip()
        if not ed_nombre:
            st.error("⚠️ El nombre de usuario no puede estar vacío.")
        elif " " in ed_nombre:
            st.error("⚠️ El nombre de usuario no puede contener espacios.")
        elif (
            ed_nombre.lower() != sel.lower()
            and any(u["nombre_usuario"].lower() == ed_nombre.lower() for u in usuarios)
        ):
            st.error(f"⚠️ Ya existe un usuario con el nombre «{ed_nombre}».")
        elif ed_pwd and len(ed_pwd) < 4:
            st.error("⚠️ La nueva contraseña debe tener al menos 4 caracteres.")
        else:
            payload: dict = {}
            if ed_nombre != sel:
                payload["nombre_usuario"] = ed_nombre
            if not es_propio:
                nuevo_rol = _ROL_LABELS_INV.get(ed_rol_label, "OPERARIO")
                if nuevo_rol != rol_actual:
                    payload["rol"] = nuevo_rol
            if ed_pwd:
                payload["contrasena"] = hashear_contrasena(ed_pwd)

            if not payload:
                st.info("No hiciste cambios para guardar.")
            else:
                try:
                    _get_supabase().table("usuarios_app").update(payload).eq(
                        "id", user["id"]
                    ).execute()
                    if es_propio and "nombre_usuario" in payload:
                        st.session_state._usuario_login = ed_nombre
                        st.session_state._nombre_usuario = ed_nombre
                    st.success(f"✅ Datos de «{ed_nombre}» actualizados correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar usuario: {e}")

    # ───── Zona de eliminación ───────────────────────────────────────
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='border-top:1px dashed #E5E7EB;margin:4px 0 12px;'></div>",
        unsafe_allow_html=True,
    )

    if es_propio:
        st.warning("⚠️ No puedes eliminar tu propia cuenta mientras estás activo.")
        return

    with st.expander("🗑️ Eliminar Usuario (acción irreversible)"):
        st.markdown(
            f"<div style='background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;"
            f"padding:12px 14px;color:#991B1B;font-size:0.85rem;'>"
            f"Vas a eliminar permanentemente al usuario <b>{sel}</b>. "
            f"Esta acción <b>no se puede deshacer</b>.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        confirm = st.checkbox(
            f"Confirmo que quiero eliminar a «{sel}»",
            key=f"_me_confirm_{user['id']}",
        )
        if st.button(
            "🗑️ Eliminar Usuario Definitivamente",
            key=f"_me_btn_del_{user['id']}",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
        ):
            try:
                _get_supabase().table("usuarios_app").delete().eq(
                    "id", user["id"]
                ).execute()
                st.success(f"✅ Usuario «{sel}» eliminado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al eliminar usuario: {e}")


def render_admin_usuarios():
    st.markdown(
        "<h3 style='color:#0056A3;font-weight:800;margin-bottom:4px;'>👥 Gestión de Usuarios</h3>"
        "<p style='color:#6B7280;font-size:0.82rem;margin-bottom:18px;'>"
        "Centro de control de acceso · Crea, modifica o elimina cuentas del sistema.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("_rol_usuario") != "ADMINISTRADOR":
        st.warning("⛔ Acceso restringido. Solo los administradores pueden gestionar usuarios.")
        return

    nombre_admin = st.session_state.get(
        "_nombre_usuario", st.session_state.get("_usuario_login", "Administrador")
    )
    _banner_sesion(nombre_admin)

    usuarios = _load_usuarios()

    tab_lista, tab_crear, tab_mod = st.tabs(
        ["📋 Listado y Control", "➕ Crear Usuario", "✏️ Modificar / Eliminar"]
    )
    with tab_lista:
        _tab_listado(usuarios)
    with tab_crear:
        _tab_crear(usuarios)
    with tab_mod:
        _tab_modificar(usuarios)
