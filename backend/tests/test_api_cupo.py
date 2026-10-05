import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from backend.api.app import handler
from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.esquema import EntradaPlan
from backend.tests.conftest import PLAN_ID


def test_429_y_reinicio(
    api: Callable[..., dict[str, Any]], cupo: Cupo, entrada: EntradaPlan,
) -> None:
    for indice in range(5):
        cupo.reservar(f"{indice:026d}", entrada)
    resultado = api("POST", "/planes", {"personas": 2})
    assert resultado["statusCode"] == 429
    assert json.loads(resultado["body"])["error"]["reinicia"] == "2026-10-05T05:00:00Z"


def test_consulta_timeout_devuelve_una_vez(
    api: Callable[..., dict[str, Any]], repo: Repositorio, entrada: EntradaPlan,
) -> None:
    antes = datetime(2026, 10, 4, 12, tzinfo=UTC) - timedelta(seconds=61)
    Cupo(repo, reloj=lambda: antes).reservar(PLAN_ID, entrada)
    for _ in range(2):
        resultado = api("GET", f"/planes/{PLAN_ID}")
        assert resultado["statusCode"] == 200
        assert json.loads(resultado["body"])["estado"] == "ERROR"
    assert json.loads(api("GET", "/perfil")["body"])["cupo"]["usados"] == 0


@pytest.mark.parametrize("condicion", ["RetriesExhausted", "EventAgeExceeded"])
def test_destino_fallo_compensa_idempotentemente(
    api: Callable[..., dict[str, Any]], cupo: Cupo, entrada: EntradaPlan, condicion: str,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    evento = {"version": "1.0", "requestContext": {"condition": condicion},
              "requestPayload": {"task": "GENERAR_PLAN", "sub": "usuario-a", "planId": PLAN_ID}}
    for _ in range(2):
        assert handler(evento, None)["statusCode"] == 200
    assert cupo.estado()["usados"] == 0


def test_evento_interno_en_body_no_se_ejecuta(api: Callable[..., dict[str, Any]]) -> None:
    assert api("POST", "/planes", {"task": "GENERAR_PLAN", "sub": "usuario-b"})["statusCode"] == 400
