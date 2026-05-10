"""Helpers de autenticación: hashing y verificación de contraseñas con bcrypt."""
import bcrypt


def es_hash_bcrypt(valor: str) -> bool:
    """Devuelve True si `valor` luce como un hash bcrypt ($2a$/$2b$/$2y$)."""
    if not valor or not isinstance(valor, str):
        return False
    return valor.startswith(("$2a$", "$2b$", "$2y$")) and len(valor) >= 59


def hashear_contrasena(plain: str) -> str:
    """Genera un hash bcrypt (cost=12) a partir de una contraseña en texto plano."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_contrasena(plain: str, hashed: str) -> bool:
    """Verifica la contraseña contra el hash bcrypt almacenado."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
