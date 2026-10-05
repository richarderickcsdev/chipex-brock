"""Importaciones compatibles con pytest y el CodeUri backend/ de SAM."""

from typing import TYPE_CHECKING

if TYPE_CHECKING or __package__ == "backend.api":
    from ..compartido.cupo import Cupo as Cupo
    from ..compartido.dynamo import Repositorio as Repositorio
    from ..compartido.dynamo import ahora_iso as ahora_iso
    from ..compartido.dynamo import atributos as atributos
    from ..compartido.dynamo import es_condicional as es_condicional
    from ..compartido.errores import CodigoError as CodigoError
    from ..compartido.errores import ErrorBrock as ErrorBrock
    from ..compartido.errores import no_encontrado as no_encontrado
    from ..compartido.esquema import EntradaPlan as EntradaPlan
    from ..compartido.esquema import MarcaCompra as MarcaCompra
    from ..compartido.esquema import Perfil as Perfil
    from ..compartido.validacion import json_publico as json_publico
    from ..compartido.validacion import validar_entrada as validar_entrada
else:
    from compartido.cupo import Cupo as Cupo
    from compartido.dynamo import Repositorio as Repositorio
    from compartido.dynamo import ahora_iso as ahora_iso
    from compartido.dynamo import atributos as atributos
    from compartido.dynamo import es_condicional as es_condicional
    from compartido.errores import CodigoError as CodigoError
    from compartido.errores import ErrorBrock as ErrorBrock
    from compartido.errores import no_encontrado as no_encontrado
    from compartido.esquema import EntradaPlan as EntradaPlan
    from compartido.esquema import MarcaCompra as MarcaCompra
    from compartido.esquema import Perfil as Perfil
    from compartido.validacion import json_publico as json_publico
    from compartido.validacion import validar_entrada as validar_entrada
