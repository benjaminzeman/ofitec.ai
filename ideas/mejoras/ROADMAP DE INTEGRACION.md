ROADMAP DE INTEGRACIÓN – Ofitec.ai 2025‑2026

Este documento actualiza el roadmap de integración tomando en cuenta las
conclusiones del análisis de cumplimiento con la Ley de Puertos【8†L43-L50】,
la Ley de Base de Datos Oficial【17†L154-L163】【19†L233-L241】 y la
Estrategia de Creación de Páginas【27†L296-L300】. Se priorizan las
incorporaciones que garantizan coherencia con las normas internas y un
despliegue progresivo de funciones avanzadas (IA, QHSE, portal
cliente) sobre el stack Next.js 14 + Flask + PostgreSQL.

Fases y Prioridades
📦 Fase 1 — Consolidación de Base

Objetivo: migrar a una base de datos PostgreSQL unificada y
estabilizar la infraestructura según la Ley de Puertos y de BD.

Migración a PostgreSQL: crear las tablas purchase_orders_unified
y vendors_unified descritas en el Artículo II【17†L154-L163】. Aplicar
constraints de unicidad y normalización, y desarrollar migraciones
idempotentes. Documentar los procedimientos de importación Chipax
según Artículo IV【17†L154-L163】.

Backups 3‑2‑1 y Healthchecks: implementar la estrategia
de backups diarios/horarios y verificar integridad automáticamente
(Artículo VII【19†L233-L241】). Incorporar un endpoint
/api/health y un job de verificación de puertos
para asegurar que el frontend opera en 3001 y el backend en 5555【8†L43-L50】.

Despliegue Blue/Green: preparar scripts de despliegue con blue/green
y failover automático basados en las entregas 9–12 (autoscaling
workers, exportación SII y rotación de secretos). Asegurar que
siempre existan dos entornos activos y que la rotación de
secretos se gestione vía Vault.

📊 Fase 2 — Módulos Financieros (NV, Aging, SII)

Objetivo: habilitar el ciclo financiero completo usando la base
unificada y la analítica de aging.

Notas de Venta (NV): desplegar el módulo de NV con
numeración anual, validación de RUT y auditoría detallada (ya
desarrollado). Asegurarse de que el PDF y los formularios
respeten el design system y de que los datos se guarden en
sales_notes relacionadas a projects y purchase_orders.

Aging AR/AP: integrar el cálculo de aging buckets en la
API financiera; basarse únicamente en las vistas canónicas
v_facturas_compra y las tablas unificadas【17†L154-L163】 para evitar
duplicados. Exponer endpoints /api/v1/aging para AR y AP.

Declaración SII F29: implementar el módulo SII/F29 como se
definió, asegurando que utilice la vista v_impuestos cuando esté
disponible y respete el Art. IV (mapping Chipax)
y el Art. V (consultas autorizadas)【17†L154-L163】.

Conciliación Bancaria y Conectores: incorporar las mejoras
del motor híbrido (reglas + fuzzy matching) en la API de
conciliación. Conectar con los nuevos conectores bancarios y
cruzar la conciliación con las órdenes unificadas.

🛡 Fase 3 — Seguridad, Roles y Portal Cliente

Objetivo: robustecer la autenticación/autorización y ofrecer un
portal cliente según la estrategia.

Gestión de Usuarios y Roles: crear las tablas usuarios_sistema,
roles_permisos y sesiones_activas siguiendo las
recomendaciones de la Estrategia de Páginas【16†L273-L280】. Integrar
autenticación SSO con Google y multi‑factor opcional. Añadir
flujos de invitación, auditoría de acciones y restricciones
por proyecto (allowed_project_ids) para clientes y
subcontratistas.

Portal Cliente: desarrollar el portal para clientes dentro
del frontend (ruta /cliente) con vistas de avance de proyectos,
estados de facturación y comunicación. Asegurarse de filtrar
resultados por customer_id y que cada usuario sólo vea sus
proyectos. Cumplir con la estética DeFi y los componentes
estandarizados【24†L45-L54】.

Matrix de Roles: mapear los roles Administrador, CFO,
Gerente, PM, Supervisor, Subcontratista y Cliente a las páginas
definidas en la Estrategia de Páginas【27†L296-L300】. Implementar
un middleware en el frontend para ocultar rutas no
autorizadas.

🌐 Fase 4 — Inteligencia y Analítica Avanzada

Objetivo: añadir capacidades IA predictivas y automatizadas en
finanzas, proyectos y riesgos.

Predicciones de Costos y Plazos: crear un servicio de IA
que entrene modelos con los 34 k registros existentes【22†L37-L45】.
Almacenar los resultados en la tabla predicciones_ml con campos
id, project_id, tipo, valor_predicho, intervalo_confianza,
score, modelo_version y created_at. Exponer
/api/v1/analytics/predictions.

Copilots por Módulo: integrar copilots conversacionales en las
secciones de finanzas, proyectos, HSE y documentos. Basarlos en
modelos LLM internos y en las vistas canónicas aprobadas【17†L154-L163】.

Analítica de Seguridad (HSE): extender QHSE con análisis de
tendencias, identificación de causas raíz y predicción de
incidentes futuros. Utilizar los modelos de incidentes y
detecciones de EPP definidos en el módulo QHSE actualizado.

🔍 Fase 5 — Gobernanza de Datos y BI

Objetivo: establecer un catálogo de datos, linaje y contratos de
datos robustos.

Catálogo y Linaje: integrar una herramienta como Marquez u
OpenLineage para rastrear el linaje de las tablas canónicas y
predicciones. Documentar transformaciones y exponer un panel
para auditores.

Data Contracts y Test de Integridad: versionar los
contratos de datos para cada vista o API, con pruebas de
compatibilidad en CI/CD. Implementar contratos para las vistas
v_facturas_compra, v_proyectos_resumen, etc.

Dashboards Provisionados: utilizar Metabase u otra
plataforma para desplegar dashboards base y conectarlos a las
vistas canónicas. Crear paquetes de dashboards para portafolio,
aging financiero y seguridad. Publicar como parte del portal
analítico.

Gobernanza y Cumplimiento

El éxito de esta hoja de ruta depende de respetar estrictamente las
normas internas. Antes de crear nuevas APIs, páginas o tablas,
consulte siempre la Ley de Puertos para no duplicar
servidores【8†L43-L50】, la Ley de Base de Datos para mantener la
integridad y las vistas canónicas【19†L233-L241】, y los documentos de
Estrategia Visual para la coherencia de la interfaz【24†L45-L54】.