"""Errores públicos sin detalles internos ni valores de las entradas."""

import json
from enum import StrEnum
from typing import Any


class CodigoError(StrEnum):
    VALIDACION = "VALIDACION"
    NO_AUTORIZADO = "NO_AUTORIZADO"
    NO_ENCONTRADO = "NO_ENCONTRADO"
    CUPO_AGOTADO = "CUPO_AGOTADO"
    CONFLICTO = "CONFLICTO"
    ERROR_INTERNO = "ERROR_INTERNO"


ESTADOS_HTTP = {
    CodigoError.VALIDACION: 400,
    CodigoError.NO_AUTORIZADO: 401,
    CodigoError.NO_ENCONTRADO: 404,
    CodigoError.CUPO_AGOTADO: 429,
    CodigoError.CONFLICTO: 409,
    CodigoError.ERROR_INTERNO: 500,
}


class ErrorBrock(Exception):
    def __init__(
        self, codigo: CodigoError, mensaje: str, *, reinicia: str | None = None
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.reinicia = reinicia

    def cuerpo(self) -> dict[str, Any]:
        error = {"codigo": self.codigo.value, "mensaje": self.mensaje}
        if self.reinicia is not None:
            error["reinicia"] = self.reinicia
        return {"error": error}

    def respuesta(self) -> dict[str, Any]:
        return {
            "statusCode": ESTADOS_HTTP[self.codigo],
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps(self.cuerpo(), ensure_ascii=False),
        }


def no_encontrado() -> ErrorBrock:
    return ErrorBrock(CodigoError.NO_ENCONTRADO, "No se encontró el recurso solicitado.")
