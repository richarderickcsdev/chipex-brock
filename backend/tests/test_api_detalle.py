import json
from collections.abc import Callable
from typing import Any

from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion
from backend.compartido.validacion import validar_plan
from backend.tests.conftest import PLAN_ID


def test_detalle_estados_y_campos_publicos(
    api: Callable[..., dict[str, Any]], cupo: Cupo, repo: Repositorio,
    entrada: EntradaPlan, respuesta_plan: dict[str, Any], metadatos: MetadatosGeneracion,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    datos = json.loads(api("GET", f"/planes/{PLAN_ID}")["body"])
    assert datos["estado"] == "GENERANDO"
    assert datos["entrada"]["personas"] == 2
    assert not {"PK", "SK", "quota_fecha", "cupo_devuelto", "evitar"}.intersection(datos)
    repo.finalizar(PLAN_ID, validar_plan(respuesta_plan, entrada), metadatos)
    datos = json.loads(api("GET", f"/planes/{PLAN_ID}")["body"])
    assert datos["estado"] == "LISTO"
    assert datos["menu"]["dias"][0]["comidas"][0]["nombre"] == "Arroz con arvejas"
    assert api("GET", f"/planes/{PLAN_ID}", sub="usuario-b")["statusCode"] == 404
    assert api("GET", "/planes/invalido")["statusCode"] == 404


def test_detalle_error_preserva_entrada(
    api: Callable[..., dict[str, Any]], cupo: Cupo, entrada: EntradaPlan,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    cupo.devolver(PLAN_ID)
    datos = json.loads(api("GET", f"/planes/{PLAN_ID}")["body"])
    assert datos["estado"] == "ERROR"
    assert datos["entrada"] == entrada.model_dump()
    assert datos["error"] == "No pudimos generar el plan."
