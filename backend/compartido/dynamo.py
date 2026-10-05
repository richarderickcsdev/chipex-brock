"""Repositorio ligado al sub autenticado; no acepta PK aportadas por el cliente."""

import base64
import binascii
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .errores import CodigoError, ErrorBrock, no_encontrado
from .esquema import EntradaPlan, MetadatosGeneracion, Perfil, PlanGenerado
from .validacion import json_publico, validar_plan

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

    @staticmethod
    def validar_id(plan_id: str) -> None:
        if not re.fullmatch(r"[0-7][0-9A-HJKMNP-TV-Z]{25}", plan_id):
            raise no_encontrado()

    def obtener(self, sk: str) -> dict[str, Any] | None:
        respuesta = self.tabla.get_item(Key=self.clave(sk), ConsistentRead=True)
        item = respuesta.get("Item")
        return dict(item) if item is not None else None

    def exigir_activa(self) -> None:
        cuenta = self.obtener("ACCOUNT")
        if cuenta and cuenta.get("estado") == "BORRADA":
            raise ErrorBrock(CodigoError.NO_AUTORIZADO, "La cuenta fue eliminada.")
        if cuenta and cuenta.get("estado") == "BORRANDO":
            raise ErrorBrock(CodigoError.CONFLICTO, "La eliminación de tu cuenta está en proceso.")

    def condicion_cuenta(self) -> dict[str, Any]:
        return {"ConditionCheck": {
            "TableName": self.tabla.name, "Key": atributos(self.clave("ACCOUNT")),
            "ConditionExpression": "attribute_not_exists(PK) OR #estado = :activa",
            "ExpressionAttributeNames": {"#estado": "estado"},
            "ExpressionAttributeValues": atributos({":activa": "ACTIVA"}),
        }}

    def perfil(self) -> dict[str, Any]:
        return self.obtener("PROFILE") or {**self.clave("PROFILE"), **Perfil().model_dump()}

    def guardar_perfil(self, perfil: Perfil) -> dict[str, Any]:
        self.exigir_activa()
        try:
            self.cliente.transact_write_items(TransactItems=cast(Any, [
                {"Update": {"TableName": self.tabla.name,
                    "Key": atributos(self.clave("PROFILE")),
                    "UpdateExpression": "SET personas_defecto = :p, evitar = :e, "
                                        "creado_en = if_not_exists(creado_en, :t)",
                    "ExpressionAttributeValues": atributos({":p": perfil.personas_defecto,
                        ":e": perfil.evitar, ":t": ahora_iso()})}},
                self.condicion_cuenta(),
            ]))
        except ClientError as exc:
            if es_condicional(exc):
                self.exigir_activa()
            raise
        return self.perfil()

    def plan(self, plan_id: str) -> dict[str, Any]:
        self.validar_id(plan_id)
        item = self.obtener(f"PLAN#{plan_id}")
        if item is None:
            raise no_encontrado()
        return item

    def lista(self, plan_id: str) -> dict[str, Any]:
        self.validar_id(plan_id)
        item = self.obtener(f"LIST#{plan_id}")
        if item is None:
            raise no_encontrado()
        return item

    def historial(self, limite: int = 20, cursor: str | None = None) -> dict[str, Any]:
        if type(limite) is not int or not 1 <= limite <= 20:
            raise ErrorBrock(CodigoError.VALIDACION, "El límite debe estar entre 1 y 20.")
        opciones: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(self.pk) & Key("SK").begins_with("PLAN#"),
            "ScanIndexForward": False, "Limit": limite, "ConsistentRead": True,
        }
        if cursor is not None:
            try:
                if len(cursor) > 2048:
                    raise ValueError
                clave = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
                if (not isinstance(clave, dict) or set(clave) != {"PK", "SK"}
                        or clave["PK"] != self.pk or not isinstance(clave["SK"], str)
                        or not clave["SK"].startswith("PLAN#")):
                    raise ValueError
                self.validar_id(clave["SK"][5:])
                opciones["ExclusiveStartKey"] = clave
            except (ValueError, TypeError, binascii.Error, ErrorBrock) as exc:
                raise ErrorBrock(CodigoError.VALIDACION, "El cursor no es válido.") from exc
        respuesta = self.tabla.query(**opciones)
        siguiente = respuesta.get("LastEvaluatedKey")
        token = (base64.urlsafe_b64encode(json_publico(siguiente).encode()).decode()
                 if siguiente else None)
        return {"planes": respuesta.get("Items", []), "cursor": token}

    def marcar_item(self, plan_id: str, item_id: str, comprado: bool) -> dict[str, Any]:
        self.validar_id(plan_id)
        if type(comprado) is not bool:
            raise ErrorBrock(CodigoError.VALIDACION, "La marca debe ser verdadero o falso.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", item_id):
            raise no_encontrado()
        try:
            resultado = self.tabla.update_item(
                Key=self.clave(f"LIST#{plan_id}"),
                UpdateExpression="SET #items.#id.comprado = :v, actualizado_en = :t",
                ConditionExpression="attribute_exists(#items.#id)",
                ExpressionAttributeNames={"#items": "items", "#id": item_id},
                ExpressionAttributeValues={":v": comprado, ":t": ahora_iso()},
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if es_condicional(exc):
                raise no_encontrado() from exc
            raise
        return dict(resultado["Attributes"])

    def finalizar(
        self, plan_id: str, resultado: PlanGenerado, metadatos: MetadatosGeneracion
    ) -> None:
        self.exigir_activa()
        guardado = self.plan(plan_id)
        entrada = EntradaPlan.model_validate_json(json_publico(guardado["entrada"]))
        resultado = validar_plan(resultado.model_dump(mode="json"), entrada, guardado["evitar"])
        menu = resultado.model_dump(mode="json", exclude={"lista_compras"})
        lista = {**self.clave(f"LIST#{plan_id}"), "actualizado_en": ahora_iso(), "items": {
            item.id: {**item.model_dump(mode="json", exclude={"id"}), "comprado": False}
            for item in resultado.lista_compras
        }}
        # Margen para nombres de atributos y representación interna de DynamoDB.
        documento = {**guardado, "menu": menu, **metadatos.model_dump()}
        if len(json_publico(documento).encode()) > 350_000:
            raise ErrorBrock(CodigoError.VALIDACION, "El menú supera el tamaño permitido.")
        try:
            self.cliente.transact_write_items(TransactItems=cast(Any, [
                {"Update": {
                    "TableName": self.tabla.name, "Key": atributos(self.clave(f"PLAN#{plan_id}")),
                    "UpdateExpression": "SET estado = :listo, menu = :m, "
                                        "prompt_version = :pv, modelo = :model, "
                                        "tokens_in = :ti, tokens_out = :to, "
                                        "latencia_ms = :lat, actualizado_en = :t",
                    "ConditionExpression": "estado = :generando AND cupo_devuelto = :no",
                    "ExpressionAttributeValues": atributos({":listo": "LISTO", ":m": menu,
                        ":pv": metadatos.prompt_version, ":model": metadatos.modelo,
                        ":ti": metadatos.tokens_in, ":to": metadatos.tokens_out,
                        ":lat": metadatos.latencia_ms, ":t": ahora_iso(),
                        ":generando": "GENERANDO", ":no": False}),
                }},
                {"Put": {"TableName": self.tabla.name, "Item": atributos(lista),
                         "ConditionExpression": "attribute_not_exists(PK)"}},
                self.condicion_cuenta(),
            ]))
        except ClientError as exc:
            if es_condicional(exc):
                self.exigir_activa()
                raise ErrorBrock(CodigoError.CONFLICTO, "El plan ya terminó.") from exc
            raise

    def eliminar_plan(self, plan_id: str) -> None:
        self.plan(plan_id)
        try:
            self.cliente.transact_write_items(TransactItems=[
                {"Delete": {"TableName": self.tabla.name,
                    "Key": atributos(self.clave(f"PLAN#{plan_id}")),
                    "ConditionExpression": "attribute_exists(PK) AND estado <> :g",
                    "ExpressionAttributeValues": atributos({":g": "GENERANDO"})}},
                {"Delete": {"TableName": self.tabla.name,
                    "Key": atributos(self.clave(f"LIST#{plan_id}"))}},
            ])
        except ClientError as exc:
            if es_condicional(exc):
                self.plan(plan_id)
                raise ErrorBrock(CodigoError.CONFLICTO, "Espera a que termine el plan.") from exc
            raise

    def eliminar_datos_usuario(
        self, *, permitir_generando: bool = False, conservar_bloqueo: bool = False
    ) -> None:
        """Borra por lotes; el llamador debe impedir nuevas escrituras de la cuenta."""
        claves: list[dict[str, Any]] = []
        opciones: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(self.pk), "ConsistentRead": True, "Limit": 25,
        }
        while True:
            respuesta = self.tabla.query(**opciones)
            for item in respuesta.get("Items", []):
                if conservar_bloqueo and item["SK"] == "ACCOUNT":
                    continue
                if not permitir_generando and item.get("estado") == "GENERANDO":
                    raise ErrorBrock(CodigoError.CONFLICTO, "Espera a que terminen tus planes.")
                claves.append({"PK": item["PK"], "SK": item["SK"]})
            siguiente = respuesta.get("LastEvaluatedKey")
            if not siguiente:
                break
            opciones["ExclusiveStartKey"] = siguiente
        with self.tabla.batch_writer() as lote:
            for clave in claves:
                lote.delete_item(Key=clave)
