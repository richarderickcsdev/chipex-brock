import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { NuevoPlan } from '../src/paginas/NuevoPlan';
import { ContextoSesion } from '../src/auth/contexto';
import { pedir } from '../src/api/cliente';
vi.mock('../src/api/cliente', () => ({
  pedir: vi.fn(),
  ErrorAPI: class extends Error {},
  mensajeError: (e: Error) => e.message,
}));
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  vi.mocked(pedir).mockResolvedValue({
    personas_defecto: 3,
    evitar: [],
    cupo: {
      limite: 5,
      restantes: 4,
      usados: 1,
      reinicia: '2026-10-16T05:00:00Z',
    },
  });
});
function montar() {
  const cache = new QueryClient();
  cache.setQueryData(['perfil', 'usuario-a'], {
    personas_defecto: 3,
    evitar: [],
    cupo: {
      limite: 5,
      restantes: 5,
      usados: 0,
      reinicia: '2026-10-16T05:00:00Z',
    },
  });
  render(
    <QueryClientProvider client={cache}>
      <ContextoSesion.Provider
        value={{
          usuario: { id: 'usuario-a', correo: 'a@example.com' },
          cargando: false,
          vencida: false,
          actualizar: async () => {},
          salir: async () => {},
        }}
      >
        <MemoryRouter initialEntries={['/nuevo']}>
          <Routes>
            <Route path="/nuevo" element={<NuevoPlan />} />
            <Route path="/planes/:planId" element={<p>Plan en proceso</p>} />
          </Routes>
        </MemoryRouter>
      </ContextoSesion.Provider>
    </QueryClientProvider>,
  );
  return userEvent.setup();
}
it('precarga el perfil y permite generar con despensa vacía usando el contrato real', async () => {
  vi.mocked(pedir).mockResolvedValueOnce({
    planId: 'plan-nuevo',
    estado: 'GENERANDO',
  });
  const user = montar();
  expect(screen.getByLabelText('Personas')).toHaveValue(3);
  expect(screen.getByLabelText('Días')).toHaveValue(7);
  expect(screen.getByText(/La despensa está vacía/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Generar mi plan' }));
  expect(await screen.findByText('Plan en proceso')).toBeVisible();
  expect(pedir).toHaveBeenCalledWith(
    '/planes',
    expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        ingredientes_texto: '',
        personas: 3,
        dias: 7,
        comidas: ['ALMUERZO', 'CENA'],
      }),
    }),
  );
});
it('impide generar sin comidas y conserva un borrador aislado por usuario', async () => {
  const user = montar();
  await user.type(screen.getByLabelText('¿Qué tienes en casa?'), 'arroz');
  await user.click(screen.getByLabelText('Almuerzo'));
  await user.click(screen.getByLabelText('Cena'));
  await user.click(screen.getByRole('button', { name: 'Generar mi plan' }));
  expect(
    await screen.findByText('Selecciona al menos una comida.'),
  ).toBeVisible();
  expect(pedir).not.toHaveBeenCalled();
  expect(sessionStorage.getItem('brock:borrador:usuario-a')).toContain('arroz');
  expect(sessionStorage.getItem('brock:borrador:usuario-b')).toBeNull();
});
it('recupera los datos del mismo usuario después de una sesión vencida', () => {
  sessionStorage.setItem(
    'brock:borrador:usuario-a',
    JSON.stringify({
      ingredientes_texto: 'tomates',
      personas: 2,
      dias: 1,
      comidas: ['CENA'],
    }),
  );
  montar();
  expect(screen.getByLabelText('¿Qué tienes en casa?')).toHaveValue('tomates');
  expect(screen.getByLabelText('Días')).toHaveValue(1);
});
