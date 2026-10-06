# mypy: disable-error-code="no-redef"
"""Construcción determinista de los mensajes enviados a Bedrock."""

from pathlib import Path

if __package__ == "backend.generador":
    from ..compartido.esquema import EntradaPlan
else:
    from compartido.esquema import EntradaPlan  # type: ignore[import-not-found]

PROMPT_VERSION = "v1"
PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts" / PROMPT_VERSION


def mensajes(entrada: EntradaPlan, evitar: list[str]) -> tuple[str, str]:
    sistema = (PROMPT_DIR / "system.txt").read_text(encoding="utf-8")
    plantilla = (PROMPT_DIR / "user_template.txt").read_text(encoding="utf-8")
    # JSON evita que comillas, etiquetas o saltos de línea alteren la plantilla.
    import json
    usuario = plantilla.replace("{{ingredientes}}", json.dumps(entrada.ingredientes_texto,
                                                               ensure_ascii=False))
    usuario = usuario.replace("{{personas}}", str(entrada.personas))
    usuario = usuario.replace("{{dias}}", str(entrada.dias))
    usuario = usuario.replace("{{comidas}}", json.dumps(entrada.comidas, ensure_ascii=False))
    usuario = usuario.replace("{{evitar}}", json.dumps(evitar, ensure_ascii=False))
    return sistema, usuario
