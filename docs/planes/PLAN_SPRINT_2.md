# SPRINT 2: Estados de Pago (EP) y Ventas con IA

## Objetivos

- Implementar módulo completo de Estados de Pago para clientes
- Desarrollar sistema de ventas (AR) con mapeo automático a proyectos
- Integrar motor de IA para sugerencias y auto-asignación

## Tareas Priority 1

### 1. Modelo de Datos EP (Estados de Pago)

**Archivos:** `tools/create_ep_schema.sql`, `backend/models/ep_models.py`

#### 1.1 Crear tablas EP

```sql
-- Estados de Pago (EP) Cliente
CREATE TABLE IF NOT EXISTS ep_headers (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  contract_id INTEGER,
  ep_number TEXT,
  period_start TEXT, 
  period_end TEXT,
  submitted_at TEXT, 
  approved_at TEXT,
  status TEXT CHECK (status IN ('draft','submitted','approved','rejected','invoiced','paid')) DEFAULT 'draft',
  retention_pct REAL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS ep_lines (
  id INTEGER PRIMARY KEY,
  ep_id INTEGER NOT NULL,
  sov_item_id INTEGER,
  item_code TEXT,
  description TEXT,
  unit TEXT,
  qty_period REAL,
  unit_price REAL,
  amount_period REAL,
  qty_cum REAL,
  amount_cum REAL,
  chapter TEXT
);
```

### 2. Sistema de Ventas (AR) con IA

**Archivos:** `backend/api_sales_invoices.py`, `backend/ar_mapping_engine.py`

#### 2.1 Motor de mapeo IA

```python
# backend/ar_mapping_engine.py
class ARMappingEngine:
    def suggest_project(self, invoice_data):
        """Sugiere proyecto para factura con explicaciones"""
        candidates = []
        
        # 1. Cliente único activo
        if self._single_active_project(invoice_data['customer_rut']):
            candidates.append({
                'project_id': project_id,
                'confidence': 0.95,
                'reasons': ['cliente único activo']
            })
        
        # 2. EP del mes con monto similar
        ep_matches = self._ep_amount_matches(invoice_data)
        candidates.extend(ep_matches)
        
        # 3. Reglas aprendidas (regex/alias)
        rule_matches = self._apply_learned_rules(invoice_data)
        candidates.extend(rule_matches)
        
        return sorted(candidates, key=lambda x: x['confidence'], reverse=True)[:5]
```

### 3. UI Estados de Pago

**Archivos:** `frontend/app/proyectos/[id]/estados-pago/page.tsx`

#### 3.1 Página EP con importador

```tsx
// frontend/app/proyectos/[id]/estados-pago/page.tsx
export default function EstadosPagoPage({ params }) {
  return (
    <div className="p-6 space-y-6">
      <EPImporter projectId={params.id} />
      <EPList projectId={params.id} />
      <EPApprovalFlow />
    </div>
  );
}
```

### 4. Integración Ventas

**Archivos:** `frontend/app/ventas/page.tsx`, `frontend/components/AssignProjectDrawer.tsx`

#### 4.1 Lista de ventas con asignación de proyecto

```tsx
// frontend/app/ventas/page.tsx
export default function VentasPage() {
  const [invoices, setInvoices] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  
  return (
    <div className="p-6">
      <InvoicesList invoices={invoices} onAssignProject={setSelectedInvoice} />
      {selectedInvoice && (
        <AssignProjectDrawer 
          invoice={selectedInvoice} 
          onClose={() => setSelectedInvoice(null)} 
        />
      )}
    </div>
  );
}
```

## APIs Requeridas

### Backend Endpoints

- `POST /api/ep/import` - Importar EP desde Excel
- `POST /api/ep/:id/approve` - Aprobar EP  
- `POST /api/ep/:id/generate-invoice` - Generar factura desde EP
- `GET /api/sales_invoices` - Lista facturas de venta
- `POST /api/ar-map/suggestions` - Sugerencias de proyecto para factura
- `POST /api/ar-map/confirm` - Confirmar asignación

## Criterios de Aceptación

- [ ] Importador de EP Excel funcionando con mapeo tolerante
- [ ] Workflow EP: draft → submitted → approved → invoiced
- [ ] Sistema de ventas muestra facturas sin proyecto asignado
- [ ] Motor IA sugiere proyectos con explicaciones (reasons)
- [ ] Auto-asignación segura para casos con alta confianza (≥0.97)
- [ ] UI responsiva siguiendo design system Ofitec

## Riesgos y Mitigaciones

- **Riesgo:** Formatos Excel diversos de clientes
- **Mitigación:** Importador tolerante + wizard interactivo de mapeo

- **Riesgo:** Sugerencias de baja calidad
- **Mitigación:** Sistema de feedback + aprendizaje continuo

## Estimación: 15 días

## Dependencias

- Sprint 1 completado (validaciones críticas)
- Esquema de base de datos estable
- Design system components listos