#!/usr/bin/env python3
"""
Script para enviar mensajes al webhook del chatbot y emular conversaciones de prueba.

Lee un JSON de mensajes (generado por parse_whatsapp_chats.py) y los envía al webhook:
- Si el siguiente mensaje tiene segundos_desde_anterior == 8: espera 8 s y envía el siguiente
- Si tiene 100 o null: espera la respuesta del POST (respuesta de la IA) antes de enviar el siguiente

Uso:
  python scripts/enviar_mensajes_chatbot.py mensajes_cliente.json
  python scripts/enviar_mensajes_chatbot.py --send 59169023378          # enviar "000"
  python scripts/enviar_mensajes_chatbot.py -s 59169023378 -m "hola"   # enviar texto custom
"""

import argparse
import json
import sys
import threading
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instala requests: pip install requests", file=sys.stderr)
    sys.exit(1)

WEBHOOK_URL = "https://n8npozos.magoreal.com/webhook/chat"


def enviar_mensaje(url: str, telefono: str, mensaje: str, timeout: int = 120) -> requests.Response:
    """Envía un mensaje al webhook del chatbot."""
    payload = {"from": telefono, "text": mensaje, "telefono": telefono}
    return requests.post(url, json=payload, timeout=timeout)


def _mostrar_respuesta(num: int, total: int, resp: requests.Response, verbose: bool) -> None:
    """Muestra la respuesta en terminal."""
    if not verbose:
        return
    print(f"  [{num}/{total}] Respuesta: {resp.status_code} {resp.reason}")
    if resp.text:
        try:
            data = resp.json()
            output = data.get("output", data)
            if isinstance(output, str):
                print(f"  -> {output}")
            else:
                print(f"  -> {json.dumps(data, ensure_ascii=False, indent=2)}")
        except Exception:
            print(f"  -> {resp.text[:500]}")


def ejecutar(mensajes: list[dict], url: str, timeout: int = 120, verbose: bool = True) -> None:
    total = len(mensajes)
    background_threads: list[threading.Thread] = []

    for i, item in enumerate(mensajes):
        telefono = item.get("telefono", "")
        mensaje = item.get("mensaje", "")
        seg_siguiente = mensajes[i + 1].get("segundos_desde_anterior") if i + 1 < total else None

        if verbose:
            print(f"\n[{i + 1}/{total}] Mensaje: {mensaje}")

        # Si el siguiente tiene 8: enviar en background, no esperar respuesta, esperar 8 s
        if seg_siguiente == 8:
            def _enviar_background(idx=i, tel=telefono, msg=mensaje):
                try:
                    resp = enviar_mensaje(url, tel, msg, timeout=timeout)
                    _mostrar_respuesta(idx + 1, total, resp, verbose)
                except requests.RequestException as e:
                    print(f"  -> Error: {e}", file=sys.stderr)

            t = threading.Thread(target=_enviar_background, daemon=False)
            t.start()
            background_threads.append(t)
            if verbose:
                print("  -> (siguiente en 8 s, no esperando respuesta)")
            time.sleep(8)
        else:
            # Esperar respuesta antes de enviar el siguiente
            try:
                resp = enviar_mensaje(url, telefono, mensaje, timeout=timeout)
                _mostrar_respuesta(i + 1, total, resp, verbose)
            except requests.RequestException as e:
                print(f"  -> Error: {e}", file=sys.stderr)
                raise

    for t in background_threads:
        t.join()


def main():
    parser = argparse.ArgumentParser(
        description="Envía mensajes al webhook del chatbot para pruebas."
    )
    parser.add_argument(
        "archivo",
        type=Path,
        nargs="?",
        default=Path("mensajes_cliente.json"),
        help="Archivo JSON de mensajes (default: mensajes_cliente.json)",
    )
    parser.add_argument(
        "--url",
        "-u",
        default=WEBHOOK_URL,
        help=f"URL del webhook (default: {WEBHOOK_URL})",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=120,
        help="Timeout en segundos para cada POST (máx. 120)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Menos salida",
    )
    parser.add_argument(
        "--prueba",
        "-p",
        action="store_true",
        dest="prueba",
        help="Solo enviar el primer mensaje y esperar la respuesta (para probar conexión)",
    )
    parser.add_argument(
        "--send",
        "-s",
        metavar="TELEFONO",
        help="Enviar mensaje '000' a un número (ej: 59169023378). Usar --mensaje para otro texto.",
    )
    parser.add_argument(
        "--mensaje",
        "-m",
        default="000",
        help="Texto a enviar con --send (default: 000)",
    )
    args = parser.parse_args()
    args.timeout = min(args.timeout, 120)

    if args.send:
        telefono = args.send.replace(" ", "").replace("+", "")
        if not telefono.isdigit():
            print("Teléfono debe contener solo dígitos (ej: 59169023378)", file=sys.stderr)
            sys.exit(1)
        print(f"Enviando '{args.mensaje}' a {telefono}...")
        try:
            resp = enviar_mensaje(args.url, telefono, args.mensaje, timeout=args.timeout)
            print(f"  -> {resp.status_code} {resp.reason}")
            if resp.text:
                try:
                    data = resp.json()
                    output = data.get("output", data)
                    print(f"  -> Respuesta: {output}" if isinstance(output, str) else f"  -> {json.dumps(data, ensure_ascii=False)}")
                except Exception:
                    print(f"  -> {resp.text[:500]}")
        except requests.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    archivo = args.archivo if args.archivo.is_absolute() else Path.cwd() / args.archivo
    if not archivo.exists():
        print(f"No existe: {archivo}", file=sys.stderr)
        sys.exit(1)

    mensajes = json.loads(archivo.read_text(encoding="utf-8"))
    if not isinstance(mensajes, list):
        mensajes = [mensajes]

    if args.prueba:
        mensajes = mensajes[:1]
        print(f"Modo prueba: enviando 1 mensaje y esperando respuesta en {args.url}")
    else:
        print(f"Enviando {len(mensajes)} mensajes a {args.url}")
    ejecutar(mensajes, args.url, timeout=args.timeout, verbose=not args.quiet)
    print("Listo.")


if __name__ == "__main__":
    main()
