# 🚀 Guía de Deployment en VPS

Esta guía te ayudará a desplegar el proyecto en tu VPS, incluyendo la migración de los datos de ChromaDB.

## 📋 Prerrequisitos

En el VPS necesitas tener instalado:
- Docker y Docker Compose
- Git
- Acceso SSH al VPS

## 🔄 Proceso de Deployment

### Paso 1: Exportar datos de ChromaDB desde tu servidor local

En tu máquina local (donde tienes los datos de ChromaDB):

```bash
# 1. Exportar el volumen de ChromaDB
./scripts/export-chroma.sh

# Esto creará un archivo en ./chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz
```

### Paso 2: Transferir datos al VPS

Tienes varias opciones para transferir el backup:

#### Opción A: Usando SCP
```bash
scp ./chroma-backup/chroma_*.tar.gz usuario@tu-vps:/ruta/destino/
```

#### Opción B: Usando RSYNC (más eficiente para archivos grandes)
```bash
rsync -avz --progress ./chroma-backup/chroma_*.tar.gz usuario@tu-vps:/ruta/destino/
```

#### Opción C: Usando un servicio de almacenamiento (Google Drive, Dropbox, etc.)
1. Sube el archivo a tu servicio de almacenamiento
2. Descárgalo en el VPS

### Paso 3: Clonar/Actualizar el repositorio en el VPS

En el VPS:

```bash
# Si es la primera vez, clona el repositorio
git clone <tu-repo-url> n8n
cd n8n

# Si ya existe el proyecto, actualiza el código
git pull origin main  # o la rama que uses
```

### Paso 4: Configurar variables de entorno

```bash
# Crear archivo .env si no existe
cp .env.example .env  # Si tienes un ejemplo, o créalo manualmente

# Editar .env con tus valores de producción
nano .env
```

**Variables importantes a configurar:**
```bash
# PostgreSQL
POSTGRES_USER=magoreal
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_DB=n8n

# N8N
N8N_ENCRYPTION_KEY=tu_clave_de_encriptacion
N8N_USER_MANAGEMENT_JWT_SECRET=tu_jwt_secret
N8N_HOST=tu-dominio.com

# ChromaDB (en Docker, usar nombres de servicio)
CHROMA_HOST=chroma
CHROMA_PORT=8000
CHROMA_COLLECTION=pozos

# Gradio
GRADIO_AUTH_USERNAME=admin
GRADIO_AUTH_PASSWORD=tu_password_seguro
ENV=production
DEBUG=false

# OpenAI (para embeddings)
OPENAI_API_KEY=tu_api_key_de_openai
EMBEDDING_MODEL=text-embedding-3-large
```

### Paso 5: Importar datos de ChromaDB

**⚠️ IMPORTANTE:** NO inicies los servicios Docker antes de importar los datos. El script de importación maneja todo automáticamente.

```bash
# Importar el volumen de ChromaDB desde el backup
./scripts/import-chroma.sh /ruta/al/backup/chroma_YYYYMMDD_HHMMSS.tar.gz
```

**¿Qué hace el script?**
- ✅ Detiene ChromaDB si está corriendo
- ✅ Elimina contenedores y volúmenes existentes (con confirmación)
- ✅ Crea un nuevo volumen
- ✅ Restaura los datos desde el backup

**Orden correcto:**
1. **Primero**: Importar los datos (el script crea el volumen automáticamente)
2. **Después**: Iniciar los servicios con `make prod`

### Paso 6: Construir y desplegar

```bash
# Construir las imágenes Docker
make build
# O si quieres reconstruir sin cache:
make rebuild

# Iniciar todos los servicios
make prod
```

### Paso 7: Verificar el despliegue

```bash
# Ver logs de todos los servicios
make logs

# Ver logs de un servicio específico
make logs-gradio
make logs-api
make logs-n8n

# Verificar que los servicios están corriendo
docker ps
```

### Paso 8: Verificar que ChromaDB tiene los datos

```bash
# Verificar que ChromaDB está respondiendo
curl http://localhost:8008/api/v2/heartbeat

# O acceder a Gradio y verificar que las colecciones están disponibles
# http://tu-vps:7860
```

## 🔄 Actualización Futura (sin migrar datos)

Para actualizar el código sin migrar datos de ChromaDB:

```bash
# 1. Actualizar código
git pull origin main

# 2. Reconstruir imágenes si hay cambios en Dockerfiles
make rebuild

# 3. Reiniciar servicios
make stop ENV=production
make prod
```

## 📦 Backup Regular

Es recomendable hacer backups regulares en producción:

```bash
# Crear backup de todos los volúmenes
make backup

# Los backups se guardan en ./backups/
```

## 🐛 Troubleshooting

### ChromaDB no inicia correctamente

```bash
# Ver logs de ChromaDB
docker logs chroma

# Verificar permisos del volumen
docker volume inspect chroma_storage
```

### Los datos no aparecen después de importar

1. Verifica que el archivo de backup se transfirió correctamente:
   ```bash
   ls -lh /ruta/al/backup/chroma_*.tar.gz
   ```

2. Verifica que el volumen se restauró:
   ```bash
   docker run --rm -v chroma_storage:/data alpine ls -la /data
   ```

3. Verifica los logs de ChromaDB:
   ```bash
   docker logs chroma
   ```

### Puerto ocupado

Si un puerto está ocupado, puedes:
- Detener el servicio que lo usa
- Cambiar el puerto en `docker-compose.yml`
- Usar un reverse proxy (nginx) para manejar múltiples servicios

## 🔒 Seguridad en Producción

1. **Cambiar todas las contraseñas por defecto**
2. **Usar HTTPS** con un reverse proxy (nginx, traefik)
3. **Configurar firewall** para exponer solo los puertos necesarios
4. **Hacer backups regulares**
5. **Mantener Docker y las imágenes actualizadas**

## 📝 Notas Importantes

- Los volúmenes de Docker persisten los datos entre reinicios
- Si necesitas mover datos entre servidores, usa los scripts de export/import
- El volumen `chroma_storage` contiene todos tus embeddings, así que mantenlo seguro
- Considera usar un servicio de backup automatizado para producción

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs: `make logs`
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de que Docker tiene suficientes recursos (memoria, disco)
