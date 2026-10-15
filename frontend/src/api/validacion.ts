import { z } from 'zod';
import { textos as t } from '../i18n/es';
export const esquemaPlan = z.object({
  ingredientes_texto: z.string().max(1000, t.validacion.ingredientes),
  personas: z
    .number(t.validacion.personas)
    .int(t.validacion.personas)
    .min(1, t.validacion.personas)
    .max(10, t.validacion.personas),
  dias: z
    .number(t.validacion.dias)
    .int(t.validacion.dias)
    .min(1, t.validacion.dias)
    .max(7, t.validacion.dias),
  comidas: z
    .array(z.enum(['DESAYUNO', 'ALMUERZO', 'CENA']))
    .min(1, t.validacion.comidas)
    .max(3),
});
