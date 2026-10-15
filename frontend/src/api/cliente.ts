import { obtenerToken, vencerSesion } from '../auth/servicio';
import { textos as t } from '../i18n/es';

export class ErrorAPI extends Error {
  constructor(
    public estado: number,
    public codigo: string,
    mensaje: string,
    public reinicia?: string,
  ) {
    super(mensaje);
  }
}
export async function pedir<T>(
  ruta: string,
  opciones: RequestInit = {},
): Promise<T> {
  if (!navigator.onLine) throw new Error(t.errorRed);
  let token: string;
  try {
    token = await obtenerToken();
  } catch {
    await vencerSesion();
    throw new Error(t.sesionVencida);
  }
  const enviar = (jwt: string) =>
    fetch(`${import.meta.env.VITE_API_URL.replace(/\/$/, '')}${ruta}`, {
      ...opciones,
      cache: 'no-store',
      headers: {
        ...opciones.headers,
        Authorization: `Bearer ${jwt}`,
        ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
      },
    });
  let respuesta: Response;
  try {
    respuesta = await enviar(token);
    if (respuesta.status === 401) {
      try {
        token = await obtenerToken(true);
      } catch {
        await vencerSesion();
        throw new Error(t.sesionVencida);
      }
      respuesta = await enviar(token);
      if (respuesta.status === 401) {
        await vencerSesion();
        throw new Error(t.sesionVencida);
      }
    }
  } catch (error) {
    if (
      (typeof error === 'object' &&
        error !== null &&
        'name' in error &&
        error.name === 'AbortError') ||
      (error instanceof Error && error.message === t.sesionVencida)
    )
      throw error;
    throw new Error(t.errorRed);
  }
  if (respuesta.status === 204) return undefined as T;
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok)
    throw new ErrorAPI(
      respuesta.status,
      datos?.error?.codigo ?? 'ERROR_INTERNO',
      datos?.error?.mensaje ?? t.errorGeneral,
      datos?.error?.reinicia,
    );
  if (datos === null) throw new Error(t.errorGeneral);
  return datos as T;
}
export const mensajeError = (error: unknown) =>
  error instanceof Error ? error.message : t.errorGeneral;
