"""Historial paginado con resúmenes públicos."""

import re

from .compartidos import CodigoError, ErrorBrock
from .http import Respuesta, Ruta, Solicitud, respuesta
from .recuperacion import recuperar


def obtener(solicitud: Solicitud) -> Respuesta:
    query = solicitud.query({"limite", "cursor"})
    limite = query.get("limite", "20")
    if not re.fullmatch(r"[0-9]{1,2}", limite):
        raise ErrorBrock(CodigoError.VALIDACION, "El límite debe estar entre 1 y 20.")
    pagina = solicitud.repo.historial(int(limite), query.get("cursor"))
    planes = []
    for guardado in pagina["planes"]:
        plan = recuperar(solicitud, guardado)
        planes.append({"planId": plan["planId"], "estado": plan["estado"],
                       "creado_en": plan["creado_en"], "dias": plan["entrada"]["dias"],
                       "personas": plan["entrada"]["personas"]})
    return respuesta(200, {"planes": planes, "cursor": pagina["cursor"]})


RUTAS: list[Ruta] = [("GET", r"/planes", "GET /planes", obtener)]
