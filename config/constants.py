import os
from datetime import timezone, timedelta

COL_TZ = timezone(timedelta(hours=-5))

CSV_PATH  = "rutas_historial.csv"
FOTOS_DIR = "fotos"
os.makedirs(FOTOS_DIR, exist_ok=True)

CSV_COLS = [
    "tipo_seguimiento",
    "fecha", "ruta", "placa", "conductor",
    "volumen_declarado", "vol_estaciones", "diferencia",
    "solidos_ruta", "crioscopia_ruta", "st_pond", "ic_pond",
    "num_estaciones", "guardado_en",
    "st_carrotanque", "grasa_muestra", "proteina_muestra", "diferencia_solidos",
    "estaciones_json", "fotos_json",
]

SEG_CSV_PATH = "seguimientos_historial.csv"
SEG_COLS = [
    "sub_tipo_seguimiento", "fecha",
    "seg_codigo", "seg_quien_trajo", "ruta", "seg_responsable",
    "seg_id_muestra", "seg_volumen", "seg_grasa", "seg_st", "seg_ic", "seg_agua",
    "seg_alcohol", "seg_cloruros", "seg_neutralizantes", "seg_observaciones",
    "seg_vol_declarado", "seg_vol_muestras", "seg_diferencia_vol",
    "seg_solidos_ruta", "seg_crioscopia_ruta", "seg_st_pond", "seg_ic_pond",
    "muestras_json", "guardado_en", "fotos_json",
]

DRAFT_PATH      = "borrador_autoguardado.json"
CATALOGO_PATH   = "estaciones_catalogo.csv"

DRAFT_EXACT_KEYS = [
    "continuar", "_tipo_servicio_guardado", "_sub_tipo_seg_guardado",
    "tipo_servicio_select", "sub_tipo_seg_select",
    "_ruta_fg",
    "imagenes_confirmadas", "imagenes_nombres_guardados",
    "trans_imagenes_confirmadas", "trans_imagenes_nombres_guardados",
    "estaciones_guardadas", "form_ver",
    "trans_fecha", "trans_placa", "trans_st_carrotanque",
    "trans_grasa", "trans_st_muestra", "trans_proteina",
    "seg_fecha", "seg_codigo", "seg_quien_trajo", "seg_ruta_acomp",
    "seg_responsable", "seg_quality_key_counter",
    "acomp_muestras", "contra_muestras",
]

DRAFT_PREFIXES = (
    "nue_",
    "fecha_ruta_", "nombre_ruta_", "placa_vehiculo_", "conductor_",
    "volumen_ruta_", "solidos_totales_", "crioscopia_",
    "seg_id_muestra_", "seg_grasa_", "seg_st_", "seg_ic_raw_", "seg_agua_",
    "seg_alcohol_", "seg_cloruros_", "seg_neutralizantes_", "seg_observaciones_",
)

_DATOS_LECHE = [
    "¿Sabías que la leche es uno de los alimentos más completos que existen?",
    "La crioscopía es vital para detectar si se añadió agua a la leche.",
    "Los sólidos totales determinan el rendimiento para la producción de leche en polvo.",
    "Una vaca lechera produce en promedio entre 20 y 35 litros de leche al día.",
    "La leche fresca debe conservarse por debajo de 4 °C para mantener su calidad.",
    "Colombia es uno de los principales productores de leche en América Latina.",
    "La acidez óptima de la leche fresca está entre 0.14 % y 0.18 % de ácido láctico.",
    "El contenido de grasa varía según la raza de la vaca y el tipo de alimentación.",
    "La leche contiene los 9 aminoácidos esenciales que el cuerpo humano no puede producir.",
]
