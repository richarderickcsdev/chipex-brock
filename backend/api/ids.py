"""ULID de 48 bits de tiempo y 80 bits aleatorios, sin dependencia adicional."""

import secrets
import time

ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def nuevo_ulid() -> str:
    valor = ((time.time_ns() // 1_000_000) << 80) | secrets.randbits(80)
    caracteres = []
    for _ in range(26):
        caracteres.append(ALFABETO[valor & 31])
        valor >>= 5
    return "".join(reversed(caracteres))
