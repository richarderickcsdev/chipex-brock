# mypy: disable-error-code="no-redef"
"""Generador asíncrono: Bedrock propone; el código valida y persiste."""

import json
import os
import time
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

if __package__ == "backend.generador":
    from ..compartido.cupo import Cupo
    from ..compartido.dynamo import Repositorio
    from ..compartido.errores import CodigoError, ErrorBrock
    from ..compartido.esquema import EntradaPlan, MetadatosGeneracion
    from ..compartido.validacion import json_publico, validar_plan
    from .bedrock import generar
    from .prompt import PROMPT_VERSION, mensajes
else:
    from compartido.cupo import Cupo  # type: ignore[import-not-found]
    from compartido.dynamo import Repositorio  # type: ignore[import-not-found]
    from compartido.errores import CodigoError, ErrorBrock  # type: ignore[import-not-found]
    from compartido.esquema import (  # type: ignore[import-not-found]
        EntradaPlan,
        MetadatosGeneracion,
    )
    from compartido.validacion import (  # type: ignore[import-not-found]
        json_publico,
        validar_plan,
    )
    from generador.bedrock import generar  # type: ignore[import-not-found]
    from generador.prompt import PROMPT_VERSION, mensajes  # type: ignore[import-not-found]


def log_metricas(plan_id: str, modelo: str, valido: bool, tokens_in: int,
                 tokens_out: int, latencia_ms: int) -> None:
    evento = {
        "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
            "Namespace": os.environ.get("POWERTOOLS_METRICS_NAMESPACE", "Brock"),
            "Dimensions": [["Stage"]], "Metrics": [
                {"Name": "TokensIn", "Unit": "Count"},
                {"Name": "TokensOut", "Unit": "Count"},
                {"Name": "GeneracionValida", "Unit": "Count"},
                {"Name": "LatenciaGeneracion", "Unit": "Milliseconds"},
            ],
        }]},
        "Stage": os.environ.get("STAGE", "unknown"), "PlanId": plan_id,
        "Model": modelo, "TokensIn": tokens_in, "TokensOut": tokens_out,
        "GeneracionValida": 1 if valido else 0, "LatenciaGeneracion": latencia_ms,
    }
    print(json.dumps(evento, ensure_ascii=False))


def datos_evento(evento: dict[str, Any]) -> tuple[str, str]:
    if evento.get("task") != "GENERAR_PLAN":
        raise ErrorBrock(CodigoError.VALIDACION, "Tarea de generación no válida.")
    sub, plan_id = evento.get("sub"), evento.get("planId")
    if not isinstance(sub, str) or not isinstance(plan_id, str):
        raise ErrorBrock(CodigoError.VALIDACION, "Tarea de generación incompleta.")
    return sub, plan_id


def handler(event: dict[str, Any], context: Any) -> None:
    inicio = time.perf_counter()
    sub, plan_id = datos_evento(event)
    repo = Repositorio.desde_entorno(sub)
    plan = repo.plan(plan_id)
    if plan["estado"] != "GENERANDO":
        return
    try:
        entrada = EntradaPlan.model_validate_json(json_publico(plan["entrada"]))
        evitar = list(plan.get("evitar", []))
        sistema, usuario = mensajes(entrada, evitar)
        modelo = os.environ["BEDROCK_MODEL_ID"]
        tokens_in = tokens_out = 0
        for intento in range(2):
            texto, tokens_in, tokens_out = generar(sistema, usuario)
            try:
                resultado = validar_plan(texto, entrada, evitar)
                break
            except ErrorBrock as exc:
                if intento == 1:
                    raise
                usuario += (
                    "\nLa respuesta anterior no fue válida. Corrige este problema y "
                    f"devuelve únicamente el JSON: {exc.mensaje}"
                )
        else:
            raise ValueError("No se obtuvo un plan válido.")
        latencia = round((time.perf_counter() - inicio) * 1000)
        repo.finalizar(plan_id, resultado, MetadatosGeneracion(
            prompt_version=PROMPT_VERSION, modelo=modelo, tokens_in=tokens_in,
            tokens_out=tokens_out, latencia_ms=latencia,
        ))
        log_metricas(plan_id, modelo, True, tokens_in, tokens_out, latencia)
    except (ErrorBrock, ValueError, ClientError, BotoCoreError) as exc:
        latencia = round((time.perf_counter() - inicio) * 1000)
        modelo = os.environ.get("BEDROCK_MODEL_ID", "desconocido")
        log_metricas(plan_id, modelo, False, locals().get("tokens_in", 0),
                     locals().get("tokens_out", 0), latencia)
        try:
            Cupo(repo).devolver(plan_id, "No pudimos generar el plan. Inténtalo de nuevo.")
        except ErrorBrock as compensacion:
            if compensacion.codigo not in {CodigoError.CONFLICTO, CodigoError.NO_ENCONTRADO}:
                raise
        print(json.dumps({"resultado": "ERROR_GENERACION", "planId": plan_id,
                          "tipo": type(exc).__name__}, ensure_ascii=False))
