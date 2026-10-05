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

from backend.compartido.cupo import Cupo
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


def test_reserva_atomica_y_duplicado(
    cupo: Cupo, repo: Repositorio, entrada: EntradaPlan
) -> None:
    cupo.reservar(PLAN_ID, entrada, ["ajo"])
    assert cupo.estado()["restantes"] == 4
    plan = repo.plan(PLAN_ID)
    assert plan["estado"] == "GENERANDO"
    assert plan["evitar"] == ["ajo"]
    with pytest.raises(ErrorBrock) as error:
        cupo.reservar(PLAN_ID, entrada)
    assert error.value.codigo == CodigoError.CONFLICTO
    assert cupo.estado()["usados"] == 1  # Transacción fallida no consume otro cupo.


def test_limite_y_sin_plan_huerfano(cupo: Cupo, entrada: EntradaPlan, repo: Repositorio) -> None:
    for indice in range(5):
        cupo.reservar(f"{indice:026d}", entrada)
    with pytest.raises(ErrorBrock) as error:
        cupo.reservar(PLAN_ID, entrada)
    assert error.value.codigo == CodigoError.CUPO_AGOTADO
    assert error.value.reinicia == "2026-10-05T05:00:00Z"
    assert repo.obtener(f"PLAN#{PLAN_ID}") is None
    assert cupo.estado()["restantes"] == 0


def test_devolucion_una_vez(cupo: Cupo, entrada: EntradaPlan, repo: Repositorio) -> None:
    cupo.reservar(PLAN_ID, entrada)
    assert cupo.devolver(PLAN_ID) is True
    assert cupo.devolver(PLAN_ID) is False
    assert cupo.estado()["usados"] == 0
    assert repo.plan(PLAN_ID)["estado"] == "ERROR"
    assert repo.plan(PLAN_ID)["cupo_devuelto"] is True


def test_medianoche_y_devolucion_dia_original(repo: Repositorio, entrada: EntradaPlan) -> None:
    antes = Cupo(repo, reloj=lambda: datetime(2026, 10, 5, 4, 59, tzinfo=UTC))
    despues = Cupo(repo, reloj=lambda: datetime(2026, 10, 5, 5, tzinfo=UTC))
    antes.reservar(PLAN_ID, entrada)
    assert antes.periodo()["fecha"] == "2026-10-04"
    assert despues.periodo()["fecha"] == "2026-10-05"
    assert despues.estado()["usados"] == 0
    despues.reservar("00000000000000000000000001", entrada)
    despues.devolver(PLAN_ID)
    assert antes.estado()["usados"] == 0
    assert despues.estado()["usados"] == 1
    contador = repo.obtener("QUOTA#2026-10-04")
    assert contador is not None
    assert contador["ttl"] > int(antes.reloj().timestamp())


def test_dos_devoluciones_concurrentes(
    cupo: Cupo, repo: Repositorio, entrada: EntradaPlan, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    barrera = Barrier(2, timeout=10)
    transaccion = Lock()
    original = repo.cliente.transact_write_items

    def competir(**opciones: Any) -> Any:
        barrera.wait()
        with transaccion:
            return original(**opciones)

    monkeypatch.setattr(repo.cliente, "transact_write_items", competir)
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [ejecutor.submit(cupo.devolver, PLAN_ID) for _ in range(2)]
        resultados = [futuro.result() for futuro in futuros]
    assert sorted(resultados) == [False, True]
    assert cupo.estado()["usados"] == 0


def test_error_aws_no_se_confunde_con_cupo_agotado(cupo: Cupo, entrada: EntradaPlan) -> None:
    with Stubber(cupo.repo.cliente) as stub:
        stub.add_client_error("transact_write_items", service_error_code="InternalServerError")
        with pytest.raises(ClientError):
            cupo.reservar(PLAN_ID, entrada)
    assert cupo.estado()["usados"] == 0


def test_cupo_corrupto_no_marca_error_sin_devolver(
    cupo: Cupo, repo: Repositorio, entrada: EntradaPlan,
) -> None:
    cupo.reservar(PLAN_ID, entrada)
    repo.tabla.delete_item(Key=repo.clave("QUOTA#2026-10-04"))
    with pytest.raises(ErrorBrock) as error:
        cupo.devolver(PLAN_ID)
    assert error.value.codigo == CodigoError.CONFLICTO
    assert repo.plan(PLAN_ID)["estado"] == "GENERANDO"
    assert repo.plan(PLAN_ID)["cupo_devuelto"] is False
