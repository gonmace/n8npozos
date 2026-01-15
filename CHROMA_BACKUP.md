# 📦 Guía de Backup y Restauración de ChromaDB

## 🔄 Proceso Completo: Local → VPS

Ahora ChromaDB usa un **bind mount** (`./chroma_storage`) en lugar de un volumen Docker, lo que hace el backup mucho más simple.

### Paso 1: Exportar ChromaDB en Local

```bash
# En tu máquina local (donde está ChromaDB con los datos)
cd /home/gonzalo/n8n

# Exportar el directorio de ChromaDB
./scripts/export-chroma.sh

# El backup se creará en: ./chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz
```

**Nota:** El script automáticamente:
- Detecta el directorio `./chroma_storage`
- Detiene el contenedor temporalmente (para consistencia)
- Crea un archivo `.tar.gz` con todos los datos
- Reinicia el contenedor

### Paso 2: Transferir el Backup al VPS

**Opción A: Usando `scp` (simple)**

```bash
# Desde tu máquina local
scp ./chroma-backup/chroma_*.tar.gz magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma-backup/
```

**Opción B: Usando `rsync` (recomendado - más eficiente)**

```bash
# Desde tu máquina local
rsync -avz --progress ./chroma-backup/chroma_*.tar.gz magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma-backup/
```

**Opción C: Transferir directamente el directorio (sin comprimir)**

```bash
# Desde tu máquina local (más rápido si tienes buena conexión)
rsync -avz --progress ./chroma_storage/ magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma_storage/
```

### Paso 3: Importar en el VPS

```bash
# Conectarte al VPS
ssh magoreal@vmi2527689.contaboserver.net

# Ir al directorio del proyecto
cd ~/n8n_pozos

# Detener servicios antes de importar (importante!)
make stop ENV=production
# O directamente:
docker compose --env-file .env -f deploy/docker-compose.yml down

# Importar el backup
./scripts/import-chroma.sh ./chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz

# Reiniciar servicios
make prod
```

## 📋 Comandos Rápidos

### En Local (Exportar)

```bash
cd /home/gonzalo/n8n

# Crear backup
./scripts/export-chroma.sh

# Ver el backup creado
ls -lh ./chroma-backup/

# Ver tamaño del directorio original
du -sh ./chroma_storage/
```

### Transferir al VPS

```bash
# Reemplaza YYYYMMDD_HHMMSS con la fecha real del backup
rsync -avz --progress ./chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz \
  magoreal@vmi2527689.contaboserver.net:~/n8n_pozos/chroma-backup/
```

### En VPS (Importar)

```bash
ssh magoreal@vmi2527689.contaboserver.net
cd ~/n8n_pozos
make stop ENV=production
./scripts/import-chroma.sh ./chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz
make prod
```

## 🔄 Migración desde Volumen Docker a Bind Mount

Si ya tienes datos en un volumen Docker y quieres migrar a bind mount:

### En Local

```bash
# 1. Detener ChromaDB
docker stop n8npozos-chroma

# 2. Exportar desde volumen Docker
docker run --rm \
  -v chroma_storage:/data:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/chroma_storage_from_volume.tar.gz -C /data .

# 3. Crear directorio y extraer
mkdir -p chroma_storage
tar xzf chroma_storage_from_volume.tar.gz -C chroma_storage

# 4. Actualizar docker-compose.yml (ya está hecho)
# 5. Reiniciar servicios
make prod
```

### En VPS

```bash
# Mismo proceso que arriba, pero en el VPS
```

## ⚠️ Advertencias Importantes

1. **Detener servicios antes de importar:** El script `import-chroma.sh` detiene ChromaDB, pero es mejor detener todos los servicios primero.

2. **El import sobrescribe datos existentes:** Si ya hay datos en ChromaDB en producción, se perderán. El script te pedirá confirmación.

3. **Verificar el tamaño del backup:** Asegúrate de que el archivo se transfirió completamente:
   ```bash
   # En local
   ls -lh ./chroma-backup/chroma_*.tar.gz
   
   # En VPS (después de transferir)
   ls -lh ~/n8n_pozos/chroma-backup/chroma_*.tar.gz
   ```

4. **Verificar que ChromaDB funciona después del import:**
   ```bash
   # En VPS
   docker logs n8npozos-chroma
   # O acceder a Gradio y verificar que las colecciones están disponibles
   ```

## 🔍 Verificar el Backup

### Verificar en Local

```bash
# Ver el tamaño del backup
du -h ./chroma-backup/chroma_*.tar.gz

# Ver el tamaño del directorio original
du -sh ./chroma_storage/

# Ver el contenido (sin extraer)
tar -tzf ./chroma-backup/chroma_*.tar.gz | head -20
```

### Verificar en VPS (después de importar)

```bash
# Ver logs de ChromaDB
docker logs n8npozos-chroma

# Verificar que el directorio tiene datos
ls -lh ./chroma_storage/
du -sh ./chroma_storage/

# Acceder a Gradio y verificar colecciones
# http://tu-vps:7860
```

## 🐛 Troubleshooting

### Error: "Directorio de ChromaDB no encontrado"

**En Local:**
```bash
# Verificar que el directorio existe
ls -la ./chroma_storage/

# Si ChromaDB no está corriendo, iniciarlo primero
docker compose --env-file .env -f deploy/docker-compose.yml up -d chroma

# Esperar a que se inicialice y luego hacer backup
sleep 5
./scripts/export-chroma.sh
```

**En VPS:**
```bash
# Verificar que el directorio existe después del import
ls -la ~/n8n_pozos/chroma_storage/
```

### Error: "Archivo de backup no encontrado"

```bash
# Verificar que el archivo existe
ls -lh ~/n8n_pozos/chroma-backup/

# Usar ruta absoluta si es necesario
./scripts/import-chroma.sh /home/magoreal/n8n_pozos/chroma-backup/chroma_YYYYMMDD_HHMMSS.tar.gz
```

### ChromaDB no inicia después del import

```bash
# Ver logs detallados
docker logs n8npozos-chroma

# Verificar permisos del directorio
ls -la ./chroma_storage/

# Asegurar permisos correctos
chmod -R 755 ./chroma_storage/

# Reiniciar el contenedor
docker restart n8npozos-chroma
```

## 💡 Ventajas del Bind Mount

- ✅ **Más simple:** Solo copiar un directorio
- ✅ **Más transparente:** Puedes ver los archivos directamente
- ✅ **Más fácil de hacer backup:** `tar czf` en lugar de manipular volúmenes Docker
- ✅ **Más fácil de transferir:** `rsync` directo del directorio
- ✅ **Más fácil de restaurar:** Solo extraer el tar.gz
