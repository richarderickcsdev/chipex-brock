import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQueryClient } from '@tanstack/react-query';
import { pedir } from '../api/cliente';
import { usePerfil } from '../api/consultas';
import type { Perfil } from '../api/tipos';
import { useSesion } from '../auth/contexto';
import { Cargando, ErrorMensaje } from '../componentes/Comunes';
import { useConexion } from '../componentes/useConexion';
import { textos as t } from '../i18n/es';
import { useNavigate } from 'react-router-dom';

const normalizar = (s: string) =>
  s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();
const esquema = z.object({
  personas_defecto: z
    .number(t.validacion.personas)
    .int(t.validacion.personas)
    .min(1, t.validacion.personas)
    .max(10, t.validacion.personas),
  evitar: z
    .array(z.string().trim().min(1).max(40))
    .max(20)
    .refine(
      (v) => new Set(v.map(normalizar)).size === v.length,
      t.validacion.preferencia,
    ),
});
function FormularioPerfil({ perfil }: { perfil: Perfil }) {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const { usuario, salir } = useSesion();
  const conectado = useConexion();
  const [ingrediente, setIngrediente] = useState('');
  const [errorPreferencia, setErrorPreferencia] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [guardado, setGuardado] = useState(false);
  const [borrando, setBorrando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [correo, setCorreo] = useState('');
  const {
    register,
    watch,
    setValue,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof esquema>>({
    resolver: zodResolver(esquema),
    defaultValues: {
      personas_defecto: perfil.personas_defecto,
      evitar: perfil.evitar,
    },
  });
  const evitar = watch('evitar');
  const agregar = () => {
    const valor = ingrediente.trim();
    if (
      !valor ||
      valor.length > 40 ||
      evitar.length >= 20 ||
      evitar.some((x) => normalizar(x) === normalizar(valor))
    ) {
      setErrorPreferencia(t.validacion.preferencia);
      return;
    }
    setValue('evitar', [...evitar, valor], { shouldDirty: true });
    setIngrediente('');
    setErrorPreferencia('');
    setGuardado(false);
  };
  const guardar = async (datos: z.infer<typeof esquema>) => {
    setError(null);
    setGuardado(false);
    try {
      const resultado = await pedir<Perfil>('/perfil', {
        method: 'PUT',
        body: JSON.stringify(datos),
      });
      cache.setQueryData(['perfil', usuario?.id], resultado);
      setGuardado(true);
    } catch (e) {
      setError(e);
    }
  };
  const eliminar = async () => {
    setBorrando(true);
    setError(null);
    try {
      await pedir('/cuenta', {
        method: 'DELETE',
        body: JSON.stringify({ confirmacion_email: correo.trim() }),
      });
      await salir();
      navigate('/acceso', {
        replace: true,
        state: { mensaje: t.borradoIniciado },
      });
    } catch (e) {
      setError(e);
    } finally {
      setBorrando(false);
    }
  };
  return (
    <div className="pila">
      <section className="tarjeta">
        <h1>{t.ajustes}</h1>
        <form onSubmit={handleSubmit(guardar)} noValidate>
          <label htmlFor="personas-defecto">{t.defecto}</label>
          <input
            id="personas-defecto"
            type="number"
            min={1}
            max={10}
            {...register('personas_defecto', { valueAsNumber: true })}
            aria-invalid={Boolean(errors.personas_defecto)}
          />
          {errors.personas_defecto && (
            <p className="campo-error">{errors.personas_defecto.message}</p>
          )}
          <label htmlFor="evitar">{t.preferencias}</label>
          <div className="entrada-accion">
            <input
              id="evitar"
              value={ingrediente}
              maxLength={40}
              onChange={(e) => setIngrediente(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  agregar();
                }
              }}
            />
            <button type="button" onClick={agregar}>
              {t.agregar}
            </button>
          </div>
          <p className="ayuda">{t.avisoPreferencias}</p>
          {(errorPreferencia || errors.evitar) && (
            <p role="alert" className="campo-error">
              {errorPreferencia || t.validacion.preferencia}
            </p>
          )}
          <ul className="etiquetas">
            {evitar.map((item, i) => (
              <li key={item}>
                {item}
                <button
                  type="button"
                  aria-label={`${t.quitar} ${item}`}
                  onClick={() => {
                    setValue(
                      'evitar',
                      evitar.filter((_, index) => index !== i),
                      { shouldDirty: true },
                    );
                    setGuardado(false);
                  }}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
          {guardado && (
            <p role="status" className="mensaje">
              {t.guardado}
            </p>
          )}
          <button className="principal" disabled={isSubmitting || !conectado}>
            {isSubmitting ? t.esperando : t.guardar}
          </button>
        </form>
      </section>
      <section className="tarjeta">
        <h2>{t.eliminarCuenta}</h2>
        <p>{t.avisoBorrado}</p>
        {!confirmando ? (
          <button className="peligro" onClick={() => setConfirmando(true)}>
            {t.eliminarCuenta}
          </button>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void eliminar();
            }}
          >
            <label htmlFor="confirmacion-email">{t.confirmarCorreo}</label>
            <input
              id="confirmacion-email"
              type="email"
              autoComplete="email"
              required
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
            />
            <div className="acciones">
              <button
                className="peligro"
                disabled={
                  borrando ||
                  !conectado ||
                  correo.trim().toLowerCase() !== usuario?.correo.toLowerCase()
                }
              >
                {borrando ? t.esperando : t.eliminarCuenta}
              </button>
              <button
                type="button"
                disabled={borrando}
                onClick={() => setConfirmando(false)}
              >
                {t.cancelar}
              </button>
            </div>
          </form>
        )}
      </section>
      <ErrorMensaje error={error} />
    </div>
  );
}
export function Ajustes() {
  const perfil = usePerfil();
  if (perfil.isPending) return <Cargando />;
  if (perfil.error)
    return (
      <>
        <ErrorMensaje error={perfil.error} />
        <button onClick={() => void perfil.refetch()}>{t.reintentar}</button>
      </>
    );
  return <FormularioPerfil perfil={perfil.data} />;
}
