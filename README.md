# Etiquetas TECI

Sistema para procesar textos de productos, generar etiquetas imprimibles y preparar catálogo digital para antigüedades TECI.

El flujo principal es:

1. Procesar archivos `.txt` a `.json`.
2. Generar etiquetas front/back desde plantillas PSD.
3. Preparar PDFs de impresión.
4. Generar páginas de catálogo digital.
5. Exportar catálogo final a PDF.

---

## Comando principal

Desde la raíz del proyecto:

```powershell
python -m src.main
```

---

## Estructura del proyecto

```text
Etiquetas_Teci/
├── config/
│   └── catalogo_distribuciones.json
│
├── data/
│   ├── categorias/
│   │   └── <categoria>/
│   │       ├── 1.txt
│   │       ├── img/
│   │       ├── processed/
│   │       ├── etiquetas/
│   │       └── impresion/
│   │
│   ├── dev/
│   │   ├── raw_txt/
│   │   ├── img/
│   │   ├── processed/
│   │   ├── etiquetas/
│   │   └── impresion/
│   │
│   └── documentos/
│       ├── certificados/
│       └── fichas_tecnicas/
│
├── output/
│   ├── catalogo/
│   │   ├── paginas/
│   │   ├── tmp/
│   │   └── catalogo_final.pdf
│   │
│   └── impresion/
│       ├── carta/
│       ├── a4/
│       └── multi_categoria/
│
├── scripts/
│   ├── analizar_descripciones_catalogo.py
│   ├── reporte_descripciones.py
│   └── __init__.py
│
├── src/
│   ├── main.py
│   ├── core/
│   ├── texto/
│   ├── etiquetas/
│   └── catalogo/
│
├── templates/
│   ├── etiquetas/
│   └── catalogo/
│
├── config.example.json
├── config.json
├── .gitignore
└── README.md
```

---

## Carpetas principales

| Carpeta | Uso |
|---|---|
| `config/` | Configuración editable del catálogo y distribuciones. |
| `data/` | Textos, imágenes, JSON procesados y salidas por categoría. |
| `output/` | PDFs y páginas generadas globales. |
| `src/` | Código principal del sistema. |
| `scripts/` | Utilidades auxiliares de análisis o mantenimiento. |
| `templates/` | Plantillas PSD de etiquetas y catálogo. |

---

## Configuración local

El archivo activo es:

```text
config.json
```

Ejemplo:

```json
{
  "env": "DEV",
  "categoria": "1-muebles_europeos_importados",
  "paper": "carta",
  "draw_guides": false,
  "debug": true
}
```

`config.json` es local y no debe subirse a Git.  
El archivo compartible es:

```text
config.example.json
```

---

## Modos de trabajo

### DEV

Usa:

```text
data/dev/
```

Sirve para pruebas rápidas sin modificar producción.

### PROD

Usa:

```text
data/categorias/<categoria>/
```

Sirve para trabajar con una categoría real.

---

## Menú principal

```text
1. Procesar TXT a JSON
2. Generar etiquetas
3. Preparar PDF de impresión
4. Generar catálogo / exportar PDF
5. Validar proyecto
6. Validar catálogo
7. Configuración
0. Salir
```

---

## Comandos directos

Procesar TXT a JSON:

```powershell
python -m src.texto.procesador
```

Actualizar un ID:

```powershell
python -m src.texto.procesador --id 44
```

Actualizar varios IDs:

```powershell
python -m src.texto.procesador --ids 7,10,11,30
```

Generar etiquetas:

```powershell
python -m src.etiquetas.generar
```

Preparar impresión:

```powershell
python -m src.etiquetas.impresion
```

Generar catálogo:

```powershell
python -m src.catalogo.menu
```

Validar catálogo:

```powershell
python -m src.catalogo.validacion
```

Validar proyecto:

```powershell
python -m src.core.validacion
```

---

## Flujo recomendado

### 1. Configurar modo y categoría

Desde el menú principal:

```text
7. Configuración
```

Ahí se puede cambiar:

- DEV / PROD
- categoría activa
- papel de impresión
- guías
- debug

### 2. Procesar textos

```text
1. Procesar TXT a JSON
```

Esto lee los `.txt` y genera archivos `.json` en `processed/`.

### 3. Generar etiquetas

```text
2. Generar etiquetas
```

Esto crea imágenes front/back en la carpeta `etiquetas/`.

### 4. Preparar PDFs de impresión

```text
3. Preparar PDF de impresión
```

Esto genera PDFs listos para imprimir.

### 5. Generar catálogo

```text
4. Generar catálogo / exportar PDF
```

Esto genera páginas PNG y el PDF final del catálogo.

---

## Formato de imágenes por producto

En producción, cada producto debe tener su carpeta:

```text
data/categorias/<categoria>/img/ACT-0001/
├── principal.png
├── 1.png
├── 2.png
├── 3.png
└── ...
```

La imagen principal debe llamarse:

```text
principal.png
```

---

## Plantillas de etiquetas

```text
templates/etiquetas/
├── horizontal/
│   ├── small/
│   ├── large/
│   └── a5/
└── vertical/
    ├── small/
    ├── large/
    └── a5/
```

Cada carpeta debe contener:

```text
front.psd
back.psd
```

En etiquetas verticales A5 también puede existir:

```text
back-texto-largo.psd
```

---

## Plantillas de catálogo

Distribuciones:

```text
templates/catalogo/distribuciones/
```

Portadas:

```text
templates/catalogo/portadas/
```

La configuración de distribuciones se controla desde:

```text
config/catalogo_distribuciones.json
```

---

## Salidas generadas

Catálogo:

```text
output/catalogo/
```

Páginas del catálogo:

```text
output/catalogo/paginas/
```

Impresión global:

```text
output/impresion/
```

Impresión por categoría:

```text
data/categorias/<categoria>/impresion/
```

---

## Limpieza recomendada

Eliminar caché de Python:

```powershell
Get-ChildItem . -Recurse -Directory -Filter "__pycache__" |
Remove-Item -Recurse -Force

Get-ChildItem . -Recurse -File | Where-Object {
    $_.Extension -in ".pyc", ".pyo", ".pyd"
} | Remove-Item -Force
```

Eliminar logs temporales:

```powershell
Get-ChildItem . -Recurse -File -Filter "*.log" |
Remove-Item -Force
```

---

## Archivos que no deben subirse

No subir:

```text
config.json
data/
output/
__pycache__/
*.pyc
*.log
*.zip
```

---

## Estado actual

Versión reorganizada con estructura basada en `src/`.

El comando oficial del sistema es:

```powershell
python -m src.main
```