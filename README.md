# chipex-brock

Planificador de comidas y lista de compras con IA. PWA con React 18 y TypeScript,
backend Python 3.12 e infraestructura serverless AWS con SAM.

## Estado

Fase 1: estructura y herramientas locales. La lógica de negocio se incorporará
en las siguientes fases. `template.yaml` es un marcador no desplegable hasta F2.

## Estructura

- `frontend/`: React, Vite, Tailwind, Router, TanStack Query, Auth, formularios y PWA.
- `backend/api/`: rutas de Lambda (F4).
- `backend/generador/`: integración Bedrock (F5).
- `backend/compartido/`: esquema, validación, DynamoDB y cupo (F3).
- `backend/prompts/`: prompts versionados (F5).
- `backend/tests/`: pruebas con pytest y moto.
- `evaluacion/`: casos y mediciones del modelo (F9).
- `template.yaml` y `samconfig.toml`: infraestructura (F2).

## Preparación local (PowerShell)

Requisitos: Python 3.12, Node 22.12+ de la rama 22, Node 24 o Node 26+
(verificado con Node 24) y Git.
Se usa `npm.cmd` para funcionar sin cambiar la política de scripts de Windows.

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe .
.\.venv\Scripts\python.exe -m pytest
```

Desde `frontend/`:

```powershell
npm.cmd ci
npm.cmd run dev
npm.cmd run lint
npm.cmd run format:check
npm.cmd run build
npm.cmd test
```

Las suites aún no contienen pruebas de negocio. Vitest permite la suite vacía;
pytest devuelve código 5 mientras no haya pruebas. Esto no representa pruebas
funcionales superadas. Las primeras pruebas del backend se incorporan en F3.

Playwright está configurado para escritorio, Android y Safari móvil. Cuando se
incorporen las pruebas E2E, instalar sus navegadores con
`npx.cmd playwright install` y ejecutar `npm.cmd run test:e2e`.

## Pendientes para infraestructura

- AWS CLI y SAM CLI no están disponibles en el PATH de esta sesión.
- Confirmar F0: cuenta, créditos, región, modelo Bedrock, cuotas, precios y Budgets.
- Completar la plantilla, el empaquetado de Lambdas y la publicación S3/CloudFront en F2.
- La PWA tiene configuración inicial; íconos PNG y validación de instalación en F8.

Las instrucciones de despliegue y eliminación se completarán al implementar F2.
Nunca guardar credenciales AWS ni tokens en el repositorio.

## Verificación de Fase 1 — 04/10/2026

| Comprobación | Resultado |
| --- | --- |
| Instalación Python en `.venv` y `pip check` | Correcta |
| Ruff | Sin errores |
| mypy | Sin errores en 6 archivos Python |
| ESLint | Sin errores |
| Prettier | Formato correcto |
| TypeScript y build Vite/PWA | Correctos |
| `npm audit` | 0 vulnerabilidades |
| pytest / Vitest | Configurados; todavía sin pruebas |
| Git | Inicializado; archivos sin commit |

React Router 7 y Vitest 5 se eligieron para evitar vulnerabilidades detectadas
en las versiones iniciales. React se mantiene en 18, según la arquitectura.
