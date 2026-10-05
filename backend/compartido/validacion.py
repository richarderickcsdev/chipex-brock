"""Validación del contrato y coherencia; nunca ejecuta la salida de la IA."""

import json
import re
from collections import defaultdict
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError

from .entrada import normalizar_nombre
from .errores import CodigoError, ErrorBrock
from .esquema import EntradaPlan, PlanGenerado, Unidad


def validar_entrada[T: BaseModel](modelo: type[T], datos: object) -> T:
    try:
        return modelo.model_validate(datos)
    except ValidationError as exc:
        # No reflejar el input del usuario ni el mensaje interno de Pydantic.
        raise ErrorBrock(CodigoError.VALIDACION, "Revisa los datos del formulario.") from exc


def cantidad_base(cantidad: float, unidad: Unidad) -> tuple[str, Decimal]:
    conversiones = {"kg": ("g", 1000), "l": ("ml", 1000)}
    base, factor = conversiones.get(unidad, (unidad, 1))
    return base, Decimal(str(cantidad)) * factor


def json_publico(datos: object) -> str:
    """Serializa números de DynamoDB sin convertir contadores en cadenas."""
    def numero(valor: object) -> int | float:
        if isinstance(valor, Decimal):
            return int(valor) if valor == valor.to_integral_value() else float(valor)
        raise TypeError(f"Tipo no serializable: {type(valor).__name__}")

    return json.dumps(datos, default=numero, ensure_ascii=False, allow_nan=False)
