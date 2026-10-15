import type { ListaCompra } from './tipos';
import { textos as t } from '../i18n/es';
import { cantidad } from '../utilidades';
export function textoLista(lista: ListaCompra) {
  return Object.entries(t.pasillos)
    .flatMap(([pasillo, nombre]) => {
      const items = lista.items.filter((i) => i.pasillo === pasillo);
      return items.length
        ? [
            nombre,
            ...items.map(
              (i) =>
                `${i.comprado ? '✓' : '□'} ${i.nombre} — ${cantidad(i.cantidad)} ${i.unidad}`,
            ),
            '',
          ]
        : [];
    })
    .join('\n');
}
