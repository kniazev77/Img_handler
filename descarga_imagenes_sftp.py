#!/usr/bin/env python3
"""
Descarga imágenes desde un servidor SFTP según un CSV,
con timeout de 30 s para la conexión y para cada descarga individual,
y logging de errores por código de producto.
"""

import os
import csv
import sys
import datetime
import socket
import paramiko
from tqdm import tqdm

def main():
    print("1) Iniciando script...")

    # 2) Parámetros
    raw = input("2) Servidor SFTP (ej. comercios.fenicio.app): ").strip()
    servidor = raw.split("://", 1)[-1].split("/")[0]
    usuario = input("3) Usuario SFTP: ").strip()
    clave = input("Contraseña SFTP: ")
    puerto_input = input("5) Puerto SFTP (si no conoces usa 22): ").strip()
    puerto = int(puerto_input) if puerto_input else 22
    ruta_remota = input("6) Ruta remota de imágenes: ").strip()
    print("   → Parámetros recibidos.")

    # 7) Leer CSV de códigos
    csv_file = "productos_sftp.csv"
    print(f"7) Leyendo CSV '{csv_file}'...")
    if not os.path.isfile(csv_file):
        print(f"   ❌ No existe '{csv_file}'.")
        sys.exit(1)

    codigos = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            code = row.get("Codigo_Producto")
            if code:
                codigos.append(code.strip())
    print(f"   ✓ {len(codigos)} códigos cargados.")
    if not codigos:
        print("   ❌ No hay códigos en el CSV.")
        sys.exit(1)

    # 8) Preparar carpeta destino y log
    carpeta_dest = "Imagenes_Descargadas_SFTP"
    os.makedirs(carpeta_dest, exist_ok=True)
    fecha_str = datetime.datetime.now().strftime("%Y%m%d")
    log_file = f"log_SFTP_{fecha_str}.csv"
    with open(log_file, "w", newline="", encoding="utf-8") as lf:
        csv.writer(lf).writerow(["Codigo_Producto", "Error"])
    print(f"8) Carpeta '{carpeta_dest}' y log '{log_file}' preparados.")

    # 9) Conexión SFTP con timeout de 30 s
    print("9) Conectando al SFTP (timeout 30 s)...")
    try:
        sock = socket.create_connection((servidor, puerto), timeout=30)
        transport = paramiko.Transport(sock)
        transport.connect(username=usuario, password=clave)
        sftp = paramiko.SFTPClient.from_transport(transport)
        # para que cada operación SFTP use 30 s de timeout
        transport.sock.settimeout(30)
        print("   ✓ Conexión SFTP establecida.")
    except (socket.timeout, socket.error) as e:
        print(f"   ❌ Timeout/error conectando al SFTP: {e}")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"   ❌ SSH error: {e}")
        sys.exit(1)

    # 10) Listar carpeta remota
    print(f"10) Listando '{ruta_remota}'...")
    try:
        todos_archivos = sftp.listdir(ruta_remota)
        print("   ✓ Listado obtenido.")
    except Exception as e:
        print(f"   ❌ Error listando ruta: {e}")
        transport.close()
        sys.exit(1)

    # 11) Filtrar archivos a descargar
    to_download = []
    for code in codigos:
        for fn in todos_archivos:
            if fn.startswith(f"{code}_") and fn.count("_") == 2:
                to_download.append((code, fn))
    print(f"11) {len(to_download)} archivos preparados para descarga.")

    if not to_download:
        print("   ℹ️  No hay imágenes para descargar. Saliendo.")
        transport.close()
        sys.exit(0)

    # 12) Descargar con timeout por archivo
    print("12) Iniciando descargas…")
    for code, fn in tqdm(to_download, desc="Descargando"):
        remoto_path = f"{ruta_remota.rstrip('/')}/{fn}"
        parts = fn.split("_")
        main = parts[0]
        last = parts[2]                       # e.g. "3.jpg"
        index = os.path.splitext(last)[0]     # "3"
        ext = os.path.splitext(last)[1]       # ".jpg"
        local_path = os.path.join(carpeta_dest, f"{main}[{index}]{ext}")

        try:
            sftp.get(remoto_path, local_path)
        except socket.timeout:
            with open(log_file, "a", newline="", encoding="utf-8") as lf:
                csv.writer(lf).writerow([code, f"{fn}: timeout de 30s"])
            continue
        except Exception as e:
            with open(log_file, "a", newline="", encoding="utf-8") as lf:
                csv.writer(lf).writerow([code, f"{fn}: {e}"])
            continue

    transport.close()
    print("13) Proceso completado. Revisa la carpeta y el log para ver errores.")


if __name__ == "__main__":
    main()