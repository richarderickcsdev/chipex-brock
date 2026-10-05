"""Router de HTTP API v2; la identidad procede del autorizador JWT."""

import re
import time
from typing import Any

from .compartidos import CodigoError, ErrorBrock, no_encontrado
from .http import Ruta, Solicitud, identidad, registrar
from .perfil import RUTAS as RUTAS_PERFIL

RUTAS: list[Ruta] = [*RUTAS_PERFIL]


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    inicio = time.perf_counter()
    sub, ruta, tipo_error = "", "DESCONOCIDA", None
    request_id = str((event.get("requestContext") or {}).get("requestId")
                     or getattr(context, "aws_request_id", "local"))
    try:
        if event.get("version") != "2.0":
            raise ErrorBrock(CodigoError.NO_AUTORIZADO, "Inicia sesión para continuar.")
        sub, claims = identidad(event)
        http = event.get("requestContext", {}).get("http", {})
        metodo = http.get("method")
        path = event.get("rawPath", http.get("path"))
        if not isinstance(path, str):
            raise no_encontrado()
        stage = event.get("requestContext", {}).get("stage")
        if isinstance(stage, str) and stage != "$default" and path.startswith(f"/{stage}/"):
            path = path[len(stage) + 1:]
        for esperado, patron, nombre, ejecutar in RUTAS:
            match = re.fullmatch(patron, path)
            if esperado == metodo and match:
                ruta = nombre
                solicitud = Solicitud(event, sub, claims, match.groupdict())
                resultado = ejecutar(solicitud)
                break
        else:
            raise no_encontrado()
    except ErrorBrock as exc:
        resultado = exc.respuesta()
    except Exception as exc:
        tipo_error = type(exc).__name__
        resultado = ErrorBrock(
            CodigoError.ERROR_INTERNO,
            "No pudimos completar la solicitud. Inténtalo más tarde.",
        ).respuesta()
    resultado["headers"]["Cache-Control"] = "no-store"
    registrar(request_id, ruta, sub, resultado["statusCode"], inicio, tipo_error)
    return resultado
