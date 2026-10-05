import { textos } from '../i18n/es';

export function Inicio() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-4xl font-bold text-green-800">{textos.nombre}</h1>
      <p className="mt-4 text-xl">{textos.descripcion}</p>
      <p className="mt-8 rounded-xl bg-white p-6 shadow-sm">
        {textos.estadoInicial}
      </p>
    </main>
  );
}
