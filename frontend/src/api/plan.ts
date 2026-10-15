import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { pedir } from './cliente';
import type { Plan } from './tipos';
import { useSesion } from '../auth/contexto';

export function usePlan(id: string) {
  const cache = useQueryClient();
  const { usuario } = useSesion();
  const consulta = useQuery({
    queryKey: ['plan', usuario?.id, id],
    queryFn: ({ signal }) =>
      pedir<Plan>(`/planes/${encodeURIComponent(id)}`, { signal }),
    refetchInterval: (query) =>
      query.state.data?.estado === 'GENERANDO' &&
      Date.now() - new Date(query.state.data.creado_en).getTime() < 65_000
        ? 2000
        : false,
  });
  useEffect(() => {
    if (consulta.data?.estado && consulta.data.estado !== 'GENERANDO') {
      void cache.invalidateQueries({ queryKey: ['perfil'] });
      void cache.invalidateQueries({ queryKey: ['historial'] });
    }
  }, [consulta.data?.estado, cache, consulta.data?.planId]);
  return consulta;
}
