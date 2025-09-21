INFRAESTRUCTURA, CI/CD Y BACKUPS – Versión Corregida

Este documento actualiza la guía de infraestructura, despliegues,
integración continua (CI/CD) y políticas de backup de ofitec.ai,
alineándola con las leyes oficiales y las conclusiones del diagnóstico.

🚢 Cumplimiento de Ley de Puertos

La infraestructura debe garantizar que sólo existen dos puertos de
exposición en el sistema principal:

Puerto 3001: Frontend Next.js. Todas las páginas y el portal
cliente deben servirse desde aquí【8†L43-L50】. Durante la
construcción/ejecución, se debe configurar el servidor de
desarrollo (npm run dev) para que corra en 3001 tanto en
desarrollo como en producción.

Puerto 5555: Backend Flask. Todas las APIs REST, incluyendo
QHSE, Finanzas, SII, Analítica y Portal, deben exponerse en este
puerto【8†L43-L50】. Se prohíben servidores paralelos (3000, 3002
o 8000).

En la pipeline de despliegue, agregar un paso de verificación
automática que ejecute:

netstat -an | grep ':3001' || exit 1
netstat -an | grep ':5555' || exit 1


Si se detecta un puerto no autorizado, se aborta el despliegue.

🛠️ CI/CD

El pipeline de integración y entrega continua (CI/CD) debe incluir:

Pruebas unitarias y de integración: ejecutar pytest para el
backend (Flask) y tests con Vitest/Jest para el frontend. Generar
reportes de cobertura. Cualquier falla detiene la pipeline.

Linting y Format: aplicar ruff/black en Python y ESLint +
Prettier en JavaScript/TypeScript antes de build.

Build Docker: construir las imágenes del backend y frontend.
Asegurar que la base de datos de producción se conecta a la
instancia PostgreSQL (no SQLite). Usar multi‑stage builds para
reducir el tamaño.

Deploy Blue/Green: implementar despliegue de dos entornos
(blue/green) con un balanceador. Cambiar el alias DNS una vez
que el nuevo entorno pase todas las pruebas de salud. Basarse en
las entregas de autoscaling y blue/green (entrega 9)【395†source】.

Rotación de Secretos y Variables: integrar la pipeline con
Vault para obtener variables sensibles (contraseñas DB,
credenciales SSO, llaves JWT). Nunca se guardan secretos en
repositorios.

Ejecución de Scripts de BD: antes del deploy, correr los
scripts de verificación de integridad (verificar_estado_db.py) y
recreación de vistas canónicas (create_finance_views.py)
en el entorno temporal. Abortarla si falla alguna verificación.

Backup Pre‑Deploy: antes de migrar la base de datos, hacer un
backup transaccional (por ejemplo, pg_dump --format=custom). En
caso de fallar, se restaura inmediatamente el backup y se
cancela el despliegue.

La definición del workflow de GitHub Actions (o la herramienta
equivalente) debe incluir estos pasos. Utilice jobs secuenciados
con needs: para asegurar el orden correcto.

🔄 Backup y Recuperación (3‑2‑1)

Para cumplir el Artículo VII de la Ley de Base de Datos【19†L233-L241】,
se implementa la estrategia 3‑2‑1:

3 Copias: mantener tres copias de cada backup:

Original (Base de Datos en Prod) – replicada en modo WAL.

Backup Primario Local – guardado en un volumen dedicado.

Backup Secundario Remoto – almacenado cifrado en un bucket
(S3, GCS u OSS) en otra región.

2 Medios Diferentes: una copia en disco local y otra en
servicio cloud. La copia local se usa para restauraciones rápidas.

1 Offsite: la copia remota (offsite) se mantiene en una región
distinta para recuperación ante desastres (DR).

Frecuencia de Backups

Transaccional: antes de cada importación masiva (Chipax
Migration, ETL) o actualización de modelo.

Horario: backups incrementales cada hora durante el horario
laboral. Se pueden aprovechar los WAL archives y pgBackRest.

Diario: backup completo a las 02:00 AM (cron job)【19†L233-L241】.

Semanal: backup completo comprimido y verificado; se mantiene
durante 4 semanas.

Mensual: backup histórico comprimido; retención de 12 meses.

Todos los backups deben pasar por un proceso de verificación de
integridad (pg_restore --list y pruebas de checksum). Se debe
probar periódicamente la restauración en un entorno de staging.

Procedimiento de Recuperación

Si se detecta corrupción de datos o se necesita volver a un estado
previo:

STOP inmediato: detener todas las operaciones del backend y
deshabilitar escritura en la BD【19†L258-L266】.

Identificar punto de restauración: seleccionar el backup más
reciente válido y los WAL necesarios.

Restaurar: usar pg_restore para la copia completa y aplicar
los WAL para alcanzar el punto deseado.

Verificar: correr los scripts de integridad y un subset de
pruebas de negocio (carga de dashboards, creación de notas de
venta, etc.).

Reapertura: una vez verificada la base, reactivar el servicio
y notificar a los usuarios.

Reporte: documentar la causa, la duración de la interrupción y
las acciones correctivas.

📈 Monitorización y Observabilidad

Se despliega un stack de observabilidad (Prometheus, Grafana y Loki)
con las siguientes características:

Exporters: se exponen métricas del backend (latencias,
errores), del frontend (tiempo de renderizado) y de la base de
datos (con postgres_exporter). Para Odoo (si se mantiene alguna
pieza), se usa odoo_exporter【11†L251-L260】.

Paneles Prediseñados: se incluyen dashboards para monitorizar:

KPIs de sistemas (CPU, memoria, disco, latencia HTTP).

Estado de jobs de ETL y backups.

Salud de microservicios (QHSE, Analítica, etc.).

Métricas de negocio (órdenes procesadas, notas de venta emitidas).

Alertas: configurar alertas en Prometheus para:

Pérdida de conexión a BD (Alerta crítica)【19†L233-L241】.

Fallos en backups automáticos.

Incremento en duplicados detectados por la capa de validación【17†L154-L163】.

Saturación del puerto 3001 o 5555.

Se recomienda enviar alertas a Slack y correo electrónico, utilizando
las integraciones ya definidas en las entregas de autoscaling y
monitorización【389†source】.

✅ Resumen de Cumplimiento

Unificación de Puertos: se aseguran las reglas 1–3 de la
Ley de Puertos【8†L43-L50】.

Integridad y Backups: se implementa la estrategia 3‑2‑1, los
backups transaccionales y procedimientos de recuperación conforme
a la Ley de Base de Datos【19†L233-L241】.

CI/CD Rigurosa: el pipeline ejecuta pruebas, verifica
integridad de BD y evita que se desplieguen builds con
configuraciones incorrectas. Se incorporan scripts de
verificación de vistas y bases de datos canónicas.

Monitorización y Alertas: se instrumentan los servicios y se
configuran alertas para incidentes críticos y degradaciones.

Con estas directrices, la infraestructura y el ciclo de vida de
despliegue de ofitec.ai se fortalecen, eliminando riesgos de puertos
erróneos, pérdida de datos y fallos silenciosos, y cumpliendo las
normas oficiales.