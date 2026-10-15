import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import {
  signIn,
  signUp,
  confirmSignUp,
  resendSignUpCode,
  resetPassword,
} from 'aws-amplify/auth';
import { Acceso } from '../src/paginas/Acceso';
import { ContextoSesion } from '../src/auth/contexto';

vi.mock('aws-amplify/auth', () => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
  resendSignUpCode: vi.fn(),
  resetPassword: vi.fn(),
  confirmResetPassword: vi.fn(),
}));
beforeEach(() => vi.resetAllMocks());
function montar(modo: 'acceso' | 'registro' | 'verificar' | 'recuperar') {
  render(
    <ContextoSesion.Provider
      value={{
        usuario: null,
        cargando: false,
        vencida: false,
        actualizar: async () => {},
        salir: async () => {},
      }}
    >
      <MemoryRouter initialEntries={['/?correo=persona%40example.com']}>
        <Routes>
          <Route path="/" element={<Acceso modo={modo} />} />
          <Route path="/verificar" element={<p>Verificación pendiente</p>} />
          <Route path="/historial" element={<p>Historial privado</p>} />
          <Route path="/restablecer" element={<p>Nuevo código solicitado</p>} />
          <Route path="/acceso" element={<p>Correo confirmado</p>} />
        </Routes>
      </MemoryRouter>
    </ContextoSesion.Provider>,
  );
  return userEvent.setup();
}
it('impide registrar contraseñas débiles sin llamar Cognito y conserva el correo', async () => {
  const user = montar('registro');
  await user.type(screen.getByLabelText('Contraseña'), 'corta');
  await user.click(screen.getByRole('button', { name: 'Crear cuenta' }));
  expect(
    await screen.findByText(
      'La contraseña debe cumplir todos los requisitos indicados.',
    ),
  ).toBeVisible();
  expect(signUp).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Correo electrónico')).toHaveValue(
    'persona@example.com',
  );
});
it('registra y dirige a la verificación sin conservar la contraseña en almacenamiento', async () => {
  const user = montar('registro');
  vi.mocked(signUp).mockResolvedValue({
    isSignUpComplete: false,
    nextStep: {
      signUpStep: 'CONFIRM_SIGN_UP',
      codeDeliveryDetails: {
        deliveryMedium: 'EMAIL',
        destination: 'p***@example.com',
        attributeName: 'email',
      },
    },
  });
  await user.type(screen.getByLabelText('Contraseña'), 'ClaveValida123');
  await user.click(screen.getByRole('button', { name: 'Crear cuenta' }));
  expect(await screen.findByText('Verificación pendiente')).toBeVisible();
  expect(signUp).toHaveBeenCalledWith(
    expect.objectContaining({
      username: 'persona@example.com',
      password: 'ClaveValida123',
    }),
  );
});
it('redirige un inicio pendiente de confirmación al flujo de verificación', async () => {
  const user = montar('acceso');
  vi.mocked(signIn).mockResolvedValue({
    isSignedIn: false,
    nextStep: { signInStep: 'CONFIRM_SIGN_UP' },
  });
  await user.type(screen.getByLabelText('Contraseña'), 'ClaveValida123');
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
  expect(await screen.findByText('Verificación pendiente')).toBeVisible();
  expect(signIn).toHaveBeenCalledWith(
    expect.objectContaining({ options: { authFlowType: 'USER_SRP_AUTH' } }),
  );
});
it('confirma un código y permite iniciar sesión', async () => {
  const user = montar('verificar');
  vi.mocked(confirmSignUp).mockResolvedValue({
    isSignUpComplete: true,
    nextStep: { signUpStep: 'DONE' },
  });
  await user.type(screen.getByLabelText('Código de verificación'), '123456');
  await user.click(screen.getByRole('button', { name: 'Verificar correo' }));
  expect(await screen.findByText('Correo confirmado')).toBeVisible();
});
it('limita el reenvío del código después de enviarlo', async () => {
  const user = montar('verificar');
  await user.click(screen.getByRole('button', { name: 'Reenviar código' }));
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Reenviar código' }),
    ).toBeDisabled(),
  );
  expect(resendSignUpCode).toHaveBeenCalledOnce();
});
it('no revela la inexistencia del correo durante recuperación', async () => {
  const user = montar('recuperar');
  vi.mocked(resetPassword).mockRejectedValue(
    Object.assign(new Error(), { name: 'UserNotFoundException' }),
  );
  await user.click(
    screen.getByRole('button', { name: 'Recuperar contraseña' }),
  );
  expect(await screen.findByText('Nuevo código solicitado')).toBeVisible();
});
