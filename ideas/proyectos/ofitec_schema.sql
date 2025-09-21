-- Ofitec core schema for Proyectos & Presupuestos
CREATE TABLE IF NOT EXISTS proyectos (
  id SERIAL PRIMARY KEY,
  codigo VARCHAR(64) UNIQUE,
  nombre TEXT NOT NULL,
  cliente_id VARCHAR(64),
  comuna VARCHAR(64),
  region VARCHAR(64),
  fecha_inicio_plan DATE,
  fecha_termino_plan DATE,
  fecha_termino_real DATE,
  estado VARCHAR(32),
  tipo VARCHAR(32),
  responsable_id VARCHAR(64),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS presupuestos (
  id SERIAL PRIMARY KEY,
  proyecto_id INTEGER REFERENCES proyectos(id),
  version INTEGER DEFAULT 1,
  estado VARCHAR(32),
  moneda VARCHAR(8) DEFAULT 'CLP',
  factor_uf DECIMAL(18,6),
  observaciones TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capitulos (
  id SERIAL PRIMARY KEY,
  presupuesto_id INTEGER REFERENCES presupuestos(id) ON DELETE CASCADE,
  codigo_capitulo VARCHAR(64),
  nombre TEXT,
  orden INTEGER,
  UNIQUE (presupuesto_id, codigo_capitulo)
);

CREATE TABLE IF NOT EXISTS partidas (
  id SERIAL PRIMARY KEY,
  capitulo_id INTEGER REFERENCES capitulos(id) ON DELETE CASCADE,
  codigo_partida VARCHAR(64),
  descripcion TEXT,
  unidad VARCHAR(16),
  cantidad DECIMAL(18,4),
  precio_unitario DECIMAL(18,4),
  costo_directo DECIMAL(18,4),
  costo_indirecto DECIMAL(18,4),
  utilidad DECIMAL(18,4),
  total DECIMAL(18,4),
  rendimiento_meta_json JSONB,
  UNIQUE (capitulo_id, codigo_partida)
);

CREATE TABLE IF NOT EXISTS apu_insumos (
  id SERIAL PRIMARY KEY,
  partida_id INTEGER REFERENCES partidas(id) ON DELETE CASCADE,
  tipo_insumo VARCHAR(16), -- material | mano_obra | maquinaria | subcontrato
  codigo_insumo VARCHAR(64),
  descripcion TEXT,
  unidad VARCHAR(16),
  cantidad DECIMAL(18,4),
  precio_unitario DECIMAL(18,4),
  subtotal DECIMAL(18,4)
);

CREATE TABLE IF NOT EXISTS avances (
  id SERIAL PRIMARY KEY,
  partida_id INTEGER REFERENCES partidas(id) ON DELETE CASCADE,
  fecha DATE,
  cantidad_avance DECIMAL(18,4),
  porcentaje DECIMAL(6,3),
  observaciones TEXT
);

CREATE TABLE IF NOT EXISTS imputaciones_financieras (
  id SERIAL PRIMARY KEY,
  partida_id INTEGER REFERENCES partidas(id) ON DELETE CASCADE,
  tipo_doc VARCHAR(16), -- oc | factura | egreso | estado_pago
  numero_doc VARCHAR(64),
  fecha DATE,
  monto DECIMAL(18,4),
  moneda VARCHAR(8) DEFAULT 'CLP',
  proveedor_id VARCHAR(64),
  enlace_doc TEXT
);

CREATE TABLE IF NOT EXISTS fx_uf (
  fecha DATE PRIMARY KEY,
  valor_uf DECIMAL(18,6) NOT NULL
);

CREATE TABLE IF NOT EXISTS retenciones (
  id SERIAL PRIMARY KEY,
  proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
  tipo VARCHAR(32),
  porcentaje DECIMAL(9,6),
  fecha_inicio DATE,
  fecha_fin DATE,
  monto_retenido DECIMAL(18,4) DEFAULT 0,
  monto_liberado DECIMAL(18,4) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS garantias (
  id SERIAL PRIMARY KEY,
  proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
  tipo VARCHAR(32), -- fiel_cumplimiento | anticipo | correcta_ejecucion
  numero VARCHAR(64),
  emisor VARCHAR(128),
  monto DECIMAL(18,4),
  fecha_inicio DATE,
  fecha_vencimiento DATE,
  estado VARCHAR(32)
);

-- Views to replicate typical Excel totals
CREATE OR REPLACE VIEW v_capitulos_totales AS
SELECT c.id AS capitulo_id, c.presupuesto_id,
       SUM(COALESCE(p.total, COALESCE(p.cantidad,0)*COALESCE(p.precio_unitario,0))) AS total_capitulo
FROM capitulos c
LEFT JOIN partidas p ON p.capitulo_id = c.id
GROUP BY c.id, c.presupuesto_id;

CREATE OR REPLACE VIEW v_presupuesto_totales AS
SELECT pr.id AS presupuesto_id,
       SUM(v.total_capitulo) AS total_presupuesto
FROM presupuestos pr
LEFT JOIN v_capitulos_totales v ON v.presupuesto_id = pr.id
GROUP BY pr.id;

-- Avances físicos
CREATE OR REPLACE VIEW v_partidas_avance AS
SELECT p.id AS partida_id,
       COALESCE(SUM(a.cantidad_avance),0) AS cantidad_avanzada,
       CASE WHEN COALESCE(p.cantidad,0)=0 THEN 0
            ELSE LEAST(1, COALESCE(SUM(a.cantidad_avance),0)/NULLIF(p.cantidad,0)) END AS avance_frac
FROM partidas p
LEFT JOIN avances a ON a.partida_id = p.id
GROUP BY p.id;
