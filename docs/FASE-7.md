# Fase 7 — Despliegue del entorno `dev` en AWS

## 1. Resumen y alcance

La fase 7 llevó a AWS la infraestructura y el backend preparados durante las
fases anteriores. El resultado registrado es la pila **`brock-dev`**, en
**`us-east-1`**, con estado **`CREATE_COMPLETE`**, y la publicación del frontend
inicial mediante S3 privado y CloudFront.

Se registraron respuestas **401 sin JWT** en los endpoints privados y respuestas
**200 para el HTML y el manifest** del frontend. Quedaron creados Cognito,
API Gateway, las dos Lambdas, DynamoDB y los recursos de observabilidad.
Bedrock quedó configurado con Claude Haiku 4.5; la primera generación autenticada
continúa pendiente.

### Fuentes y fecha del registro

- Registro del despliegue: commits de F7 del **13/10/2026**, zona `-05:00`.
- Ampliación documental: **14/10/2026**.
- Fuentes: `template.yaml`, `samconfig.toml`, `scripts/`,
  `config/aws/`, `README.md`, `docs/HISTORIAL.md` e historial Git.
- Los estados de AWS descritos como realizados corresponden al último registro
  versionado. Esta ampliación documental no ejecutó consultas ni despliegues en AWS.
- Los comandos de las secciones operativas permiten reproducir o volver a
  comprobar el entorno; no constituyen evidencia de una nueva ejecución.

### Relación con las fases anteriores y siguientes

| Fase | Aporte al despliegue |
| --- | --- |
| F1 | Estructura, herramientas y scaffold React/Vite/PWA |
| F2 | Infraestructura SAM: identidad, datos, cómputo, alojamiento y alertas |
| F3 | Validaciones, contratos, repositorio y control de cupo |
| F4 | API privada, generación asíncrona y baja de cuenta |
| F5 | Integración Bedrock Converse, prompt, validación y métricas |
| F6 | Gate local de 117 pruebas, Ruff, mypy y SAM build |
| F7 | Despliegue `dev`, publicación inicial y comprobaciones de acceso |
| F8 | Pantallas, autenticación e integración frontend/API |
| F9 | Evaluación real del modelo y mediciones correspondientes |

## 2. Identificación del entorno

| Dato | Valor registrado |
| --- | --- |
| Proyecto | Brock |
| Entorno | `dev` |
| Pila CloudFormation | `brock-dev` |
| Región | `us-east-1` |
| Estado de la pila | `CREATE_COMPLETE` |
| API | `https://ypdvyu4ev7.execute-api.us-east-1.amazonaws.com/dev` |
| Frontend | `https://d1z78xb68rmhq3.cloudfront.net` |
| Cognito User Pool | `us-east-1_Y24UyAiKr` |
| Cognito App Client | `16ve22c8lo414dl4ktb80qe11h` |
| Tabla DynamoDB | `brock-dev` |
| Distribución CloudFront | `EGDI9BGWT3SF4` |
| Lambda API | `brock-api-dev` |
| Lambda generador | `brock-generador-dev` |
| Modelo configurado | Claude Haiku 4.5 |
| Cupo configurado por defecto | 5 planes por usuario/día; zona `America/Lima` |
| Presupuesto reutilizado | USD 10 mensuales a nivel de cuenta |

El nombre físico del bucket frontend, el ARN del tópico SNS y el ID exacto de
modelo deben consultarse en los outputs o parámetros de la pila. No se deducen
del nombre comercial del modelo ni se inventan valores para completar la tabla.
Los IDs y URLs de esta sección son configuración pública de la aplicación.

## 3. Arquitectura desplegada

```text
Navegador
  ├─ HTTPS → CloudFront → OAC/SigV4 → S3 privado (frontend)
  ├─ Cognito → registro, verificación, SRP y renovación de sesión
  └─ Authorization: Bearer <JWT>
       ↓
     HTTP API /dev → autorizador JWT Cognito
       ↓
     Lambda API ──────────────→ DynamoDB brock-dev
       │
       ├─ invocación asíncrona → Lambda generador
       │                           ├─ Bedrock Converse
       │                           └─ DynamoDB: plan, lista y metadatos
       │
       └─ worker interno de baja de cuenta → Cognito y DynamoDB

Fallo asíncrono del generador → destino Lambda API
Lambdas → CloudWatch Logs/métricas → alarmas → SNS → correo
AWS Budgets de cuenta → alertas de presupuesto existentes
```

El diagrama representa la infraestructura y el flujo implementado en backend.
Las pantallas que permiten completar ese recorrido desde el navegador se
desarrollan en F8.

## 4. Inventario y configuración técnica

### 4.1. DynamoDB

Recurso lógico `Tabla`, nombre `brock-dev`:

- Facturación bajo demanda: `PAY_PER_REQUEST`.
- Clave de partición `PK` y clave de ordenación `SK`, ambas de tipo cadena.
- Cifrado en reposo habilitado.
- TTL habilitado sobre el atributo `ttl`.
- Recuperación a un punto en el tiempo, PITR, habilitada.
- Etiquetas `Project=Brock` y `Stage=dev`.

La misma tabla almacena perfiles, planes, listas y control de cupo mediante el
modelo de claves del backend compartido. El backend liga el acceso al `sub`
recibido del autorizador JWT. La creación de la tabla en AWS está registrada;
las pruebas reales de aislamiento autenticado siguen pendientes.

### 4.2. Cognito

Recursos lógicos `UserPool` y `UserPoolClient`:

- Nombre del pool: `brock-dev`; cliente: `brock-web-dev`.
- Correo como usuario, sin distinción entre mayúsculas y minúsculas.
- Autorregistro habilitado y verificación automática del atributo de correo.
- Recuperación mediante correo verificado.
- Contraseña mínima de 10 caracteres, con minúsculas, mayúsculas y números;
  los símbolos no son obligatorios.
- Asunto de verificación: `Verifica tu correo en Brock`.
- Mensaje: `Tu código de verificación de Brock es {####}.`.
- Cliente sin secreto, apropiado para una aplicación web pública.
- Flujos `ALLOW_USER_SRP_AUTH` y `ALLOW_REFRESH_TOKEN_AUTH`.
- Access token e ID token: 30 minutos; refresh token: 30 días.
- Revocación de tokens habilitada y protección contra errores que revelen
  existencia de usuarios.

El cliente no habilita `USER_PASSWORD_AUTH`; las comprobaciones de inicio de
sesión deben usar SRP mediante la integración elegida en F8. La creación de los
recursos no acredita todavía entrega de correos, recuperación ni sesión real.

### 4.3. API Gateway HTTP API

Recurso lógico `Api`, etapa `dev`:

- Integración proxy `ANY /{proxy+}` hacia la Lambda API.
- Payload HTTP API versión `2.0`.
- Autorizador JWT Cognito por defecto.
- Token tomado de `Authorization`.
- Issuer: `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Y24UyAiKr`.
- Audience: `16ve22c8lo414dl4ktb80qe11h`.
- Límite configurado en `dev`: 5 peticiones/segundo y ráfaga de 10.
- Métricas detalladas de etapa habilitadas.

CORS permite el origen `https://d1z78xb68rmhq3.cloudfront.net`, los headers
`Authorization` y `Content-Type`, y los métodos `GET`, `PUT`, `POST`, `PATCH`,
`DELETE` y `OPTIONS`, con `MaxAge=300` segundos. El origen Vite local no forma
parte de esa configuración; su integración debe resolverse en F8.

Los límites son configuración de throttling de API Gateway. La fase 7 no
registra una prueba de carga real que confirme el comportamiento bajo ráfagas.

### 4.4. Funciones Lambda y ejecución asíncrona

| Propiedad | API | Generador |
| --- | --- | --- |
| Recurso lógico | `FnApi` | `FnGenerador` |
| Handler | `api.app.handler` | `generador.app.handler` |
| Runtime | Python 3.12 | Python 3.12 |
| Arquitectura | ARM64 | ARM64 |
| Memoria | 256 MB | 512 MB |
| Timeout | 10 segundos | 60 segundos |
| Log group | `/aws/lambda/brock-api-dev` | `/aws/lambda/brock-generador-dev` |
| Retención de logs | 14 días | 14 días |
| Formato de logs | JSON | JSON |

Ambas reciben `TABLE_NAME`, `STAGE`, `CUPO_DIARIO`,
`QUOTA_TIMEZONE=America/Lima` y `POWERTOOLS_METRICS_NAMESPACE=Brock/dev`.
La API recibe además el nombre del generador y el User Pool; el generador
recibe el modelo, precios y `MAX_OUTPUT_TOKENS=8192`.

Configuración asíncrona del generador:

- `MaximumRetryAttempts=0` para errores de función.
- `MaximumEventAgeInSeconds=60`.
- Destino `OnFailure`: ARN de `FnApi` mediante `!GetAtt FnApi.Arn`.

El backend reserva cupo y crea el plan `GENERANDO` antes de invocar el generador.
En éxito persiste menú y compras y publica `LISTO`. Ante fallos confirmados o
generaciones vencidas, las rutas de recuperación devuelven el cupo de manera
idempotente y marcan `ERROR`. Una respuesta tardía no debe sobrescribir un plan
ya compensado. Esas reglas tienen cobertura local; falta verificarlas en AWS
con un usuario autenticado.

La API tiene dos reintentos asíncronos y edad máxima de evento de 3600 segundos,
aplicables a invocaciones asíncronas internas. Estos parámetros no significan
que una petición HTTP de API Gateway se reintente automáticamente dos veces.

### 4.5. IAM y separación de responsabilidades

| Rol | Permisos principales | Alcance definido |
| --- | --- | --- |
| `ApiRole` | Lectura/escritura/borrado, query y lotes DynamoDB | Tabla del entorno |
| `ApiRole` | Invocar generador e invocarse como worker | Funciones del entorno |
| `ApiRole` | `AdminGetUser`, `AdminDisableUser`, `AdminDeleteUser` | User Pool del entorno |
| `GeneradorRole` | Lectura, actualización, escritura y transacciones DynamoDB | Tabla del entorno |
| `GeneradorRole` | `bedrock:InvokeModel` | ARN del foundation model regional configurado |
| `GeneradorRole` | Invocar API como destino de fallo | Lambda API del entorno |
| Ambos | Crear streams y escribir logs | Log group correspondiente |

El generador no tiene permisos de borrado DynamoDB y la API no tiene permiso de
invocación Bedrock. La llamada SDK `Converse` se autoriza con
`bedrock:InvokeModel`; F7 retiró la acción `bedrock:Converse` de la política.

La plantilla construye el ARN
`arn:aws:bedrock:us-east-1::foundation-model/<BedrockModelId>`.
Los perfiles de inferencia y las invocaciones entre regiones requieren un
tratamiento de ARN y permisos distinto al definido aquí.

### 4.6. S3 y CloudFront

- Bucket con las cuatro opciones de bloqueo de acceso público activas.
- Propiedad de objetos `BucketOwnerEnforced` y cifrado `AES256`.
- Origin Access Control con firma SigV4 y `SigningBehavior=always`.
- Política de lectura para CloudFront condicionada al ARN de esta distribución.
- Denegación de solicitudes S3 sin transporte seguro.
- CloudFront con raíz `index.html`, redirección HTTP→HTTPS, IPv6, HTTP/2 y HTTP/3.
- `PriceClass_100`, compresión y certificado predeterminado de CloudFront.
- Métodos permitidos `GET`, `HEAD`, `OPTIONS`; caché de `GET` y `HEAD`.
- Política administrada de caché `658327ea-f89d-4fab-a63d-7e88639e58f6`.
- Política de headers de respuesta `67f7725c-6f97-4210-82d7-5512b31e9d03`.
- Fallback SPA: errores de origen 403 y 404 responden con `/index.html`, HTTP
  200 y TTL de error de 0 segundos.

La publicación usa `frontend/dist/`. El manifest y el HTML respondieron 200
según el registro. La instalación PWA, los iconos PNG, las actualizaciones y el
comportamiento móvil requieren la validación prevista en F8. Al comprobar un
asset conviene revisar también el contenido y `Content-Type`: el fallback SPA
puede devolver HTML con 200 para una ruta inexistente.

### 4.7. Observabilidad, SNS y presupuesto

Tópico SNS: `brock-alertas-dev`, con suscripción al correo configurado.
Su política permite publicar a CloudWatch desde alarmas `brock-dev-*` de la
misma cuenta. La suscripción quedó **pendiente de confirmación manual**.

| Alarma | Métrica | Umbral | Ventana |
| --- | --- | --- | --- |
| `brock-dev-api-errors` | Lambda API `Errors`, suma | ≥ 3 | 300 segundos, 1 período |
| `brock-dev-generador-errors` | Generador `Errors`, suma | ≥ 1 | 300 segundos, 1 período |
| `brock-dev-api-5xx` | API Gateway `5xx`, suma | ≥ 3 | 300 segundos, 1 período |

Las tres usan `TreatMissingData=notBreaching` y envían acciones al tópico SNS.
Estos son umbrales de conteo; no representan tasas porcentuales. Un error de
negocio capturado por la función no necesariamente aumenta la métrica Lambda
`Errors`. No hay registro de una prueba de recepción de alarmas por correo.

Se reutilizó el Budget existente de **USD 10 a nivel de cuenta**. El parámetro
`CreateStackBudget=false` evita crear el recurso `MonthlyBudget` de la pila.
Esta condición no enlaza ni modifica automáticamente el presupuesto existente.

Si se habilitara el recurso opcional, la plantilla definiría un presupuesto
mensual de cuenta, sin filtro exclusivo para Brock, que excluye créditos y
reembolsos, con avisos reales al superar 50/80/100 % y previstos al superar
100 %. Esas propiedades de la plantilla no prueban la configuración efectiva
del presupuesto externo reutilizado. Un Budget emite avisos; no impone un
corte automático del consumo.

## 5. Cambios realizados específicamente en F7

| Commit | Cambio y finalidad |
| --- | --- |
| `40b15f4` | Preparación `dev`: precios positivos obligatorios, recuperación opcional del correo desde Budget, modo preview, presupuesto de pila condicional y permiso Bedrock corregido |
| `1e7c104` | Destino asíncrono `OnFailure` enlazado con `!GetAtt FnApi.Arn` |
| `97f8bc5` | Registro del despliegue, outputs, comprobaciones y pendientes |

### 5.1. Precios explícitos

Los archivos de ejemplo dejaron de proponer precios `0` y los scripts exigen
precios positivos. Esto evita publicar métricas de costo nulo por falta de
configuración. La plantilla mantiene el valor predeterminado `0` para ambos
parámetros; por eso el procedimiento documentado usa los scripts y pasa los
precios explícitamente.

### 5.2. Correo recuperable desde el presupuesto existente

Si `ALERT_EMAIL` está vacío, `deploy.ps1` consulta los suscriptores de una
notificación del presupuesto existente: `ACTUAL`, `GREATER_THAN`, umbral 50.
El nombre se toma de `ALERT_EMAIL_BUDGET_NAME` o, por defecto, de
`Presupuesto chipa`. Usa el primer suscriptor de tipo `EMAIL`.

Esta ruta requiere que existan el presupuesto, esa notificación y un correo,
además de permisos para consultarlos. Si no se obtiene dirección, el script
interrumpe el despliegue. El correo recuperado se pasa a `AlertEmail`.

### 5.3. Dependencia del destino de fallo

La referencia al destino del generador pasó de un ARN construido con texto a
`!GetAtt FnApi.Arn`. Así CloudFormation/SAM puede reconocer la relación con el
recurso Lambda de destino. El historial acredita este cambio; no conserva una
salida de error que permita afirmar aquí un mensaje exacto de fallo anterior.

## 6. Preparación y procedimiento reproducible

Los siguientes comandos se ejecutan desde la raíz del repositorio en PowerShell,
salvo donde se indica otro directorio. Los valores de perfil, correo e ID de
modelo deben corresponder a la cuenta y configuración del operador.

### 6.1. Herramientas y perfil

Requisitos: Python 3.12, Node compatible con el frontend, Git, AWS CLI y SAM CLI.
El repositorio registra SAM CLI 1.166.2 y AWS CLI v1 1.46.1 en `.venv-tools`.
Los scripts llaman a `aws` y `sam` por nombre; deben resolverse en el PATH de
la sesión. Para usar las herramientas locales:

```powershell
$env:PATH = "$(Get-Location)\.venv-tools\Scripts;$env:PATH"
$env:SAM_CLI_TELEMETRY = '0'
$env:AWS_EC2_METADATA_DISABLED = 'true'
aws --version
sam --version
```

Las credenciales se resuelven mediante un perfil AWS. Para un perfil nuevo,
configurarlo con el mecanismo de credenciales disponible en la organización y
verificar su identidad:

```powershell
aws sts get-caller-identity --profile <perfil> --region us-east-1
```

La identidad de despliegue necesita crear o actualizar los recursos de la
plantilla, roles IAM y artefactos SAM. Los roles de ejecución Lambda descritos
antes tienen otra función y no sustituyen los permisos del operador.

### 6.2. Configuración local

Si todavía no existe el archivo local, copiar el ejemplo:

```powershell
Copy-Item config/aws/dev.env.example config/aws/dev.env
```

Completarlo con este esquema; los marcadores entre `<...>` son valores a resolver:

```dotenv
AWS_PROFILE=<perfil>
AWS_REGION=us-east-1
STAGE=dev
BEDROCK_MODEL_ID=<id-regional-exacto-habilitado>
ALERT_EMAIL=<correo-de-alertas>
CUPO_DIARIO=5
MONTHLY_BUDGET_USD=10
BEDROCK_INPUT_PRICE_PER_MILLION=1
BEDROCK_OUTPUT_PRICE_PER_MILLION=5
```

Los precios 1 y 5 son los registrados para este despliegue, en USD por millón
de tokens; comprobar su vigencia antes de un nuevo despliegue. No son una
garantía de tarifa futura.

`aws-config.ps1` lee pares `CLAVE=VALOR`, omite líneas vacías y comentarios al
inicio de línea, y divide por el primer `=`. No es un intérprete de shell:
usar valores directos sin comillas ni comentarios al final. Valida región,
etapa, correo cuando se proporciona, cupo entre 1 y 100, presupuesto mínimo de
USD 1 y precios positivos. `dev.env` está ignorado por Git.

### 6.3. Comprobación previa

```powershell
.\scripts\aws-check.ps1 -Config config/aws/dev.env
sam validate --lint --region us-east-1
```

`aws-check.ps1` consulta STS y lista modelos de Anthropic en Bedrock. Su éxito
prueba acceso a esas consultas; no demuestra una invocación del modelo ni que
el ID seleccionado esté habilitado para generar.

El gate anterior, F6, registró 117 pruebas pytest y comprobaciones Ruff, mypy y
SAM build correctas. Si se cambia el código antes de desplegar, corresponde
volver a pasar las verificaciones del proyecto para ese nuevo estado.

### 6.4. Previsualización y despliegue

```powershell
.\scripts\deploy.ps1 -Config config/aws/dev.env -PreviewOnly
```

El script lee la configuración, resuelve el correo si hace falta, verifica AWS,
ejecuta `sam build --config-env dev` y crea un change set sin ejecutarlo usando
`--no-execute-changeset --no-confirm-changeset`. El preview utiliza AWS y puede
subir artefactos; no es una simulación exclusivamente local.

Para desplegar:

```powershell
.\scripts\deploy.ps1 -Config config/aws/dev.env
```

La configuración de `samconfig.toml` selecciona `brock-dev`,
`resolve_s3=true`, `confirm_changeset=true` y `CAPABILITY_IAM`. El script pasa
etapa, región, perfil, modelo, correo, cupo, presupuesto y precios, y fuerza
`CreateStackBudget=false`.

Añadir `CreateStackBudget=true` a `dev.env` no activa un presupuesto: el script
no lee esa variable y envía siempre `false`. Cualquier activación futura exige
un procedimiento de despliegue que pase ese parámetro explícitamente.

SAM empaqueta `backend/`, incluyendo API, generador, módulos compartidos y
prompts. El build del proyecto fue preparado para dependencias Linux/ARM64.
CloudFormation aplica el change set aceptado y expone los outputs.

### 6.5. Exportar la configuración del frontend

```powershell
.\scripts\export-frontend-config.ps1 -Config config/aws/dev.env
```

Lee los outputs de `brock-dev` y escribe `frontend/.env.local`:

```dotenv
VITE_API_URL=https://ypdvyu4ev7.execute-api.us-east-1.amazonaws.com/dev
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_Y24UyAiKr
VITE_COGNITO_CLIENT_ID=16ve22c8lo414dl4ktb80qe11h
```

El script comprueba que existan los cuatro outputs requeridos. Las variables
`VITE_*` se incorporan al build del navegador: contienen configuración pública.
Un cambio de valores requiere recompilar y publicar el frontend.

### 6.6. Compilar y publicar

Obtener el bucket desde el output `FrontendBucketName`. Desde `frontend/`:

```powershell
npm.cmd ci
npm.cmd run build
aws s3 sync dist/ s3://<FrontendBucketName> --delete --region us-east-1 --profile <perfil>
aws cloudfront create-invalidation --distribution-id EGDI9BGWT3SF4 --paths "/*" --profile <perfil>
```

`--delete` sincroniza eliminando objetos del bucket que no estén en `dist/`.
La invalidación solicita retirar los objetos cacheados; su aceptación no
significa que la propagación haya terminado. El despliegue SAM y esta publicación
son pasos independientes: `deploy.ps1` no compila ni sube el frontend.

## 7. Comprobaciones realizadas y cobertura pendiente

| Comprobación | Estado registrado | Qué acredita |
| --- | --- | --- |
| CloudFormation | `CREATE_COMPLETE` | Creación de recursos de la pila |
| Lambda API, generador y DynamoDB | Creados | Disponibilidad de infraestructura |
| API privada sin JWT | HTTP 401 | Rechazo de solicitudes anónimas |
| Cognito pool y cliente | Creados, SRP configurado | Infraestructura de identidad |
| Publicación S3/CloudFront | Realizada | Assets frontend publicados |
| HTML y manifest CloudFront | HTTP 200 | Acceso HTTP a los recursos comprobados |
| Modelo Bedrock | Haiku 4.5 activo, autorizado y configurado según el registro | Preparación para generación |
| Generación autenticada real | Pendiente | No hay evidencia del flujo completo en AWS |
| SNS | Suscripción pendiente | Falta confirmar recepción por correo |
| Presupuesto | Cuenta, USD 10, reutilizado | Sin segundo Budget creado por la pila |

### 7.1. Rutas privadas desplegadas

| Método | Ruta | Función prevista |
| --- | --- | --- |
| GET | `/perfil` | Perfil y cupo restante |
| PUT | `/perfil` | Actualización de perfil/preferencias |
| POST | `/planes` | Reserva, creación e invocación asíncrona; respuesta 202 |
| GET | `/planes` | Historial paginado |
| GET | `/planes/{planId}` | Consulta de estado y recuperación de vencidos |
| DELETE | `/planes/{planId}` | Eliminación conjunta del plan y lista |
| GET | `/planes/{planId}/lista` | Compras ordenadas por pasillo |
| PATCH | `/planes/{planId}/lista/items/{itemId}` | Marcado puntual |
| DELETE | `/cuenta` | Inicio de baja asíncrona |

Un 401 sin JWT no prueba la lógica de negocio de estas rutas ni la integración
API→generador→Bedrock→DynamoDB. Esas capacidades tienen pruebas locales y
requieren todavía validación autenticada en AWS.

### 7.2. Consultas para volver a comprobar el entorno

Desde la raíz, preparar variables de sesión:

```powershell
$settings = & .\scripts\aws-config.ps1 -Config config/aws/dev.env
$profile = $settings['AWS_PROFILE']
$region = $settings['AWS_REGION']
$stack = "brock-$($settings['STAGE'])"
```

Estado, parámetros, outputs y recursos:

```powershell
aws cloudformation describe-stacks --stack-name $stack --profile $profile --region $region
aws cloudformation list-stack-resources --stack-name $stack --profile $profile --region $region
```

Ejemplos de acceso sin autenticación y consulta del frontend:

```powershell
curl.exe -i https://ypdvyu4ev7.execute-api.us-east-1.amazonaws.com/dev/perfil
curl.exe -i https://d1z78xb68rmhq3.cloudfront.net/
curl.exe -i https://d1z78xb68rmhq3.cloudfront.net/manifest.webmanifest
```

Configuración de funciones y alarmas:

```powershell
aws lambda get-function-configuration --function-name brock-api-dev --profile $profile --region $region
aws lambda get-function-configuration --function-name brock-generador-dev --profile $profile --region $region
aws lambda get-function-event-invoke-config --function-name brock-generador-dev --profile $profile --region $region
aws cloudwatch describe-alarms --alarm-name-prefix brock-dev- --profile $profile --region $region
```

Obtener el tópico desde los outputs y revisar la suscripción:

```powershell
$topicArn = aws cloudformation describe-stacks --stack-name $stack --profile $profile --region $region --query "Stacks[0].Outputs[?OutputKey=='AlertTopicArn'].OutputValue" --output text
aws sns list-subscriptions-by-topic --topic-arn $topicArn --profile $profile --region $region
```

`PendingConfirmation` requiere aceptar el enlace del correo SNS. Después debe
comprobarse nuevamente el estado y la recepción efectiva de una notificación.
El repositorio no contiene un registro de esa confirmación.

## 8. Costos y límites

Precios de referencia configurados para el cálculo de Bedrock:

- Entrada: **USD 1 por millón de tokens**.
- Salida: **USD 5 por millón de tokens**.

Fórmula del componente estimado por tokens:

```text
costo_USD = (tokens_entrada × 1 + tokens_salida × 5) / 1 000 000
```

Ejemplo ilustrativo: 2000 tokens de entrada y 4000 de salida equivalen a
`0.002 + 0.020 = USD 0.022`. No es una medición real de F7. Un reintento por
salida inválida también puede consumir tokens y generar costo.

El backend persiste modelo, versión de prompt, tokens y latencia, y emite
métricas EMF de generación y costo estimado. La factura efectiva depende del
modelo, región y modalidad y es la referencia final. El cálculo anterior no
incluye Lambda, API Gateway, DynamoDB/PITR, S3, CloudFront, logs ni otros servicios.

El cupo diario limita planes por usuario y el throttling limita peticiones a
la API según su configuración. Ninguno equivale a un límite monetario de la
cuenta. No se documenta un costo total real de esta fase porque no hay una
medición de facturación adjunta al registro.

## 9. Diagnóstico operativo

| Síntoma | Revisión recomendada |
| --- | --- |
| `aws` o `sam` no reconocido | PATH de la sesión y herramientas de `.venv-tools` |
| STS falla | Perfil, vigencia de credenciales y cuenta seleccionada |
| Consulta Bedrock falla | Región, permisos del perfil y acceso al servicio |
| Modelo lista pero la generación falla | ID exacto, habilitación, tipo de modelo, permisos y logs del generador |
| Error de precios antes del deploy | Ambos precios positivos en el archivo local |
| No se obtiene correo de Budget | `ALERT_EMAIL` o nombre/notificación/suscriptores del presupuesto existente |
| Pila falla o queda en rollback | Eventos CloudFormation antes de repetir el despliegue |
| API devuelve 401 con sesión | Caducidad, issuer, audience/client ID y envío de `Authorization` |
| Navegador bloquea por CORS | Origen real frente al origen CloudFront permitido |
| Frontend conserva versión previa | Build publicado, invalidación y estado de actualización del service worker |
| Asset devuelve HTML en lugar de JS/manifest | Ruta del objeto y fallback SPA 403/404 |
| Plan no sale de `GENERANDO` | Logs API/generador, invocación asíncrona, destino de fallo y recuperación de vencidos |
| Alarmas sin correo | Estado SNS y confirmación del suscriptor |
| Borrado de pila falla por S3 | Contenido restante en el bucket frontend |

Para revisar un fallo de despliegue:

```powershell
aws cloudformation describe-stack-events --stack-name $stack --profile $profile --region $region
```

Los grupos de logs a consultar son `/aws/lambda/brock-api-dev` y
`/aws/lambda/brock-generador-dev`. Los eventos y logs permiten diagnosticar un
fallo concreto; el historial de F7 no conserva una bitácora exhaustiva de errores.

## 10. Eliminación y recursos externos

El procedimiento implementado es:

```powershell
.\scripts\delete.ps1 -Config config/aws/dev.env
```

El script solicita escribir `DELETE`, obtiene el bucket desde los outputs,
lo vacía y ejecuta `sam delete --no-prompts`. La opción `-Force` omite la
confirmación inicial del script.

La plantilla no define políticas de retención de datos: eliminar la pila
elimina sus recursos, incluidos usuarios, tabla y grupos de logs. El script
necesita que la configuración local siga siendo válida, incluidos los precios,
porque comparte el lector `aws-config.ps1`.

Recursos que requieren revisión por separado:

- Bucket administrado por SAM y artefactos compartidos, fuera de `brock-dev`.
- Presupuesto de cuenta reutilizado, que no pertenece a esta pila.
- Credenciales/perfiles locales, ajenos al ciclo de vida de CloudFormation.

No hay registro de una eliminación real del entorno F7; la pila consta como
creada en la última evidencia versionada.

## 11. Pendientes y entrega a F8

| Pendiente | Criterio de comprobación |
| --- | --- |
| Confirmar SNS | Suscripción confirmada y recepción de notificación verificada |
| Registro Cognito | Usuario creado, código recibido y correo confirmado |
| Inicio/cierre de sesión | SRP funcional y manejo de sesión en frontend |
| Recuperación y renovación | Correos y renovación de tokens probados |
| Perfil autenticado | Lectura/actualización real usando el `sub` del JWT |
| Primera generación Bedrock | POST 202, evolución a `LISTO`, menú/lista válidos y metadatos reales |
| Historial y lista | Lectura, paginación, marcado y eliminación autenticados |
| Aislamiento real | Un segundo usuario no accede ni modifica datos del primero |
| Fallos y cupo | Compensación e idempotencia observadas en el entorno real |
| Baja de cuenta | Bloqueo, baja Cognito y eliminación DynamoDB comprobados |
| Throttling | Comportamiento real de API Gateway observado |
| PWA completa | Pantallas, iconos e instalación/actualización en dispositivos |

**Conclusión de F7:** el entorno de desarrollo quedó desplegado y accesible con
protección JWT, y el frontend inicial quedó publicado. La entrega a F8 incluye
las URLs e identificadores necesarios para integrar la aplicación. El cierre
funcional de extremo a extremo requiere completar las comprobaciones pendientes
anteriores y registrar sus resultados.
