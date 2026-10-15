import { useEffect, useState } from 'react';
export function useConexion() {
  const [conectado, setConectado] = useState(navigator.onLine);
  useEffect(() => {
    const actualizar = () => setConectado(navigator.onLine);
    window.addEventListener('online', actualizar);
    window.addEventListener('offline', actualizar);
    return () => {
      window.removeEventListener('online', actualizar);
      window.removeEventListener('offline', actualizar);
    };
  }, []);
  return conectado;
}
