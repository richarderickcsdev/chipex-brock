import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import { pedir } from '../api/cliente';
import type { PaginaPlanes } from '../api/tipos';
import { Cargando, ErrorMensaje } from '../componentes/Comunes';
import { textos as t } from '../i18n/es';
import { fecha } from '../utilidades';
import { useSesion } from '../auth/contexto';

export function Historial() {
  const cache = useQueryClient();
  const { usuario } = useSesion();
  const [confirmar, setConfirmar] = useState<string | null>(null);
  const mas = useRef<HTMLButtonElement>(null);
  const historial = useInfiniteQuery({
    queryKey: ['historial', usuario?.id],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      pedir<PaginaPlanes>(
        `/planes?limite=20${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`,
        { signal },
      ),
    getNextPageParam: (pagina) => pagina.cursor ?? undefined,
  });
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = historial;
  useEffect(() => {
    if (!mas.current || !hasNextPage || !('IntersectionObserver' in window))
      return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !isFetchingNextPage)
        void fetchNextPage();
    });
    observer.observe(mas.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  const borrar = useMutation({
    mutationFn: (id: string) =>
      pedir<void>(`/planes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    onSuccess: () => {
      setConfirmar(null);
      void cache.invalidateQueries({ queryKey: ['historial'] });
    },
  });
  const planes = historial.data?.pages.flatMap((p) => p.planes) ?? [];
  return (
    <section>
      <div className="titulo-acciones">
        <h1>{t.historial}</h1>
        <Link className="boton principal" to="/nuevo">
          {t.nuevo}
        </Link>
      </div>
      {historial.isPending && <Cargando />}
      <ErrorMensaje error={historial.error || borrar.error} />
      {historial.error && (
        <button onClick={() => void historial.refetch()}>{t.reintentar}</button>
      )}
      {!historial.isPending && !historial.error && planes.length === 0 && (
        <p className="tarjeta">{t.vacio}</p>
      )}
      <ul className="historial">
        {planes.map((plan) => (
          <li key={plan.planId} className="tarjeta">
            <Link to={`/planes/${encodeURIComponent(plan.planId)}`}>
              <h2>{t.personasDias(plan.personas, plan.dias)}</h2>
              <time dateTime={plan.creado_en}>{fecha(plan.creado_en)}</time>
              <span className={`estado ${plan.estado.toLowerCase()}`}>
                {t.estado[plan.estado]}
              </span>
            </Link>
            {confirmar === plan.planId ? (
              <div className="confirmacion">
                <p>{t.confirmarPlan}</p>
                <div className="acciones">
                  <button
                    className="peligro"
                    disabled={borrar.isPending}
                    onClick={() => borrar.mutate(plan.planId)}
                  >
                    {t.eliminar}
                  </button>
                  <button
                    disabled={borrar.isPending}
                    onClick={() => setConfirmar(null)}
                  >
                    {t.cancelar}
                  </button>
                </div>
              </div>
            ) : (
              <button
                className="enlace"
                disabled={plan.estado === 'GENERANDO'}
                title={
                  plan.estado === 'GENERANDO' ? t.noBorrarActivo : undefined
                }
                onClick={() => setConfirmar(plan.planId)}
              >
                {t.eliminar}
              </button>
            )}
          </li>
        ))}
      </ul>
      {historial.hasNextPage && (
        <button
          ref={mas}
          disabled={historial.isFetchingNextPage}
          onClick={() => void historial.fetchNextPage()}
        >
          {historial.isFetchingNextPage ? t.cargando : t.cargarMas}
        </button>
      )}
    </section>
  );
}
