#!/usr/bin/env python3
"""
Descarga imágenes listadas en un CSV y guarda las fallidas en
output_errores_descarga_<fecha>.csv, indicando el motivo de cada error.

Uso:
    python descarga_imagenes.py <ruta_csv>
"""
import csv
import sys
import pathlib
from datetime import datetime
from urllib.parse import urlparse

import requests
from tqdm import tqdm

# ---------- Configuración ----------
MAX_IMGS         = 6
IMG_COL_TEMPLATE = "Imagen {}"
ERR_COL_TEMPLATE = "Motivo {}"
DEST_FOLDER_NAME = "Imagenes Descargadas_2"
TIMEOUT_SEC      = 15
CHUNK_SIZE       = 65_536
HEADERS          = {"User-Agent": "img-downloader-Real2B/1.0"}
# -----------------------------------


def extension_from_url(url: str) -> str:
    ext = pathlib.Path(urlparse(url).path).suffix.lower()
    return ext or ".jpg"


def download_image(url: str, dest_path: pathlib.Path) -> tuple[bool, str | None]:
    """
    Devuelve (ok, motivo_error).  ok=True si se descargó.
    Si ok=False, motivo_error contiene HTTP xxx o el texto de excepción.
    """
    try:
        r = requests.get(url, timeout=TIMEOUT_SEC, stream=True, headers=HEADERS)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(CHUNK_SIZE):
                    f.write(chunk)
            return True, None
        motivo = f"HTTP {r.status_code}"
        print(f"[WARN] {url} → {motivo}")
        return False, motivo
    except requests.RequestException as e:
        motivo = type(e).__name__
        print(f"[ERROR] {url} → {e}")
        return False, motivo


def main(csv_path: pathlib.Path):
    if not csv_path.is_file():
        sys.exit(f"No se encontró el archivo: {csv_path}")

    script_dir = pathlib.Path(__file__).resolve().parent
    dest_root  = script_dir / DEST_FOLDER_NAME
    dest_root.mkdir(exist_ok=True)

    # Encabezados dinámicos
    img_headers  = [IMG_COL_TEMPLATE.format(i) for i in range(1, MAX_IMGS + 1)]
    err_headers  = [ERR_COL_TEMPLATE.format(i) for i in range(1, MAX_IMGS + 1)]
    header       = ["Codigo_Interno"] + img_headers + err_headers

    failed_rows  = {}   # code -> dict( header -> value )
    total_imgs   = 0
    rows         = []

    # ——— Leer CSV y contar imágenes ———
    with csv_path.open(newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            rows.append(row)
            total_imgs += sum(
                1 for col in img_headers if (row.get(col) or "").strip()
            )

    # ——— Descargar con barra de progreso ———
    ok = fail = 0
    with tqdm(total=total_imgs, desc="Descargando", unit="img") as pbar:
        for row in rows:
            code = row["Codigo_Interno"].strip()
            if not code:
                # Avanza tantos como URLs hubiese, pero sin procesar (no debería ocurrir)
                pbar.update(sum(1 for col in img_headers if (row.get(col) or "").strip()))
                continue

            img_index = 1
            for col_idx, col_name in enumerate(img_headers, start=1):
                url = (row.get(col_name) or "").strip()
                if not url:
                    continue

                filename  = f"{code}[{img_index:02d}]{extension_from_url(url)}"
                dest_file = dest_root / filename

                success, motivo = download_image(url, dest_file)
                if success:
                    ok += 1
                else:
                    fail += 1
                    # Crear fila de error si no existe
                    if code not in failed_rows:
                        failed_rows[code] = {h: "" for h in header}
                        failed_rows[code]["Codigo_Interno"] = code
                    failed_rows[code][col_name]              = url
                    failed_rows[code][ERR_COL_TEMPLATE.format(col_idx)] = motivo

                img_index += 1
                pbar.update(1)

    # ——— Guardar CSV de errores si los hubiera ———
    if failed_rows:
        ts        = datetime.now().strftime("%Y%m%d_%H%M")
        error_csv = script_dir / f"output_errores_descarga_{ts}.csv"
        with error_csv.open("w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(failed_rows.values())
        print(f"\nSe guardó el detalle de {fail} descargas fallidas en:\n{error_csv}")

    # ——— Resumen ———
    print("\n--- Resumen ---")
    print(f"Imágenes procesadas : {total_imgs}")
    print(f"Descargadas OK      : {ok}")
    print(f"Fallidas            : {fail}")
    print(f"Guardadas en        : {dest_root}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        csv_file = pathlib.Path(sys.argv[1])
    else:
        csv_file = pathlib.Path(input("Ruta al CSV: ").strip())
    main(csv_file)
