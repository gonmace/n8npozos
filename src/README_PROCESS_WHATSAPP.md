# Procesador de Archivos de WhatsApp

Script Python para procesar archivos de chat de WhatsApp y convertirlos en formato estructurado con etiquetas `ai:` y `user:`.

## Descripción

Este script procesa archivos de chat exportados de WhatsApp y:
1. Elimina la primera línea que contiene el texto de la empresa
2. Identifica si cada línea pertenece a la empresa o al usuario
3. Reemplaza las líneas de la empresa con `ai: [mensaje]`
4. Reemplaza las líneas del usuario con `user: [mensaje]`

## Uso

```bash
python process_whatsapp.py "texto_empresa" "telefono" archivo_entrada.txt [archivo_salida.txt]
```

### Parámetros

1. **texto_empresa** (entre comillas): Texto que identifica a la empresa en el chat
   - Ejemplo: `"Limpieza de pozos:"`
   - Este texto se usa para identificar mensajes de la empresa

2. **telefono** (entre comillas): Número de teléfono del usuario
   - Ejemplo: `"+591 69023378"`
   - Este número se usa para identificar mensajes del usuario

3. **archivo_entrada.txt**: Ruta al archivo de WhatsApp a procesar

4. **archivo_salida.txt** (opcional): Ruta donde guardar el archivo procesado
   - Si no se especifica, se crea automáticamente como `[nombre_original]_procesado.txt`

### Ejemplos

#### Ejemplo 1: Procesamiento básico
```bash
python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" chat.txt
```

Esto creará un archivo `chat_procesado.txt` con el resultado.

#### Ejemplo 2: Especificando archivo de salida
```bash
python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" chat.txt resultado.txt
```

#### Ejemplo 3: Con ruta completa (Windows)
```bash
python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" "C:\Users\gonma\Desktop\ppp\chats\Chat de WhatsApp con +591 69023378.txt"
```

#### Ejemplo 4: Con ruta completa (Linux/Mac)
```bash
python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" "/home/usuario/chats/chat.txt"
```

## Formato de Entrada

El script espera archivos en el formato estándar de exportación de WhatsApp:

```
[DD/MM/YYYY, HH:MM:SS AM/PM] - Nombre Empresa: Mensaje de la empresa
[DD/MM/YYYY, HH:MM:SS AM/PM] - +591 69023378: Mensaje del usuario
```

## Formato de Salida

El archivo procesado tendrá el siguiente formato:

```
ai: Mensaje de la empresa
user: Mensaje del usuario
ai: Otro mensaje de la empresa
user: Respuesta del usuario
```

## Características

- ✅ Elimina automáticamente la primera línea que contiene el texto de la empresa
- ✅ Identifica mensajes de empresa y usuario basándose en el texto y teléfono proporcionados
- ✅ Extrae solo el contenido del mensaje (sin fecha, hora, nombre)
- ✅ Maneja diferentes formatos de números de teléfono
- ✅ Soporta codificación UTF-8 y maneja errores de codificación
- ✅ Proporciona información detallada durante el procesamiento

## Requisitos

- Python 3.6 o superior
- No requiere dependencias externas (usa solo librerías estándar)

## Notas

- El script busca el texto de la empresa de forma case-insensitive (no distingue mayúsculas/minúsculas)
- El teléfono se busca en diferentes formatos (con/sin espacios, con/sin +, etc.)
- Si una línea no se puede identificar claramente, se mantiene como está o se marca como `user:` por defecto
- Las líneas vacías se mantienen en el archivo de salida

## Solución de Problemas

### Error: "El archivo no existe"
- Verifica que la ruta del archivo sea correcta
- En Windows, usa comillas dobles alrededor de rutas con espacios
- Usa barras invertidas (`\`) en Windows o barras normales (`/`) en Linux/Mac

### No identifica correctamente los mensajes
- Asegúrate de que el texto de la empresa coincida exactamente con el que aparece en el chat
- Verifica que el número de teléfono sea correcto
- El script busca variantes del teléfono (con/sin espacios, +, etc.)

### Caracteres especiales no se muestran correctamente
- El script usa UTF-8 por defecto
- Si hay problemas, verifica la codificación del archivo original

## Ejemplo Completo

```bash
# 1. Navegar al directorio del script
cd src

# 2. Ejecutar el procesamiento
python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" "C:\Users\gonma\Desktop\ppp\chats\Chat de WhatsApp con +591 69023378.txt"

# 3. El resultado se guardará en:
# "C:\Users\gonma\Desktop\ppp\chats\Chat de WhatsApp con +591 69023378_procesado.txt"
```
