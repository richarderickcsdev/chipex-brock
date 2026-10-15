import { useEffect, useState } from 'react';
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  signIn,
  signUp,
  confirmSignUp,
  resendSignUpCode,
  resetPassword,
  confirmResetPassword,
} from 'aws-amplify/auth';
import { useSesion } from '../auth/contexto';
import { mensajeAuth } from '../auth/servicio';
import { textos as t } from '../i18n/es';

type Modo = 'acceso' | 'registro' | 'verificar' | 'recuperar' | 'restablecer';
const rutas: Record<Modo, string> = {
  acceso: '/acceso',
  registro: '/registro',
  verificar: '/verificar',
  recuperar: '/recuperar',
  restablecer: '/restablecer',
};
const claveValida = (valor: string) =>
  valor.length >= 10 &&
  /[a-z]/.test(valor) &&
  /[A-Z]/.test(valor) &&
  /[0-9]/.test(valor);

export function Acceso({ modo }: { modo: Modo }) {
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { actualizar, vencida } = useSesion();
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [mostrar, setMostrar] = useState(false);
  const [espera, setEspera] = useState(0);
  const [reenviando, setReenviando] = useState(false);
  const necesitaClave = ['acceso', 'registro', 'restablecer'].includes(modo);
  const necesitaCodigo = ['verificar', 'restablecer'].includes(modo);
  const esquema = z
    .object({
      correo: z.email(t.validacion.correo),
      clave: z.string().optional(),
      codigo: z.string().optional(),
    })
    .superRefine((datos, ctx) => {
      if (
        necesitaClave &&
        (!datos.clave || (modo !== 'acceso' && !claveValida(datos.clave)))
      )
        ctx.addIssue({
          code: 'custom',
          path: ['clave'],
          message: t.validacion.clave,
        });
      if (necesitaCodigo && !datos.codigo?.trim())
        ctx.addIssue({
          code: 'custom',
          path: ['codigo'],
          message: t.validacion.codigo,
        });
    });
  type Datos = z.infer<typeof esquema>;
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    mode: 'onBlur',
    defaultValues: { correo: params.get('correo') ?? '' },
    shouldUnregister: true,
  });
  useEffect(() => {
    if (espera <= 0) return;
    const timer = window.setTimeout(() => setEspera(espera - 1), 1000);
    return () => clearTimeout(timer);
  }, [espera]);
  const ir = (siguiente: Modo, correo: string) =>
    navigate(`${rutas[siguiente]}?correo=${encodeURIComponent(correo)}`, {
      state: location.state,
    });
  const enviar = async (datos: Datos) => {
    setError('');
    setMensaje('');
    try {
      if (modo === 'registro') {
        await signUp({
          username: datos.correo,
          password: datos.clave!,
          options: { userAttributes: { email: datos.correo } },
        });
        ir('verificar', datos.correo);
      } else if (modo === 'verificar') {
        await confirmSignUp({
          username: datos.correo,
          confirmationCode: datos.codigo!.trim(),
        });
        navigate('/acceso', {
          state: { ...location.state, mensaje: t.verificado },
          replace: true,
        });
      } else if (modo === 'recuperar') {
        try {
          await resetPassword({ username: datos.correo });
        } catch (e) {
          if (!(e instanceof Error) || e.name !== 'UserNotFoundException')
            throw e;
        }
        ir('restablecer', datos.correo);
      } else if (modo === 'restablecer') {
        await confirmResetPassword({
          username: datos.correo,
          confirmationCode: datos.codigo!.trim(),
          newPassword: datos.clave!,
        });
        navigate('/acceso', {
          state: { ...location.state, mensaje: t.claveCambiada },
          replace: true,
        });
      } else {
        const resultado = await signIn({
          username: datos.correo,
          password: datos.clave!,
          options: { authFlowType: 'USER_SRP_AUTH' },
        });
        if (resultado.nextStep.signInStep === 'CONFIRM_SIGN_UP') {
          ir('verificar', datos.correo);
          return;
        }
        if (resultado.nextStep.signInStep === 'RESET_PASSWORD') {
          ir('recuperar', datos.correo);
          return;
        }
        if (!resultado.isSignedIn) throw new Error();
        await actualizar();
        const destino = location.state?.desde;
        navigate(
          typeof destino === 'string' &&
            destino.startsWith('/') &&
            !destino.startsWith('//')
            ? destino
            : '/historial',
          { replace: true },
        );
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'UserNotConfirmedException')
        ir('verificar', datos.correo);
      else setError(mensajeAuth(e));
    }
  };
  const reenviar = async () => {
    if (espera || reenviando) return;
    const correo = getValues('correo');
    if (!z.email().safeParse(correo).success) {
      setError(t.validacion.correo);
      return;
    }
    setError('');
    setReenviando(true);
    try {
      if (modo === 'verificar') await resendSignUpCode({ username: correo });
      else {
        try {
          await resetPassword({ username: correo });
        } catch (e) {
          if (!(e instanceof Error) || e.name !== 'UserNotFoundException')
            throw e;
        }
      }
      setMensaje(t.codigoEnviado);
      setEspera(60);
    } catch (e) {
      setError(mensajeAuth(e));
    } finally {
      setReenviando(false);
    }
  };
  const titulo = modo === 'restablecer' ? t.nuevaClave : t[modo];
  return (
    <section className="tarjeta acceso">
      <p className="ceja">{t.nombre}</p>
      <h1>{titulo}</h1>
      <p>{t.descripcion}</p>
      {vencida && (
        <p className="mensaje" role="status">
          {t.sesionVencida}
        </p>
      )}
      {(mensaje || location.state?.mensaje || modo === 'restablecer') && (
        <p role="status" className="mensaje">
          {mensaje || location.state?.mensaje || t.codigoEnviado}
        </p>
      )}
      <form onSubmit={handleSubmit(enviar)} noValidate>
        <label htmlFor="correo">{t.correo}</label>
        <input
          id="correo"
          type="email"
          autoComplete="email"
          {...register('correo')}
          aria-invalid={Boolean(errors.correo)}
          aria-describedby={errors.correo ? 'error-correo' : undefined}
        />
        {errors.correo && (
          <p id="error-correo" className="campo-error">
            {errors.correo.message}
          </p>
        )}
        {necesitaCodigo && (
          <>
            <label htmlFor="codigo">{t.codigo}</label>
            <input
              id="codigo"
              inputMode="numeric"
              autoComplete="one-time-code"
              {...register('codigo')}
              aria-invalid={Boolean(errors.codigo)}
              aria-describedby={errors.codigo ? 'error-codigo' : undefined}
            />
            {errors.codigo && (
              <p id="error-codigo" className="campo-error">
                {errors.codigo.message}
              </p>
            )}
          </>
        )}
        {necesitaClave && (
          <>
            <label htmlFor="clave">{t.clave}</label>
            <input
              id="clave"
              type={mostrar ? 'text' : 'password'}
              autoComplete={
                modo === 'acceso' ? 'current-password' : 'new-password'
              }
              {...register('clave')}
              aria-invalid={Boolean(errors.clave)}
              aria-describedby="ayuda-clave"
            />
            <button
              type="button"
              className="enlace"
              onClick={() => setMostrar(!mostrar)}
              aria-pressed={mostrar}
            >
              {mostrar ? t.ocultarClave : t.mostrarClave}
            </button>
            <p
              id="ayuda-clave"
              className={errors.clave ? 'campo-error' : 'ayuda'}
            >
              {errors.clave?.message || (modo !== 'acceso' ? t.politica : '')}
            </p>
          </>
        )}
        {error && (
          <p role="alert" className="mensaje error">
            {error}
          </p>
        )}
        <button className="principal ancho" disabled={isSubmitting}>
          {isSubmitting ? t.esperando : titulo}
        </button>
      </form>
      {necesitaCodigo && (
        <>
          <button
            type="button"
            className="secundario"
            onClick={() => void reenviar()}
            disabled={espera > 0 || reenviando}
          >
            {t.reenviar}
          </button>
          {espera > 0 && <p role="status">{t.esperaReenvio(espera)}</p>}
        </>
      )}
      <div className="acciones">
        {modo !== 'acceso' && (
          <Link to="/acceso" state={location.state}>
            {t.acceso}
          </Link>
        )}
        {modo === 'acceso' && (
          <>
            <Link to="/registro" state={location.state}>
              {t.registro}
            </Link>
            <Link to="/recuperar" state={location.state}>
              {t.olvide}
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
