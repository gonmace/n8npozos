#!/usr/bin/env python3
"""
Script para extraer mensajes del cliente de exportaciones de WhatsApp.

Lee archivos .txt en chats/ y genera un JSON con:
- telefono: número del cliente (prefijo +591)
- mensaje: texto del mensaje
- segundos_desde_anterior: tiempo en segundos desde el mensaje anterior del mismo cliente
  (null si es el primer mensaje o si hay mensajes del bot en medio)

Uso:
  python scripts/parse_whatsapp_chats.py --por-archivo
  python scripts/parse_whatsapp_chats.py --archivo "chats/Chat de WhatsApp con +591 69023378.txt"
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


# Patrón: fecha, hora - SENDER: mensaje
# Ejemplo: 7/1/2026, 10:38 a. m. - +591 72154413: Buenos días
LINE_PATTERN = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{4}),\s*(\d{1,2}:\d{2}\s*[ap]\.\s*m\.)\s*-\s*(.+?):\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)

# Cliente: número con prefijo +591
CLIENT_PATTERN = re.compile(r"^\+\s*591\s*(\d+)$", re.IGNORECASE)


def parse_datetime(date_str: str, time_str: str) -> datetime | None:
    """Convierte '7/1/2026' y '10:38 a. m.' a datetime."""
    try:
        # Normalizar espacios Unicode (WhatsApp usa U+202F) a espacio normal
        t = time_str.strip().replace("\u202f", " ").replace("\xa0", " ")
        # "a. m." -> "AM", "p. m." -> "PM"
        t = re.sub(r"a\.\s*m\.", "AM", t, flags=re.IGNORECASE)
        t = re.sub(r"p\.\s*m\.", "PM", t, flags=re.IGNORECASE)
        t = re.sub(r"\s+", " ", t).strip()
        dt_str = f"{date_str} {t}"
        # WhatsApp exporta en dd/mm/yyyy (formato habitual en español)
        return datetime.strptime(dt_str, "%d/%m/%Y %I:%M %p")
    except ValueError:
        return None


def is_client_sender(sender: str) -> bool:
    """True si el mensaje es del cliente (número +591)."""
    return bool(CLIENT_PATTERN.match(sender.strip()))


def normalize_phone(sender: str) -> str:
    """Normaliza el teléfono a formato 591XXXXXXXX."""
    m = CLIENT_PATTERN.match(sender.strip())
    if m:
        return "591" + m.group(1)
    return sender


def parse_line(line: str) -> dict | None:
    """
    Parsea una línea. Retorna dict con date, time, sender, message, datetime
    o None si no coincide.
    """
    line = line.strip()
    if not line:
        return None

    m = LINE_PATTERN.match(line)
    if not m:
        return None

    date_str, time_str, sender, message = m.groups()
    dt = parse_datetime(date_str, time_str)
    return {
        "date_str": date_str,
        "time_str": time_str,
        "sender": sender.strip(),
        "message": message.strip(),
        "datetime": dt,
    }


def extract_client_messages(chat_path: Path) -> list[dict]:
    """
    Extrae mensajes del cliente de un archivo de chat.
    Retorna lista de {telefono, mensaje, segundos_desde_anterior}.
    segundos_desde_anterior solo se incluye cuando hay dos mensajes seguidos del cliente
    (sin mensaje del bot u otro en medio).
    """
    content = chat_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # Recolectar TODOS los mensajes (cliente y bot) para detectar consecutividad
    all_entries: list[dict] = []
    for line in lines:
        parsed = parse_line(line)
        if not parsed or parsed["datetime"] is None:
            continue
        parsed["_is_client"] = is_client_sender(parsed["sender"])
        if parsed["_is_client"]:
            parsed["_phone"] = normalize_phone(parsed["sender"])
        all_entries.append(parsed)

    all_entries.sort(key=lambda x: x["datetime"])

    result: list[dict] = []
    for i, parsed in enumerate(all_entries):
        if not parsed["_is_client"]:
            continue

        phone = parsed["_phone"]
        msg = parsed["message"]
        dt = parsed["datetime"]

        segundos = None
        # Solo si el mensaje anterior en el chat fue del mismo cliente (seguidos)
        if i > 0:
            prev = all_entries[i - 1]
            if prev.get("_is_client") and prev.get("_phone") == phone:
                delta = max(0, int((dt - prev["datetime"]).total_seconds()))
                segundos = 8 if delta <= 60 else 100

        result.append({
            "telefono": phone,
            "mensaje": msg,
            "segundos_desde_anterior": segundos,
        })

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extrae mensajes del cliente de chats de WhatsApp para emular el chatbot."
    )
    parser.add_argument(
        "--archivo",
        "-a",
        type=Path,
        help="Archivo .txt de chat de WhatsApp",
    )
    parser.add_argument(
        "--por-archivo",
        action="store_true",
        help="Procesar todos los .txt en chats/ y generar <telefono>.json por cada uno",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    chats_dir = base / "chats"

    if args.por_archivo:
        files = list(chats_dir.rglob("*.txt"))
    elif args.archivo:
        archivo = args.archivo if args.archivo.is_absolute() else base / args.archivo
        files = [archivo]
    else:
        print("Usar --archivo o --por-archivo", file=__import__("sys").stderr)
        return 1

    if not files:
        print("No se encontraron archivos .txt", file=__import__("sys").stderr)
        return 1

    for f in sorted(files):
        if not f.exists():
            continue
        msgs = extract_client_messages(f)
        telefono = msgs[0]["telefono"] if msgs else None
        if not telefono:
            print(f"  (sin mensajes del cliente) -> {f.name}", file=__import__("sys").stderr)
            continue
        out = f.parent / f"{telefono}.json"
        out.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(msgs)} mensajes -> {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
