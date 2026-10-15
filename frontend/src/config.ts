import { Amplify } from 'aws-amplify';

export const configurado = Boolean(
  import.meta.env.VITE_API_URL &&
  import.meta.env.VITE_COGNITO_USER_POOL_ID &&
  import.meta.env.VITE_COGNITO_CLIENT_ID,
);
export function configurarAWS() {
  if (configurado)
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
          userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
          loginWith: { email: true },
        },
      },
    });
}
