import { beforeEach, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { Sesion } from '../src/auth/Sesion';
import { useSesion } from '../src/auth/contexto';
import { EVENTO_SESION, obtenerToken } from '../src/auth/servicio';
vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: vi.fn(),
  signOut: vi.fn(),
}));
vi.mock('aws-amplify/utils', () => ({
  Hub: { listen: vi.fn(() => () => {}) },
}));
vi.mock('../src/auth/servicio', () => ({
  EVENTO_SESION: 'brock:sesion-vencida',
  obtenerToken: vi.fn(),
}));
function Estado() {
  const { usuario, vencida, salir } = useSesion();
  return (
    <>
      <p>{usuario?.correo ?? 'Sin sesión'}</p>
      {vencida && <p>Sesión vencida</p>}
      <button onClick={() => void salir()}>Salir</button>
    </>
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  vi.mocked(obtenerToken).mockResolvedValue('token');
  vi.mocked(getCurrentUser).mockResolvedValue({
    userId: 'usuario-a',
    username: 'persona',
    signInDetails: { loginId: 'a@example.com' },
  });
  vi.mocked(signOut).mockResolvedValue();
});
function montar() {
  const cache = new QueryClient();
  cache.setQueryData(['lista', 'usuario-a'], { privado: true });
  sessionStorage.setItem('brock:borrador:usuario-a', 'arroz');
  render(
    <QueryClientProvider client={cache}>
      <Sesion>
        <Estado />
      </Sesion>
    </QueryClientProvider>,
  );
  return cache;
}
it('al cerrar sesión elimina caché privada y borrador del dispositivo', async () => {
  const cache = montar();
  await screen.findByText('a@example.com');
  await userEvent.setup().click(screen.getByRole('button', { name: 'Salir' }));
  expect(await screen.findByText('Sin sesión')).toBeVisible();
  expect(signOut).toHaveBeenCalledOnce();
  expect(cache.getQueryData(['lista', 'usuario-a'])).toBeUndefined();
  expect(sessionStorage.getItem('brock:borrador:usuario-a')).toBeNull();
});
it('ante vencimiento borra datos consultados pero conserva el borrador de esa pestaña', async () => {
  const cache = montar();
  await screen.findByText('a@example.com');
  act(() => window.dispatchEvent(new Event(EVENTO_SESION)));
  expect(screen.getByText('Sin sesión')).toBeVisible();
  expect(screen.getByText('Sesión vencida')).toBeVisible();
  expect(cache.getQueryData(['lista', 'usuario-a'])).toBeUndefined();
  expect(sessionStorage.getItem('brock:borrador:usuario-a')).toBe('arroz');
});
