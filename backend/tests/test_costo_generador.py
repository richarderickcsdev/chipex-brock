from decimal import Decimal

import pytest

from backend.generador.costo import costo_estimado


def test_costo_por_plan() -> None:
    assert costo_estimado(1_000_000, 2_000_000, "3", "15") == Decimal("33")


@pytest.mark.parametrize("tokens_in,tokens_out,entrada,salida", [
    (-1, 0, "1", "1"), (0, -1, "1", "1"), (1, 1, "-1", "1"),
    (1, 1, "x", "1"),
])
def test_costo_rechaza_valores_invalidos(
    tokens_in: int, tokens_out: int, entrada: str, salida: str,
) -> None:
    with pytest.raises(ValueError):
        costo_estimado(tokens_in, tokens_out, entrada, salida)
