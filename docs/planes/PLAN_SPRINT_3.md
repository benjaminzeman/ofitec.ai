# SPRINT 3: Conciliación Bancaria Avanzada y Matching PO↔Factura

## 📊 **Estado Actual - Sistema Completo Disponible**

### **✅ CONCILIACIÓN BANCARIA - 100% DESARROLLADA**
**Ubicación:** `ofitec_conciliacion_bancaria/` (sistema completo)
**Estado:** Totalmente funcional con 7 tablas + ML Engine

**Sistema Disponible:**
- ✅ **Base de Datos**: 7 tablas especializadas (cuentas, movimientos, facturas, sueldos, gastos, conciliaciones)
- ✅ **ML Engine**: Scoring 0-100% con algoritmos de matching inteligente
- ✅ **API REST**: 8 endpoints funcionales para todas las operaciones
- ✅ **Validaciones**: RUT chileno, duplicados, alias automático
- ✅ **Matching Avanzado**: 1↔1, 1↔N, N↔1 con subset-sum algorithms

### **🔗 MATCHING PO↔FACTURA - Base Disponible**
**Fuente:** `purchase_orders_unified` (16,289 registros)
**Estado:** Datos listos, requiere interfaz de matching

---

## Objetivos

- Implementar conciliación bancaria inteligente con UI contextual
- Desarrollar sistema de matching automático PO↔Factura con IA
- Establecer motor de aprendizaje continuo para ambos sistemas

## Tareas Priority 1

### 1. Conciliación Bancaria Inteligente

**Archivos:** `backend/conciliation/intelligent_matching.py`, `frontend/components/ReconcileDrawer.tsx`

#### 1.1 Motor de conciliación avanzado

```python
# backend/conciliation/intelligent_matching.py
class IntelligentReconciliation:
    def suggest_matches(self, source, options):
        """Motor avanzado de conciliación"""
        candidates = []
        
        # Generación de candidatos por monto, fecha, identidad, contenido
        amount_matches = self._find_amount_matches(source, options)
        date_matches = self._find_date_matches(source, options)
        identity_matches = self._find_identity_matches(source, options)
        content_matches = self._find_content_matches(source, options)
        
        # Scoring y ranking
        for candidate in self._merge_candidates([amount_matches, date_matches, identity_matches, content_matches]):
            score = self._calculate_confidence_score(candidate, source)
            if score > 0.3:  # umbral mínimo
                candidates.append({
                    'candidate': candidate,
                    'confidence': score,
                    'reasons': self._explain_match(candidate, source)
                })
        
        return sorted(candidates, key=lambda x: x['confidence'], reverse=True)[:5]
    
    def _calculate_confidence_score(self, candidate, source):
        """Cálculo de confianza con explicabilidad"""
        score = 0.0
        
        # Monto (50%)
        amount_score = self._score_amount_match(candidate.amount, source.amount)
        score += amount_score * 0.5
        
        # Fecha (20%)  
        date_score = self._score_date_match(candidate.date, source.date)
        score += date_score * 0.2
        
        # Identidad (20%) - RUT, alias, folio
        identity_score = self._score_identity_match(candidate, source)  
        score += identity_score * 0.2
        
        # Contenido (10%) - similitud de descripción
        content_score = self._score_content_match(candidate.description, source.description)
        score += content_score * 0.1
        
        return min(1.0, score)
```

#### 1.2 UI Contextual - Botón Conciliar en todas las vistas

```tsx
// frontend/components/ReconcileDrawer.tsx
export default function ReconcileDrawer({ source, onClose }) {
  const [suggestions, setSuggestions] = useState([]);
  const [selected, setSelected] = useState(null);
  
  useEffect(() => {
    fetchSuggestions(source).then(setSuggestions);
  }, [source]);
  
  const handleConfirm = async () => {
    await confirmReconciliation(source, selected);
    onClose();
  };
  
  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-white border-l p-4 z-50">
      <div className="space-y-3">
        <h3 className="text-lg font-semibold">Conciliar</h3>
        
        {suggestions.map((item, idx) => (
          <div key={idx} className="rounded-2xl border p-3">
            <div className="flex justify-between items-center">
              <span className="font-medium">{item.candidate.description}</span>
              <span className="text-xs">conf {(item.confidence * 100).toFixed(1)}%</span>
            </div>
            
            <div className="text-xs text-neutral-500 mt-1">
              {item.reasons.join(' • ')}
            </div>
            
            <div className="mt-2 flex gap-2">
              <button 
                onClick={() => setSelected(item)}
                className="border px-2 py-1 rounded"
              >
                Elegir
              </button>
              {idx === 0 && item.confidence >= 0.92 && (
                <button 
                  onClick={() => { setSelected(item); handleConfirm(); }}
                  className="border px-2 py-1 rounded bg-lime-600 text-white"
                >
                  Aceptar #1
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {selected && (
        <div className="mt-4">
          <button onClick={handleConfirm} className="w-full py-2 bg-lime-600 text-white rounded">
            Confirmar Conciliación
          </button>
        </div>
      )}
    </div>
  );
}
```

### 2. Matching PO↔Factura con IA

**Archivos:** `backend/ap_match/intelligent_matching.py`, `backend/api_ap_match.py`

#### 2.1 Motor de matching PO-Factura

```python
# backend/ap_match/intelligent_matching.py
class APMatchEngine:
    def suggest_po_matches(self, invoice_data):
        """Sugiere órdenes de compra para una factura"""
        vendor_id = invoice_data.get('vendor_id')
        amount = invoice_data.get('amount')
        date = invoice_data.get('date')
        
        candidates = self._generate_po_candidates(vendor_id, amount, date)
        scored_candidates = []
        
        for candidate in candidates:
            confidence = self._calculate_po_match_confidence(candidate, invoice_data)
            if confidence > 0.3:
                scored_candidates.append({
                    'candidate': {
                        'po_id': candidate['po_id'],
                        'lines': candidate['available_lines'],
                        'coverage': {
                            'amount': sum(line['amount_remaining'] for line in candidate['available_lines']),
                            'pct': self._calculate_coverage_pct(candidate, amount)
                        }
                    },
                    'confidence': confidence,
                    'reasons': self._explain_po_match(candidate, invoice_data)
                })
        
        return sorted(scored_candidates, key=lambda x: x['confidence'], reverse=True)[:5]
    
    def _calculate_po_match_confidence(self, po_candidate, invoice_data):
        """Scoring para matching PO-Factura"""
        score = 0.0
        
        # Monto (50%)
        amount_score = self._score_amount_coverage(po_candidate, invoice_data['amount'])
        score += amount_score * 0.5
        
        # Fecha (20%)
        date_score = self._score_date_proximity(po_candidate['po_date'], invoice_data['date'])
        score += date_score * 0.2
        
        # Proveedor (20%)
        vendor_score = 1.0 if po_candidate['vendor_id'] == invoice_data['vendor_id'] else 0.0
        score += vendor_score * 0.2
        
        # Descripción/contenido (10%)
        content_score = self._score_content_similarity(po_candidate, invoice_data)
        score += content_score * 0.1
        
        return min(1.0, score)
```

#### 2.2 API endpoints para matching

```python
# backend/api_ap_match.py
from flask import Blueprint, request, jsonify

bp = Blueprint('ap_match', __name__)

@bp.post('/api/ap-match/suggestions')
def ap_match_suggestions():
    """Sugerencias de matching PO-Factura"""
    data = request.get_json()
    
    engine = APMatchEngine()
    suggestions = engine.suggest_po_matches(data)
    
    return jsonify({'items': suggestions})

@bp.post('/api/ap-match/confirm')
def ap_match_confirm():
    """Confirmar asociación PO-Factura"""
    data = request.get_json()
    
    # Validaciones 3-way matching
    violations = validate_three_way_match(data)
    if violations:
        return jsonify({'error': 'three_way_violations', 'violations': violations}), 422
    
    # Guardar enlaces
    links_created = save_ap_po_links(data)
    
    # Log evento para aprendizaje
    log_ap_match_event(data)
    
    return jsonify({'ok': True, 'links_created': links_created})
```

### 3. Sistema de Aprendizaje Continuo

**Archivos:** `backend/learning/feedback_engine.py`

#### 3.1 Motor de aprendizaje

```python
# backend/learning/feedback_engine.py
class FeedbackEngine:
    def record_reconciliation_feedback(self, event_data):
        """Registra feedback de conciliación para aprendizaje"""
        event = ReconTrainingEvent(
            source_json=json.dumps(event_data['source']),
            candidates_json=json.dumps(event_data['candidates']),
            chosen_json=json.dumps(event_data['chosen']),
            accepted=event_data['accepted'],
            confidence=event_data['confidence'],
            reasons=','.join(event_data['reasons'])
        )
        db.session.add(event)
        
        # Actualizar aliases y patrones
        self._update_aliases_from_feedback(event_data)
        
        db.session.commit()
    
    def _update_aliases_from_feedback(self, event_data):
        """Actualiza aliases basado en feedback positivo"""
        if event_data['accepted'] and event_data['confidence'] > 0.85:
            # Extraer patrones de descripción exitosos
            pattern = self._extract_pattern(event_data['source']['description'])
            if pattern:
                alias = ReconAlias(
                    rut=event_data['chosen']['rut'],
                    pattern=pattern,
                    confidence=event_data['confidence'],
                    hits=1
                )
                db.session.merge(alias)
```

## APIs Requeridas

### Conciliación Bancaria
- `POST /api/conciliacion/sugerencias` - Sugerencias inteligentes
- `POST /api/conciliacion/preview` - Vista previa de conciliación  
- `POST /api/conciliacion/confirmar` - Confirmar conciliación
- `GET /api/conciliacion/events` - Stream SSE de eventos

### Matching PO↔Factura
- `POST /api/ap-match/suggestions` - Sugerencias de matching
- `POST /api/ap-match/preview` - Preview de asociación
- `POST /api/ap-match/confirm` - Confirmar matching

## Componentes Frontend

### Conciliación
- `ReconcileButton` - Botón contextual en todas las vistas
- `ReconcileDrawer` - Panel lateral de conciliación
- `ReasonChips` - Chips explicativos de razones

### Matching
- `APMatchDrawer` - Panel de asociación PO-Factura
- `ThreeWayStatus` - Semáforos de validación 3-way

## Criterios de Aceptación

- [ ] Botón "Conciliar" presente en facturas, cartola, pagos, gastos
- [ ] Motor de conciliación con explicabilidad (reasons)
- [ ] Sistema de matching PO-Factura con validaciones 3-way
- [ ] Aprendizaje continuo actualizando aliases automáticamente
- [ ] Auto-conciliación segura para casos de alta confianza
- [ ] UI contextual sin fricción (drawer lateral)
- [ ] Logging completo de eventos para auditoría

## Riesgos y Mitigaciones

- **Riesgo:** Falsos positivos en auto-conciliación
- **Mitigación:** Umbrales conservadores (≥0.97) y logging exhaustivo

- **Riesgo:** Performance con grandes volúmenes
- **Mitigación:** Índices optimizados y caché de candidatos

## Estimación: 18 días

## Dependencias

- Sprint 2 completado (ventas y EP)
- Tablas de conciliación y matching creadas
- Motor de validaciones funcionando