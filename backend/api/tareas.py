"""Entrada privada para destinos asíncronos Lambda; no se toma del body HTTP."""

from typing import Any

from .compartidos import CodigoError, Cupo, ErrorBrock, Repositorio
from .http import respuesta


def procesar(evento: dict[str, Any]) -> dict[str, Any]:
    contexto = evento.get("requestContext") or {}
    payload = evento.get("requestPayload")
    if (evento.get("version") == "1.0" and isinstance(payload, dict)
            and contexto.get("condition") in {"RetriesExhausted", "EventAgeExceeded"}
            and payload.get("task") == "GENERAR_PLAN"):
        sub, plan_id = payload.get("sub"), payload.get("planId")
        if not isinstance(sub, str) or not isinstance(plan_id, str):
            raise ErrorBrock(CodigoError.NO_AUTORIZADO, "Evento interno no válido.")
        repo = Repositorio.desde_entorno(sub)
        try:
            Cupo(repo).devolver(plan_id, "No pudimos completar la generación. Inténtalo más tarde.")
        except ErrorBrock as exc:
            if exc.codigo not in {CodigoError.CONFLICTO, CodigoError.NO_ENCONTRADO}:
                raise
        return respuesta(200, {"procesado": True})
    raise ErrorBrock(CodigoError.NO_AUTORIZADO, "Evento interno no válido.")
