import base64
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock
from typing import TYPE_CHECKING, Any

import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from backend.compartido.dynamo import Repositorio
from backend.compartido.errores import CodigoError, ErrorBrock
from backend.compartido.esquema import EntradaPlan, MetadatosGeneracion, Perfil
from backend.compartido.validacion import validar_plan
from backend.tests.conftest import PLAN_ID

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table


def test_perfil_aislado(repo: Repositorio, tabla: "Table") -> None:
    assert repo.perfil()["personas_defecto"] == 1
    primero = repo.guardar_perfil(Perfil(personas_defecto=4, evitar=["ajo"]))
    segundo = repo.guardar_perfil(Perfil(personas_defecto=2))
    assert segundo["creado_en"] == primero["creado_en"]
    assert segundo["personas_defecto"] == 2
    assert Repositorio(tabla, "usuario-b").perfil()["personas_defecto"] == 1
