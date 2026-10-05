"""Fixtures sin acceso a AWS real."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import boto3
import pytest
from moto import mock_aws

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
