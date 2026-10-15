import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pedir } from '../api/cliente';
import type { ItemCompra, ListaCompra, Pasillo } from '../api/tipos';
import { useSesion } from '../auth/contexto';
import { AvisoIA, Cargando, ErrorMensaje } from '../componentes/Comunes';
import { useConexion } from '../componentes/useConexion';
import { textoLista } from '../api/textoLista';
import { textos as t } from '../i18n/es';
import { cantidad } from '../utilidades';

export function Compras() {
  const { planId = '' } = useParams();
  const { usuario } = useSesion();
  const cache = useQueryClient();
  const conectado = useConexion();
  const [mensaje, setMensaje] = useState('');
  const [manual, setManual] = useState('');
  const [fallo, setFallo] = useState(false);
  const clave = ['lista', usuario?.id, planId];
  const ruta = `/planes/${encodeURIComponent(planId)}/lista`;
  const lista = useQuery({
    queryKey: clave,
    queryFn: ({ signal }) => pedir<ListaCompra>(ruta, { signal }),
  });
  const marcar = useMutation({
    mutationFn: (item: ItemCompra) =>
      pedir<ItemCompra>(`${ruta}/items/${encodeURIComponent(item.id)}`, {
        method: 'PATCH',
        body: JSON.stringify({ comprado: !item.comprado }),
      }),
    onMutate: async (item) => {
      setFallo(false);
      await cache.cancelQueries({ queryKey: clave });
      const anterior = cache.getQueryData<ListaCompra>(clave);
      cache.setQueryData<ListaCompra>(clave, (actual) =>
        actual
          ? {
              ...actual,
              items: actual.items.map((i) =>
                i.id === item.id ? { ...i, comprado: !i.comprado } : i,
              ),
            }
          : actual,
      );
      return { anterior };
    },
    onError: (_error, _item, contexto) => {
      if (contexto?.anterior) cache.setQueryData(clave, contexto.anterior);
      setFallo(true);
    },
    onSuccess: (resultado) => {
      cache.setQueryData<ListaCompra>(clave, (actual) =>
        actual
          ? {
              ...actual,
              items: actual.items.map((i) =>
                i.id === resultado.id ? { ...i, ...resultado } : i,
              ),
            }
          : actual,
      );
    },
  });
  const compartir = async () => {
    if (!lista.data) return;
    const text = textoLista(lista.data);
    setMensaje('');
    setManual('');
    try {
      if (navigator.share) await navigator.share({ title: t.compras, text });
      else if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setMensaje(t.copiado);
      } else setManual(text);
    } catch (e) {
      if (!(e instanceof Error) || e.name !== 'AbortError') setManual(text);
    }
  };
  const comprados = lista.data?.items.filter((i) => i.comprado).length ?? 0;
  const total = lista.data?.items.length ?? 0;
  return (
    <section className="pila">
      <div className="titulo-acciones">
        <h1>{t.compras}</h1>
        <Link to={`/planes/${encodeURIComponent(planId)}`}>{t.menu}</Link>
      </div>
      <AvisoIA />
      {lista.isPending && <Cargando />}
      <ErrorMensaje error={lista.error} />
      {lista.error && (
        <button onClick={() => void lista.refetch()}>{t.reintentar}</button>
      )}
      {fallo && (
        <p role="alert" className="mensaje error">
          {t.falloMarca}
        </p>
      )}
      {lista.data && (
        <>
          <div className="tarjeta">
            <p role="status">{t.progreso(comprados, total)}</p>
            <progress
              value={comprados}
              max={total || 1}
              aria-label={t.progreso(comprados, total)}
            />
            <div className="acciones">
              <button onClick={() => void compartir()}>{t.compartir}</button>
            </div>
            {mensaje && <p role="status">{mensaje}</p>}
            {manual && (
              <>
                <label htmlFor="texto-lista">{t.copiaManual}</label>
                <textarea
                  id="texto-lista"
                  readOnly
                  rows={8}
                  value={manual}
                  onFocus={(e) => e.target.select()}
                />
              </>
            )}
          </div>
          {total === 0 ? (
            <p className="tarjeta">{t.nadaComprar}</p>
          ) : (
            comprados === total && (
              <p role="status" className="mensaje">
                {t.completa}
              </p>
            )
          )}
          {(Object.keys(t.pasillos) as Pasillo[]).map((pasillo) => {
            const items = lista.data.items.filter((i) => i.pasillo === pasillo);
            if (!items.length) return null;
            const todos = items.every((i) => i.comprado);
            return (
              <details className="tarjeta pasillo" key={pasillo} open={!todos}>
                <summary>
                  {t.pasillos[pasillo]} {todos ? '✓' : ''}{' '}
                  <span className="ayuda">
                    {t.progreso(
                      items.filter((i) => i.comprado).length,
                      items.length,
                    )}
                  </span>
                </summary>
                <ul>
                  {items.map((item) => (
                    <li key={item.id}>
                      <label
                        className={`compra ${item.comprado ? 'comprado' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={item.comprado}
                          disabled={marcar.isPending || !conectado}
                          onChange={() => marcar.mutate(item)}
                        />
                        <span>
                          {item.nombre} — {cantidad(item.cantidad)}{' '}
                          {item.unidad}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </details>
            );
          })}
        </>
      )}
    </section>
  );
}
