export type TipoComida = 'DESAYUNO' | 'ALMUERZO' | 'CENA';
export type Pasillo =
  | 'FRUTAS_VERDURAS'
  | 'CARNES_PESCADOS'
  | 'LACTEOS_HUEVOS'
  | 'PANADERIA'
  | 'DESPENSA'
  | 'CONGELADOS'
  | 'BEBIDAS'
  | 'LIMPIEZA'
  | 'OTROS';
export interface EntradaPlan {
  ingredientes_texto: string;
  personas: number;
  dias: number;
  comidas: TipoComida[];
}
export interface Perfil {
  personas_defecto: number;
  evitar: string[];
  cupo: { limite: number; usados: number; restantes: number; reinicia: string };
}
export interface Ingrediente {
  nombre: string;
  cantidad: number;
  unidad: string;
  en_casa: boolean;
}
export interface Comida {
  tipo: TipoComida;
  nombre: string;
  tiempo_min?: number | null;
  ingredientes: Ingrediente[];
  pasos: string[];
}
export interface Plan {
  planId: string;
  estado: 'GENERANDO' | 'LISTO' | 'ERROR';
  entrada: EntradaPlan;
  creado_en: string;
  error?: string;
  prompt_version?: string;
  modelo?: string;
  menu?: {
    version_esquema: string;
    dias: { dia: number; comidas: Comida[] }[];
  };
}
export interface ResumenPlan {
  planId: string;
  estado: Plan['estado'];
  creado_en: string;
  dias: number;
  personas: number;
}
export interface PaginaPlanes {
  planes: ResumenPlan[];
  cursor: string | null;
}
export interface ItemCompra {
  id: string;
  nombre: string;
  cantidad: number;
  unidad: string;
  pasillo: Pasillo;
  comprado: boolean;
}
export interface ListaCompra {
  planId: string;
  items: ItemCompra[];
  actualizado_en: string;
}
