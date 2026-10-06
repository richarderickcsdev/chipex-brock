"""Carga ligera local; el throttling definitivo es una propiedad de API Gateway."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from backend.api.app import handler


def test_rafaga_lecturas_no_corrompe_respuestas(
    api: Callable[..., dict[str, Any]],
) -> None:
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados = list(executor.map(lambda _: api("GET", "/perfil"), range(30)))
    assert all(resultado["statusCode"] == 200 for resultado in resultados)
    assert all("PK" not in resultado["body"] and "SK" not in resultado["body"]
               for resultado in resultados)


def test_evento_interno_no_se_expone_como_endpoint_http(
    api: Callable[..., dict[str, Any]],
) -> None:
    resultado = api("POST", "/perfil", {"version": "brock-interno-v1",
                                         "task": "ELIMINAR_CUENTA", "sub": "otro"})
    assert resultado["statusCode"] == 404
    interno = handler({"version": "brock-interno-v1", "task": "NO_EXISTE"}, None)
    assert interno["statusCode"] == 401
