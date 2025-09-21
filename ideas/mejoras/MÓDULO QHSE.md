MÓDULO QHSE – Seguridad, Salud y Medio Ambiente

Este documento describe la versión corregida del módulo QHSE (Quality,
Health, Safety & Environment) conforme a los lineamientos oficiales de
Ofitec.ai. Incorpora las conclusiones del diagnóstico: integrar IA
para detección de EPP, analítica de incidentes, conexión con la matriz
de riesgos y cumplimiento de las leyes de puertos y de base de datos.

🎯 Objetivo

Brindar una gestión integral de incidentes y seguridad en obra que
permita registrar eventos en tiempo real, detectar incumplimientos de
equipos de protección personal (EPP) mediante visión artificial,
generar análisis de tendencias y alimentar automáticamente la matriz
corporativa de riesgos. El módulo opera sobre el backend Flask
3001/5555 siguiendo la Ley de Puertos【8†L43-L50】 y guarda datos en
tablas normalizadas conforme a la Ley de Base de Datos【17†L154-L163】.

🗄️ Modelo de Datos

Todas las tablas nuevas se crean en la base de datos PostgreSQL. Se
validan RUTs cuando corresponda (p.ej., supervisor) y se aplican
constraints de integridad referencial. Se sugieren los siguientes
modelos:

incidentes_hse
Campo	Tipo	Obligatorio	Descripción
id	SERIAL PK	Sí	Identificador único
project_id	INTEGER FK	Sí	Proyecto asociado
tipo	TEXT	Sí	Tipo de incidente (lesión, casi-accidente…)
severidad	TEXT	Sí	Nivel (Menor, Mayor, Crítico)
descripcion	TEXT	Sí	Relato del incidente
responsable_id	INTEGER FK	No	Usuario responsable / testigo
fecha	TIMESTAMP	Sí	Fecha y hora del incidente
ubicacion_gps	POINT	No	Coordenadas GPS (lat, lon)
adjuntos_url	TEXT[]	No	URLs de fotos o documentos
estado	TEXT	Sí	{abierto, investigación, cerrado}
created_at	TIMESTAMP	Sí	Fecha creación (DEFAULT NOW())
inspecciones_seguridad
Campo	Tipo	Obligatorio	Descripción
id	SERIAL PK	Sí	Identificador único
inspector_id	INTEGER FK	Sí	Usuario que realiza la inspección
project_id	INTEGER FK	Sí	Proyecto asociado
fecha	TIMESTAMP	Sí	Fecha de inspección
checklist	JSONB	Sí	Resultados de checklist (OK/No OK/No Aplica)
observaciones	TEXT	No	Observaciones adicionales
adjuntos_url	TEXT[]	No	Evidencias visuales
cumplimiento	REAL	Sí	Porcentaje de cumplimiento calculado automáticamente
created_at	TIMESTAMP	Sí	Fecha de creación
epp_detecciones

Tabla para almacenar resultados de detección automática de EPP mediante
visión artificial.

Campo	Tipo	Obligatorio	Descripción
id	SERIAL PK	Sí	Identificador único
inspection_id	INTEGER FK	Sí	Inspección asociada (opcional si se genera ad hoc)
project_id	INTEGER FK	Sí	Proyecto asociado
fecha	TIMESTAMP	Sí	Fecha/hora de la imagen
imagen_url	TEXT	Sí	URL de la imagen procesada
elementos_detect	JSONB	Sí	Detalle de detecciones (casco=true, chaleco=false, ...)
score	REAL	Sí	Confianza promedio de detección (0–1)
cumple_epp	BOOLEAN	Sí	true si todos los EPP obligatorios están presentes
created_at	TIMESTAMP	Sí	Fecha creación
Integración con Riesgos

Al cerrarse un incidente de severidad Mayor o Crítico, se debe
crear o actualizar un registro en project_risk con categoría
“Seguridad” y las probabilidades/impactos calculados por IA. Se
propone un trigger que inserte en project_risk y un campo
hse_incident_id para relacionar el riesgo con el incidente.

🧠 IA y Automatización
Detección de EPP

Ingesta de imágenes: las inspecciones y los reportes diarios
podrán adjuntar fotografías. Se usan presigned URLs de S3/MinIO.

Servicio de visión artificial: se utiliza un microservicio
(p.ej., FastAPI) que emplea modelos de detección de objetos
preentrenados para identificar cascos, chalecos reflectantes,
botas de seguridad, guantes y arnés. Retorna un JSON con las
etiquetas y la confianza.

Evaluación de cumplimiento: se define, por proyecto o por
actividad, qué EPP son obligatorios. El backend compara los
elementos detectados con esta lista. Si falta alguno, la
detección se marca como cumple_epp=false y se dispara una
notificación (correo/app o alerta en dashboard).

Almacenamiento: los resultados se almacenan en
epp_detecciones con la relación a la inspección o incidente
correspondiente.

Analítica de Incidentes y Tendencias

El módulo incluye un servicio de analítica que extrae patrones de los
incidentes registrados:

Tendencias temporales: número de incidentes por mes, por tipo
y proyecto; gráfico de heatmap para identificar períodos con mayor
siniestralidad.

Causas raíz: análisis de co-ocurrencia entre descripciones y
checklist; uso de modelos de clustering para agrupar causas
comunes (e.g., falta de capacitación, mala señalización).

Predicción de Accidentes: entrenamiento de un modelo de
clasificación que estime la probabilidad de que un proyecto registre
un incidente en el próximo periodo, utilizando variables como
cumplimiento de EPP, historial de incidentes, horas hombre, etc.
Los resultados se guardan en la tabla predicciones_hse con
campos project_id, probabilidad_incidente,
intervalo_confianza y created_at.

Los reportes de analítica deben exponerse como parte de la sección
HSE Analytics descrita en la Estrategia de Páginas【27†L302-L307】.

🔗 Endpoints API

Todos los endpoints deben seguir el prefijo /api/v1/qhse y devolver
JSON. Se requiere autenticación y autorización basada en roles.

GET /incidents → Listar incidentes con filtros por proyecto,
fecha, severidad y estado.

POST /incidents → Crear un nuevo incidente (borrador). Valida
datos e inicia flujo de gestión.

PATCH /incidents/{id} → Actualizar estado o detalles de un
incidente.

GET /inspections → Listar inspecciones y su porcentaje de
cumplimiento.

POST /inspections → Crear nueva inspección con checklist.

GET /epp-detections → Consultar detecciones de EPP (usar
filtros por proyecto y cumplimiento).

POST /epp-detections → Registrar resultado de una detección
automática de EPP (consumido por el microservicio de IA).

GET /analytics/incidents → Resumen de tendencias, causas raíz
y estadísticas de incidentes.

GET /analytics/prediction/{project_id} → Probabilidad de
incidente futuro para un proyecto.

🖥️ Frontend y UX

El módulo QHSE se integra dentro del frontend Next.js en la sección
Operaciones de Obra【27†L242-L248】. Se deben utilizar los
componentes de la estrategia visual para garantizar coherencia:

Tablas y KPICards: para incidentes abiertos/cerrados, tasa de
cumplimiento de inspecciones y predicción de accidentes. Usar
cabeceras grises y bordes de 1px【24†L83-L91】.

Badges: mostrar el estado del incidente (Abierto, Investigación,
Cerrado) con los colores verde, ámbar y rojo definidos【24†L94-L102】.

Cards: agrupar estadísticas (incidentes por severidad, número
de inspecciones completadas) con radius 12 px y sin sombras【24†L45-L54】.

Visualización IA: en la página de inspecciones se pueden
mostrar miniaturas con overlay de detección (colores o bounding
boxes) para ilustrar los EPP detectados. Usar un modal para ver
la imagen completa con la detección.

Filtros y Búsqueda: proporcionar filtros por periodo, tipo de
incidente, severidad y proyecto. Mantener consistencia con
formularios (inputs sin sombras, botones con variantes primarias,
etc.)【24†L89-L97】.

🔒 Permisos y Seguridad

Basado en la matriz de roles oficial, se definen los siguientes
permisos:

Administrador: puede ver y administrar todos los incidentes,
inspecciones y configuraciones. Acceso a analíticas y predicciones.

HSE Manager: puede registrar, editar y cerrar incidentes e
inspecciones de su área. Accede a analíticas de sus proyectos.

Supervisor de Obra: registra incidentes e inspecciones para
proyectos asignados. Visualiza predicción de accidentes.

Cliente: sólo puede ver reportes agregados de incidentes
cerrados relacionados a su proyecto, sin detalles sensibles.

El control de acceso se implementará mediante el módulo de seguridad
central (ofitec_security), utilizando JWT y roles por proyecto. Se
incorporará la lista allowed_project_ids en la sesión del usuario,
siguiendo el concepto de allowed_partner_ids adaptado a una base
propia【28†L31-L38】.

✅ Cumplimiento de Normas

Ley de Puertos: todas las páginas QHSE se alojan en el
frontend principal (3001) y consumen APIs desde 5555; no se
generan microfrontends ni servidores adicionales【8†L43-L50】.

Ley de Base de Datos: las tablas propuestas cumplen con
integridad referencial y se integran con las vistas financieras y
de proyectos cuando corresponde【17†L154-L163】. Se respeta la
prevención de duplicados en incidentes e inspecciones mediante
índices únicos (p.ej., combinación project_id + fecha).

Estrategia Visual: la UI utiliza los tokens y componentes
definidos (cards, badges, colores, tipografía)【24†L45-L54】.

Estrategia de Páginas: este módulo forma parte de las
páginas de Operaciones de Obra (HSE Inteligente) y genera
analíticas en la sección correspondiente【27†L242-L248】.

Con esta versión, el módulo QHSE se alinea con los documentos
oficiales y las conclusiones del estudio, integrando IA para
seguridad, alimentando la matriz de riesgos y respetando las
normativas internas en datos, puertos y diseño.