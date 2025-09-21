MÓDULO ANALÍTICA AVANZADA – Predicciones y IA en ofitec.ai

Esta versión actualizada del módulo Analítica Avanzada incorpora las
conclusiones del estudio: se centra en predicción de costos y plazos,
copilots conversacionales, simulaciones y dashboards analíticos, todo
respetando la Ley de Base de Datos (uso de vistas canónicas y
evitar duplicados)【17†L154-L163】 y la Ley de Puertos (único
frontend y backend)【8†L43-L50】.

🎯 Objetivo

Ofrecer una capa de inteligencia sobre los datos financieros y de
operaciones para generar pronósticos, escenarios, recomendaciones y
copilots que asistan a usuarios de negocio (CEO, CFO, PM, HSE
Manager, Cliente). La analítica avanzada debe explotar los más de
34 k registros integrados【22†L37-L45】 mediante algoritmos de
Machine Learning y modelos estadísticos, pero siempre a partir de
datos consolidados y validados.

🗄️ Datos de Entrada

Se utilizan exclusivamente las vistas canónicas y tablas
normalizadas definidas en la Ley de Base de Datos para extraer
información confiable. Las principales fuentes son:

vista_proyectos_resumen – para métricas de proyectos (nº órdenes,
valor total, proveedores únicos).

vista_ordenes_completas – para detalles de órdenes (fecha,
monto, proveedor)【16†L204-L212】.

zoho_proyectos – para presupuesto y costo de cada proyecto.

purchase_orders_unified, vendors_unified – base de órdenes y
proveedores consolidada【17†L154-L163】.

Datos de riesgos (project_risk) y de HSE (incidentes_hse) –
alimentan modelos de probabilidad de incidentes y desviaciones.

Se prohíbe utilizar tablas temporales o consultas directas a fuentes
no normalizadas (Art. V.2【19†L299-L308】).

🧠 Motor de Predicciones

El módulo incorpora un servicio de Machine Learning que genera
predicciones y simulaciones en distintos dominios:

1. Pronóstico de Costos

Entrenamiento: utiliza la serie de órdenes por proyecto
(fecha, monto, categoría) y el presupuesto planificado. Se aplican
técnicas de regresión temporal (ARIMA, Prophet) y modelos de
árboles (Random Forest, Gradient Boosting) para capturar estacionalidad.

Predicción: para cada proyecto, genera costo_predicho y
intervalo_confianza para los próximos 3, 6 y 12 meses. Calcula
también el desvío estimado respecto al presupuesto (delta = predicho - presupuesto).

Almacenamiento: los resultados se guardan en la tabla
predicciones_ml con campos:

id	project_id	tipo	valor_predicho	intervalo_confianza	score	modelo_version	created_at
PK	FK	'costo'	NUMERIC	NUMERIC[]	REAL	TEXT	TIMESTAMP
2. Pronóstico de Plazos

Entrenamiento: se basa en los reportes diarios (avance físico
acumulado), hitos planificados y órdenes de cambio. Se entrenan
modelos de regresión y survival analysis para estimar el tiempo
restante y la fecha final real.

Predicción: para cada proyecto, genera fecha_fin_predicha y
probabilidad_atraso. Se actualiza al recibir nuevos reportes de
avance.

Almacenamiento: se registra en predicciones_ml con tipo
plazo.

3. Predicción de Riesgos y Seguridad

Entrenamiento: usa datos de la matriz de riesgos,
incidentes HSE y cumplimiento de EPP. Se entrena un modelo de
clasificación para estimar la probabilidad de que ocurra un
incidente grave o un riesgo de alto impacto en un proyecto.

Predicción: se expone a los módulos de QHSE y project_risk
para actualizar las matrices de riesgos en tiempo real.

Almacenamiento: se guarda en predicciones_ml con tipo
riesgo e incluye probabilidad_incidente y probabilidad_desvio_costos.

🤖 Copilots por Módulo

El módulo incorpora asistentes conversacionales entrenados sobre los
datos de la empresa. Cada copiloto utiliza un LLM conectado a las
vistas canónicas para responder preguntas en lenguaje natural. Los
copilots se integran en las siguientes secciones:

Copilot	Objetivo
Finanzas	Responder sobre costos, aging, SII F29, margen y cashflow
Proyectos	Indicar avance, ROI, desviaciones y órdenes de cambio
HSE	Consultar incidentes, inspecciones y predicciones de riesgo
Documentos	Buscar documentos y notas de venta, resumir actas

Cada copilot accede a la API con permisos del usuario y respeta
restricciones de datos. No responde preguntas que requieran
información de otros proyectos no autorizados.

🧠 Simulaciones de Escenarios

Para la proyección de flujos financieros y riesgos se implementa un
módulo de simulación Monte Carlo:

Variables de Entrada: presupuestos, órdenes comprometidas,
facturación pendiente, aging buckets y probabilidad de cobro.

Escenarios: se generan 10 000 simulaciones por proyecto para
calcular rangos de cashflow y probabilidad de quiebres de
liquidez. Se generan tres escenarios: optimista, base y
pesimista, siguiendo la estrategia de finanzas【22†L65-L73】.

Salidas: para cada proyecto se entrega un rango probable de
cashflow neto mensual y un gráfico de densidad. También se
calcula el Value at Risk (VaR) financiero y se comparan con
márgenes aceptables.

🔗 API REST

Los servicios del módulo se exponen bajo /api/v1/analytics:

GET /predictions?type=costo → Devuelve predicciones de costos
con filtros opcionales por proyecto y fecha.

GET /predictions?type=plazo → Devuelve predicciones de plazos.

GET /predictions?type=riesgo → Devuelve predicciones de riesgos
e incidentes.

GET /copilot → Ruta común que recibe una pregunta y devuelve la
respuesta del copilot correspondiente según el rol del usuario.

POST /simulations → Ejecuta una simulación Monte Carlo con
parámetros custom y devuelve estadísticas (requiere roles CFO o CEO).

Todas las rutas requieren autenticación y devuelven datos en JSON. Se
deben aplicar límites de rate‑limiting y logging de auditoría.

🖥️ Frontend y Visualización

Las funcionalidades de analítica se integran en la sección Dashboard
Ejecutivo y en páginas de Finanzas Avanzadas. Para
visualizaciones se deben utilizar los componentes del design system:

KPICards para mostrar valores predichos y desviaciones.

Gráficos (Charts) generados con la librería de frontend
(Recharts) para series temporales, distribuciones y boxplots. Se
deben incluir títulos de eje y leyendas e indicar claramente
intervalos de confianza.

Tablas para listar predicciones con filtros por proyecto y
fecha. Cabeceras grises, filas alternas y opción de exportar a
CSV/Excel.

Componentes interactivos: controles para seleccionar el
escenario (optimista/base/pesimista) y ver efectos en cashflow.

La UI debe adaptarse a modo oscuro/claro y respetar la paleta de
colores y tipografía oficiales【24†L45-L54】.

✅ Cumplimiento y Buenas Prácticas

Uso de Vistas Canónicas: todas las consultas de entrenamiento y
predicción se basan en vista_ordenes_completas,
vista_proyectos_resumen y demás vistas autorizadas
(Art. V.1【17†L154-L163】). Nunca se consulta tablas brutas.

Prevenir Duplicados: los modelos se entrenan con
anti‑duplicación multicapa: se elimina cualquier orden duplicada
detectada por los índices de la tabla unificada【19†L233-L241】.

Seguridad y Roles: se controla el acceso a resultados de
predicción y simulaciones mediante roles; sólo CFO/CEO pueden
ejecutar simulaciones, mientras que PM y Clientes pueden ver
predicciones de sus proyectos. La auditoría registra quién
solicitó cada predicción.

Trazabilidad y Versionado: cada registro en predicciones_ml
almacena modelo_version para poder reproducir resultados. Los
modelos se versionan con MLflow o similar y se documenta el
linaje de datos.【28†L62-L70】

Con estas correcciones, el módulo de Analítica Avanzada se alinea
con la visión de ofitec.ai: predicciones confiables, basadas en datos
validados, con una experiencia unificada en el portal y cumpliendo
exigencias de gobernanza y seguridad.