import json
from collections.abc import Callable
from typing import Any

from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion
from backend.compartido.validacion import validar_plan
from backend.tests.conftest import PLAN_ID


def test_lista_publica_y_aislamiento(
    api: Callable[..., dict[str, Any]], cupo: Cupo, repo: Repositorio,
    entrada: EntradaPlan, respuesta_plan: dict[str, Any], metadatos: MetadatosGeneracion,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    assert api("GET", f"/planes/{PLAN_ID}/lista")["statusCode"] == 404
    repo.finalizar(PLAN_ID, validar_plan(respuesta_plan, entrada), metadatos)
    datos = json.loads(api("GET", f"/planes/{PLAN_ID}/lista")["body"])
    assert datos["items"][0] == {"id": "it_01", "nombre": "Arvejas", "cantidad": 100,
        "unidad": "g", "pasillo": "DESPENSA", "comprado": False}
    assert "PK" not in datos
    assert api("GET", f"/planes/{PLAN_ID}/lista", sub="usuario-b")["statusCode"] == 404
