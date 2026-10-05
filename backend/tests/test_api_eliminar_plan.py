import json
from collections.abc import Callable
from typing import Any

from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion
from backend.compartido.validacion import validar_plan
from backend.tests.conftest import PLAN_ID


def test_eliminar_204_no_devuelve_cupo_listo(
    api: Callable[..., dict[str, Any]], cupo: Cupo, repo: Repositorio,
    entrada: EntradaPlan, respuesta_plan: dict[str, Any], metadatos: MetadatosGeneracion,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    assert api("DELETE", f"/planes/{PLAN_ID}")["statusCode"] == 409
    assert api("DELETE", f"/planes/{PLAN_ID}", sub="usuario-b")["statusCode"] == 404
    repo.finalizar(PLAN_ID, validar_plan(respuesta_plan, entrada), metadatos)
    resultado = api("DELETE", f"/planes/{PLAN_ID}")
    assert resultado["statusCode"] == 204
    assert resultado["body"] == ""
    assert api("GET", f"/planes/{PLAN_ID}")["statusCode"] == 404
    assert api("GET", f"/planes/{PLAN_ID}/lista")["statusCode"] == 404
    assert json.loads(api("GET", "/perfil")["body"])["cupo"]["usados"] == 1
