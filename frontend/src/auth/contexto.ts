import { createContext, useContext } from 'react';
export interface Usuario {
  id: string;
  correo: string;
}
export const ContextoSesion = createContext<{
  usuario: Usuario | null;
  cargando: boolean;
  vencida: boolean;
  actualizar: () => Promise<void>;
  salir: () => Promise<void>;
}>({
  usuario: null,
  cargando: true,
  vencida: false,
  actualizar: async () => {},
  salir: async () => {},
});
export const useSesion = () => useContext(ContextoSesion);
