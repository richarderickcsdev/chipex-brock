import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Compras } from '../src/paginas/Compras';
import { textoLista } from '../src/api/textoLista';
import { pedir } from '../src/api/cliente';
import type { ListaCompra } from '../src/api/tipos';
vi.mock('../src/api/cliente', () => ({
  pedir: vi.fn(),
  mensajeError: (e: Error) => e.message,
}));
const lista: ListaCompra = {
  planId: 'plan-a',
  actualizado_en: '2026-10-14T12:00:00Z',
  items: [
    {
      id: 'i1',
      nombre: 'Arroz',
      cantidad: 500,
      unidad: 'g',
      pasillo: 'DESPENSA',
      comprado: false,
    },
  ],
};
beforeEach(() => vi.resetAllMocks());
function montar() {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={['/planes/plan-a/lista']}>
        <Routes>
          <Route path="/planes/:planId/lista" element={<Compras />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return userEvent.setup();
}
it('actualiza de forma optimista y revierte la casilla si falla el servidor', async () => {
  let rechazar!: (e: Error) => void;
  vi.mocked(pedir)
    .mockResolvedValueOnce(lista)
    .mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          rechazar = reject;
        }),
    );
  const user = montar();
  const casilla = await screen.findByRole('checkbox', { name: /Arroz/ });
  await user.click(casilla);
  await waitFor(() => expect(casilla).toBeChecked());
  expect(casilla).toBeDisabled();
  rechazar(new Error('Red interrumpida'));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Restauramos el estado anterior',
  );
  await waitFor(() => expect(casilla).not.toBeChecked());
});
it('guarda la marca y muestra el progreso completado', async () => {
  vi.mocked(pedir)
    .mockResolvedValueOnce(lista)
    .mockResolvedValueOnce({ ...lista.items[0], comprado: true });
  const user = montar();
  await user.click(await screen.findByRole('checkbox', { name: /Arroz/ }));
  expect(await screen.findByText('¡Lista completada!')).toBeVisible();
  expect(pedir).toHaveBeenLastCalledWith('/planes/plan-a/lista/items/i1', {
    method: 'PATCH',
    body: '{"comprado":true}',
  });
});
it('produce texto por pasillo con cantidades y marcas para compartir', () => {
  expect(textoLista(lista)).toContain('Despensa\n□ Arroz — 500 g');
});
