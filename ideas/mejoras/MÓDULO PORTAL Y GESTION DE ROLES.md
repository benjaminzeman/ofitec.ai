MÓDULO PORTAL Y GESTIÓN DE ROLES – Versión Corregida

Este documento redefine el módulo Portal Cliente y la Gestión de
Roles y Usuarios de ofitec.ai en consonancia con las conclusiones
del diagnóstico y las leyes internas. Incorpora mejoras en
autenticación, invitaciones, permisos y estructura de datos.

🎯 Objetivo

Portal Cliente: brindar a clientes y socios externos un acceso
seguro a la información de sus proyectos, documentos y
métricas, respetando la separación de datos y la estética DeFi.

Gestión de Usuarios y Roles: administrar usuarios de la
plataforma (internos y externos) con flujos de alta, baja,
roles y auditoría, incluyendo autenticación federada (SSO) y
multifactor opcional.

🗄️ Modelo de Datos

Se introducen nuevas tablas canónicas para la gestión de usuarios y
permisos. Estas tablas se rigen por la Ley de Base de Datos: se
aplican validaciones de unicidad, integridad referencial y
auditoría.

usuarios_sistema
Campo	Tipo	Obligatorio	Descripción
id	SERIAL PK	Sí	Identificador único
email	TEXT UNIQUE	Sí	Correo del usuario (case‑insensitive)
nombre	TEXT	Sí	Nombre completo
auth_provider	TEXT	Sí	{'local','google','azure'}
password_hash	TEXT	No*	Hash de contraseña (solo para auth local; cifrado scrypt)
mfa_enabled	BOOLEAN	Sí	Indica si usa MFA (TOTP)
rol_principal	TEXT	Sí	{Administrador,CFO,Gerente,PM,Supervisor,Cliente,HSEMgr}
estado	TEXT	Sí	{activo,inactivo,pending_invite}
allowed_project_ids	INT[]	No	Lista de proyectos que el usuario puede ver (rol Cliente)
created_at	TIMESTAMP	Sí	Fecha de creación
last_login_at	TIMESTAMP	No	Último inicio de sesión exitoso

Nota: El campo password_hash se usa solo para usuarios con
auth_provider='local'. Cuando se usa SSO, se almacena el
sub federado y el hash se mantiene nulo.

roles_permisos

Define las acciones permitidas para cada rol sobre cada recurso
(endpoint o página). Se utiliza un esquema de tipo role → recurso → acción.

id	rol	recurso	puede_leer	puede_crear	puede_actualizar	puede_eliminar
PK	TEXT	TEXT	BOOLEAN	BOOLEAN	BOOLEAN	BOOLEAN

Ejemplo: para el rol PM, el recurso incidentes_hse tiene
puede_leer=true, puede_crear=true, puede_actualizar=true y
puede_eliminar=false.

sesiones_activas

Tabla para administrar sesiones JWT y auditoría.

id	SERIAL PK
usuario_id	INTEGER FK
jti	TEXT UNIQUE
issued_at	TIMESTAMP
expires_at	TIMESTAMP
ip_address	INET
user_agent	TEXT
revoked	BOOLEAN

Se debe eliminar periódicamente sesiones expiradas para cumplir con la
política de retención mínima.

🔒 Autenticación y Seguridad

SSO con Google: se habilita login federado usando OAuth2
(Google Workspace). En el flujo de login se solicita el correo
corporativo y se verifica contra el dominio permitido.

Contraseña local opcional: para usuarios sin SSO, se usa
registro con email/contraseña y se aplica MFA vía TOTP.

Multi‑Factor Authentication (MFA): configurable por rol. Los
roles de administrador y CFO deben habilitar MFA obligatoriamente.

Invitaciones Controladas: sólo roles Administrador o CFO
pueden invitar a nuevos usuarios. Se envía un correo con token de
registro. El usuario se crea con estado=pending_invite y
rol_principal preliminar hasta que complete la activación.

Auditoría: se registra cada login, cambio de rol, adición o
revocación de proyectos en la tabla de sesiones, con IP y
user‑agent. Se generan alertas si se detectan múltiples fallos o
accesos desde ubicaciones inusuales.

Revocación y Rotación de Secretos: se integra con Vault para
rotar credenciales de base de datos y otros secretos. Los tokens
de sesión se revocan al cambiar contraseña o rol.

🧑‍💻 Administración de Roles y Permisos

El módulo incluye un panel de administración para gestionar los roles
de cada usuario y sus permisos granulares. Acciones principales:

Asignar roles: seleccionar uno de los roles predefinidos.

Editar permisos: ajustar permisos específicos para un recurso
(habilitar o restringir creación/edición/borrado). Útil para
proyectos con necesidades especiales.

Asignar proyectos (allowed_project_ids): para roles Cliente y
Subcontratista, seleccionar los proyectos a los que tienen acceso.

Desactivar usuario: marcar estado=inactivo (no borra
historiales).

Reset de MFA: regenerar secreto TOTP en caso de extravío.

La interfaz de roles se apoya en tablas ordenadas, formularios y
modales, siguiendo el design system (inputs sin sombras, botones
primarios en color lime, etc.)【24†L45-L54】.

🌐 Portal Cliente

El portal cliente se integra en la ruta /cliente del frontend (puerto
3001) y ofrece a usuarios externos una vista de sus proyectos,
documentos y estados financieros. Características:

Lista de Proyectos: muestra todos los proyectos dentro de
allowed_project_ids del usuario. Para cada proyecto se
despliega avance físico, presupuesto vs gasto y KPIs de seguridad.

Documentos y Notas de Venta: acceso a actas, planos, notas de
venta aprobadas y otros archivos. Se implementa un buscador con
permisos granulados (no mostrar documentos de otros proyectos).

Comunicación: widget de mensajería (como un chat) para
interactuar con el PM o Supervisor. Integrar con WhatsApp API si
corresponde.

Estado de Pagos: lista de facturas o notas de venta con
estado (pendiente, pagada, vencida). Basado en aging AR/AP y
v_facturas_compra【17†L154-L163】.

Configuración: permite cambiar idioma, activar notificaciones y
gestionar MFA (si habilitado).

📑 API REST

Para exponer la gestión de usuarios y portal, se definen rutas bajo
/api/v1/users y /api/v1/portal:

POST /auth/login → Inicio de sesión (SSO o local).

POST /auth/mfa/verify → Verificar código TOTP.

POST /auth/invite → Enviar invitación (admin/CFO).

GET /users → Listar usuarios (admin/CFO).

POST /users → Crear usuario (a partir de invitación).

PATCH /users/{id} → Actualizar roles/permisos/estado.

GET /portal/projects → Proyectos disponibles para el usuario.

GET /portal/documents → Documentos y notas de venta filtradas.

GET /portal/financial → Estados de pagos y aging.

POST /portal/messages → Crear mensaje en la comunicación.

Los endpoints responden JSON y validan roles y allowed_project_ids.

🖥️ UX y Diseño

La interfaz de usuario debe seguir estrictamente la Estrategia
Visual: paleta oscura por defecto, radius de 12 px, nada de
sombras【24†L45-L54】. Consideraciones especiales:

Accesibilidad: contrastes correctos para modo oscuro/claro y
textos legibles. Form labels claros y descriptivos.

Responsive: el portal cliente debe adaptarse a móviles para
clientes en terreno. Utilizar grid y breakpoints de Tailwind.

Componentes reutilizables: las tablas, formularios y modales
emplean los componentes base (Card, Table, Input, Button). Los
estados de pagos usan badges de colores según la paleta semántica.

Flujo de invitación: al abrir un enlace de invitación, mostrar
un formulario de registro con validaciones. Si el usuario ya está
registrado, redirigir al login.

✅ Cumplimiento

Ley de Puertos: el portal y la gestión de usuarios se alojan
en el frontend 3001; los endpoints residen en 5555. No se
utilizan puertos adicionales【8†L43-L50】.

Ley de Base de Datos: las nuevas tablas cumplen con
integridad referencial y se relacionan con proyectos y
órdenes unificadas. Se evitan duplicados (indice UNIQUE en
email).【17†L154-L163】

Estrategia de Páginas: las vistas de este módulo se derivan
de la sección Clientes y de Configuración/Admin【27†L316-L324】.

Estrategia Visual: se respetan los tokens, componentes y
paleta definidos【24†L45-L54】.

Con estas mejoras, el módulo de Portal y Roles se ajusta a las
especificaciones oficiales y provee una base sólida y segura para
gestionar usuarios internos y externos, ofreciendo una experiencia
uniforme en el portal y un control granular de acceso.