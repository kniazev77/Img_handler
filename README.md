# Img_handler

Tools to download product images (via HTTP or SFTP) and upload them to SQL Server.
The flow is simple: read a CSV with codes/URLs, download images to a local folder,
and then insert images and thumbnails into dbo.Imagen.

## Included flows

1) HTTP download from CSV URLs
- Script: descarga_imagenes.py
- Input: CSV with Codigo_Interno and columns Imagen 1..Imagen 6
- Output: local folder with images and an error CSV if failures occur

2) SFTP download from a remote server
- Script: descarga_imagenes_sftp.py
- Input: CSV with Codigo_Producto
- Output: local folder with images and a CSV error log

3) Upload to SQL Server
- Script: subir_imagenes.py
- Input: local folder with downloaded images
- Output: new rows in dbo.Imagen and a text log

## Requirements

- Windows 10/11
- Python 3.10+
- Microsoft ODBC Driver 17 (or 18) for SQL Server
- Access to a SQL Server with dbo.Imagen table
- Access to an SFTP server (only if using the SFTP flow)

## Installation

1) Create and activate a virtual environment (optional)

```
python -m venv .venv
.venv\Scripts\activate
```

2) Install dependencies

```
pip install requests tqdm paramiko pyodbc Pillow
```

## Configuration

### CLOUD03 environment variable

The SQL Server upload script reads the base connection string from CLOUD03.
Expected format (without the database name):

```
SERVER=your_server;UID=your_user;PWD=your_password
```

PowerShell example:

```
setx CLOUD03 "SERVER=sql01;UID=user;PWD=pass"
```

Notes:
- The script appends DATABASE and encryption options automatically.
- If you use ODBC Driver 18, you can change the driver in subir_imagenes.py.

### SFTP access

The descarga_imagenes_sftp.py script prompts in the console for:
- Server (host or URL)
- User
- Password
- Port (default 22)
- Remote images path

## Usage

### 1) HTTP download by CSV

```
python descarga_imagenes.py Descargar.csv
```

The script saves images in:

```
Imagenes Descargadas_2
```

If there are errors, it writes:

```
output_errores_descarga_YYYYMMDD_HHMM.csv
```

### 2) SFTP download by CSV

```
python descarga_imagenes_sftp.py
```

Inputs:
- productos_sftp.csv with column Codigo_Producto

Outputs:
- Imagenes_Descargadas_SFTP
- log_SFTP_YYYYMMDD.csv

Expected remote filename convention:
- The script filters names with the pattern: code_*_index.ext
- Example: 59975_anything_3.jpg -> saved as 59975[3].jpg

### 3) Upload images to SQL Server

Before running, make sure the images folder exists:

```
Imagenes Descargadas
```

Then:

```
python subir_imagenes.py
```

The script:
- Checks duplicates by Nombre
- Validates that the image is correct
- Generates a 256x256 PNG thumbnail
- Inserts into dbo.Imagen
- Writes results to logs_inserts.txt

## Input formats

### Descargar.csv (HTTP)

Expected headers:

```
Codigo_Interno,Imagen 1,Imagen 2,Imagen 3,Imagen 4,Imagen 5,Imagen 6
```

### productos_sftp.csv (SFTP)

Expected header:

```
Codigo_Producto
```

## Outputs and logs

- HTTP download: Imagenes Descargadas_2
- HTTP errors: output_errores_descarga_YYYYMMDD_HHMM.csv
- SFTP download: Imagenes_Descargadas_SFTP
- SFTP log: log_SFTP_YYYYMMDD.csv
- SQL insert log: logs_inserts.txt

## Troubleshooting

- "CLOUD03 is not defined": create the environment variable with the connection string.
- "Connection error": validate server, user, password, and installed ODBC driver.
- "Imagenes Descargadas folder does not exist": create it or move the images.
- SQL error about Usr_Creacion: check triggers or a customized dbo.Imagen schema.

## Notes

- For HTTP download, the output folder is "Imagenes Descargadas_2" but the upload uses
  "Imagenes Descargadas". Adjust the folder or rename it to match your flow.
- The scripts use timeouts and log failures for later review.
