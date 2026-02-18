#!/usr/bin/env python3
"""
Script para procesar archivos de chat de WhatsApp y convertirlos en formato estructurado.

Uso:
    python process_whatsapp.py "texto_empresa" "telefono" archivo_entrada.txt [archivo_salida.txt]

Ejemplo:
    python process_whatsapp.py "Limpieza de pozos:" "+591 69023378" chat.txt chat_procesado.txt
"""

import sys
import re
import os
from typing import Optional


def identificar_tipo_linea(linea: str, texto_empresa: str, telefono: str) -> Optional[str]:
    """
    Identifica si una línea pertenece a la empresa o al usuario.
    
    Args:
        linea: Línea del archivo a analizar
        texto_empresa: Texto que identifica a la empresa
        telefono: Número de teléfono del usuario
        
    Returns:
        'empresa' si la línea es de la empresa
        'usuario' si la línea es del usuario
        None si no se puede determinar
    """
    linea_lower = linea.lower()
    texto_empresa_lower = texto_empresa.lower().strip()
    telefono_limpio = re.sub(r'[\s\+\-\(\)]', '', telefono)
    
    # Preparar variantes del teléfono para búsqueda
    telefono_variantes = [
        telefono.strip(),
        telefono_limpio,
        telefono.replace('+', '').replace(' ', '').strip(),
        telefono.replace('+', '').replace('-', '').replace(' ', '').strip(),
        telefono.replace('+', '').replace(' ', '').replace('(', '').replace(')', '').strip(),
    ]
    # Filtrar variantes muy cortas
    telefono_variantes = [t for t in telefono_variantes if len(t) >= 6]
    
    # Buscar patrones comunes de WhatsApp
    # Formato: [fecha hora] - Nombre: mensaje
    patron_whatsapp = r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]?M?\]\s*-\s*([^:]+):\s*(.+)'
    match = re.match(patron_whatsapp, linea)
    
    if match:
        nombre = match.group(1).strip()
        mensaje = match.group(2).strip()
        nombre_sin_espacios = nombre.replace(' ', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Prioridad 1: Si el nombre contiene el texto de la empresa, es empresa
        if texto_empresa_lower in nombre.lower():
            return 'empresa'
        
        # Prioridad 2: Si el nombre contiene el teléfono, es usuario
        for tel_var in telefono_variantes:
            tel_var_sin_espacios = tel_var.replace(' ', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
            if tel_var_sin_espacios in nombre_sin_espacios or tel_var_sin_espacios in nombre:
                return 'usuario'
        
        # Prioridad 3: Si el mensaje contiene el texto de la empresa (puede ser respuesta)
        if texto_empresa_lower in mensaje.lower():
            return 'empresa'
    
    # Si no coincide con el patrón de WhatsApp, buscar directamente en la línea
    # Buscar el texto de la empresa en la línea completa
    if texto_empresa_lower in linea_lower:
        return 'empresa'
    
    # Buscar el teléfono en la línea completa
    for tel_var in telefono_variantes:
        tel_var_sin_espacios = tel_var.replace(' ', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
        linea_sin_espacios = linea.replace(' ', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
        if tel_var_sin_espacios in linea_sin_espacios or tel_var in linea:
            return 'usuario'
    
    return None


def procesar_archivo_whatsapp(
    archivo_entrada: str,
    texto_empresa: str,
    telefono: str,
    archivo_salida: Optional[str] = None
) -> str:
    """
    Procesa un archivo de WhatsApp y lo convierte en formato estructurado.
    
    Args:
        archivo_entrada: Ruta al archivo de WhatsApp original
        texto_empresa: Texto que identifica a la empresa
        telefono: Número de teléfono del usuario
        archivo_salida: Ruta al archivo de salida (opcional, si no se proporciona se usa entrada_procesado.txt)
        
    Returns:
        Ruta al archivo procesado
    """
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(f"El archivo {archivo_entrada} no existe")
    
    # Determinar archivo de salida
    if archivo_salida is None:
        base, ext = os.path.splitext(archivo_entrada)
        archivo_salida = f"{base}_procesado{ext}"
    
    texto_empresa_lower = texto_empresa.lower()
    lineas_procesadas = []
    encontro_empresa = False
    eliminar_siguiente = False
    
    # Texto a reemplazar
    texto_a_reemplazar = "¿Puedes darme más información sobre esto?"
    texto_reemplazo = "Cuanto cuesta el servicio?"
    
    def aplicar_reemplazo(mensaje: str) -> str:
        """Aplica reemplazos de texto al mensaje"""
        if texto_a_reemplazar in mensaje:
            mensaje = mensaje.replace(texto_a_reemplazar, texto_reemplazo)
        return mensaje
    
    print(f"📖 Leyendo archivo: {archivo_entrada}")
    print(f"🔍 Buscando empresa: '{texto_empresa}'")
    print(f"📱 Teléfono usuario: '{telefono}'")
    
    with open(archivo_entrada, 'r', encoding='utf-8', errors='ignore') as f:
        lineas = f.readlines()
    
    total_lineas = len(lineas)
    print(f"📊 Total de líneas a procesar: {total_lineas}")
    
    for i, linea in enumerate(lineas, 1):
        linea_original = linea.rstrip('\n\r')
        linea_stripped = linea_original.strip()
        
        # Si la línea está vacía, mantenerla
        if not linea_stripped:
            lineas_procesadas.append('')
            continue
        
        # Eliminar líneas que contengan mensajes de seguridad de WhatsApp
        if "Cambió tu código de seguridad con" in linea_stripped:
            print(f"🗑️  Línea {i} eliminada (mensaje de seguridad): {linea_stripped[:50]}...")
            continue
        
        # Buscar la primera línea con el texto de la empresa y eliminarla
        if not encontro_empresa and texto_empresa_lower in linea_stripped.lower():
            print(f"🗑️  Línea {i} eliminada (contiene texto de empresa): {linea_stripped[:50]}...")
            encontro_empresa = True
            eliminar_siguiente = True
            continue
        
        # Si acabamos de eliminar una línea, procesar la siguiente
        if eliminar_siguiente:
            eliminar_siguiente = False
        
        # Identificar el tipo de línea
        tipo = identificar_tipo_linea(linea_stripped, texto_empresa, telefono)
        
        if tipo == 'empresa':
            # Extraer solo el mensaje (sin fecha/hora/nombre)
            # Usar un patrón que capture TODO después del nombre del remitente
            patron_mensaje = r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]?M?\]\s*-\s*[^:]+:\s*(.+)'
            match = re.match(patron_mensaje, linea_stripped)
            
            if match:
                mensaje = match.group(1).strip()
                mensaje = aplicar_reemplazo(mensaje)
                lineas_procesadas.append(f"ai: {mensaje}")
            else:
                # Si no coincide con el patrón estándar, buscar manualmente
                if ' - ' in linea_stripped:
                    # Dividir por " - " y tomar la segunda parte (remitente: mensaje)
                    partes_guion = linea_stripped.split(' - ', 1)
                    if len(partes_guion) > 1:
                        parte_derecha = partes_guion[1]
                        # Buscar el primer ":" que separa el nombre del mensaje
                        indice_dos_puntos = parte_derecha.find(':')
                        if indice_dos_puntos >= 0:
                            # Extraer todo después del primer ":" (incluye URLs completas)
                            mensaje = parte_derecha[indice_dos_puntos + 1:].strip()
                            mensaje = aplicar_reemplazo(mensaje)
                            lineas_procesadas.append(f"ai: {mensaje}")
                        else:
                            # Si no hay ":", la parte derecha es el mensaje completo
                            mensaje = aplicar_reemplazo(parte_derecha)
                            lineas_procesadas.append(f"ai: {mensaje}")
                    else:
                        mensaje = aplicar_reemplazo(linea_stripped)
                        lineas_procesadas.append(f"ai: {mensaje}")
                elif ':' in linea_stripped:
                    # Si no hay " - ", buscar el primer ":" que separa nombre de mensaje
                    if linea_stripped.startswith(('http://', 'https://')):
                        mensaje = aplicar_reemplazo(linea_stripped)
                        lineas_procesadas.append(f"ai: {mensaje}")
                    else:
                        indice_primer_dos_puntos = linea_stripped.find(':')
                        if indice_primer_dos_puntos >= 0:
                            mensaje = linea_stripped[indice_primer_dos_puntos + 1:].strip()
                            mensaje = aplicar_reemplazo(mensaje)
                            lineas_procesadas.append(f"ai: {mensaje}")
                        else:
                            mensaje = aplicar_reemplazo(linea_stripped)
                            lineas_procesadas.append(f"ai: {mensaje}")
                else:
                    # No hay ":" ni " - ", es probablemente solo el mensaje
                    mensaje = aplicar_reemplazo(linea_stripped)
                    lineas_procesadas.append(f"ai: {mensaje}")
        
        elif tipo == 'usuario':
            # Extraer solo el mensaje (sin fecha/hora/nombre)
            # Usar un patrón que capture TODO después del nombre del remitente
            # Esto maneja URLs y otros casos con múltiples ":"
            patron_mensaje = r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]?M?\]\s*-\s*[^:]+:\s*(.+)'
            match = re.match(patron_mensaje, linea_stripped)
            
            if match:
                mensaje = match.group(1).strip()
                mensaje = aplicar_reemplazo(mensaje)
                lineas_procesadas.append(f"user: {mensaje}")
            else:
                # Si no coincide con el patrón estándar, buscar manualmente
                # Buscar el patrón " - " que separa fecha de remitente
                if ' - ' in linea_stripped:
                    # Dividir por " - " y tomar la segunda parte (remitente: mensaje)
                    partes_guion = linea_stripped.split(' - ', 1)
                    if len(partes_guion) > 1:
                        parte_derecha = partes_guion[1]
                        # Buscar el primer ":" que separa el nombre del mensaje
                        # Usar find() para encontrar el primer ":" después del nombre
                        indice_dos_puntos = parte_derecha.find(':')
                        if indice_dos_puntos >= 0:
                            # Extraer todo después del primer ":" (incluye URLs completas)
                            mensaje = parte_derecha[indice_dos_puntos + 1:].strip()
                            mensaje = aplicar_reemplazo(mensaje)
                            lineas_procesadas.append(f"user: {mensaje}")
                        else:
                            # Si no hay ":", la parte derecha es el mensaje completo
                            mensaje = aplicar_reemplazo(parte_derecha)
                            lineas_procesadas.append(f"user: {mensaje}")
                    else:
                        mensaje = aplicar_reemplazo(linea_stripped)
                        lineas_procesadas.append(f"user: {mensaje}")
                elif ':' in linea_stripped:
                    # Si no hay " - ", buscar el primer ":" que separa nombre de mensaje
                    # Pero verificar primero si la línea empieza con http (es solo el mensaje)
                    if linea_stripped.startswith(('http://', 'https://')):
                        mensaje = aplicar_reemplazo(linea_stripped)
                        lineas_procesadas.append(f"user: {mensaje}")
                    else:
                        # Buscar el primer ":" que probablemente separa nombre de mensaje
                        indice_primer_dos_puntos = linea_stripped.find(':')
                        if indice_primer_dos_puntos >= 0:
                            mensaje = linea_stripped[indice_primer_dos_puntos + 1:].strip()
                            mensaje = aplicar_reemplazo(mensaje)
                            lineas_procesadas.append(f"user: {mensaje}")
                        else:
                            mensaje = aplicar_reemplazo(linea_stripped)
                            lineas_procesadas.append(f"user: {mensaje}")
                else:
                    # No hay ":" ni " - ", es probablemente solo el mensaje
                    mensaje = aplicar_reemplazo(linea_stripped)
                    lineas_procesadas.append(f"user: {mensaje}")
        
        else:
            # Si no se puede identificar, intentar extraer el mensaje
            patron_mensaje = r'\[\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]?M?\]\s*-\s*[^:]+:\s*(.+)'
            match = re.match(patron_mensaje, linea_stripped)
            
            if match:
                mensaje = match.group(1).strip()
                mensaje = aplicar_reemplazo(mensaje)
                # Por defecto, asumir que es del usuario si no se puede identificar
                lineas_procesadas.append(f"user: {mensaje}")
            elif ':' in linea_stripped:
                # Intentar extraer después del último ":"
                partes = linea_stripped.rsplit(':', 1)
                if len(partes) > 1:
                    mensaje = partes[1].strip()
                    mensaje = aplicar_reemplazo(mensaje)
                    lineas_procesadas.append(f"user: {mensaje}")
                else:
                    mensaje = aplicar_reemplazo(linea_stripped)
                    lineas_procesadas.append(mensaje)
            else:
                mensaje = aplicar_reemplazo(linea_stripped)
                lineas_procesadas.append(mensaje)
    
    # Combinar líneas consecutivas que empiezan con "ai:" o "user:"
    lineas_finales = []
    i = 0
    while i < len(lineas_procesadas):
        linea_actual = lineas_procesadas[i]
        
        # Si la línea empieza con "ai:", buscar líneas consecutivas
        if linea_actual.startswith("ai: "):
            mensajes_ai = []
            # Extraer el mensaje de la primera línea (sin "ai: ")
            mensaje = linea_actual[4:].strip()  # Quitar "ai: " (4 caracteres)
            mensajes_ai.append(mensaje)
            
            # Buscar líneas consecutivas que también empiecen con "ai:"
            j = i + 1
            while j < len(lineas_procesadas) and lineas_procesadas[j].startswith("ai: "):
                mensaje_siguiente = lineas_procesadas[j][4:].strip()  # Quitar "ai: "
                mensajes_ai.append(mensaje_siguiente)
                j += 1
            
            # Si hay más de un mensaje, combinarlos
            if len(mensajes_ai) > 1:
                mensaje_combinado = "\\n".join(mensajes_ai)
                lineas_finales.append(f"ai: {mensaje_combinado}")
                print(f"🔗 Líneas {i+1}-{j} combinadas: {len(mensajes_ai)} mensajes de ai")
            else:
                # Solo una línea, mantenerla como está
                lineas_finales.append(linea_actual)
            
            # Avanzar al siguiente índice después de las líneas procesadas
            i = j
        
        # Si la línea empieza con "user:", buscar líneas consecutivas
        elif linea_actual.startswith("user: "):
            mensajes_user = []
            # Extraer el mensaje de la primera línea (sin "user: ")
            mensaje = linea_actual[6:].strip()  # Quitar "user: " (6 caracteres)
            mensajes_user.append(mensaje)
            
            # Buscar líneas consecutivas que también empiecen con "user:"
            j = i + 1
            while j < len(lineas_procesadas) and lineas_procesadas[j].startswith("user: "):
                mensaje_siguiente = lineas_procesadas[j][6:].strip()  # Quitar "user: "
                mensajes_user.append(mensaje_siguiente)
                j += 1
            
            # Si hay más de un mensaje, combinarlos
            if len(mensajes_user) > 1:
                mensaje_combinado = "\\n".join(mensajes_user)
                lineas_finales.append(f"user: {mensaje_combinado}")
                print(f"🔗 Líneas {i+1}-{j} combinadas: {len(mensajes_user)} mensajes de user")
            else:
                # Solo una línea, mantenerla como está
                lineas_finales.append(linea_actual)
            
            # Avanzar al siguiente índice después de las líneas procesadas
            i = j
        else:
            # No es una línea "ai:" ni "user:", mantenerla como está
            lineas_finales.append(linea_actual)
            i += 1
    
    # Escribir el archivo procesado
    print(f"💾 Escribiendo archivo procesado: {archivo_salida}")
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas_finales))
        if lineas_finales and lineas_finales[-1]:  # Agregar nueva línea final si es necesario
            f.write('\n')
    
    print(f"✅ Procesamiento completado!")
    print(f"   Líneas procesadas: {len(lineas_procesadas)}")
    print(f"   Archivo guardado en: {archivo_salida}")
    
    return archivo_salida


def main():
    """Función principal del script"""
    if len(sys.argv) < 4:
        print("❌ Error: Faltan argumentos")
        print("\nUso:")
        print(f"  {sys.argv[0]} \"texto_empresa\" \"telefono\" archivo_entrada.txt [archivo_salida.txt]")
        print("\nEjemplo:")
        print(f"  {sys.argv[0]} \"Limpieza de pozos:\" \"+591 69023378\" chat.txt")
        print(f"  {sys.argv[0]} \"Limpieza de pozos:\" \"+591 69023378\" chat.txt salida.txt")
        sys.exit(1)
    
    texto_empresa = sys.argv[1]
    telefono = sys.argv[2]
    archivo_entrada = sys.argv[3]
    archivo_salida = sys.argv[4] if len(sys.argv) > 4 else None
    
    try:
        archivo_procesado = procesar_archivo_whatsapp(
            archivo_entrada=archivo_entrada,
            texto_empresa=texto_empresa,
            telefono=telefono,
            archivo_salida=archivo_salida
        )
        print(f"\n✨ Archivo procesado exitosamente: {archivo_procesado}")
    except Exception as e:
        print(f"❌ Error al procesar el archivo: {str(e)}")
        import traceback
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
