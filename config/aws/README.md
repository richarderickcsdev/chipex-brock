# Conexión con AWS

Esta carpeta contiene parámetros de conexión, no credenciales. Los archivos
`dev.env` y `prod.env` son locales y están ignorados por Git. Solo se versionan
los ejemplos.

## Preparar un perfil AWS

Instala AWS CLI y configura un perfil nombrado. No escribas claves en este
repositorio:

```powershell
aws configure --profile brock-dev
aws sts get-caller-identity --profile brock-dev
```

También se admiten perfiles SSO:

```powershell
aws configure sso --profile brock-dev
aws sso login --profile brock-dev
```

## Preparar la configuración

```powershell
Copy-Item config/aws/dev.env.example config/aws/dev.env
```

Completa al menos `AWS_PROFILE`, `AWS_REGION`, `BEDROCK_MODEL_ID` y `ALERT_EMAIL`.
El modelo debe estar disponible y habilitado en la región elegida.

## Comandos

Desde la raíz:

```powershell
.\scripts\aws-check.ps1 -Config config/aws/dev.env
.\scripts\deploy.ps1 -Config config/aws/dev.env
.\scripts\export-frontend-config.ps1 -Config config/aws/dev.env
.\scripts\delete.ps1 -Config config/aws/dev.env
```

El despliegue pide confirmación a SAM y crea la pila, Cognito, API Gateway,
Lambdas, DynamoDB, S3, CloudFront, alarmas, SNS y Budget definidos en
`template.yaml`. La confirmación de la suscripción SNS llega al correo indicado.

## Valores disponibles

| Variable | Uso |
| --- | --- |
| `AWS_PROFILE` | Perfil local de AWS CLI; nunca una clave |
| `AWS_REGION` | Región del despliegue |
| `STAGE` | `dev` o `prod` |
| `BEDROCK_MODEL_ID` | Foundation model compatible con Converse |
| `ALERT_EMAIL` | SNS y AWS Budgets |
| `CUPO_DIARIO` | Planes máximos por usuario/día |
| `MONTHLY_BUDGET_USD` | Límite mensual del Budget |

Los scripts exportan los outputs de CloudFormation a `frontend/.env.local`.
Ese archivo está ignorado y solo contiene IDs/URLs públicas de configuración,
no secretos. Las credenciales las resuelve la cadena estándar de AWS mediante
`AWS_PROFILE`.

No ejecutes `deploy.ps1` hasta haber completado F0: créditos, cuotas y precios
de Bedrock, región, modelo y condiciones de Cognito.
