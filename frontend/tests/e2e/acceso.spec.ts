import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('las rutas privadas exigen sesión y el registro valida contraseña en móvil/escritorio', async ({
  page,
}) => {
  await page.goto('/nuevo');
  await expect(
    page.getByRole('heading', { name: 'Iniciar sesión' }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Crear cuenta' }).click();
  await expect(
    page.getByRole('heading', { name: 'Crear cuenta' }),
  ).toBeVisible();
  await page.getByLabel('Correo electrónico').fill('prueba@example.com');
  await page.getByLabel('Contraseña', { exact: true }).fill('corta');
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await expect(
    page.getByText(
      'La contraseña debe cumplir todos los requisitos indicados.',
    ),
  ).toBeVisible();
  await expect(page.getByLabel('Correo electrónico')).toHaveValue(
    'prueba@example.com',
  );
  const desborda = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(desborda).toBe(false);
  const accesibilidad = await new AxeBuilder({ page }).analyze();
  expect(accesibilidad.violations).toEqual([]);
});
