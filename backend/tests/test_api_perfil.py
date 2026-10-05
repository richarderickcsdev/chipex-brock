import json
from collections.abc import Callable
from typing import Any

import pytest


def test_perfil_por_defecto_y_actualizacion(api: Callable[..., dict[str, Any]]) -> None:
    resultado = api("GET", "/dev/perfil")
    assert resultado["statusCode"] == 200
    datos = json.loads(resultado["body"])
    assert datos["personas_defecto"] == 1
    assert datos["cupo"]["restantes"] == 5
    assert "PK" not in datos and "SK" not in datos
    assert resultado["headers"]["Cache-Control"] == "no-store"
    primero = json.loads(api("PUT", "/perfil", {"personas_defecto": 4})["body"])
    segundo = json.loads(api("PUT", "/perfil", {"personas_defecto": 2})["body"])
    assert segundo["creado_en"] == primero["creado_en"]
    assert json.loads(api("GET", "/perfil")["body"])["personas_defecto"] == 2
    assert json.loads(api("GET", "/perfil", sub="usuario-b")["body"])["personas_defecto"] == 1


@pytest.mark.parametrize("body", [{"personas_defecto": 0}, {"personas_defecto": 11},
                                   {"personas_defecto": "2"}, {"sub": "otro"}])
def test_perfil_rechaza_formulario_invalido(
    api: Callable[..., dict[str, Any]], body: dict[str, Any],
) -> None:
    assert api("PUT", "/perfil", body)["statusCode"] == 400
