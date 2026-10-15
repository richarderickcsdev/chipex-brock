import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { pedir, ErrorAPI } from '../src/api/cliente';
import { obtenerToken, vencerSesion } from '../src/auth/servicio';

vi.mock('../src/auth/servicio', () => ({
  obtenerToken: vi.fn(),
  vencerSesion: vi.fn(),
}));
const fetchMock = vi.fn();
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal('fetch', fetchMock);
  vi.mocked(obtenerToken).mockResolvedValue('jwt-inicial');
  vi.mocked(vencerSesion).mockResolvedValue();
});
afterEach(() => vi.unstubAllGlobals());
describe('cliente autenticado', () => {
  it('renueva el token una vez ante 401 y conserva método/body', async () => {
    vi.mocked(obtenerToken)
      .mockResolvedValueOnce('anterior')
      .mockResolvedValueOnce('renovado');
    fetchMock
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response('{"ok":true}'));
    await expect(
      pedir('/perfil', { method: 'PUT', body: '{"personas_defecto":2}' }),
    ).resolves.toEqual({ ok: true });
    expect(obtenerToken).toHaveBeenLastCalledWith(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: 'PUT',
      cache: 'no-store',
      body: '{"personas_defecto":2}',
      headers: {
        Authorization: 'Bearer renovado',
        'Content-Type': 'application/json',
      },
    });
  });
  it('cierra la sesión tras segundo 401 y no entra en un bucle', async () => {
    fetchMock.mockImplementation(
      async () => new Response('{}', { status: 401 }),
    );
    await expect(pedir('/perfil')).rejects.toThrow('Tu sesión terminó');
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(vencerSesion).toHaveBeenCalledOnce();
  });
  it('rechaza antes de enviar si no hay sesión', async () => {
    vi.mocked(obtenerToken).mockRejectedValue(new Error('SESION'));
    await expect(pedir('/planes')).rejects.toThrow('Tu sesión terminó');
    expect(fetchMock).not.toHaveBeenCalled();
    expect(vencerSesion).toHaveBeenCalledOnce();
  });
  it('expone cupo y reinicio sin reintentar POST en 429', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            codigo: 'CUPO_AGOTADO',
            mensaje: 'Sin cupo',
            reinicia: '2026-10-16T05:00:00Z',
          },
        }),
        { status: 429 },
      ),
    );
    const error = await pedir('/planes', { method: 'POST', body: '{}' }).catch(
      (e) => e,
    );
    expect(error).toBeInstanceOf(ErrorAPI);
    if (!(error instanceof ErrorAPI)) throw new Error('Se esperaba ErrorAPI');
    expect(error.reinicia).toBe('2026-10-16T05:00:00Z');
    expect(fetchMock).toHaveBeenCalledOnce();
  });
  it('admite DELETE 204 sin intentar leer JSON', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(
      pedir('/planes/id', { method: 'DELETE' }),
    ).resolves.toBeUndefined();
  });
  it('conserva las cancelaciones para no publicar datos de una ruta abandonada', async () => {
    fetchMock.mockRejectedValue(new DOMException('Cancelado', 'AbortError'));
    await expect(pedir('/perfil')).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(vencerSesion).not.toHaveBeenCalled();
  });
});
