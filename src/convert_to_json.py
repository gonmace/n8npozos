#!/usr/bin/env python3
"""
Script para convertir archivos _procesado.txt a formato JSON.

Busca todos los archivos que terminan en "_procesado.txt" en el mismo directorio
y los convierte a JSON con la estructura:
[
  {
    "user": "texto",
    "ai": "texto"
  },
  {
    "user": "texto",
    "ai": "texto"
  },
  ...
]

Uso:
    python convert_to_json.py [directorio]
    
Si no se especifica directorio, usa el directorio actual.
"""

import os
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional


def procesar_linea(linea: str) -> Optional[Dict[str, str]]:
    """
    Procesa una línea y extrae el tipo (user/ai) y el mensaje.
    
    Args:
        linea: Línea del archivo procesado
        
    Returns:
        Dict con 'tipo' y 'mensaje', o None si la línea está vacía o no es válida
    """
    linea = linea.strip()
    
    if not linea:
        return None
    
    # Detectar si es user o ai
    if linea.startswith("user: "):
        mensaje = linea[6:].strip()  # Quitar "user: "
        # Reemplazar \n literales por saltos de línea reales
        mensaje = mensaje.replace("\\n", "\n")
        return {"tipo": "user", "mensaje": mensaje}
    elif linea.startswith("ai: "):
        mensaje = linea[4:].strip()  # Quitar "ai: "
        # Reemplazar \n literales por saltos de línea reales
        mensaje = mensaje.replace("\\n", "\n")
        return {"tipo": "ai", "mensaje": mensaje}
    
    return None


def convertir_a_json(archivo_entrada: str) -> List[Dict[str, str]]:
    """
    Convierte un archivo _procesado.txt a formato JSON.
    
    Args:
        archivo_entrada: Ruta al archivo _procesado.txt
        
    Returns:
        Lista de diccionarios con estructura {user: "...", ai: "..."}
    """
    conversaciones = []
    user_actual = None
    
    print(f"📖 Leyendo archivo: {archivo_entrada}")
    
    try:
        with open(archivo_entrada, 'r', encoding='utf-8', errors='ignore') as f:
            lineas = f.readlines()
    except Exception as e:
        print(f"❌ Error al leer el archivo: {str(e)}")
        return []
    
    for i, linea in enumerate(lineas, 1):
        resultado = procesar_linea(linea)
        
        if resultado is None:
            continue
        
        tipo = resultado["tipo"]
        mensaje = resultado["mensaje"]
        
        if tipo == "user":
            # Si hay un user pendiente sin ai, guardarlo con ai vacío
            if user_actual is not None:
                conversaciones.append({
                    "user": user_actual,
                    "ai": ""
                })
            
            # Guardar el nuevo mensaje de user
            user_actual = mensaje
        
        elif tipo == "ai":
            # Si hay un user pendiente, crear el objeto completo
            if user_actual is not None:
                conversaciones.append({
                    "user": user_actual,
                    "ai": mensaje
                })
                user_actual = None
            else:
                # Si no hay user previo, crear con user vacío
                conversaciones.append({
                    "user": "",
                    "ai": mensaje
                })
    
    # Si queda un user sin ai al final, agregarlo
    if user_actual is not None:
        conversaciones.append({
            "user": user_actual,
            "ai": ""
        })
    
    return conversaciones


def procesar_archivo(archivo_entrada: str) -> Optional[str]:
    """
    Procesa un archivo _procesado.txt y genera el JSON correspondiente.
    
    Args:
        archivo_entrada: Ruta al archivo _procesado.txt
        
    Returns:
        Ruta al archivo JSON generado, o None si hay error
    """
    # Generar nombre del archivo de salida
    base, ext = os.path.splitext(archivo_entrada)
    archivo_salida = f"{base}.json"
    
    # Convertir a JSON
    conversaciones = convertir_a_json(archivo_entrada)
    
    if not conversaciones:
        print(f"⚠️  No se encontraron conversaciones en {archivo_entrada}")
        return None
    
    # Escribir el archivo JSON
    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(conversaciones, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Archivo JSON creado: {archivo_salida}")
        print(f"   Conversaciones procesadas: {len(conversaciones)}")
        return archivo_salida
    except Exception as e:
        print(f"❌ Error al escribir el archivo JSON: {str(e)}")
        return None


def buscar_archivos_procesados(directorio: str = ".") -> List[str]:
    """
    Busca todos los archivos que terminan en "_procesado.txt" en el directorio.
    
    Args:
        directorio: Directorio donde buscar (por defecto, directorio actual)
        
    Returns:
        Lista de rutas a archivos encontrados
    """
    archivos_encontrados = []
    
    try:
        directorio_path = Path(directorio)
        if not directorio_path.exists():
            print(f"❌ El directorio {directorio} no existe")
            return []
        
        # Buscar archivos que terminan en "_procesado.txt"
        for archivo in directorio_path.iterdir():
            if archivo.is_file() and archivo.name.endswith("_procesado.txt"):
                archivos_encontrados.append(str(archivo))
        
        return sorted(archivos_encontrados)
    except Exception as e:
        print(f"❌ Error al buscar archivos: {str(e)}")
        return []


def main():
    """Función principal del script"""
    # Determinar directorio
    if len(sys.argv) > 1:
        directorio = sys.argv[1]
    else:
        directorio = "."
    
    print(f"🔍 Buscando archivos _procesado.txt en: {os.path.abspath(directorio)}")
    
    # Buscar archivos
    archivos = buscar_archivos_procesados(directorio)
    
    if not archivos:
        print("⚠️  No se encontraron archivos que terminen en '_procesado.txt'")
        return
    
    print(f"📁 Archivos encontrados: {len(archivos)}")
    for archivo in archivos:
        print(f"   - {os.path.basename(archivo)}")
    
    print("\n🔄 Procesando archivos...\n")
    
    # Procesar cada archivo
    archivos_procesados = 0
    for archivo in archivos:
        print(f"\n{'='*60}")
        resultado = procesar_archivo(archivo)
        if resultado:
            archivos_procesados += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Procesamiento completado!")
    print(f"   Archivos procesados: {archivos_procesados}/{len(archivos)}")


if __name__ == "__main__":
    main()
