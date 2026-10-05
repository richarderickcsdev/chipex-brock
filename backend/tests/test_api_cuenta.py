import json
from collections.abc import Callable
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from backend.api.app import handler
from backend.api.http import Solicitud
from backend.compartido.cupo import Cupo
from backend.compartido.dynamo import Repositorio
from backend.compartido.errores import ErrorBrock
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion, Perfil
from backend.compartido.validacion import validar_plan
from backend.tests.conftest import PLAN_ID


@pytest.fixture
def usuario_cognito(
    api: Callable[..., dict[str, Any]], monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    cliente = boto3.client("cognito-idp")
    pool = cliente.create_user_pool(PoolName="brock-test")["UserPool"]["Id"]
    usuario = cliente.admin_create_user(UserPoolId=pool, Username="usuario-cognito",
        UserAttributes=[{"Name": "email", "Value": "persona@example.com"}],
        MessageAction="SUPPRESS")["User"]
    sub = next(item["Value"] for item in usuario["Attributes"] if item["Name"] == "sub")
    monkeypatch.setenv("USER_POOL_ID", pool)
    return {"sub": sub, "username": usuario["Username"], "pool": pool}


def test_baja_asincrona_bloquea_y_elimina_cognito(
    api: Callable[..., dict[str, Any]], usuario_cognito: dict[str, str],
    monkeypatch: pytest.MonkeyPatch, repo: Repositorio, entrada: EntradaPlan,
) -> None:
    eventos = []

    class LambdaSimulada:
        def invoke(self, **datos: Any) -> dict[str, int]:
            eventos.append(json.loads(datos["Payload"]))
            return {"StatusCode": 202}

    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: LambdaSimulada()))
    sub = usuario_cognito["sub"]
    propio = Repositorio(repo.tabla, sub)
    propio.guardar_perfil(Perfil(personas_defecto=3))
    Cupo(propio).reservar(PLAN_ID, entrada)
    repo.guardar_perfil(Perfil(personas_defecto=4))  # Otro usuario no se borra.
    claims = {"sub": sub, "username": usuario_cognito["username"]}
    assert api("DELETE", "/cuenta", {"confirmacion_email": "incorrecto@example.com"},
               claims=claims)["statusCode"] == 400
    resultado = api(
        "DELETE", "/cuenta", {"confirmacion_email": "persona@example.com"}, claims=claims,
    )
    assert resultado["statusCode"] == 202
    assert api("GET", "/perfil", claims=claims)["statusCode"] == 409
    with pytest.raises(ErrorBrock):
        propio.guardar_perfil(Perfil())
    for _ in range(2):
        assert handler(eventos[0], None)["statusCode"] == 200
    assert propio.obtener("PROFILE") is None
    assert propio.obtener(f"PLAN#{PLAN_ID}") is None
    assert propio.obtener("ACCOUNT")["estado"] == "BORRADA"  # type: ignore[index]
    assert api("GET", "/perfil", claims=claims)["statusCode"] == 401
    assert repo.perfil()["personas_defecto"] == 4
    with pytest.raises(ClientError) as error:
        boto3.client("cognito-idp").admin_get_user(UserPoolId=usuario_cognito["pool"],
                                                Username=usuario_cognito["username"])
    assert error.value.response["Error"]["Code"] == "UserNotFoundException"


def test_bloqueo_transaccional_impide_planes_y_resultados_tardios(
    repo: Repositorio, entrada: EntradaPlan, respuesta_plan: dict[str, Any],
    metadatos: MetadatosGeneracion,
) -> None:
    cupo = Cupo(repo)
    cupo.reservar(PLAN_ID, entrada)
    repo.tabla.put_item(Item={**repo.clave("ACCOUNT"), "estado": "BORRANDO"})
    with pytest.raises(ErrorBrock):
        cupo.reservar("00000000000000000000000001", entrada)
    with pytest.raises(ErrorBrock):
        repo.finalizar(PLAN_ID, validar_plan(respuesta_plan, entrada), metadatos)
    assert repo.obtener(f"LIST#{PLAN_ID}") is None


def test_fallo_parcial_worker_se_propaga_y_permite_reintento(
    api: Callable[..., dict[str, Any]], usuario_cognito: dict[str, str], repo: Repositorio,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    propio = Repositorio(repo.tabla, usuario_cognito["sub"])
    propio.guardar_perfil(Perfil())
    propio.tabla.put_item(Item={**propio.clave("ACCOUNT"), "estado": "BORRANDO",
                               "usuario_cognito": usuario_cognito["username"]})
    evento = {
        "version": "brock-interno-v1", "task": "ELIMINAR_CUENTA",
        "sub": usuario_cognito["sub"],
    }
    original = Repositorio.eliminar_datos_usuario

    def fallar(self: Repositorio, **opciones: Any) -> None:
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(Repositorio, "eliminar_datos_usuario", fallar)
    with pytest.raises(RuntimeError):
        handler(evento, None)
    assert propio.obtener("PROFILE") is not None
    monkeypatch.setattr(Repositorio, "eliminar_datos_usuario", original)
    assert handler(evento, None)["statusCode"] == 200
    assert propio.obtener("PROFILE") is None


def test_cola_fallida_conserva_bloqueo_y_delete_puede_reintentarse(
    api: Callable[..., dict[str, Any]], usuario_cognito: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cliente = boto3.client("lambda")
    monkeypatch.setattr(Solicitud, "lambdas", property(lambda self: cliente))
    claims = {"sub": usuario_cognito["sub"], "username": usuario_cognito["username"]}
    with Stubber(cliente) as stub:
        stub.add_client_error("invoke", service_error_code="TooManyRequestsException")
        assert api("DELETE", "/cuenta", {"confirmacion_email": "persona@example.com"},
                   claims=claims)["statusCode"] == 500
    assert api("GET", "/perfil", claims=claims)["statusCode"] == 409
    with Stubber(cliente) as stub:
        stub.add_response("invoke", {"StatusCode": 202})
        assert api("DELETE", "/cuenta", {"confirmacion_email": "persona@example.com"},
                   claims=claims)["statusCode"] == 202
