"""Repositorio ligado al sub autenticado; no acepta PK aportadas por el cliente."""

import base64
import binascii
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .errores import CodigoError, ErrorBrock, no_encontrado
from .esquema import EntradaPlan, MetadatosGeneracion, Perfil, PlanGenerado
from .validacion import json_publico

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table


def ahora_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def para_dynamo(datos: dict[str, Any]) -> dict[str, Any]:
    return dict(json.loads(json_publico(datos), parse_float=Decimal))


def atributos(datos: dict[str, Any]) -> dict[str, Any]:
    serializador = TypeSerializer()
    return {k: serializador.serialize(v) for k, v in para_dynamo(datos).items()}


def es_condicional(exc: ClientError) -> bool:
    codigo = exc.response["Error"]["Code"]
    return codigo == "ConditionalCheckFailedException" or (
        codigo == "TransactionCanceledException"
        and any(r.get("Code") == "ConditionalCheckFailed"
                for r in exc.response.get("CancellationReasons", []))
    )


class Repositorio:
    def __init__(self, tabla: "Table", sub: str) -> None:
        if not sub or len(sub) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", sub):
            raise ErrorBrock(CodigoError.NO_AUTORIZADO, "Inicia sesión para continuar.")
        self.tabla = tabla
        # El cliente del Resource transforma atributos automáticamente; las
        # transacciones usan un cliente independiente con AttributeValue explícito.
        self.cliente = boto3.client(
            "dynamodb", region_name=tabla.meta.client.meta.region_name,
            endpoint_url=tabla.meta.client.meta.endpoint_url,
        )
        self.pk = f"USER#{sub}"

    @classmethod
    def desde_entorno(cls, sub: str) -> "Repositorio":
        import os

        return cls(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]), sub)

    def clave(self, sk: str) -> dict[str, str]:
        return {"PK": self.pk, "SK": sk}

    def obtener(self, sk: str) -> dict[str, Any] | None:
        respuesta = self.tabla.get_item(Key=self.clave(sk), ConsistentRead=True)
        item = respuesta.get("Item")
        return dict(item) if item is not None else None

    def perfil(self) -> dict[str, Any]:
        return self.obtener("PROFILE") or {**self.clave("PROFILE"), **Perfil().model_dump()}

    def guardar_perfil(self, perfil: Perfil) -> dict[str, Any]:
        respuesta = self.tabla.update_item(
            Key=self.clave("PROFILE"),
            UpdateExpression="SET personas_defecto = :p, evitar = :e, "
                             "creado_en = if_not_exists(creado_en, :t)",
            ExpressionAttributeValues={":p": perfil.personas_defecto, ":e": perfil.evitar,
                                       ":t": ahora_iso()},
            ReturnValues="ALL_NEW",
        )
        return dict(respuesta["Attributes"])

    def eliminar_datos_usuario(self) -> None:
        """Borra por lotes; el llamador debe impedir nuevas escrituras de la cuenta."""
        claves: list[dict[str, Any]] = []
        opciones: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(self.pk), "ConsistentRead": True, "Limit": 25,
        }
        while True:
            respuesta = self.tabla.query(**opciones)
            for item in respuesta.get("Items", []):
                if item.get("estado") == "GENERANDO":
                    raise ErrorBrock(CodigoError.CONFLICTO, "Espera a que terminen tus planes.")
                claves.append({"PK": item["PK"], "SK": item["SK"]})
            siguiente = respuesta.get("LastEvaluatedKey")
            if not siguiente:
                break
            opciones["ExclusiveStartKey"] = siguiente
        with self.tabla.batch_writer() as lote:
            for clave in claves:
                lote.delete_item(Key=clave)
