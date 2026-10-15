import { useEffect, useState } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';
import { textos as t } from '../i18n/es';

interface EventoInstalar extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: string }>;
}
export function PWA() {
  const [instalar, setInstalar] = useState<EventoInstalar | null>(null);
  const [registro, setRegistro] = useState<ServiceWorkerRegistration>();
  const {
    needRefresh: [actualizar],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW: (_url, registration) => setRegistro(registration),
  });
  const ios =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const standalone =
    window.matchMedia?.('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone;
  useEffect(() => {
    const antes = (e: Event) => {
      e.preventDefault();
      setInstalar(e as EventoInstalar);
    };
    const instalado = () => setInstalar(null);
    window.addEventListener('beforeinstallprompt', antes);
    window.addEventListener('appinstalled', instalado);
    return () => {
      window.removeEventListener('beforeinstallprompt', antes);
      window.removeEventListener('appinstalled', instalado);
    };
  }, []);
  useEffect(() => {
    if (!registro) return;
    const timer = window.setInterval(
      () => {
        if (navigator.onLine) void registro.update().catch(() => undefined);
      },
      60 * 60 * 1000,
    );
    return () => clearInterval(timer);
  }, [registro]);
  const pedirInstalacion = async () => {
    if (!instalar) return;
    try {
      await instalar.prompt();
      await instalar.userChoice;
    } finally {
      setInstalar(null);
    }
  };
  return (
    <aside className="pwa" aria-label={t.nombre}>
      {instalar && (
        <button onClick={() => void pedirInstalacion()}>{t.instalar}</button>
      )}
      {ios && !standalone && <p className="ayuda">{t.ios}</p>}
      {actualizar && (
        <div className="mensaje" role="status">
          <p>{t.versionNueva}</p>
          <button onClick={() => void updateServiceWorker(true)}>
            {t.actualizar}
          </button>
        </div>
      )}
    </aside>
  );
}
