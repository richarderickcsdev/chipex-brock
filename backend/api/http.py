"""Transporte HTTP API v2, identidad, validación y respuestas públicas."""

import base64
import binascii
import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from typing import Any

import boto3
from botocore.config import Config

from .compartidos import CodigoError, Cupo, ErrorBrock, Repositorio, json_publico

Respuesta = dict[str, Any]


class _LambdaLocal:
    """Acepta la cola local; Bedrock real se prueba en F7/F9."""

    def invoke(self, **_: Any) -> dict[str, int]:
        return {"StatusCode": 202}


def ahora_utc() -> datetime:
    return datetime.now(UTC)


@dataclass
class Solicitud:
    evento: dict[str, Any]
    sub: str
    claims: dict[str, Any]
    parametros: dict[str, str]
    ahora: datetime = field(default_factory=lambda: ahora_utc())

    @cached_property
    def repo(self) -> Repositorio:
        return Repositorio.desde_entorno(self.sub)

    @cached_property
    def cupo(self) -> Cupo:
        return Cupo(self.repo, reloj=lambda: self.ahora)

    @cached_property
    def lambdas(self) -> Any:
        if os.environ.get("BROCK_LOCAL_MODE") == "true":
            return _LambdaLocal()
        # No reintentar Invoke automáticamente ante respuestas ambiguas.
        return boto3.client("lambda", config=Config(
            connect_timeout=2, read_timeout=3, retries={"total_max_attempts": 1},
        ))

    @cached_property
    def cognito(self) -> Any:
        return boto3.client("cognito-idp", config=Config(connect_timeout=2, read_timeout=3))

    def cuerpo(self) -> dict[str, Any]:
        raw = self.evento.get("body")
        try:
            if not isinstance(raw, str) or len(raw.encode()) > 24_000:
                raise ValueError
            if self.evento.get("isBase64Encoded") is True:
                raw = base64.b64decode(raw, validate=True).decode("utf-8")
            if len(raw.encode()) > 16_384:
                raise ValueError

            def objeto(pares: list[tuple[str, Any]]) -> dict[str, Any]:
                resultado: dict[str, Any] = {}
                for clave, valor in pares:
                    if clave in resultado:
                        raise ValueError
                    resultado[clave] = valor
                return resultado

            datos = json.loads(raw, object_pairs_hook=objeto,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(datos, dict):
                raise ValueError
            return datos
        except (ValueError, UnicodeError, binascii.Error) as exc:
            raise ErrorBrock(CodigoError.VALIDACION, "Envía un cuerpo JSON válido.") from exc

    def query(self, permitidos: set[str]) -> dict[str, str]:
        datos = self.evento.get("queryStringParameters") or {}
        if not isinstance(datos, dict) or set(datos) - permitidos or any(
            not isinstance(valor, str) for valor in datos.values()
        ):
            raise ErrorBrock(CodigoError.VALIDACION, "Revisa los parámetros de la consulta.")
        return dict(datos)


Ruta = tuple[str, str, str, Callable[[Solicitud], Respuesta]]


def identidad(evento: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    try:
        claims = evento["requestContext"]["authorizer"]["jwt"]["claims"]
        sub = claims["sub"]
        if not isinstance(claims, dict) or not isinstance(sub, str) or not sub:
            raise ValueError
        return sub, dict(claims)
    except (KeyError, TypeError, ValueError) as exc:
        raise ErrorBrock(CodigoError.NO_AUTORIZADO, "Inicia sesión para continuar.") from exc


def respuesta(estado: int, datos: object = None) -> Respuesta:
    return {"statusCode": estado, "headers": {
        "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
    }, "body": "" if estado == 204 else json_publico(datos)}


def registrar(request_id: str, ruta: str, sub: str, estado: int, inicio: float,
              tipo_error: str | None = None) -> None:
    datos = {"requestId": request_id, "ruta": ruta,
             "usuario": hashlib.sha256(sub.encode()).hexdigest()[:16] if sub else None,
             "duracion_ms": round((time.perf_counter() - inicio) * 1000), "estado": estado}
    if tipo_error:
        datos["tipo_error"] = tipo_error
    print(json.dumps(datos, ensure_ascii=False))
