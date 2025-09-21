Services directory
==================

Conciliación Bancaria se gestiona como servicio independiente por lineamientos de docs_oficiales (Ley de BD / Art. X):

- No se versiona el código del servicio dentro del repo del Portal.
- Agregarlo como submódulo Git cuando exista su repositorio remoto:

  git submodule add <REMOTE_URL> services/conciliacion_bancaria

- Variables de entorno en el Portal para consumir el servicio:
  - CONCILIACION_API_URL (p.ej. http://localhost:5600)

Docker Compose del Portal no levanta el servicio; se despliega por separado.

