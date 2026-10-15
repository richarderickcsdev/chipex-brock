import { lazy, Suspense, useState } from 'react';
import {
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { useSesion } from './auth/contexto';
import { configurado } from './config';
import { Cargando, ErrorMensaje, FocoRuta } from './componentes/Comunes';
import { useConexion } from './componentes/useConexion';
import { PWA } from './componentes/PWA';
import { textos as t } from './i18n/es';

const Acceso = lazy(() =>
  import('./paginas/Acceso').then((m) => ({ default: m.Acceso })),
);
const NuevoPlan = lazy(() =>
  import('./paginas/NuevoPlan').then((m) => ({ default: m.NuevoPlan })),
);
const Ajustes = lazy(() =>
  import('./paginas/Ajustes').then((m) => ({ default: m.Ajustes })),
);
const Historial = lazy(() =>
  import('./paginas/Historial').then((m) => ({ default: m.Historial })),
);
const DetallePlan = lazy(() =>
  import('./paginas/DetallePlan').then((m) => ({ default: m.DetallePlan })),
);
const Compras = lazy(() =>
  import('./paginas/Compras').then((m) => ({ default: m.Compras })),
);

function Privado() {
  const { usuario, cargando } = useSesion();
  const location = useLocation();
  if (cargando) return <Cargando />;
  return usuario ? (
    <Outlet />
  ) : (
    <Navigate
      to="/acceso"
      replace
      state={{ desde: location.pathname + location.search }}
    />
  );
}
function Publico() {
  const { usuario, cargando } = useSesion();
  if (cargando) return <Cargando />;
  return usuario ? <Navigate to="/historial" replace /> : <Outlet />;
}
export function App() {
  const { usuario, salir } = useSesion();
  const [error, setError] = useState<unknown>(null);
  const [saliendo, setSaliendo] = useState(false);
  const conectado = useConexion();
  const cerrar = async () => {
    setError(null);
    setSaliendo(true);
    try {
      await salir();
    } catch (e) {
      setError(e);
    } finally {
      setSaliendo(false);
    }
  };
  return (
    <>
      <a className="saltar" href="#contenido">
        {t.saltar}
      </a>
      <header className="cabecera">
        <Link className="marca" to={usuario ? '/historial' : '/acceso'}>
          ◒ {t.nombre}
        </Link>
        {usuario && (
          <>
            <nav aria-label={t.menuPrincipal}>
              <NavLink to="/nuevo">{t.nuevo}</NavLink>
              <NavLink to="/historial">{t.historial}</NavLink>
              <NavLink to="/ajustes">{t.ajustes}</NavLink>
            </nav>
            <button
              className="enlace"
              disabled={saliendo}
              onClick={() => void cerrar()}
            >
              {t.salir}
            </button>
          </>
        )}
      </header>
      <main id="contenido" tabIndex={-1}>
        <FocoRuta />
        {!conectado && (
          <p role="status" className="mensaje">
            {t.sinConexion}
          </p>
        )}
        <ErrorMensaje error={error} />
        {!configurado ? (
          <p role="alert" className="mensaje error">
            {t.configuracion}
          </p>
        ) : (
          <Suspense fallback={<Cargando />}>
            <Routes>
              <Route element={<Publico />}>
                <Route
                  path="/acceso"
                  element={<Acceso key="acceso" modo="acceso" />}
                />
                <Route
                  path="/registro"
                  element={<Acceso key="registro" modo="registro" />}
                />
                <Route
                  path="/verificar"
                  element={<Acceso key="verificar" modo="verificar" />}
                />
                <Route
                  path="/recuperar"
                  element={<Acceso key="recuperar" modo="recuperar" />}
                />
                <Route
                  path="/restablecer"
                  element={<Acceso key="restablecer" modo="restablecer" />}
                />
              </Route>
              <Route element={<Privado />}>
                <Route path="/nuevo" element={<NuevoPlan />} />
                <Route path="/ajustes" element={<Ajustes />} />
                <Route path="/historial" element={<Historial />} />
                <Route path="/planes/:planId" element={<DetallePlan />} />
                <Route path="/planes/:planId/lista" element={<Compras />} />
              </Route>
              <Route path="*" element={<Navigate to="/historial" replace />} />
            </Routes>
          </Suspense>
        )}
        <PWA />
      </main>
      <footer>{t.descripcion}</footer>
    </>
  );
}
