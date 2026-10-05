"""Cupo diario atómico, asociado al día original e idempotente al devolver."""

import os
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from botocore.exceptions import ClientError

from .dynamo import Repositorio, atributos, es_condicional
from .errores import CodigoError, ErrorBrock
from .esquema import EntradaPlan, Perfil


class Cupo:
    def __init__(
        self, repositorio: Repositorio, limite: int | None = None,
        reloj: Callable[[], datetime] | None = None, zona: str | None = None,
    ) -> None:
        self.repo = repositorio
        self.limite = limite if limite is not None else int(os.environ.get("CUPO_DIARIO", "5"))
        if type(self.limite) is not int or not 1 <= self.limite <= 100:
            raise ValueError("CUPO_DIARIO debe estar entre 1 y 100.")
        self.zona = ZoneInfo(zona or os.environ.get("QUOTA_TIMEZONE", "America/Lima"))
        self.reloj = reloj or (lambda: datetime.now(UTC))

    def periodo(self) -> dict[str, Any]:
        ahora = self.reloj()
        if ahora.tzinfo is None:
            raise ValueError("El reloj debe incluir zona horaria.")
        local = ahora.astimezone(self.zona)
        manana = datetime.combine(local.date() + timedelta(days=1), time(), self.zona)
        return {
            "fecha": local.date().isoformat(),
            "reinicia": manana.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "ttl": int((manana + timedelta(days=2)).timestamp()),
            "ahora": ahora.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }

    def estado(self) -> dict[str, Any]:
        periodo = self.periodo()
        item = self.repo.obtener(f"QUOTA#{periodo['fecha']}")
        usados = int(item["usados"]) if item else 0
        return {"limite": self.limite, "usados": usados,
                "restantes": max(0, self.limite - usados), "reinicia": periodo["reinicia"]}

    def reservar(self, plan_id: str, entrada: EntradaPlan, evitar: list[str] | None = None) -> None:
        self.repo.exigir_activa()
        self.repo.validar_id(plan_id)
        preferencias = Perfil(evitar=evitar or []).evitar
        periodo = self.periodo()
        plan = {**self.repo.clave(f"PLAN#{plan_id}"), "planId": plan_id,
                "estado": "GENERANDO", "entrada": entrada.model_dump(), "evitar": preferencias,
                "creado_en": periodo["ahora"], "quota_fecha": periodo["fecha"],
                "cupo_devuelto": False}
        try:
            self.repo.cliente.transact_write_items(TransactItems=cast(Any, [
                {"Update": {
                    "TableName": self.repo.tabla.name,
                    "Key": atributos(self.repo.clave(f"QUOTA#{periodo['fecha']}")),
                    "UpdateExpression": "SET usados = if_not_exists(usados, :cero) + :uno, "
                                        "#ttl = :ttl",
                    "ExpressionAttributeNames": {"#ttl": "ttl"},
                    "ConditionExpression": "attribute_not_exists(usados) OR usados < :limite",
                    "ExpressionAttributeValues": atributos({":cero": 0, ":uno": 1,
                        ":ttl": periodo["ttl"], ":limite": self.limite}),
                }},
                {"Put": {"TableName": self.repo.tabla.name, "Item": atributos(plan),
                         "ConditionExpression": "attribute_not_exists(PK)"}},
                self.repo.condicion_cuenta(),
            ]))
        except ClientError as exc:
            if es_condicional(exc):
                self.repo.exigir_activa()
                if self.repo.obtener(f"PLAN#{plan_id}") is not None:
                    raise ErrorBrock(
                        CodigoError.CONFLICTO, "Este intento ya está registrado."
                    ) from exc
                raise ErrorBrock(CodigoError.CUPO_AGOTADO,
                    f"Alcanzaste el límite de {self.limite} planes por día.",
                    reinicia=periodo["reinicia"]) from exc
            raise

    def devolver(self, plan_id: str, mensaje: str = "No pudimos generar el plan.") -> bool:
        plan = self.repo.plan(plan_id)
        if plan.get("cupo_devuelto") is True:
            return False
        if plan["estado"] != "GENERANDO":
            raise ErrorBrock(CodigoError.CONFLICTO, "El plan ya terminó.")
        if not mensaje or len(mensaje) > 500:
            raise ValueError("El mensaje de error debe tener entre 1 y 500 caracteres.")
        try:
            self.repo.cliente.transact_write_items(TransactItems=[
                {"Update": {
                    "TableName": self.repo.tabla.name,
                    "Key": atributos(self.repo.clave(f"QUOTA#{plan['quota_fecha']}")),
                    "UpdateExpression": "SET usados = usados - :uno",
                    "ConditionExpression": "attribute_exists(usados) AND usados >= :uno",
                    "ExpressionAttributeValues": atributos({":uno": 1}),
                }},
                {"Update": {
                    "TableName": self.repo.tabla.name,
                    "Key": atributos(self.repo.clave(f"PLAN#{plan_id}")),
                    "UpdateExpression": "SET estado = :error, #error = :mensaje, "
                                        "cupo_devuelto = :si, actualizado_en = :t",
                    "ConditionExpression": "estado = :g AND cupo_devuelto = :no",
                    "ExpressionAttributeNames": {"#error": "error"},
                    "ExpressionAttributeValues": atributos({":error": "ERROR", ":mensaje": mensaje,
                        ":si": True, ":no": False, ":g": "GENERANDO",
                        ":t": self.periodo()["ahora"]}),
                }},
            ])
        except ClientError as exc:
            if es_condicional(exc):
                if self.repo.plan(plan_id).get("cupo_devuelto") is True:
                    return False
                raise ErrorBrock(CodigoError.CONFLICTO, "No se pudo devolver este cupo.") from exc
            raise
        return True
