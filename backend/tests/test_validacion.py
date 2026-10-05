import json
from decimal import Decimal
from typing import Any

import pytest

from backend.compartido.entrada import limpiar_texto
from backend.compartido.errores import CodigoError, ErrorBrock
from backend.compartido.esquema import ESQUEMA_PLAN, EntradaPlan, MarcaCompra, Perfil
from backend.compartido.validacion import json_publico, validar_entrada, validar_plan


def test_plan_json_valido(entrada: EntradaPlan, respuesta_plan: dict[str, Any]) -> None:
    assert validar_plan(json.dumps(respuesta_plan), entrada).lista_compras[0].cantidad == 100
    assert ESQUEMA_PLAN["additionalProperties"] is False


@pytest.mark.parametrize("respuesta", ["texto ajeno", "```json\n{}\n```", "{}", "[]"])
def test_ia_solo_json_contrato(respuesta: str, entrada: EntradaPlan) -> None:
    with pytest.raises(ErrorBrock):
        validar_plan(respuesta, entrada)


@pytest.mark.parametrize("campo,valor", [
    ("cantidad", 0), ("cantidad", -1), ("cantidad", "100"), ("cantidad", True),
    ("cantidad", float("nan")), ("cantidad", float("inf")),
    ("unidad", "libra"), ("pasillo", "OTRO_PASILLO"), ("extra", "no"),
])
def test_esquema_item(
    campo: str, valor: object, entrada: EntradaPlan, respuesta_plan: dict[str, Any]
) -> None:
    respuesta_plan["lista_compras"][0][campo] = valor
    with pytest.raises(ErrorBrock):
        validar_plan(respuesta_plan, entrada)


def test_dias_y_comidas_exactos(entrada: EntradaPlan, respuesta_plan: dict[str, Any]) -> None:
    respuesta_plan["dias"][0]["dia"] = 2
    with pytest.raises(ErrorBrock, match="días"):
        validar_plan(respuesta_plan, entrada)
    respuesta_plan["dias"][0]["dia"] = 1
    respuesta_plan["dias"][0]["comidas"] *= 2
    with pytest.raises(ErrorBrock, match="comidas"):
        validar_plan(respuesta_plan, entrada)


def test_cantidades_unidades_agrupadas(
    entrada: EntradaPlan, respuesta_plan: dict[str, Any]
) -> None:
    ingredientes = respuesta_plan["dias"][0]["comidas"][0]["ingredientes"]
    ingredientes.append({"nombre": "arvejas", "cantidad": 0.1, "unidad": "kg", "en_casa": False})
    respuesta_plan["lista_compras"][0]["cantidad"] = 0.2
    respuesta_plan["lista_compras"][0]["unidad"] = "kg"
    validar_plan(respuesta_plan, entrada)
    respuesta_plan["lista_compras"][0]["cantidad"] = 0.3
    with pytest.raises(ErrorBrock, match="cantidades"):
        validar_plan(respuesta_plan, entrada)


def test_no_comprar_disponible_y_si_compra_parcial(
    entrada: EntradaPlan, respuesta_plan: dict[str, Any]
) -> None:
    ingredientes = respuesta_plan["dias"][0]["comidas"][0]["ingredientes"]
    ingredientes.append({"nombre": "Arvejas", "cantidad": 50, "unidad": "g", "en_casa": True})
    validar_plan(respuesta_plan, entrada)  # Compra solo los 100 g faltantes.
    ingredientes[1]["en_casa"] = True
    with pytest.raises(ErrorBrock, match="cantidades"):
        validar_plan(respuesta_plan, entrada)


def test_duplicados_id_y_nombre(entrada: EntradaPlan, respuesta_plan: dict[str, Any]) -> None:
    respuesta_plan["lista_compras"].append(dict(respuesta_plan["lista_compras"][0]))
    with pytest.raises(ErrorBrock, match="identificadores"):
        validar_plan(respuesta_plan, entrada)
    respuesta_plan["lista_compras"][1]["id"] = "it_02"
    with pytest.raises(ErrorBrock, match="agrupar"):
        validar_plan(respuesta_plan, entrada)
