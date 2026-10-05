# Brock local con Docker

Este entorno ejecuta la Lambda API mediante un adaptador HTTP y DynamoDB Local.
No crea recursos AWS, no valida Cognito y no llama Bedrock. El header
`X-Local-User-Sub` sustituye únicamente al JWT para pruebas locales.

## Requisitos

- Docker Desktop iniciado.
- Docker Compose incluido en Docker Desktop.

## Arrancar

Desde la raíz del repositorio:

```powershell
docker compose -f docker/docker-compose.yml up --build
```

La API queda en `http://localhost:3000`. La tabla se crea automáticamente en
DynamoDB Local. `LOCAL_RESET_TABLE=true` borra y recrea la tabla al arrancar.
Usa `false` para conservar datos mientras reinicias el servicio.

## Probar endpoints

Perfil:

```powershell
curl.exe -i http://localhost:3000/perfil
curl.exe -i -X PUT http://localhost:3000/perfil `
  -H "Content-Type: application/json" `
  -d '{"personas_defecto":2,"evitar":["ajo"]}'
```

Crear un plan. En local la invocación del generador se acepta, pero no se llama
Bedrock; el plan queda `GENERANDO` hasta que F5 incorpore un generador simulado
o una herramienta de completar fixtures:

```powershell
curl.exe -i -X POST http://localhost:3000/planes `
  -H "Content-Type: application/json" `
  -d '{"personas":2,"dias":1,"comidas":["ALMUERZO"]}'
```

Usar otro usuario para comprobar aislamiento:

```powershell
curl.exe -i -H "X-Local-User-Sub: usuario-b" http://localhost:3000/perfil
```

Ver logs y detener:

```powershell
docker compose -f docker/docker-compose.yml logs -f api
docker compose -f docker/docker-compose.yml down
```

## Limitaciones intencionales

- No se simula la firma ni expiración de JWT; la autenticación real se prueba
  con Cognito después de F7.
- No se simula Cognito Admin API ni la baja real de cuentas.
- No se simula la respuesta de Bedrock ni se marca automáticamente un plan como
  `LISTO`. La API sí prueba reserva, cupo, estados e aislamiento.
- El modo local acepta la invocación del generador con `BROCK_LOCAL_MODE=true`.
  Esa variable nunca debe configurarse en `dev` o `prod`.
- No ejecutar este compose con credenciales AWS reales.

Para probar el empaquetado SAM de Lambda con Docker, usar además:

```powershell
.\.venv-tools\Scripts\sam.exe local start-api --template .aws-sam/build/template.yaml
```

Ese comando es una alternativa a este adaptador y requiere configurar el
endpoint local de DynamoDB para la Lambda. El compose anterior es el camino
recomendado para las pruebas HTTP rápidas y aisladas.
