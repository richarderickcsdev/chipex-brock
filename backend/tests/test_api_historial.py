import json
from collections.abc import Callable
from typing import Any

import pytest

from backend.compartido.dynamo import Repositorio


def test_historial_publico_paginado(
    api: Callable[..., dict[str, Any]], repo: Repositorio,
) -> None:
    assert json.loads(api("GET", "/planes")["body"]) == {"planes": [], "cursor": None}
    for indice in range(23):
        plan_id = f"{indice:026d}"
        repo.tabla.put_item(Item={**repo.clave(f"PLAN#{plan_id}"), "planId": plan_id,
            "estado": "ERROR", "entrada": {"dias": 1, "personas": 2},
            "creado_en": "2026-10-04T12:00:00Z"})
    primera = json.loads(api("GET", "/planes")["body"])
    assert len(primera["planes"]) == 20
    assert primera["planes"][0]["planId"] == f"{22:026d}"
    assert "PK" not in primera["planes"][0]
    segunda = json.loads(api("GET", "/planes", query={"cursor": primera["cursor"]})["body"])
    assert len(segunda["planes"]) == 3
    assert segunda["cursor"] is None
    assert api("GET", "/planes", sub="usuario-b", query={"cursor": primera["cursor"]})[
        "statusCode"] == 400


@pytest.mark.parametrize("query", [{"limite": "0"}, {"limite": "21"}, {"limite": "abc"},
                                   {"cursor": "!!!"}, {"usuario": "otro"}])
def test_historial_parametros_invalidos(
    api: Callable[..., dict[str, Any]], query: dict[str, str],
) -> None:
    assert api("GET", "/planes", query=query)["statusCode"] == 400
