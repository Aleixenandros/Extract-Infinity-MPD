# Extract-Infinity-MPD
Extrae manifiestos MPD/M3U8 de Mediaset Infinity y genera el comando para descargar con yt-dlp

El script utiliza Selenium para analizar el tráfico de red del reproductor, acepta las cookies, bloquea anuncios y detecta el MPD del vídeo.

---

## Características

- Detección automática de manifiestos **MPD** y **M3U8**
- Bloqueo de anuncios
- Aceptación automática de cookies
- Generación directa del comando `yt-dlp`
- Limpieza del título para usarlo como nombre de archivo

---

## Requisitos

- Python **3.8 o superior**
- Google Chrome o Chromium instalado
- yl-dp para la descarga del vídeo a partir del m3u8

---

## Instalación

Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/Extract-Infinity-MPD.git
cd Extract-Infinity-MPD
chmod +755 extraer_mpd.py
```

### Instala las dependencias de Python:

```bash
pip install -r requirements.txt
```
## Ejemplos de uso

```bash
python3 SCRIPT + URL
python3 extraer_mpd.py https://www.mediasetinfinity.es/...
```
