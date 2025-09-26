# SPRINT 1: Control Financiero 360 Mejorado

## Objetivos
- Implementar validaciones críticas de negocio
- Mejorar UI de control financiero con KPIs y semáforos
- Establecer foundations para siguiente sprint

## Tareas Priority 0

### 1. Backend - Validaciones Críticas
**Archivos:** `backend/server.py`, `backend/validation_engine.py`

#### 1.1 Crear motor de validaciones
```python
# backend/validation_engine.py
class ValidationEngine:
    @staticmethod
    def validate_invoice_vs_po(invoice_amount, po_remaining):
        if invoice_amount > po_remaining:
            return {
                "error": "invoice_over_po", 
                "po_remaining": po_remaining,
                "attempted": invoice_amount
            }
        return None
    
    @staticmethod
    def validate_payment_vs_invoice(payment_amount, invoice_balance):
        if payment_amount > invoice_balance:
            return {
                "error": "overpaid",
                "invoice_balance": invoice_balance,
                "attempted": payment_amount
            }
        return None
```

#### 1.2 Mejorar endpoint control financiero
```python
@app.route("/api/control_financiero/resumen")
def api_control_financiero_resumen_v2():
    # Añadir campos invoiced, paid, available_real
    # Implementar flags exceeds_budget, invoice_over_po, overpaid
    # Agregar metadata con fuentes
```

### 2. Frontend - UI Mejorada
**Archivos:** `frontend/app/proyectos/control/page.tsx`, `frontend/components/FinancialKPIs.tsx`

#### 2.1 Componente KPI Cards con semáforos
```tsx
// frontend/components/FinancialKPIs.tsx
export function FinancialKPIs({ data }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <KPICard label="PC" value={data.budget_cost} />
      <KPICard label="Comprometido" value={data.committed} />
      <KPICard label="Facturado" value={data.invoiced} />
      <KPICard label="Pagado" value={data.paid} />
      <KPICard label="Disponible Conservador" value={data.available_conservative} />
      <KPICard label="Disponible Real" value={data.available_real} />
    </div>
  );
}
```

### 3. Validaciones y Testing
**Archivos:** `backend/tests/test_validation_engine.py`

## Criterios de Aceptación
- [ ] Validaciones server-side implementadas con códigos 422
- [ ] UI muestra KPIs con semáforos funcionando
- [ ] Flags de alerta visibles en interfaz
- [ ] Tests unitarios pasando
- [ ] Endpoint control financiero retorna metadata completa

## Estimación: 10 días