# chipex-brock

Planificador de comidas y lista de compras con IA. PWA con React 18 y TypeScript,
backend Python 3.12 e infraestructura serverless AWS con SAM.

## Estado

Fases 1, 2, 3 y 4: base local, infraestructura, módulos compartidos y API
implementados y verificados. La generación real con Bedrock sigue pendiente de F5.

## Convención de commits

Los cambios se organizan por historia de usuario dentro de cada etapa, indicando
la etapa del plan, el identificador de la HU y una descripción del avance real:

```text
Etapa <n>, HU-<nn>: <descripción breve>
```

Ejemplos:

```text
Etapa 3, HU-14: validar el esquema y la coherencia del plan
Etapa 3, HU-16: implementar reserva y devolución del cupo diario
Etapa 4, HU-08: implementar lectura y actualización del perfil
```

Cada commit incluye el código, las pruebas y la documentación correspondientes
a esa historia. La descripción indica el trabajo efectivamente realizado;
el commit no implica que estén completos criterios que dependan de otras etapas.
Los cambios compartidos que no corresponden exclusivamente a una HU indican
su propósito mediante etiquetas como `BASE`, `QA` o `DOCUMENTACION`:

```text
Etapa 1, BASE: crear estructura y herramientas de desarrollo
Etapa 3, QA: completar pruebas de integración compartidas
Etapas 1-3, DOCUMENTACION: registrar avances y convención de commits
```

El historial inicial de dos commits fue reorganizado con autorización en commits
por HU y tareas transversales. La clasificación está registrada en
[`docs/HISTORIAL.md`](docs/HISTORIAL.md). Las HU sin cambios específicos conservan
su estado pendiente; no se crean commits vacíos para simular su implementación.

## Estructura

- `frontend/`: React, Vite, Tailwind, Router, TanStack Query, Auth, formularios y PWA.
- `backend/api/`: rutas HTTP, tareas asíncronas y baja de cuenta (F4 completada).
- `backend/generador/`: integración Bedrock (F5).
- `backend/compartido/`: esquema, validación, DynamoDB y cupo (F3 completada).
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

El backend tiene 58 pruebas de validación e integración con DynamoDB simulada
mediante moto. El frontend todavía no tiene pruebas de negocio; Vitest permite
su suite vacía. Las pruebas actuales no invocan AWS ni Bedrock reales.

Playwright está configurado para escritorio, Android y Safari móvil. Cuando se
incorporen las pruebas E2E, instalar sus navegadores con
`npx.cmd playwright install` y ejecutar `npm.cmd run test:e2e`.

## Infraestructura — Fase 2

`template.yaml` define:

- DynamoDB `brock-{stage}` con PK/SK, bajo demanda, cifrado, TTL y PITR.
- Cognito por entorno, correo verificado, SRP, cliente sin secreto y tokens cortos.
- HTTP API con JWT, CORS al dominio CloudFront y límites por etapa:
  dev 5 peticiones/s (ráfaga 10), prod 20 peticiones/s (ráfaga 40).
- Lambda API (256 MB, 10 s) y generador (512 MB, 60 s), Python 3.12/arm64.
- Generador asíncrono con 0 reintentos ante errores de función y edad máxima
  del evento de 60 s. La idempotencia y recuperación de cupo se implementarán
  en F3–F5; desactivar reintentos no garantiza entrega exactamente una vez.
- Roles separados: API sin acceso Bedrock; generador sin capacidad de borrar
  datos; acceso a la tabla y a los grupos de logs concretos.
- S3 privado cifrado y CloudFront HTTPS con OAC y fallback SPA.
- Logs JSON de Lambda con retención de 14 días, alarmas de errores Lambda/5xx,
  SNS por correo y presupuesto de 10 USD configurable.

El presupuesto cubre el gasto de **toda la cuenta**, no solo Brock. Excluye
créditos y reembolsos para reflejar consumo incluso durante el período de prueba.
Cada stack crea su presupuesto con alertas reales al superar 50/80/100 % y
una alerta prevista al superar 100 %. Las alarmas operativas son umbrales de
conteo iniciales; las tasas y métricas de validación se completan en F5/F11.

### Herramientas AWS locales

Instaladas en `.venv-tools`, separadas de las dependencias del backend:
SAM CLI 1.166.2 y AWS CLI v1 (1.46.1). No se modificó el PATH global.

```powershell
py -3.12 -m venv .venv-tools
.\.venv-tools\Scripts\python.exe -m pip install -r requirements-tools.txt
$env:SAM_CLI_TELEMETRY = '0'
$env:AWS_EC2_METADATA_DISABLED = 'true'
.\.venv-tools\Scripts\sam.exe validate --lint --region us-east-1
.\.venv-tools\Scripts\sam.exe build --config-env dev
```

`us-east-1` solo se utilizó para validar la sintaxis; la región real se decide
en F0. Build verificado sin Docker: SAM resuelve las dependencias de F3 con
wheels Linux/ARM64, incluida la extensión nativa de Pydantic.
`CodeUri: backend/` incluye ambos paquetes y `compartido/`, con handlers
`api.app.handler` y `generador.app.handler`. Mantener las dependencias fijadas
en `backend/requirements.txt` compatibles con `pyproject.toml`. Si una futura
dependencia requiere compilación, usar `sam build --use-container` con Docker.

### Parámetros para el despliegue de F7

| Parámetro | Uso |
| --- | --- |
| `Stage` | `dev` o `prod`; separa tabla, usuarios, API, Lambdas, bucket y CDN |
| `BedrockModelId` | Obligatorio: foundation model regional compatible con Converse |
| `AlertEmail` | Obligatorio: correo para SNS y Budgets |
| `CupoDiario` | Por defecto 5, zona `America/Lima` |
| `MonthlyBudgetUsd` | Por defecto 10 USD mensuales |

El permiso Bedrock se restringe al ARN regional derivado del modelo. Si el
modelo elegido requiere un perfil de inferencia (por ejemplo, ID `us.*`),
adaptar explícitamente sus ARN y regiones antes de desplegar; esta plantilla
no concede acceso global para perfiles. La elección sigue pendiente de F0.

Cuando se complete F6 y se disponga de un perfil AWS configurado:

```powershell
.\.venv-tools\Scripts\sam.exe deploy --config-env dev --region <region> --profile <perfil> --parameter-overrides Stage=dev BedrockModelId=<modelo> AlertEmail=<correo> CupoDiario=5 MonthlyBudgetUsd=10
```

Para prod usar `--config-env prod` y `Stage=prod`. Confirmar la suscripción
SNS desde el correo recibido. Los outputs dan URL API, URL frontend, bucket,
distribución, tabla, región e identificadores Cognito; sirven para completar
`frontend/.env` según `.env.example` (nunca incluir secretos).

### Publicación del frontend (F7/F8)

Desde `frontend/`, tras configurar los outputs del entorno:

```powershell
npm.cmd run build
..\.venv-tools\Scripts\python.exe -m awscli s3 sync dist/ s3://<bucket> --delete --region <region> --profile <perfil>
..\.venv-tools\Scripts\python.exe -m awscli cloudfront create-invalidation --distribution-id <id> --paths "/*" --profile <perfil>
```

CORS permite solo la URL CloudFront de la propia pila; el acceso desde Vite
local requerirá un proxy de desarrollo al integrar la API en F8.

### Eliminación del entorno

Antes de borrar la pila, vaciar su bucket frontend (CloudFormation no elimina
un bucket no vacío). Desde la raíz:

```powershell
.\.venv-tools\Scripts\python.exe -m awscli s3 rm s3://<bucket-del-entorno> --recursive --region <region> --profile <perfil>
.\.venv-tools\Scripts\sam.exe delete --config-env dev --stack-name brock-dev --region <region> --profile <perfil>
```

Usar los nombres y entorno prod al eliminar prod. La plantilla no tiene
políticas de retención: se borran datos, usuarios y logs de la pila. SAM puede
usar un bucket administrado de artefactos compartido entre despliegues; revisar
los artefactos residuales al cerrar la práctica. Verificar creación, alertas y
eliminación en AWS sigue siendo parte del despliegue, no de la validación local.

### Pendientes

- Confirmar F0: cuenta, créditos, región, modelo, cuotas y precios.
- Conectar los módulos compartidos a las rutas en F4 y al generador en F5.
- Implementar recuperación de generaciones vencidas y bloqueo de nuevas
  escrituras durante la eliminación de cuenta al integrar las Lambdas.
- Incorporar correos de recuperación en español y eliminación Cognito en la
  implementación de acceso/cuenta; no se otorgan permisos administrativos aún.
- Completar íconos PNG y validación de instalación PWA en F8.

Nunca guardar credenciales AWS ni tokens en el repositorio.

## API — Fase 4

La Lambda `api` recibe eventos HTTP API v2 y solo acepta el `sub` de
`requestContext.authorizer.jwt.claims`. No confía en un usuario del body, query
string, path ni en un header enviado fuera del autorizador. Las respuestas
privadas no incluyen `PK`, `SK`, `quota_fecha` ni `cupo_devuelto`.

| Ruta | Estado |
| --- | --- |
| `GET /perfil` | Implementada; incluye cupo restante |
| `PUT /perfil` | Implementada; valida personas y preferencias |
| `POST /planes` | Implementada; reserva y crea `GENERANDO`, invoca generador como evento |
| `GET /planes` | Implementada; historial descendente con cursor |
| `GET /planes/{planId}` | Implementada; recupera generaciones vencidas |
| `DELETE /planes/{planId}` | Implementada; borra plan/lista, no devuelve cupo |
| `GET /planes/{planId}/lista` | Implementada; ordenada por pasillo |
| `PATCH /planes/{planId}/lista/items/{itemId}` | Implementada; actualización puntual |
| `DELETE /cuenta` | Implementada; baja asíncrona y bloqueo de escrituras |

La respuesta a `POST /planes` es 202. Un error confirmado al invocar Lambda
devuelve el cupo y marca el plan `ERROR`; un timeout ambiguo conserva el plan
`GENERANDO` para evitar duplicar generaciones. Un plan que supera 60 segundos
se recupera durante consultas y devuelve su cupo una sola vez.

La eliminación de cuenta escribe `ACCOUNT=BORRANDO` antes de encolar el worker.
Ese estado bloquea escrituras, el worker deshabilita y elimina Cognito, borra
la partición DynamoDB y deja `ACCOUNT=BORRADA` con TTL. El evento del worker es
interno y no se acepta como body HTTP. Si el worker falla, el bloqueo permanece
y el evento puede reintentarse sin borrar datos parcialmente como si hubiera
terminado.

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

## Verificación de Fase 2 — 04/10/2026

| Comprobación | Resultado |
| --- | --- |
| `sam validate --lint` | Plantilla fuente válida |
| `sam build --config-env dev` | Correcto, Python 3.12/arm64 |
| Validación de `.aws-sam/build/template.yaml` | Correcta |
| Importación de handlers empaquetados | Correcta; API provisional devuelve 501 |
| Ruff / mypy | Sin errores en 8 archivos Python |
| Dependencias de herramientas (`pip check`) | Correctas |
| SAM CLI / AWS CLI | Ejecutables mediante `.venv-tools` |
| Despliegue y pruebas en AWS | Pendientes de F7 |

## Verificación de Fase 4 — 04/10/2026

- 100 pruebas pytest aprobadas, incluyendo eventos HTTP API v2, JWT/sub,
  perfiles, planes, cupos, historiales, listas, marcado y baja Cognito simulada.
- Ruff, mypy y `pip check` sin errores.
- `sam validate --lint` y `sam build --config-env dev` correctos.
- La plantilla incluye destino de fallo asíncrono para compensar generaciones
  vencidas y configuración de permisos para la Lambda API/worker.
- No se ha desplegado en AWS; F6 y F7 siguen pendientes.

## Backend compartido — Fase 3

| Módulo | Responsabilidad |
| --- | --- |
| `esquema.py` | Modelos Pydantic estrictos y JSON Schema completo del plan |
| `entrada.py` | Limpieza de controles y normalización de nombres |
| `validacion.py` | Validación de días, comidas, preferencias y lista de compras |
| `errores.py` | Los seis códigos públicos y respuestas HTTP uniformes |
| `dynamo.py` | Perfil, planes, listas, marcado, paginación y borrado por usuario |
| `cupo.py` | Reserva/devolución atómicas, TTL y reinicio diario en Lima |

Cada `Repositorio` queda ligado al `sub` que deberá tomar la API del JWT.
Los identificadores ajenos o inexistentes producen el mismo error 404.
El historial pagina hasta 20 planes en orden descendente y valida que el
cursor pertenezca a la misma partición.

`Cupo.reservar` crea el plan `GENERANDO` y aumenta el contador en una sola
transacción. `Cupo.devolver` pasa a `ERROR` y devuelve el cupo una sola vez,
al contador del día original. `Repositorio.finalizar` guarda menú y lista
juntos y pasa a `LISTO`; un resultado tardío no puede publicar después de
que se devolvió el cupo. Eliminar un plan listo no devuelve cupo.

Detalles de integración y alcance de las validaciones en
[`backend/compartido/README.md`](backend/compartido/README.md).

### Verificación de Fase 3 — 04/10/2026

- 58 pruebas pytest aprobadas: contratos, límites, limpieza, coherencia,
  cantidades, preferencias, aislamiento, paginación, borrado por lotes,
  cupos, concurrencia simulada y cambio de día.
- Ruff y mypy sin errores; dependencias Python compatibles (`pip check`).
- `sam validate --lint` y `sam build --config-env dev` correctos.
- Binario Pydantic empaquetado para CPython 3.12/Linux/aarch64.

Las pruebas concurrentes sincronizan la entrada de dos solicitudes y serializan
solo la ejecución interna de moto para modelar transacciones atómicas:
moto no garantiza aislamiento transaccional entre hilos. El código productivo
usa las condiciones y transacciones de DynamoDB, sin bloqueos locales.
