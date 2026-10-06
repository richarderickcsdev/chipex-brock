"""Cálculo opcional de costo estimado a partir de precios configurados."""

from decimal import Decimal, InvalidOperation


def costo_estimado(
    tokens_in: int, tokens_out: int, precio_entrada_millon: str,
    precio_salida_millon: str,
) -> Decimal:
    if tokens_in < 0 or tokens_out < 0:
        raise ValueError("Los tokens no pueden ser negativos.")
    try:
        entrada = Decimal(precio_entrada_millon)
        salida = Decimal(precio_salida_millon)
    except InvalidOperation as exc:
        raise ValueError("El precio configurado no es válido.") from exc
    if entrada < 0 or salida < 0:
        raise ValueError("Los precios no pueden ser negativos.")
    return (Decimal(tokens_in) * entrada + Decimal(tokens_out) * salida) / Decimal(1_000_000)
