# Backend compartido — F3

## Contratos

`EntradaPlan` acepta ingredientes vacíos o hasta 1.000 caracteres, 1–10
personas, 1–7 días y 1–3 comidas sin repetir. Predeterminados: siete días,
almuerzo y cena. El texto se limpia antes de usarlo, pero la longitud máxima
se aplica también a la entrada original para evitar eludir el límite con espacios.

`Perfil` valida 1–10 personas y hasta 20 preferencias de 40 caracteres,
sin nombres vacíos o duplicados normalizados. `MarcaCompra` exige un booleano
real. Todos los modelos rechazan campos adicionales y conversiones de cadenas,
booleanos y números a tipos distintos.

`ESQUEMA_PLAN` es el JSON Schema generado por Pydantic. Completa los objetos
anidados del esquema ilustrativo de arquitectura: cantidades positivas finitas,
unidades y pasillos permitidos, nombres e identificadores acotados y listas con
límites. Cada paso tiene hasta 500 caracteres. `tiempo_min` sigue siendo opcional
en el contrato; cuando existe, debe estar entre 1 y 480 minutos.

`validar_entrada(Modelo, datos)` devuelve un modelo o un `ErrorBrock` con 400.
`validar_plan(json_o_dict, entrada, evitar)` acepta JSON puro y devuelve
`PlanGenerado` solo después de validar estructura y coherencia.

## Coherencia del menú y compras

- Días exactamente 1..N, en orden y sin repeticiones.
- Cada día contiene exactamente las comidas solicitadas.
- IDs de compra únicos; cantidades positivas y finitas desde el esquema.
- Las preferencias se buscan por palabras completas, sin distinguir acentos
  ni mayúsculas; se admiten plurales simples. Se revisan nombres y pasos.
- Los ingredientes marcados `en_casa: false` se suman por nombre normalizado y
  familia de unidades. Se convierten kg a g y l a ml con aritmética Decimal.
- La lista debe coincidir con esos totales y no duplicar nombres/unidades.
  Un producto que aparece tanto disponible como faltante se compra únicamente
  por la suma faltante, no por la parte disponible.

No se infieren sinónimos ni se convierte `paquete` a gramos sin conocer su
tamaño. La preferencia es un filtro léxico, no una garantía de alergias ni una
validación nutricional. Los nombres/flags propuestos por la IA deben mantener
coherencia; cuantificar el stock real a partir del texto libre sigue siendo parte
de la generación, no una prueba determinista de inventario.

## Repositorio

`Repositorio.desde_entorno(sub)` usa `TABLE_NAME`. El `sub` debe provenir de
las claims autenticadas por API Gateway en F4. Ningún método recibe otra PK.

- `perfil()` / `guardar_perfil(Perfil)`: el perfil inexistente usa una persona
  por defecto; la fecha de creación se conserva al actualizar.
- `plan(plan_id)` / `lista(plan_id)`: lecturas consistentes; 404 uniforme.
- `historial(limite=20, cursor=None)`: Query descendente sobre `PLAN#`, cursor
  opaco Base64 validado contra el usuario y tipo de clave. No permite lecturas
  de otra partición ni filtrado de datos ajenos.
- `marcar_item(...)`: actualización puntual del mapa; no crea ítems inexistentes.
- `finalizar(plan_id, PlanGenerado, MetadatosGeneracion)`: revalida la respuesta,
  exige `GENERANDO` y guarda menú + lista en una transacción. Guarda versión,
  modelo, tokens y latencia como atributos del plan. La lista inicia sin marcas.
- `eliminar_plan(plan_id)`: borra plan y lista juntos; 409 si sigue generando.
- `eliminar_datos_usuario()`: Query paginado y BatchWrite con reintentos de
  ítems no procesados gestionados por boto3. Rechaza planes activos y se puede
  repetir. Solo elimina DynamoDB: la baja Cognito y el bloqueo de nuevas
  escrituras deben orquestarse al implementar la eliminación de cuenta.

Se conservan los tipos `Decimal` de DynamoDB dentro del repositorio;
`json_publico` convierte números para las respuestas HTTP. F4 debe construir
respuestas públicas y no exponer automáticamente los registros internos PK/SK.

## Cupo y estados

`Cupo` obtiene `CUPO_DIARIO` (5 por defecto) y `QUOTA_TIMEZONE` (`America/Lima`).
Permite inyectar un reloj con zona horaria para pruebas.

1. `estado()`: límite, usados, restantes y próxima medianoche en UTC.
2. `reservar(plan_id, EntradaPlan, evitar)`: transacción de contador condicional
   y creación del plan. Guarda `quota_fecha`, `cupo_devuelto: false` y snapshot
   de preferencias. Un ID repetido da 409; superar el cupo da 429 con `reinicia`.
3. `devolver(plan_id, mensaje)`: exige `GENERANDO`, decrementa el contador
   original y marca `ERROR` / `cupo_devuelto: true` atómicamente. Devuelve `True`
   la primera vez y `False` en reintentos. Nunca devuelve cupo de un plan listo.

Los contadores llevan TTL de hasta tres días desde el inicio del día local.
El reinicio depende de la fecha de la clave, no de cuándo DynamoDB borra el TTL.
Las transacciones impiden contadores negativos, planes huérfanos al reservar y
publicación de resultados después de una devolución. Si falta el contador,
la devolución falla sin modificar a medias el estado del plan.

## Integración siguiente

F4 debe generar el ULID, obtener el perfil, reservar antes de invocar Lambda y
compensar un fallo confirmado de invocación. F4/F5 también deben gestionar
timeouts, eventos expirados y posibles entregas duplicadas. La devolución
idempotente está disponible, pero F3 no incluye un temporizador ni un worker
que detecte automáticamente una generación vencida.
