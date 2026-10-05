"""Baja asíncrona con bloqueo de escrituras y eliminación Cognito idempotente."""

import os
from datetime import timedelta

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict, Field

from .compartidos import (
    CodigoError,
    ErrorBrock,
    Repositorio,
    es_condicional,
    json_publico,
    validar_entrada,
)
from .http import Respuesta, Ruta, Solicitud, ahora_utc, respuesta


class Confirmacion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    confirmacion_email: str = Field(min_length=3, max_length=254)


def iniciar(solicitud: Solicitud) -> Respuesta:
    solicitud.query(set())
    datos = validar_entrada(Confirmacion, solicitud.cuerpo())
    cuenta = solicitud.repo.obtener("ACCOUNT")
    if cuenta and cuenta["estado"] == "BORRADA":
        raise ErrorBrock(CodigoError.NO_AUTORIZADO, "La cuenta fue eliminada.")
    username = solicitud.claims.get("username") or solicitud.claims.get("cognito:username")
    username = username or solicitud.sub
    usuario = solicitud.cognito.admin_get_user(
        UserPoolId=os.environ["USER_POOL_ID"], Username=username,
    )
    atributos = {item["Name"]: item["Value"] for item in usuario["UserAttributes"]}
    if atributos.get("sub") != solicitud.sub:
        raise ErrorBrock(CodigoError.NO_AUTORIZADO, "La sesión no corresponde a esta cuenta.")
    if datos.confirmacion_email.casefold() != atributos.get("email", "").casefold():
        raise ErrorBrock(CodigoError.VALIDACION, "Confirma el correo de tu cuenta para eliminarla.")
    solicitud.repo.tabla.update_item(
        Key=solicitud.repo.clave("ACCOUNT"),
        UpdateExpression="SET #estado = :b, usuario_cognito = :u, "
                         "creado_en = if_not_exists(creado_en, :t)",
        ConditionExpression="attribute_not_exists(PK) OR #estado = :b",
        ExpressionAttributeNames={"#estado": "estado"},
        ExpressionAttributeValues={":b": "BORRANDO", ":u": usuario["Username"],
                                   ":t": solicitud.ahora.isoformat()},
    )
    # El bloqueo permanece si Invoke falla: repetir DELETE vuelve a encolar.
    resultado = solicitud.lambdas.invoke(
        FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event",
        Payload=json_publico({"version": "brock-interno-v1", "task": "ELIMINAR_CUENTA",
                              "sub": solicitud.sub}).encode(),
    )
    if resultado.get("StatusCode") != 202:
        raise ErrorBrock(CodigoError.ERROR_INTERNO, "Reintenta la eliminación de tu cuenta.")
    return respuesta(202, {"estado": "ELIMINANDO"})


def ejecutar(sub: str) -> None:
    repo = Repositorio.desde_entorno(sub)
    cuenta = repo.obtener("ACCOUNT")
    if not cuenta or cuenta["estado"] == "BORRADA":
        return
    if cuenta["estado"] != "BORRANDO":
        raise ValueError("La cuenta no está bloqueada para eliminación")
    cognito = boto3.client("cognito-idp")
    argumentos = {"UserPoolId": os.environ["USER_POOL_ID"], "Username": cuenta["usuario_cognito"]}
    for operacion in [cognito.admin_disable_user]:
        try:
            operacion(**argumentos)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "UserNotFoundException":
                raise
    repo.eliminar_datos_usuario(permitir_generando=True, conservar_bloqueo=True)
    try:
        cognito.admin_delete_user(**argumentos)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "UserNotFoundException":
            raise
    try:
        repo.tabla.update_item(
            Key=repo.clave("ACCOUNT"),
            UpdateExpression="SET #estado = :fin, #ttl = :ttl REMOVE usuario_cognito",
            ConditionExpression="#estado = :b",
            ExpressionAttributeNames={"#estado": "estado", "#ttl": "ttl"},
            ExpressionAttributeValues={":fin": "BORRADA", ":b": "BORRANDO",
                                       ":ttl": int((ahora_utc() + timedelta(days=1)).timestamp())},
        )
    except ClientError as exc:
        if not es_condicional(exc) or (repo.obtener("ACCOUNT") or {}).get("estado") != "BORRADA":
            raise


RUTAS: list[Ruta] = [("DELETE", r"/cuenta", "DELETE /cuenta", iniciar)]
