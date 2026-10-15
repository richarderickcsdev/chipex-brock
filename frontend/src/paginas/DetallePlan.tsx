import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { usePlan } from '../api/plan';
import { ErrorAPI } from '../api/cliente';
import { AvisoIA, Cargando, ErrorMensaje } from '../componentes/Comunes';
import { textos as t } from '../i18n/es';
import { cantidad, fecha } from '../utilidades';

export function DetallePlan() {
  const { planId = '' } = useParams();
  const consulta = usePlan(planId);
  const [params, setParams] = useSearchParams();
  const [ahora, setAhora] = useState(() => Date.now());
  const plan = consulta.data;
  useEffect(() => {
    if (plan?.estado !== 'GENERANDO') return;
    const timer = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [plan?.estado]);
  if (consulta.isPending) return <Cargando />;
  if (consulta.error || !plan)
    return (
      <section className="tarjeta">
        <h1>
          {consulta.error instanceof ErrorAPI && consulta.error.estado === 404
            ? t.noEncontrado
            : t.errorGeneral}
        </h1>
        <ErrorMensaje error={consulta.error} />
        <Link to="/historial">{t.volver}</Link>
        <button onClick={() => void consulta.refetch()}>{t.reintentar}</button>
      </section>
    );
  const agotado = ahora - new Date(plan.creado_en).getTime() >= 60_000;
  const dia =
    plan.menu?.dias.find((d) => d.dia === Number(params.get('dia'))) ??
    plan.menu?.dias[0];
  return (
    <section className="pila">
      <div className="titulo-acciones">
        <div>
          <h1>{t.menu}</h1>
          <p>
            {t.personasDias(plan.entrada.personas, plan.entrada.dias)} ·{' '}
            {fecha(plan.creado_en)}
          </p>
        </div>
        <Link to="/historial">{t.volver}</Link>
      </div>
      {plan.estado === 'GENERANDO' && (
        <div className="tarjeta" role="status">
          <h2>{t.generando}</h2>
          <progress aria-label={t.generando} />
          <p>{agotado ? t.esperaAgotada : t.progresoGeneracion}</p>
          {agotado && (
            <button
              onClick={() => void consulta.refetch()}
              disabled={consulta.isFetching}
            >
              {t.consultar}
            </button>
          )}
        </div>
      )}
      {plan.estado === 'ERROR' && (
        <div className="tarjeta">
          <p role="alert" className="mensaje error">
            {plan.error || t.errorGeneral}
          </p>
          <Link
            className="boton principal"
            to="/nuevo"
            state={{ entrada: plan.entrada }}
          >
            {t.mismosDatos}
          </Link>
        </div>
      )}
      {plan.estado === 'LISTO' && (
        <>
          <AvisoIA />
          <div className="acciones">
            <Link
              className="boton principal"
              to={`/planes/${encodeURIComponent(planId)}/lista`}
            >
              {t.compras}
            </Link>
            <Link to="/nuevo" state={{ entrada: plan.entrada }}>
              {t.otroPlan}
            </Link>
          </div>
          <div className="dias" role="group" aria-label={t.dias}>
            {plan.menu?.dias.map((d) => (
              <button
                key={d.dia}
                aria-pressed={dia?.dia === d.dia}
                onClick={() =>
                  setParams({ dia: String(d.dia) }, { replace: true })
                }
              >
                {t.dia(d.dia)}
              </button>
            ))}
          </div>
          <div className="platos">
            {dia?.comidas.map((comida) => (
              <article className="tarjeta" key={comida.tipo}>
                <p className="ceja">{t.tiposComida[comida.tipo]}</p>
                <h2>{comida.nombre}</h2>
                {comida.tiempo_min && <p>{t.minutos(comida.tiempo_min)}</p>}
                <p>
                  {comida.ingredientes
                    .slice(0, 3)
                    .map((i) => i.nombre)
                    .join(', ')}
                </p>
                <details>
                  <summary>{t.detalle}</summary>
                  <ul className="ingredientes">
                    {comida.ingredientes.map((item, index) => (
                      <li key={index}>
                        {item.nombre} — {cantidad(item.cantidad)} {item.unidad}{' '}
                        <span className="etiqueta">
                          {item.en_casa ? t.enCasa : t.comprar}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <h3>{t.pasos}</h3>
                  <ol>
                    {comida.pasos.map((paso, index) => (
                      <li key={index}>{paso}</li>
                    ))}
                  </ol>
                </details>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
