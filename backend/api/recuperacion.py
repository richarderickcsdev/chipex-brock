"""Recupera cupo por fallo confirmado o al consultar un plan vencido."""

from datetime import datetime
from typing import Any

from .compartidos import CodigoError, ErrorBrock
from .http import Solicitud


def recuperar(solicitud: Solicitud, plan: dict[str, Any]) -> dict[str, Any]:
    if plan["estado"] != "GENERANDO":
        return plan
    creado = datetime.fromisoformat(plan["creado_en"].replace("Z", "+00:00"))
    if (solicitud.ahora - creado).total_seconds() < 60:
        return plan
    try:
        solicitud.cupo.devolver(plan["planId"], "La generación tardó demasiado. Puedes reintentar.")
    except ErrorBrock as exc:
        if exc.codigo != CodigoError.CONFLICTO:
            raise
    return solicitud.repo.plan(plan["planId"])


def recuperar_recientes(solicitud: Solicitud) -> None:
    for plan in solicitud.repo.historial()["planes"]:
        recuperar(solicitud, plan)
