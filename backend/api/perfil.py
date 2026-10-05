"""Perfil y cupo público del usuario autenticado."""

from .compartidos import Perfil, validar_entrada
from .http import Respuesta, Ruta, Solicitud, respuesta


def publico(solicitud: Solicitud) -> dict[str, object]:
    perfil = solicitud.repo.perfil()
    datos = {clave: perfil[clave] for clave in ("personas_defecto", "evitar", "creado_en")
             if clave in perfil}
    datos["cupo"] = solicitud.cupo.estado()
    return datos


def obtener(solicitud: Solicitud) -> Respuesta:
    solicitud.query(set())
    return respuesta(200, publico(solicitud))


def guardar(solicitud: Solicitud) -> Respuesta:
    solicitud.query(set())
    solicitud.repo.guardar_perfil(validar_entrada(Perfil, solicitud.cuerpo()))
    return respuesta(200, publico(solicitud))


RUTAS: list[Ruta] = [
    ("GET", r"/perfil", "GET /perfil", obtener),
    ("PUT", r"/perfil", "PUT /perfil", guardar),
]
