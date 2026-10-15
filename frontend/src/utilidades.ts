export const fecha = (valor: string) =>
  new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(valor));
export const cantidad = (valor: number) =>
  new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 }).format(valor);
export const limpiarTexto = (texto: string) =>
  texto
    .replace(/[\p{Cc}\p{Cf}]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
