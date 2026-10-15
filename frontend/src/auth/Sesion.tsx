import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { useQueryClient } from '@tanstack/react-query';
import { ContextoSesion, type Usuario } from './contexto';
import { EVENTO_SESION, obtenerToken } from './servicio';

export function Sesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const [vencida, setVencida] = useState(false);
  const cache = useQueryClient();
  const actualizar = useCallback(async () => {
    try {
      await obtenerToken();
      const user = await getCurrentUser();
      setUsuario({
        id: user.userId,
        correo: user.signInDetails?.loginId ?? user.username,
      });
      setVencida(false);
    } catch {
      setUsuario(null);
    } finally {
      setCargando(false);
    }
  }, []);
  const limpiar = useCallback(() => {
    void cache.cancelQueries();
    cache.clear();
    setUsuario(null);
  }, [cache]);
  const salir = useCallback(async () => {
    await signOut();
    // El borrador solo se conserva ante vencimiento, nunca tras cierre explícito.
    try {
      if (usuario) sessionStorage.removeItem(`brock:borrador:${usuario.id}`);
    } catch {
      /* El cierre de sesión no depende del almacenamiento del navegador. */
    }
    limpiar();
  }, [usuario, limpiar]);
  useEffect(() => {
    void actualizar();
    const quitar = Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signedIn') void actualizar();
      if (payload.event === 'signedOut') limpiar();
      if (payload.event === 'tokenRefresh_failure') {
        setVencida(true);
        limpiar();
      }
    });
    const expirar = () => {
      setVencida(true);
      limpiar();
    };
    window.addEventListener(EVENTO_SESION, expirar);
    return () => {
      quitar();
      window.removeEventListener(EVENTO_SESION, expirar);
    };
  }, [actualizar, limpiar]);
  return (
    <ContextoSesion.Provider
      value={{ usuario, cargando, vencida, actualizar, salir }}
    >
      {children}
    </ContextoSesion.Provider>
  );
}
