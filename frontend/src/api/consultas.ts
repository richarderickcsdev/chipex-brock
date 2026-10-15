import { useQuery } from '@tanstack/react-query';
import { pedir } from './cliente';
import type { Perfil } from './tipos';
import { useSesion } from '../auth/contexto';
export function usePerfil() {
  const { usuario } = useSesion();
  return useQuery({
    queryKey: ['perfil', usuario?.id],
    queryFn: ({ signal }) => pedir<Perfil>('/perfil', { signal }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
