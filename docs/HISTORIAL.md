# Organización del historial por etapa e historia

Cada commit describe una contribución real a una HU dentro de una etapa.
Una misma HU puede recibir avances en distintas etapas. El orden respeta las
dependencias técnicas: comienza con la base y con HU-01 para la autenticación.
La existencia de un commit no significa que toda la HU esté terminada.

## Etapa 1

- **BASE:** estructura del repositorio, frontend inicial, herramientas Python y
  TypeScript, dependencias, configuración de pruebas y archivos iniciales SAM.
  Son preparativos compartidos, no historias de usuario completas.

## Etapa 2

| HU | Contribución |
| --- | --- |
| HU-01 | User Pool y política de registro por correo y contraseña |
| HU-02 | Verificación automática y plantilla del correo de verificación |
| HU-03 | Cliente Cognito sin secreto y configuración de inicio por SRP |
| HU-06 | Duración, renovación y revocación de tokens Cognito |
| HU-28 | Alojamiento de la PWA con S3 privado y CloudFront HTTPS/OAC |
| HU-33 | Tabla aislada por entorno, API JWT y roles separados de Lambda |
| HU-16 | Configuración de invocación asíncrona sin reintentos ante errores |
| HU-34 | Límites de peticiones por etapa |
| HU-36 | Presupuesto y alertas de consumo |
| HU-38 | Configuración SAM por entorno y herramientas AWS reproducibles |
| HU-39 | SNS y alarmas de errores Lambda/API |

Los handlers de esta etapa son provisionales. Las interfaces de autenticación,
los endpoints funcionales y las pruebas en AWS aún corresponden a etapas futuras.

## Etapa 3

| HU o tarea | Contribución |
| --- | --- |
| BASE | Contratos compartidos, utilidades de texto/errores/serialización y dependencias Lambda |
| HU-07 | Borrado paginado por lotes de datos DynamoDB del usuario |
| HU-08 | Lectura y actualización del perfil, conservando su fecha de creación |
| HU-14 | Validación del formato del menú y coherencia con la solicitud |
| HU-09 | Pruebas de límites y exclusión léxica de preferencias |
| HU-10 | Pruebas de limpieza de ingredientes y despensa vacía |
| HU-11 | Pruebas de tipos y límites de personas/días |
| HU-12 | Pruebas de selección válida y no repetida de comidas |
| HU-16 | Reserva transaccional y devolución idempotente del cupo en Lima |
| HU-20 | Lectura de la lista y persistencia conjunta del menú y las compras |
| HU-21 | Marcado puntual de ítems y validación de booleanos |
| HU-24 | Historial descendente y cursor validado por usuario |
| HU-26 | Eliminación conjunta de plan/lista con protección de planes activos |
| HU-33 | Pruebas de aislamiento de planes, listas, perfiles y cupos |
| HU-35 | Pruebas de rechazo de entradas adicionales, excesivas o con controles |
| HU-37 | Persistencia de modelo, versión del prompt, tokens y latencia |
| QA | Pruebas de integración y contratos transversales |
| DOCUMENTACION | Estado de las etapas, instrucciones y convención de commits |

Los modelos y utilidades de BASE son compartidos por varias HU; los commits
de pruebas de HU-09/10/11/12/35 comprueban esas capacidades sin duplicar módulos.
HU-07 cubre aquí DynamoDB, no la baja Cognito ni su pantalla. HU-37 prepara
la persistencia; la medición real de Bedrock se incorpora en F5/F9.

## Verificaciones del estado final

- 58 pruebas pytest aprobadas con DynamoDB simulada.
- Ruff y mypy sin errores.
- SAM build Linux/ARM64 y validación de plantilla correctos.
- Frontend compilado y comprobado en F1.
- Despliegue y comprobaciones en AWS pendientes de F7.

## Etapa 4

| HU o tarea | Contribución |
| --- | --- |
| BASE | Router HTTP API v2, identidad JWT, límites de body, logging anonimizado y respuestas sin atributos internos |
| HU-07 | `DELETE /cuenta`, bloqueo `BORRANDO`, worker interno idempotente, baja Cognito y borrado DynamoDB |
| HU-08 | `GET /perfil` y `PUT /perfil` |
| HU-09 | Guardado y validación de preferencias por API |
| HU-13 | `POST /planes`, ULID e invocación asíncrona del generador |
| HU-16 | Recuperación de cupo ante fallos confirmados y generaciones vencidas |
| HU-17 | `GET /planes/{planId}` y estados públicos |
| HU-20 | `GET /planes/{planId}/lista` ordenada por pasillo |
| HU-21 | `PATCH /planes/{planId}/lista/items/{itemId}` |
| HU-24 | `GET /planes` con cursor y resumen público |
| HU-26 | `DELETE /planes/{planId}` con respuesta 204 |
| HU-33 | Todas las rutas privadas usan exclusivamente el `sub` del JWT y pruebas de aislamiento |

| BASE | Entorno Docker local con DynamoDB Local y adaptador HTTP API v2, sin acceso a AWS |

HU-14, HU-15 y HU-35 tienen soporte compartido y pruebas de validación, pero la
integración de sus mensajes de generación continúa en F5. HU-01 a HU-06 tienen
infraestructura Cognito de F2; las pantallas y flujos de frontend continúan en F8.
