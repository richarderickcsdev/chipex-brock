"""Lista pública ordenada por pasillo."""

from .http import Respuesta, Ruta, Solicitud, respuesta

PASILLOS = ["FRUTAS_VERDURAS", "CARNES_PESCADOS", "LACTEOS_HUEVOS", "PANADERIA",
            "DESPENSA", "CONGELADOS", "BEBIDAS", "LIMPIEZA", "OTROS"]


def obtener(solicitud: Solicitud) -> Respuesta:
    solicitud.query(set())
    plan_id = solicitud.parametros["planId"]
    lista = solicitud.repo.lista(plan_id)
    items = [{"id": item_id, **item} for item_id, item in lista["items"].items()]
    items.sort(key=lambda item: (PASILLOS.index(item["pasillo"]), item["nombre"].casefold()))
    return respuesta(200, {"planId": plan_id, "items": items,
                           "actualizado_en": lista["actualizado_en"]})


RUTAS: list[Ruta] = [
    ("GET", r"/planes/(?P<planId>[^/]+)/lista", "GET /planes/{planId}/lista", obtener),
]
