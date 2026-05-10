def calcular_estado_calidad(row: dict) -> str:
    """Retorna 'CONFORME' o 'DESVIACIÓN' según los parámetros de la ruta.
    Solo aplica a registros de tipo RUTAS."""
    if str(row.get("tipo_seguimiento", "RUTAS")).strip() != "RUTAS":
        return "CONFORME"
    try:
        st_val = float(str(row.get("solidos_ruta", "")).replace(",", "."))
        if 0 < st_val < 12.60:
            return "DESVIACIÓN"
    except (ValueError, TypeError):
        pass
    try:
        ic_val = float(str(row.get("crioscopia_ruta", "")).replace(",", "."))
        if ic_val > -0.535 or ic_val < -0.550:
            return "DESVIACIÓN"
    except (ValueError, TypeError):
        pass
    return "CONFORME"


def parse_num(val, default=None):
    if val is None:
        return default
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return default
