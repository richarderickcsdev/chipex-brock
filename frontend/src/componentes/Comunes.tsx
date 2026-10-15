import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { mensajeError } from '../api/cliente';
import { textos as t } from '../i18n/es';

export function ErrorMensaje({ error }: { error: unknown }) {
  return error ? (
    <p role="alert" className="mensaje error">
      {mensajeError(error)}
    </p>
  ) : null;
}
export function Cargando() {
  return (
    <p role="status" className="mensaje">
      {t.cargando}
    </p>
  );
}
export function AvisoIA() {
  return <p className="aviso-ia">{t.avisoIA}</p>;
}
export function FocoRuta() {
  const { pathname } = useLocation();
  useEffect(() => {
    document.getElementById('contenido')?.focus();
  }, [pathname]);
  return null;
}
