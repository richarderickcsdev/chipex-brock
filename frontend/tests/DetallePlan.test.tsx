import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DetallePlan } from '../src/paginas/DetallePlan';
import { pedir } from '../src/api/cliente';
import type { Plan } from '../src/api/tipos';
vi.mock('../src/api/cliente', () => ({
  pedir: vi.fn(),
  ErrorAPI: class extends Error {},
  mensajeError: (e: Error) => e.message,
}));
const base: Plan = {
  planId: 'plan-a',
  estado: 'GENERANDO',
  creado_en: new Date().toISOString(),
  entrada: {
    ingredientes_texto: 'arroz',
    personas: 2,
    dias: 1,
    comidas: ['CENA'],
  },
};
beforeEach(() => vi.resetAllMocks());
function montar() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={['/planes/plan-a']}>
        <Routes>
          <Route path="/planes/:planId" element={<DetallePlan />} />
          <Route path="/nuevo" element={<p>Reintento preparado</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
it('consulta el estado asíncrono hasta publicar el menú validado', async () => {
  vi.mocked(pedir)
    .mockResolvedValueOnce(base)
    .mockResolvedValue({
      ...base,
      estado: 'LISTO',
      menu: {
        version_esquema: '1.0',
        dias: [
          {
            dia: 1,
            comidas: [
              {
                tipo: 'CENA',
                nombre: 'Arroz con verduras',
                ingredientes: [
                  {
                    nombre: 'Arroz',
                    cantidad: 200,
                    unidad: 'g',
                    en_casa: true,
                  },
                ],
                pasos: ['Cocina el arroz.'],
              },
            ],
          },
        ],
      },
    });
  montar();
  expect(
    await screen.findByRole('heading', { name: 'Generando tu menú…' }),
  ).toBeVisible();
  await waitFor(
    () =>
      expect(
        screen.getByRole('heading', { name: 'Arroz con verduras' }),
      ).toBeVisible(),
    { timeout: 4000 },
  );
  expect(pedir).toHaveBeenCalledTimes(2);
  expect(screen.getByText(/Menú generado con IA/)).toBeVisible();
});
it('ofrece volver al formulario con la entrada original cuando falla', async () => {
  vi.mocked(pedir).mockResolvedValue({
    ...base,
    estado: 'ERROR',
    error: 'No pudimos generar el plan.',
  });
  montar();
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'No pudimos generar el plan.',
  );
  await userEvent
    .setup()
    .click(
      screen.getByRole('link', { name: 'Reintentar con los mismos datos' }),
    );
  expect(await screen.findByText('Reintento preparado')).toBeVisible();
});
