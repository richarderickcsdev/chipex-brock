"""Flujo integrado API -> DynamoDB -> generador -> API."""

import json
from collections.abc import Callable
from typing import Any

from backend.api.http import Solicitud
from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion
from backend.compartido.validacion import validar_plan
from backend.generador import app as generador_app
from backend.tests.conftest import PLAN_ID


def test_flujo_completo_plan_lista_historial_y_borrado(
    api: Callable[..., dict[str, Any]], tabla: Any, respuesta_plan: dict[str, Any],
    monkeypatch: Any,
) -> None:
    generador_app_modelo = json.dumps(respuesta_plan)
    eventos: list[dict[str, Any]] = []

    class LambdaSimulada:
        def invoke(self, **datos: Any) -> dict[str, int]:
            eventos.append(json.loads(datos["Payload"]))
            return {"StatusCode": 202}

    monkeypatch.setenv("BEDROCK_MODEL_ID", "modelo-integracion")
    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: LambdaSimulada()))
    monkeypatch.setattr(generador_app, "generar",
                        lambda *_: (generador_app_modelo, 100, 200))
    assert api("PUT", "/perfil", {"personas_defecto": 2})["statusCode"] == 200
    creado = json.loads(api("POST", "/planes", {
        "ingredientes_texto": "arroz, arvejas", "personas": 2, "dias": 1,
        "comidas": ["ALMUERZO"],
    })["body"])
    assert creado["estado"] == "GENERANDO"
    assert eventos[0]["planId"] == creado["planId"]
    generador_app.handler(eventos[0], None)
    plan_id = creado["planId"]
    assert json.loads(api("GET", f"/planes/{plan_id}")["body"])["estado"] == "LISTO"
    lista = json.loads(api("GET", f"/planes/{plan_id}/lista")["body"])
    assert lista["items"][0]["comprado"] is False
    assert api("PATCH", f"/planes/{plan_id}/lista/items/it_01",
               {"comprado": True})["statusCode"] == 200
    historial = json.loads(api("GET", "/planes")["body"])
    assert historial["planes"][0]["planId"] == plan_id
    assert api("DELETE", f"/planes/{plan_id}")["statusCode"] == 204


def test_flujo_integrado_aisla_datos_de_usuario_b(
    api: Callable[..., dict[str, Any]], cupo: Cupo, repo: Repositorio,
    entrada: EntradaPlan, respuesta_plan: dict[str, Any], metadatos: MetadatosGeneracion,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    repo.finalizar(PLAN_ID, validar_plan(respuesta_plan, entrada), metadatos)
    ruta = f"/planes/{PLAN_ID}"
    assert api("GET", ruta, sub="usuario-b")["statusCode"] == 404
    assert api("DELETE", ruta, sub="usuario-b")["statusCode"] == 404
    assert api("GET", f"{ruta}/lista", sub="usuario-b")["statusCode"] == 404
    assert api("PATCH", f"/planes/{PLAN_ID}/lista/items/it_01", {"comprado": True},
               sub="usuario-b")["statusCode"] == 404
