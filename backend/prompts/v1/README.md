# Prompt v1

`system.txt` es fijo y versionado. `user_template.txt` se rellena con JSON
serializado por código; los valores no se interpolan como instrucciones libres.
La salida se valida siempre con Pydantic y con las reglas de coherencia de F3.
