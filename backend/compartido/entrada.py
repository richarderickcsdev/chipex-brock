"""Limpieza de texto y normalización para comparaciones deterministas."""

import re
import unicodedata


def limpiar_texto(texto: str) -> str:
    """Conserva palabras; reemplaza controles y colapsa espacios/saltos de línea."""
    sin_controles = "".join(
        " " if unicodedata.category(caracter).startswith("C") else caracter
        for caracter in texto
    )
    return " ".join(sin_controles.split())


def normalizar_nombre(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"\w+", sin_acentos))
