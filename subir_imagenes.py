"""
Subir imágenes a dbo.Imagen con barra de progreso y chequeos extra.
Requiere: pyodbc, Pillow, tqdm
"""

import os
import re
import sys
import io
import datetime as dt
from pathlib import Path

import pyodbc
from PIL import Image
from tqdm import tqdm 

# ───────────────────────────────────────────────────────────────
# 1. Conexión
# ───────────────────────────────────────────────────────────────
conn_base = os.getenv("CLOUD03")
if not conn_base:
    sys.exit("❌  La variable de entorno 'CLOUD03' no está definida.")

db_name = input("Indique el nombre de la Base de Datos del Cliente: ").strip()
if not db_name:
    sys.exit("❌  Debes ingresar un nombre de base de datos.")

confirm = input(
    f"Se insertarán las imágenes al cliente {db_name.upper()}, "
    "ingrese ‘y’ para confirmar o ‘n’ para abortar ejecución: "
).lower()
if confirm != "y":
    sys.exit("Operación cancelada por el usuario.")

# Driver 17 (cambias a 18 si lo instalas)
driver_tag = "ODBC Driver 17 for SQL Server"

conn_str = (
    f"DRIVER={{{driver_tag}}};"
    f"{conn_base};"
    f"DATABASE={db_name};"
    "Encrypt=yes;TrustServerCertificate=yes;"
)

try:
    cnxn = pyodbc.connect(conn_str, autocommit=False)
except pyodbc.Error as exc:
    sys.exit(f"❌  Error de conexión: {exc}")

# ➋ MOSTRAR MENSAJE DE CONEXIÓN OK
m = re.search(r"SERVER=([^;]+)", conn_base, re.I)
srv = m.group(1) if m else "<desconocido>"
print(f"✅  Conexión al servidor {srv} realizada con éxito.")

# ➌ VERIFICAR QUE ESTAMOS EN LA DB CORRECTA
with cnxn.cursor() as cur:
    cur.execute("SELECT DB_NAME()")
    current_db = cur.fetchone()[0]
if current_db.lower() != db_name.lower():
    cnxn.close()
    sys.exit(
        f"❌  La conexión apunta a {current_db}, no a {db_name}. "
        "Revisa la variable CLOUD03 o el nombre ingresado."
    )

cursor = cnxn.cursor()

# ───────────────────────────────────────────────────────────────
# 2. Rutas y log
# ───────────────────────────────────────────────────────────────
root_dir   = Path(__file__).resolve().parent
images_dir = root_dir / "Imagenes Descargadas"
if not images_dir.is_dir():
    sys.exit(f"❌  La carpeta '{images_dir}' no existe.")

log_path = root_dir / "logs_inserts.txt"
log_file = log_path.open("a", encoding="utf-8")

# ───────────────────────────────────────────────────────────────
# 3. Consultas
# ───────────────────────────────────────────────────────────────
SQL_EXISTE = "SELECT 1 FROM dbo.Imagen WHERE Nombre = ?;"
SQL_INSERT = """
INSERT INTO dbo.Imagen
       (Nombre, Dato4, Imagen_URL, Formato, Thumbnail, Imagen,
        Fecha_Creacion, Usr_Creacion)
VALUES (?, 'PRODUCTO', NULL, 0, ?, ?, GETDATE(), 1);
"""

# ───────────────────────────────────────────────────────────────
# 4. Procesamiento con barra de progreso
# ───────────────────────────────────────────────────────────────
FORMATOS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
archivos = [p for p in images_dir.iterdir() if p.suffix.lower() in FORMATOS]

total, insertados, duplicados, fallidos = 0, 0, 0, 0

for img_path in tqdm(archivos, desc="Subiendo imágenes"):   # ➍ NUEVO
    total += 1
    nombre = img_path.stem

    # Duplicados
    cursor.execute(SQL_EXISTE, nombre)
    if cursor.fetchone():
        duplicados += 1
        log_file.write(f"{dt.datetime.now()}: {nombre} – duplicado, se salta.\n")
        continue

    # Leer/validar + thumbnail
    try:
        with Image.open(img_path) as im:
            im.verify()
        with Image.open(img_path) as im_full:
            bytes_full = img_path.read_bytes()
            im_full.thumbnail((256, 256))
            thumb_buf = io.BytesIO()
            im_full.save(thumb_buf, format="PNG")
            bytes_thumb = thumb_buf.getvalue()
    except Exception as e:
        fallidos += 1
        log_file.write(f"{dt.datetime.now()}: {nombre} – error de imagen: {e}\n")
        continue

    # Insert
    try:
        cursor.execute(SQL_INSERT, nombre, bytes_thumb, bytes_full)
        cnxn.commit()
        insertados += 1
        log_file.write(f"{dt.datetime.now()}: {nombre} – insert OK.\n")
    except Exception as e:
        cnxn.rollback()
        fallidos += 1
        log_file.write(f"{dt.datetime.now()}: {nombre} – error SQL: {e}\n")

# ───────────────────────────────────────────────────────────────
# 5. Cierre
# ───────────────────────────────────────────────────────────────
cursor.close(); cnxn.close(); log_file.close()

print(
    f"\nProceso finalizado: {insertados} insertados – "
    f"{duplicados} duplicados – {fallidos} errores – "
    f"{total} archivos revisados.\n"
    f"Revisa el log en: {log_path}"
)