"""Fixtures sin acceso a AWS real."""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import boto3
import pytest
from moto import mock_aws

from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

PLAN_ID = "01J9ZK3Q8M4X7R2T6V5B1N0WCD"


@pytest.fixture
def tabla(monkeypatch: pytest.MonkeyPatch) -> Iterator["Table"]:
    for nombre in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        monkeypatch.setenv(nombre, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="us-east-1").create_table(
            TableName="brock-test", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                       {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                  {"AttributeName": "SK", "AttributeType": "S"}],
        )


@pytest.fixture
def repo(tabla: "Table") -> Repositorio:
    return Repositorio(tabla, "usuario-a")


@pytest.fixture
def cupo(repo: Repositorio) -> Cupo:
    return Cupo(repo, limite=5, reloj=lambda: datetime(2026, 10, 4, 12, tzinfo=UTC))


@pytest.fixture
def entrada() -> EntradaPlan:
    return EntradaPlan(personas=2, dias=1, comidas=["ALMUERZO"])


@pytest.fixture
def metadatos() -> MetadatosGeneracion:
    return MetadatosGeneracion(prompt_version="v1", modelo="modelo-test", tokens_in=100,
                              tokens_out=200, latencia_ms=1000)


@pytest.fixture
def respuesta_plan() -> dict[str, Any]:
    return {
        "version_esquema": "1.0",
        "dias": [{"dia": 1, "comidas": [{
            "tipo": "ALMUERZO", "nombre": "Arroz con arvejas", "tiempo_min": 20,
            "ingredientes": [
                {"nombre": "Arroz", "cantidad": 200, "unidad": "g", "en_casa": True},
                {"nombre": "Arvejas", "cantidad": 100, "unidad": "g", "en_casa": False},
            ], "pasos": ["Cocina el arroz.", "Agrega las arvejas."],
        }]}],
        "lista_compras": [{"id": "it_01", "nombre": "Arvejas", "cantidad": 100,
                           "unidad": "g", "pasillo": "DESPENSA"}],
    }


@pytest.fixture
def api(tabla: "Table", monkeypatch: pytest.MonkeyPatch) -> Callable[..., dict[str, Any]]:
    from backend.api import http
    from backend.api.app import handler

    monkeypatch.setenv("TABLE_NAME", tabla.name)
    monkeypatch.setenv("FN_GENERADOR", "brock-generador-test")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "brock-api-test")
    monkeypatch.setenv("CUPO_DIARIO", "5")
    monkeypatch.setattr(http, "ahora_utc", lambda: datetime(2026, 10, 4, 12, tzinfo=UTC))

    def llamar(metodo: str, path: str, body: object = None, sub: str = "usuario-a",
               query: dict[str, str] | None = None,
               claims: dict[str, Any] | None = None) -> dict[str, Any]:
        evento = {
            "version": "2.0", "rawPath": path, "queryStringParameters": query,
            "body": body if isinstance(body, str) else json.dumps(body),
            "requestContext": {"requestId": "req-test", "stage": "dev",
                "http": {"method": metodo, "path": path},
                "authorizer": {"jwt": {"claims": claims or {"sub": sub}}}},
        }
        return handler(evento, None)

    return llamar
