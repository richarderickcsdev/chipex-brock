import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { pedir, ErrorAPI } from '../api/cliente';
import { usePerfil } from '../api/consultas';
import type { EntradaPlan, Perfil, Plan, TipoComida } from '../api/tipos';
import { useSesion } from '../auth/contexto';
import { Cargando, ErrorMensaje } from '../componentes/Comunes';
import { useConexion } from '../componentes/useConexion';
import { esquemaPlan } from '../api/validacion';
import { textos as t } from '../i18n/es';
import { fecha, limpiarTexto } from '../utilidades';

function leerBorrador(clave: string): unknown {
  try {
    return JSON.parse(sessionStorage.getItem(clave) ?? 'null');
  } catch {
    return null;
  }
}
function FormularioPlan({
  perfil,
  usuario,
}: {
  perfil: Perfil;
  usuario: string;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const conectado = useConexion();
  const [error, setError] = useState<unknown>(null);
  const clave = `brock:borrador:${usuario}`;
  const [inicial] = useState(() => {
    const anterior = esquemaPlan.safeParse(location.state?.entrada);
    if (anterior.success) return anterior.data;
    const borrador = leerBorrador(clave);
    const datos =
      typeof borrador === 'object' && borrador !== null
        ? (borrador as Partial<EntradaPlan>)
        : {};
    // Conservar también formularios incompletos: la validación ocurre al enviar.
    return {
      ingredientes_texto:
        typeof datos.ingredientes_texto === 'string'
          ? datos.ingredientes_texto
          : '',
      personas:
        typeof datos.personas === 'number'
          ? datos.personas
          : perfil.personas_defecto,
      dias: typeof datos.dias === 'number' ? datos.dias : 7,
      comidas: Array.isArray(datos.comidas)
        ? datos.comidas.filter((tipo): tipo is TipoComida =>
            ['DESAYUNO', 'ALMUERZO', 'CENA'].includes(tipo),
          )
        : (['ALMUERZO', 'CENA'] as TipoComida[]),
    };
  });
  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EntradaPlan>({
    resolver: zodResolver(esquemaPlan),
    defaultValues: inicial,
  });
  useEffect(() => {
    const subscription = watch((valores) => {
      try {
        sessionStorage.setItem(clave, JSON.stringify(valores));
      } catch {
        /* El almacenamiento puede estar deshabilitado. */
      }
    });
    return () => subscription.unsubscribe();
  }, [watch, clave]);
  const ingredientes = watch('ingredientes_texto');
  const enviar = async (datos: EntradaPlan) => {
    setError(null);
    try {
      const plan = await pedir<Pick<Plan, 'planId' | 'estado'>>('/planes', {
        method: 'POST',
        body: JSON.stringify({
          ...datos,
          ingredientes_texto: limpiarTexto(datos.ingredientes_texto),
        }),
      });
      try {
        sessionStorage.removeItem(clave);
      } catch {
        /* El plan ya fue aceptado; continuar a su estado. */
      }
      void cache.invalidateQueries({ queryKey: ['perfil'] });
      void cache.invalidateQueries({ queryKey: ['historial'] });
      navigate(`/planes/${encodeURIComponent(plan.planId)}`);
    } catch (e) {
      setError(e);
      if (e instanceof ErrorAPI && e.estado === 429)
        void cache.invalidateQueries({ queryKey: ['perfil'] });
    }
  };
  return (
    <section className="tarjeta">
      <h1>{t.nuevo}</h1>
      <p className="cupo">
        {t.cupo(perfil.cupo.restantes, perfil.cupo.limite)}
      </p>
      <p className="ayuda">{t.reinicio(fecha(perfil.cupo.reinicia))}</p>
      {perfil.cupo.restantes === 0 && (
        <p role="status" className="mensaje">
          {t.agotado}
        </p>
      )}
      <form onSubmit={handleSubmit(enviar)} noValidate>
        <label htmlFor="ingredientes">{t.ingredientes}</label>
        <textarea
          id="ingredientes"
          rows={5}
          placeholder={t.ejemplo}
          {...register('ingredientes_texto')}
          aria-describedby="contador ingredientes-error"
          aria-invalid={Boolean(errors.ingredientes_texto)}
        />
        <p id="contador" className="ayuda">
          {t.contador(ingredientes.length)}
        </p>
        {errors.ingredientes_texto && (
          <p id="ingredientes-error" className="campo-error">
            {errors.ingredientes_texto.message}
          </p>
        )}
        {!ingredientes.trim() && <p className="mensaje">{t.despensaVacia}</p>}
        <div className="dos-columnas">
          <div>
            <label htmlFor="personas">{t.personas}</label>
            <input
              id="personas"
              type="number"
              min={1}
              max={10}
              {...register('personas', { valueAsNumber: true })}
              aria-invalid={Boolean(errors.personas)}
              aria-describedby="personas-error"
            />
            {errors.personas && (
              <p id="personas-error" className="campo-error">
                {errors.personas.message}
              </p>
            )}
          </div>
          <div>
            <label htmlFor="dias">{t.dias}</label>
            <input
              id="dias"
              type="number"
              min={1}
              max={7}
              {...register('dias', { valueAsNumber: true })}
              aria-invalid={Boolean(errors.dias)}
              aria-describedby="dias-error"
            />
            {errors.dias && (
              <p id="dias-error" className="campo-error">
                {errors.dias.message}
              </p>
            )}
          </div>
        </div>
        <fieldset aria-describedby="comidas-error">
          <legend>{t.comidas}</legend>
          <div className="opciones">
            {(['DESAYUNO', 'ALMUERZO', 'CENA'] as const).map((tipo) => (
              <label key={tipo} className="opcion">
                <input type="checkbox" value={tipo} {...register('comidas')} />
                {t.tiposComida[tipo]}
              </label>
            ))}
          </div>
          {errors.comidas && (
            <p id="comidas-error" className="campo-error">
              {errors.comidas.message}
            </p>
          )}
        </fieldset>
        <ErrorMensaje error={error} />
        {error instanceof ErrorAPI && error.reinicia && (
          <p>{t.reinicio(fecha(error.reinicia))}</p>
        )}
        <button
          className="principal generar"
          disabled={
            isSubmitting ||
            !conectado ||
            perfil.cupo.restantes === 0 ||
            ingredientes.length > 1000
          }
        >
          {isSubmitting ? t.generando : t.generar}
        </button>
      </form>
    </section>
  );
}
export function NuevoPlan() {
  const perfil = usePerfil();
  const { usuario } = useSesion();
  if (perfil.isPending) return <Cargando />;
  if (perfil.error)
    return (
      <>
        <ErrorMensaje error={perfil.error} />
        <button onClick={() => void perfil.refetch()}>{t.reintentar}</button>
      </>
    );
  return (
    <FormularioPlan
      key={usuario!.id}
      usuario={usuario!.id}
      perfil={perfil.data}
    />
  );
}
