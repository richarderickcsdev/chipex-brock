"""Contratos completos de entrada y respuesta del modelo, versión 1.0."""

import unicodedata
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from .entrada import limpiar_texto, normalizar_nombre

TipoComida = Literal["DESAYUNO", "ALMUERZO", "CENA"]
Unidad = Literal["g", "kg", "ml", "l", "unidad", "paquete"]
Pasillo = Literal[
    "FRUTAS_VERDURAS", "CARNES_PESCADOS", "LACTEOS_HUEVOS", "PANADERIA",
    "DESPENSA", "CONGELADOS", "BEBIDAS", "LIMPIEZA", "OTROS",
]


def texto_seguro(valor: str) -> str:
    if any(unicodedata.category(c).startswith("C") and not c.isspace() for c in valor):
        raise ValueError("El texto contiene caracteres de control.")
    return valor


Nombre = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(texto_seguro)]
Cantidad = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Paso = Annotated[str, Field(min_length=1, max_length=500), AfterValidator(texto_seguro)]
Preferencia = Annotated[str, Field(min_length=1, max_length=40), AfterValidator(texto_seguro)]
PlanId = Annotated[str, Field(pattern=r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$")]


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def rechazar_controles(cls, valor: object) -> object:
        if isinstance(valor, str) and limpiar_texto(valor) != " ".join(valor.split()):
            raise ValueError("El texto contiene caracteres de control.")
        return valor


def comidas_por_defecto() -> list[TipoComida]:
    return ["ALMUERZO", "CENA"]


class EntradaPlan(Contrato):
    ingredientes_texto: Annotated[str, Field(max_length=1000)] = ""
    personas: Annotated[int, Field(ge=1, le=10)]
    dias: Annotated[int, Field(ge=1, le=7)] = 7
    comidas: Annotated[list[TipoComida], Field(min_length=1, max_length=3)] = Field(
        default_factory=comidas_por_defecto
    )

    @field_validator("ingredientes_texto", mode="before")
    @classmethod
    def limpiar_ingredientes(cls, valor: object) -> object:
        if isinstance(valor, str):
            if len(valor) > 1000:
                raise ValueError("El texto no puede superar los 1.000 caracteres.")
            return limpiar_texto(valor)
        return valor

    @field_validator("comidas")
    @classmethod
    def comidas_unicas(cls, valor: list[TipoComida]) -> list[TipoComida]:
        if len(set(valor)) != len(valor):
            raise ValueError("Las comidas no deben repetirse.")
        return valor


class Perfil(Contrato):
    personas_defecto: Annotated[int, Field(ge=1, le=10)] = 1
    evitar: Annotated[list[Preferencia], Field(max_length=20)] = Field(default_factory=list)

    @field_validator("evitar")
    @classmethod
    def evitar_unicos(cls, valor: list[str]) -> list[str]:
        nombres = [normalizar_nombre(v) for v in valor]
        if any(not nombre for nombre in nombres) or len(set(nombres)) != len(nombres):
            raise ValueError("Las preferencias deben ser nombres únicos y no vacíos.")
        return valor


class MarcaCompra(Contrato):
    comprado: bool


class Ingrediente(Contrato):
    nombre: Nombre
    cantidad: Cantidad
    unidad: Unidad
    en_casa: bool


class Comida(Contrato):
    tipo: TipoComida
    nombre: Nombre
    tiempo_min: Annotated[int, Field(ge=1, le=480)] | None = None
    ingredientes: Annotated[list[Ingrediente], Field(min_length=1, max_length=30)]
    pasos: Annotated[list[Paso], Field(min_length=1, max_length=15)]


class Dia(Contrato):
    dia: Annotated[int, Field(ge=1, le=7)]
    comidas: Annotated[list[Comida], Field(min_length=1, max_length=3)]


class ItemCompra(Contrato):
    id: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]
    nombre: Nombre
    cantidad: Cantidad
    unidad: Unidad
    pasillo: Pasillo


class PlanGenerado(Contrato):
    version_esquema: Literal["1.0"]
    dias: Annotated[list[Dia], Field(min_length=1, max_length=7)]
    lista_compras: Annotated[list[ItemCompra], Field(max_length=120)]


class MetadatosGeneracion(Contrato):
    prompt_version: Annotated[str, Field(min_length=1, max_length=40)]
    modelo: Annotated[str, Field(min_length=1, max_length=256)]
    tokens_in: Annotated[int, Field(ge=0)]
    tokens_out: Annotated[int, Field(ge=0)]
    latencia_ms: Annotated[int, Field(ge=0)]


ESQUEMA_PLAN = PlanGenerado.model_json_schema()
