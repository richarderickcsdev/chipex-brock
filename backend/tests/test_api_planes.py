import json
import re
from collections.abc import Callable
from typing import Any

import boto3
import pytest
from botocore.exceptions import ReadTimeoutError
from botocore.stub import ANY, Stubber

from backend.api.http import Solicitud
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import Perfil


def test_post_reserva_snapshot_y_evento(
    api: Callable[..., dict[str, Any]], repo: Repositorio, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo.guardar_perfil(Perfil(personas_defecto=2, evitar=["ajo"]))
    capturados = []

    class LambdaSimulada:
        def invoke(self, **datos: Any) -> dict[str, int]:
            capturados.append(datos)
            return {"StatusCode": 202}

    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: LambdaSimulada()))
    resultado = api("POST", "/planes", {"personas": 2, "dias": 1,
                                        "ingredientes_texto": "  pollo,\n arroz  "})
    assert resultado["statusCode"] == 202
    datos = json.loads(resultado["body"])
    assert re.fullmatch(r"[0-7][0-9A-HJKMNP-TV-Z]{25}", datos["planId"])
    plan = repo.plan(datos["planId"])
    assert plan["estado"] == "GENERANDO"
    assert plan["entrada"]["ingredientes_texto"] == "pollo, arroz"
    assert plan["evitar"] == ["ajo"]
    assert capturados[0]["InvocationType"] == "Event"
    assert json.loads(capturados[0]["Payload"]) == {
        "task": "GENERAR_PLAN", "sub": "usuario-a", "planId": datos["planId"],
    }
    assert json.loads(api("GET", "/perfil")["body"])["cupo"]["restantes"] == 4


@pytest.mark.parametrize("datos", [{"personas": 0}, {"personas": 2, "dias": 8},
    {"personas": 2, "comidas": []}, {"personas": 2, "sub": "otro"}])
def test_post_invalido_no_reserva(
    api: Callable[..., dict[str, Any]], datos: dict[str, Any], repo: Repositorio,
) -> None:
    assert api("POST", "/planes", datos)["statusCode"] == 400
    assert repo.historial()["planes"] == []


def test_rechazo_lambda_devuelve_cupo(
    api: Callable[..., dict[str, Any]], repo: Repositorio, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = boto3.client("lambda")
    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: cliente))
    with Stubber(cliente) as stub:
        stub.add_client_error("invoke", service_error_code="TooManyRequestsException",
            expected_params={"FunctionName": "brock-generador-test", "InvocationType": "Event",
                             "Payload": ANY})
        assert api("POST", "/planes", {"personas": 2})["statusCode"] == 500
    assert repo.historial()["planes"][0]["estado"] == "ERROR"
    assert json.loads(api("GET", "/perfil")["body"])["cupo"]["usados"] == 0


def test_timeout_ambiguo_no_devuelve_cupo_inmediatamente(
    api: Callable[..., dict[str, Any]], repo: Repositorio, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class LambdaSimulada:
        def invoke(self, **datos: Any) -> None:
            raise ReadTimeoutError(endpoint_url="https://lambda.test")

    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: LambdaSimulada()))
    assert api("POST", "/planes", {"personas": 2})["statusCode"] == 202
    assert repo.historial()["planes"][0]["estado"] == "GENERANDO"
