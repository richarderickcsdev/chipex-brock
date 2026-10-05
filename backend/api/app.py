"""Entrada provisional; las rutas se implementan en F4."""

import json


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    """Expone explícitamente que la API todavía no está implementada."""
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"error": {"codigo": "ERROR_INTERNO", "mensaje": "API en construcción."}}
        ),
    }
