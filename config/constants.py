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
    # ── Datos curiosos ────────────────────────────────────────────────
    "¿Sabías que la leche es uno de los alimentos más completos que existen?",
    "La leche contiene los 9 aminoácidos esenciales que el cuerpo humano no puede producir.",
    "Una vaca lechera produce en promedio entre 20 y 35 litros de leche al día.",
    "Una vaca de alta producción puede llegar a dar más de 50 litros diarios en pico de lactancia.",
    "Para producir 1 kg de queso se necesitan aproximadamente 10 litros de leche.",
    "Para 1 kg de mantequilla se requieren cerca de 22 litros de leche.",
    "Para 1 kg de leche en polvo entera se necesitan unos 8 litros de leche líquida.",
    "La leche está compuesta en un 87 % por agua y 13 % por sólidos totales.",
    "Colombia produce alrededor de 7.500 millones de litros de leche al año.",
    "El consumo promedio de leche por colombiano es cercano a 145 litros per cápita anuales.",
    "Antioquia, Cundinamarca, Boyacá y Nariño concentran más del 60 % de la producción nacional.",
    "La raza Holstein es la más usada en trópico alto colombiano por su alto volumen de producción.",
    "En trópico bajo predominan razas como Gyr, Pardo Suizo y cruces F1 (Holstein × Gyr).",
    "El calostro es la primera leche post-parto y aporta inmunoglobulinas vitales para el ternero.",
    "El color de la leche se debe a la dispersión de la luz en la grasa y la caseína.",
    "El sabor ligeramente dulce de la leche proviene de la lactosa, su principal carbohidrato.",

    # ── Generalidades técnicas ────────────────────────────────────────
    "La crioscopía es vital para detectar si se añadió agua a la leche.",
    "El punto crioscópico normal de la leche cruda está entre -0,530 °C y -0,560 °C (escala Hortvet).",
    "Los sólidos totales determinan el rendimiento para la producción de leche en polvo.",
    "La leche fresca debe conservarse por debajo de 4 °C para mantener su calidad.",
    "La acidez óptima de la leche fresca está entre 0,14 % y 0,18 % de ácido láctico.",
    "El pH normal de la leche cruda está entre 6,6 y 6,8.",
    "Una densidad menor a 1,028 g/mL puede indicar adición de agua.",
    "El contenido de grasa varía según la raza de la vaca y el tipo de alimentación.",
    "La prueba de alcohol detecta inestabilidad proteica por acidez o desbalance mineral.",
    "La presencia de cloruros elevados puede indicar mastitis subclínica.",
    "La detección de neutralizantes (carbonatos, bicarbonatos) revela adulteración para enmascarar acidez.",
    "El recuento de células somáticas (RCS) es el indicador más confiable de salud de la ubre.",
    "La pasteurización HTST trata la leche a 72-75 °C durante 15-20 segundos.",
    "La esterilización UHT eleva la temperatura a 135-150 °C durante 2-4 segundos.",
    "El termizado (57-68 °C por 15 s) reduce la carga microbiana sin destruir enzimas nativas.",
    "La cadena de frío en transporte debe mantener la leche entre 2 °C y 6 °C.",
    "El proceso CIP (Clean In Place) garantiza la higiene de tanques y tuberías sin desmontaje.",

    # ── Normatividad colombiana ───────────────────────────────────────
    "Decreto 616 de 2006: reglamento técnico sobre leche cruda y productos lácteos en Colombia.",
    "El Decreto 616/2006 establece los requisitos sanitarios para producción, transporte y comercialización de leche.",
    "Resolución 017 de 2012 del MADR: sistema de pago de leche cruda al productor por calidad e higiene.",
    "Resolución 077 de 2024 del MADR: actualizó la fórmula de pago de leche al productor en Colombia.",
    "El pago por calidad bonifica grasa, proteína, sólidos totales y baja carga bacteriana (UFC).",
    "El pago por higiene se basa en el recuento total de bacterias (UFC/mL) y células somáticas (CCS/mL).",
    "Resolución 2674 de 2013 del MinSalud: requisitos sanitarios para alimentos, incluida la leche procesada.",
    "Resolución 333 de 2011 del MinSalud: rotulado y etiquetado nutricional de alimentos envasados.",
    "Resolución 810 de 2021 del MinSalud: etiquetado frontal de advertencia (sellos octagonales).",
    "Decreto 1880 de 2011: comercialización de leche cruda para consumo humano directo bajo condiciones específicas.",
    "Resolución 003585 de 2008 del ICA: medidas sanitarias para predios productores de leche.",
    "El INVIMA es la autoridad sanitaria que vigila plantas pasteurizadoras y productos lácteos en Colombia.",
    "El ICA certifica los Hatos Libres de Brucelosis y Tuberculosis bovina, requisito para acopio formal.",
    "La leche cruda destinada a planta debe enfriarse a ≤ 4 °C dentro de las 2 horas siguientes al ordeño.",
    "El transporte de leche cruda requiere carrotanques isotérmicos en acero inoxidable según Decreto 616.",
    "La densidad mínima exigida por el Decreto 616 es 1,030 g/mL a 15 °C para leche entera cruda.",
    "El Decreto 616 fija un mínimo de 3,0 % de grasa y 8,3 % de sólidos no grasos para leche entera cruda.",
    "La proteína mínima exigida por norma colombiana es 2,9 % m/m en leche cruda.",
    "Resolución 1382 de 2013 del MinSalud: límites máximos de aflatoxina M1 en leche y derivados (0,5 µg/kg).",
    "Norma NTC 399: requisitos fisicoquímicos de la leche cruda en Colombia (referencia ICONTEC).",
    "Norma NTC 4978: método de referencia para determinación de punto crioscópico en leche.",
    "Norma NTC 750: requisitos para leche pasteurizada destinada al consumo humano.",
]
