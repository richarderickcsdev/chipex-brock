"""Cliente Converse y normalización de su respuesta."""

import json
import os
from typing import Any

import boto3
from botocore.config import Config


def cliente() -> Any:
    return boto3.client("bedrock-runtime", config=Config(
        connect_timeout=5, read_timeout=55, retries={"total_max_attempts": 1},
    ))


def texto_converse(respuesta: dict[str, Any]) -> str:
    try:
        bloques = respuesta["output"]["message"]["content"]
        textos = [bloque["text"] for bloque in bloques if isinstance(bloque.get("text"), str)]
        texto = "".join(textos).strip()
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("Respuesta Bedrock sin texto.") from exc
    if not texto or texto.startswith("```") or not texto.startswith("{"):
        raise ValueError("Bedrock no devolvió JSON puro.")
    try:
        objeto = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError("Bedrock devolvió JSON inválido.") from exc
    if not isinstance(objeto, dict):
        raise ValueError("Bedrock no devolvió un objeto JSON.")
    return texto


def generar(sistema: str, usuario: str) -> tuple[str, int, int]:
    respuesta = cliente().converse(
        modelId=os.environ["BEDROCK_MODEL_ID"],
        system=[{"text": sistema}],
        messages=[{"role": "user", "content": [{"text": usuario}]}],
        inferenceConfig={
            "temperature": 0.1,
            "maxTokens": int(os.environ.get("MAX_OUTPUT_TOKENS", "8192")),
        },
    )
    uso = respuesta.get("usage", {})
    return (
        texto_converse(respuesta),
        int(uso.get("inputTokens", 0)),
        int(uso.get("outputTokens", 0)),
    )
