"""Creación asíncrona y presentación pública de los planes."""

import os

from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from .compartidos import CodigoError, EntradaPlan, ErrorBrock, json_publico, validar_entrada
from .http import Respuesta, Ruta, Solicitud, respuesta
from .ids import nuevo_ulid


def crear(solicitud: Solicitud) -> Respuesta:
    solicitud.query(set())
    entrada = validar_entrada(EntradaPlan, solicitud.cuerpo())
    preferencias = solicitud.repo.perfil()["evitar"]
    plan_id = nuevo_ulid()
    solicitud.cupo.reservar(plan_id, entrada, preferencias)
    rechazado = False
    try:
        invocacion = solicitud.lambdas.invoke(
            FunctionName=os.environ["FN_GENERADOR"], InvocationType="Event",
            Payload=json_publico({"task": "GENERAR_PLAN", "sub": solicitud.sub,
                                  "planId": plan_id}).encode(),
        )
        rechazado = invocacion.get("StatusCode") != 202
    except (ClientError, EndpointConnectionError):
        rechazado = True
    except BotoCoreError:
        # Un timeout de lectura puede ocurrir después de aceptar el evento.
        # Conservamos el plan: la consulta recuperará el intento si vence.
        pass
    if rechazado:
        solicitud.cupo.devolver(plan_id, "No pudimos iniciar la generación. Inténtalo más tarde.")
        raise ErrorBrock(CodigoError.ERROR_INTERNO,
                         "No pudimos iniciar la generación. Inténtalo más tarde.")
    return respuesta(202, {"planId": plan_id, "estado": "GENERANDO"})


RUTAS: list[Ruta] = [("POST", r"/planes", "POST /planes", crear)]
