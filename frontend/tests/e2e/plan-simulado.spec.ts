import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { loadEnv } from 'vite';

// Tokens sintéticos para probar el navegador: todas las rutas API se interceptan.
// No se inicia sesión en AWS ni se envía ninguna generación a Bedrock.
test('flujo simulado de plan, menú, lista, marcado y cierre de sesión', async ({
  page,
}) => {
  await page.route(/https:\/\/cognito-idp\..*\.amazonaws\.com/, (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
      },
      contentType: 'application/x-amz-json-1.1',
      body: '{}',
    }),
  );
  const clientId = loadEnv(
    'test',
    process.cwd(),
    'VITE_',
  ).VITE_COGNITO_CLIENT_ID;
  const apiUrl = loadEnv('test', process.cwd(), 'VITE_').VITE_API_URL.replace(
    /\/$/,
    '',
  );
  const user = 'usuario-e2e';
  const payload = {
    sub: user,
    username: user,
    'cognito:username': user,
    email: 'e2e@example.com',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    auth_time: Math.floor(Date.now() / 1000),
  };
  const jwt = (tipo: string) =>
    `${Buffer.from(JSON.stringify({ alg: 'RS256', typ: 'JWT' })).toString('base64url')}.${Buffer.from(JSON.stringify({ ...payload, token_use: tipo, aud: clientId, client_id: clientId })).toString('base64url')}.firma-simulada`;
  await page.addInitScript(
    ({ clientId, user, access, id }) => {
      const prefix = `CognitoIdentityServiceProvider.${clientId}`;
      localStorage.setItem(`${prefix}.LastAuthUser`, user);
      localStorage.setItem(`${prefix}.${user}.accessToken`, access);
      localStorage.setItem(`${prefix}.${user}.idToken`, id);
      localStorage.setItem(
        `${prefix}.${user}.refreshToken`,
        'refresh-simulado',
      );
      localStorage.setItem(`${prefix}.${user}.clockDrift`, '0');
      localStorage.setItem(
        `${prefix}.${user}.signInDetails`,
        JSON.stringify({
          loginId: 'e2e@example.com',
          authFlowType: 'USER_SRP_AUTH',
        }),
      );
    },
    { clientId, user, access: jwt('access'), id: jwt('id') },
  );
  const id = '01J9ZK3Q8M4X7R2T6V5B1N0WCD';
  const entrada = {
    ingredientes_texto: 'arroz',
    personas: 2,
    dias: 1,
    comidas: ['CENA'],
  };
  const creado = new Date().toISOString();
  let consultas = 0;
  let comprado = false;
  let creadoPlan = false;
  await page.route(
    (url) =>
      url.pathname.startsWith('/api/') || url.href.startsWith(`${apiUrl}/`),
    async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.startsWith('/api/')
        ? url.pathname
        : `/api${url.pathname.slice(new URL(apiUrl).pathname.length)}`;
      const method = route.request().method();
      const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Authorization,Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
      };
      if (method === 'OPTIONS') {
        await route.fulfill({ status: 204, headers });
        return;
      }
      let body: unknown;
      let status = 200;
      if (path === '/api/perfil')
        body = {
          personas_defecto: 2,
          evitar: [],
          cupo: {
            limite: 5,
            usados: creadoPlan ? 1 : 0,
            restantes: creadoPlan ? 4 : 5,
            reinicia: new Date(Date.now() + 86400000).toISOString(),
          },
        };
      else if (path === '/api/planes' && method === 'POST') {
        expect(route.request().postDataJSON()).toEqual(entrada);
        creadoPlan = true;
        status = 202;
        body = { planId: id, estado: 'GENERANDO' };
      } else if (path === '/api/planes')
        body = {
          planes: creadoPlan
            ? [
                {
                  planId: id,
                  estado: 'LISTO',
                  creado_en: creado,
                  dias: 1,
                  personas: 2,
                },
              ]
            : [],
          cursor: null,
        };
      else if (path === `/api/planes/${id}`) {
        consultas++;
        body = {
          planId: id,
          estado: consultas === 1 ? 'GENERANDO' : 'LISTO',
          entrada,
          creado_en: creado,
          menu: {
            version_esquema: '1.0',
            dias: [
              {
                dia: 1,
                comidas: [
                  {
                    tipo: 'CENA',
                    nombre: 'Arroz con verduras',
                    tiempo_min: 20,
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
        };
      } else if (path === `/api/planes/${id}/lista`)
        body = {
          planId: id,
          actualizado_en: creado,
          items: [
            {
              id: 'i1',
              nombre: 'Tomate',
              cantidad: 2,
              unidad: 'unidad',
              pasillo: 'FRUTAS_VERDURAS',
              comprado,
            },
          ],
        };
      else if (
        path === `/api/planes/${id}/lista/items/i1` &&
        method === 'PATCH'
      ) {
        comprado = route.request().postDataJSON().comprado;
        body = {
          id: 'i1',
          nombre: 'Tomate',
          cantidad: 2,
          unidad: 'unidad',
          pasillo: 'FRUTAS_VERDURAS',
          comprado,
        };
      } else {
        await route.abort();
        throw new Error(`Ruta no simulada: ${method} ${path}`);
      }
      await route.fulfill({
        status,
        headers,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });
    },
  );
  await page.goto('/nuevo');
  await expect(page.getByRole('heading', { name: 'Nuevo plan' })).toBeVisible();
  await page.getByLabel('¿Qué tienes en casa?').fill('arroz');
  await page.getByLabel('Días', { exact: true }).fill('1');
  await page.getByLabel('Almuerzo').uncheck();
  await page.getByRole('button', { name: 'Generar mi plan' }).click();
  await expect(
    page.getByRole('heading', { name: 'Arroz con verduras' }),
  ).toBeVisible();
  await page.getByText('Ingredientes y preparación').click();
  await expect(page.getByText('Cocina el arroz.')).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByRole('link', { name: 'Lista de compras' }).click();
  await page.getByRole('checkbox', { name: /Tomate/ }).click();
  await expect(page.getByText('¡Lista completada!')).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
  ).toBe(false);
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(
    page.getByRole('heading', { name: 'Iniciar sesión' }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole('heading', { name: 'Iniciar sesión' }),
  ).toBeVisible();
});
