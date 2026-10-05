import base64
import json

import pytest

from backend.api.app import handler
from backend.api.http import Solicitud
from backend.compartido.errores import ErrorBrock


@pytest.mark.parametrize("body", [None, "", "[]", '{"a":1,"a":2}', '{"a":NaN}', "{", "x" * 24_001])
def test_cuerpo_invalido(body: object) -> None:
    solicitud = Solicitud({"body": body}, "usuario-a", {}, {})
    with pytest.raises(ErrorBrock):
        solicitud.cuerpo()


def test_cuerpo_base64() -> None:
    body = base64.b64encode('{"nombre":"limón"}'.encode()).decode()
    solicitud = Solicitud({"body": body, "isBase64Encoded": True}, "usuario-a", {}, {})
    assert solicitud.cuerpo() == {"nombre": "limón"}


def test_sin_claims_no_confia_en_header(capsys: pytest.CaptureFixture[str]) -> None:
    evento = {"version": "2.0", "headers": {"Authorization": "Bearer secreto"},
              "body": '{"sub":"usuario-a"}', "requestContext": {"requestId": "req-1"}}
    resultado = handler(evento, None)
    assert resultado["statusCode"] == 401
    log = json.loads(capsys.readouterr().out)
    assert log["requestId"] == "req-1"
    assert "secreto" not in json.dumps(log)
    assert "usuario-a" not in json.dumps(log)
