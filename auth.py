"""
Módulo de autenticación para QualiLact.
Gestiona usuarios con roles: ADMIN y OPERARIO.
"""

import json
import os
import hashlib
import streamlit as st
from datetime import datetime, timezone, timedelta

# Zona horaria Colombia
COL_TZ = timezone(timedelta(hours=-5))

USERS_FILE = "usuarios.json"
SESSIONS_FILE = "sesiones.json"

# Contraseñas hasheadas por defecto (cambiar en producción)
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "ADMIN",
        "nombre": "Administrador",
        "creado_en": datetime.now(tz=COL_TZ).isoformat(),
    },
    "operario": {
        "password_hash": hashlib.sha256("operario123".encode()).hexdigest(),
        "role": "OPERARIO",
        "nombre": "Operario",
        "creado_en": datetime.now(tz=COL_TZ).isoformat(),
    },
}


def hash_password(password: str) -> str:
    """Hashea una contraseña."""
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> dict:
    """Carga los usuarios desde el archivo JSON."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USERS, f, ensure_ascii=False, indent=2)
        return DEFAULT_USERS
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_USERS


def save_users(users: dict):
    """Guarda los usuarios en el archivo JSON."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def create_user(username: str, password: str, role: str, nombre: str = ""):
    """Crea un nuevo usuario."""
    users = load_users()
    
    if username in users:
        return False, "El usuario ya existe"
    
    if role not in ("ADMIN", "OPERARIO"):
        return False, "Rol no válido"
    
    users[username] = {
        "password_hash": hash_password(password),
        "role": role,
        "nombre": nombre or username,
        "creado_en": datetime.now(tz=COL_TZ).isoformat(),
    }
    
    save_users(users)
    return True, "Usuario creado exitosamente"


def verify_login(username: str, password: str) -> tuple:
    """Verifica las credenciales del usuario."""
    users = load_users()
    
    if username not in users:
        return False, "Usuario no encontrado"
    
    user = users[username]
    if user["password_hash"] != hash_password(password):
        return False, "Contraseña incorrecta"
    
    return True, user


def init_session_state():
    """Inicializa el estado de la sesión para autenticación."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_data" not in st.session_state:
        st.session_state.user_data = None


def render_login():
    """Renderiza la pantalla de login."""
    st.set_page_config(page_title="QualiLact - Login", page_icon="🧪", layout="centered")
    
    st.markdown(
        """
        <style>
        .stApp { background-color: #F0F5F9 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Encabezado
    st.markdown(
        """
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            padding: 40px 0 20px 0;
            margin-bottom: 30px;
        ">
            <div style="font-size: 3rem;">🐄🥛</div>
            <div>
                <div style="
                    font-size: 2.2rem;
                    font-weight: 800;
                    color: #0056A3;
                    letter-spacing: 1px;
                    font-family: 'Segoe UI', sans-serif;
                ">QualiLact</div>
                <div style="
                    font-size: 0.95rem;
                    color: #6B7280;
                    font-weight: 400;
                    text-align: center;
                ">Control de Calidad en Leche Fresca</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Tarjeta de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div style="
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            ">
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            """
            <div style="
                font-size: 1.3rem;
                font-weight: 700;
                color: #0056A3;
                margin-bottom: 20px;
                text-align: center;
            ">Iniciar Sesión</div>
            """,
            unsafe_allow_html=True,
        )
        
        username = st.text_input(
            "👤 Usuario",
            placeholder="Ingrese su usuario",
            key="login_user",
        )
        
        password = st.text_input(
            "🔐 Contraseña",
            type="password",
            placeholder="Ingrese su contraseña",
            key="login_pass",
        )
        
        if st.button("🔓 INICIAR SESIÓN", type="primary", use_container_width=True):
            success, result = verify_login(username, password)
            
            if success:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_role = result["role"]
                st.session_state.user_data = result
                st.success(f"¡Bienvenido {result['nombre']}!")
                st.rerun()
            else:
                st.error(result)
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        # Información de credenciales de prueba
        st.info(
            """
            **Credenciales de prueba:**
            
            👤 **Admin:**
            - Usuario: `admin`
            - Contraseña: `admin123`
            
            👤 **Operario:**
            - Usuario: `operario`
            - Contraseña: `operario123`
            """
        )
        
        st.markdown(
            """
            </div>
            """,
            unsafe_allow_html=True,
        )


def check_admin_access():
    """Verifica si el usuario actual tiene acceso de administrador."""
    return st.session_state.get("user_role") == "ADMIN"


def check_operario_access():
    """Verifica si el usuario actual tiene acceso de operario."""
    return st.session_state.get("user_role") in ("OPERARIO", "ADMIN")


def render_logout_button():
    """Renderiza el botón de logout en la sidebar."""
    with st.sidebar:
        st.markdown("---")
        
        user_info = st.session_state.get("user_data", {})
        role_emoji = "👨‍💼" if st.session_state.get("user_role") == "ADMIN" else "👷"
        
        st.markdown(
            f"""
            <div style="
                padding: 12px;
                background: #EAF1FA;
                border-radius: 8px;
                margin-bottom: 10px;
                border-left: 4px solid #0056A3;
            ">
                <div style="font-size: 0.75rem; color: #6B7280; font-weight: 600;">
                    USUARIO ACTUAL
                </div>
                <div style="font-size: 0.95rem; font-weight: 700; color: #0056A3;">
                    {role_emoji} {user_info.get('nombre', 'Usuario')}
                </div>
                <div style="font-size: 0.7rem; color: #9CA3AF; margin-top: 2px;">
                    {st.session_state.get('user_role', 'DESCONOCIDO')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.session_state.user_data = None
            st.rerun()
