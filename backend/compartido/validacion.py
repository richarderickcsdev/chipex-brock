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


def recalcular_lista_compras(plan: PlanGenerado) -> list:
    """Recalcula la lista de compras a partir de los ingredientes en_casa=false."""
    from .esquema import ItemCompra
    # Conservar el pasillo que la IA asignó a cada nombre de ingrediente.
    pasillo_por_nombre: dict[str, str] = {}
    for item in plan.lista_compras:
        clave = normalizar_nombre(item.nombre)
        if clave not in pasillo_por_nombre:
            pasillo_por_nombre[clave] = item.pasillo
    faltantes: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for dia in plan.dias:
        for comida in dia.comidas:
            for ing in comida.ingredientes:
                if not ing.en_casa:
                    unidad, cantidad = cantidad_base(ing.cantidad, ing.unidad)
                    faltantes[(normalizar_nombre(ing.nombre), unidad)] += cantidad
    items = []
    for i, ((nombre, unidad), cantidad) in enumerate(sorted(faltantes.items()), 1):
        items.append(ItemCompra(
            id=f"it_{i:02d}", nombre=nombre.title(),
            cantidad=float(cantidad), unidad=unidad,
            pasillo=pasillo_por_nombre.get(nombre, "OTROS"),
        ))
    return items


def validar_coherencia(plan: PlanGenerado, entrada: EntradaPlan, evitar: list[str]) -> None:
    def invalido(mensaje: str) -> None:
        raise ErrorBrock(CodigoError.VALIDACION, mensaje)

    if [dia.dia for dia in plan.dias] != list(range(1, entrada.dias + 1)):
        invalido("Los días del menú no coinciden con los solicitados.")
    for dia in plan.dias:
        tipos = [comida.tipo for comida in dia.comidas]
        if len(tipos) != len(entrada.comidas) or set(tipos) != set(entrada.comidas):
            invalido("Las comidas del menú no coinciden con las solicitadas.")
    if len({item.id for item in plan.lista_compras}) != len(plan.lista_compras):
        invalido("La lista contiene identificadores repetidos.")

    # Revisa nombres y pasos visibles; comparación léxica, no filtro de alergias.
    textos = [item.nombre for item in plan.lista_compras]
    faltantes: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for dia in plan.dias:
        for comida in dia.comidas:
            textos.extend([comida.nombre, *comida.pasos])
            for ingrediente in comida.ingredientes:
                textos.append(ingrediente.nombre)
                if not ingrediente.en_casa:
                    unidad, cantidad = cantidad_base(ingrediente.cantidad, ingrediente.unidad)
                    faltantes[(normalizar_nombre(ingrediente.nombre), unidad)] += cantidad
    for preferencia in evitar:
        palabras = normalizar_nombre(preferencia).split()
        if not palabras:
            invalido("La preferencia a evitar no es válida.")
        patron = r"\b" + r"\s+".join(re.escape(p) + r"(?:s|es)?" for p in palabras) + r"\b"
        if any(re.search(patron, normalizar_nombre(texto)) for texto in textos):
            invalido("El resultado contiene un ingrediente que prefieres evitar.")

    compras: dict[tuple[str, str], Decimal] = {}
    for item in plan.lista_compras:
        unidad, cantidad = cantidad_base(item.cantidad, item.unidad)
        clave = (normalizar_nombre(item.nombre), unidad)
        if clave in compras:
            invalido("La lista debe agrupar los ingredientes repetidos.")
        compras[clave] = cantidad
    # La lista se recalcula en validar_plan; aquí solo verificamos que sea coherente en formato.


def validar_plan(
    datos: str | dict[str, Any], entrada: EntradaPlan, evitar: list[str] | None = None
) -> PlanGenerado:
    try:
        plan = (PlanGenerado.model_validate_json(datos) if isinstance(datos, str)
                else PlanGenerado.model_validate(datos))
    except ValidationError as exc:
        raise ErrorBrock(CodigoError.VALIDACION, "El menú no cumple el formato esperado.") from exc
    validar_coherencia(plan, entrada, evitar or [])
    # El código recalcula la lista: la IA propone el menú, el código decide compras.
    plan.lista_compras = recalcular_lista_compras(plan)
    return plan


def json_publico(datos: object) -> str:
    """Serializa números de DynamoDB sin convertir contadores en cadenas."""
    def numero(valor: object) -> int | float:
        if isinstance(valor, Decimal):
            return int(valor) if valor == valor.to_integral_value() else float(valor)
        raise TypeError(f"Tipo no serializable: {type(valor).__name__}")

    return json.dumps(datos, default=numero, ensure_ascii=False, allow_nan=False)
