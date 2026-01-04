# Guía de Dependencias

Este documento explica qué archivo de dependencias usar y por qué.

## Archivos de Dependencias

### `requirements.txt` - Producción
**Cuándo usar:** Para entornos de producción y cuando construyas la imagen Docker.

**Contiene:**
- `gradio` - Framework para crear la interfaz web del panel de administración
- `chromadb` - Cliente Python para conectarse a ChromaDB
- `requests` - Necesario para el healthcheck de Docker

**Instalación:**
```bash
pip install -r requirements.txt
```

### `requirements-dev.txt` - Desarrollo
**Cuándo usar:** Para desarrollo local cuando quieras herramientas adicionales de testing, formateo y debugging.

**Contiene:**
- Todas las dependencias de `requirements.txt` (incluidas automáticamente)
- `pytest` y `pytest-cov` - Para testing y cobertura
- `black` - Formateador de código Python
- `flake8` - Linter de código Python
- `mypy` - Verificación de tipos estáticos
- `ipython` - REPL interactivo mejorado

**Instalación:**
```bash
pip install -r requirements-dev.txt
```

## ¿Cuál usar?

### Para Producción (Docker)
El Dockerfile usa automáticamente `requirements.txt`:
```dockerfile
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
```

### Para Desarrollo Local
Si desarrollas localmente (sin Docker), puedes usar:
- Solo producción: `pip install -r requirements.txt`
- Con herramientas de desarrollo: `pip install -r requirements-dev.txt`

### En Docker Compose
- **Producción:** Usa `requirements.txt` (definido en `docker/gradio/Dockerfile`)
- **Desarrollo:** Usa `requirements-dev.txt` (definido en `docker/gradio/Dockerfile.dev`)

## Dependencias NO Incluidas

Las siguientes dependencias fueron removidas porque no se usan en el código:

- ❌ `openai` - No se usa en el código actual

Si en el futuro necesitas usar OpenAI, agrégalo a `requirements.txt`.

## Verificar Dependencias

Para ver qué dependencias se usan realmente en el código:

```bash
# Ver imports en el código
grep -r "^import \|^from " src/

# Verificar dependencias instaladas
pip list
```


