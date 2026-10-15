import { fetchAuthSession, signOut } from 'aws-amplify/auth';
import { textos as t } from '../i18n/es';

export const EVENTO_SESION = 'brock:sesion-vencida';
export async function obtenerToken(forceRefresh = false) {
  const session = await fetchAuthSession({ forceRefresh });
  const token = session.tokens?.accessToken.toString();
  if (!token) throw new Error('SESION');
  return token;
}
export async function vencerSesion() {
  window.dispatchEvent(new Event(EVENTO_SESION));
  await signOut().catch(() => undefined);
}
export function mensajeAuth(error: unknown) {
  const nombre = error instanceof Error ? error.name : '';
  if (['CodeMismatchException', 'ExpiredCodeException'].includes(nombre))
    return t.codigoInvalido;
  if (
    [
      'LimitExceededException',
      'TooManyRequestsException',
      'TooManyFailedAttemptsException',
    ].includes(nombre)
  )
    return t.temporal;
  if (nombre === 'UsernameExistsException') return t.correoRegistrado;
  if (nombre === 'InvalidPasswordException') return t.validacion.clave;
  if (nombre === 'NetworkError') return t.errorRed;
  return t.credenciales;
}
