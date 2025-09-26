# SPRINT 4: Portal Cliente y Analítica Avanzada

## Objetivos

- Implementar portal cliente completo con autenticación y roles
- Desarrollar módulo de analítica avanzada con predicciones ML
- Establecer copilots conversacionales por módulo
- Implementar simulaciones Monte Carlo para cashflow

## Tareas Priority 1

### 1. Portal Cliente y Gestión de Roles

**Archivos:** `backend/auth/`, `frontend/app/cliente/`, `backend/models/usuarios.py`

#### 1.1 Sistema de Autenticación

```python
# backend/auth/auth_service.py
class AuthService:
    def authenticate_user(self, email, password=None, provider='local'):
        """Autenticación con soporte SSO"""
        if provider == 'local':
            return self._authenticate_local(email, password)
        elif provider == 'google':
            return self._authenticate_google(email)
        elif provider == 'azure':
            return self._authenticate_azure(email)
    
    def create_session(self, user_id, ip_address, user_agent):
        """Crear sesión JWT con auditoría"""
        jti = str(uuid.uuid4())
        payload = {
            'user_id': user_id,
            'jti': jti,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        # Registrar sesión para auditoría
        session = SesionActiva(
            usuario_id=user_id,
            jti=jti,
            issued_at=datetime.utcnow(),
            expires_at=payload['exp'],
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        db.session.commit()
        
        return token
```

#### 1.2 Modelo de permisos granulares

```python
# backend/models/usuarios.py
class Usuario(db.Model):
    __tablename__ = 'usuarios_sistema'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    auth_provider = db.Column(db.String(20), nullable=False)  # local, google, azure
    password_hash = db.Column(db.Text)
    mfa_enabled = db.Column(db.Boolean, default=False)
    rol_principal = db.Column(db.String(50), nullable=False)  # Admin, CFO, PM, Cliente, etc.
    estado = db.Column(db.String(20), default='activo')
    allowed_project_ids = db.Column(db.JSON)  # para rol Cliente
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

class RolPermiso(db.Model):
    __tablename__ = 'roles_permisos'
    id = db.Column(db.Integer, primary_key=True)
    rol = db.Column(db.String(50), nullable=False)
    recurso = db.Column(db.String(100), nullable=False)
    puede_leer = db.Column(db.Boolean, default=False)
    puede_crear = db.Column(db.Boolean, default=False)
    puede_actualizar = db.Column(db.Boolean, default=False)
    puede_eliminar = db.Column(db.Boolean, default=False)
```

#### 1.3 Portal Cliente Frontend

```tsx
// frontend/app/cliente/page.tsx
export default function ClientPortalPage() {
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [documents, setDocuments] = useState([]);
  
  useEffect(() => {
    loadClientData();
  }, []);
  
  const loadClientData = async () => {
    const userData = await fetchCurrentUser();
    setUser(userData);
    
    if (userData?.allowed_project_ids) {
      const projectsData = await fetchClientProjects(userData.allowed_project_ids);
      setProjects(projectsData);
      
      const docsData = await fetchClientDocuments(userData.allowed_project_ids);
      setDocuments(docsData);
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-50">
      <ClientHeader user={user} />
      
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Resumen de Proyectos */}
          <div className="lg:col-span-2">
            <ProjectsSummary projects={projects} />
          </div>
          
          {/* Panel lateral */}
          <div className="space-y-6">
            <PaymentStatus projects={projects} />
            <RecentDocuments documents={documents} />
            <MessagingWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 2. Analítica Avanzada con ML

**Archivos:** `backend/analytics/`, `backend/ml/prediction_engine.py`

#### 2.1 Motor de Predicciones

```python
# backend/ml/prediction_engine.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

class PredictionEngine:
    def __init__(self):
        self.cost_model = None
        self.timeline_model = None
        self.risk_model = None
    
    def train_cost_predictions(self):
        """Entrenar modelo de predicción de costos"""
        # Cargar datos históricos desde vistas canónicas
        df = self._load_cost_training_data()
        
        # Feature engineering
        features = self._extract_cost_features(df)
        target = df['actual_cost']
        
        # Entrenar modelo
        self.cost_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.cost_model.fit(features, target)
        
        # Guardar modelo
        joblib.dump(self.cost_model, 'models/cost_prediction.joblib')
        
        return self._evaluate_model(self.cost_model, features, target)
    
    def predict_project_cost(self, project_id, horizon_months=3):
        """Predecir costo futuro de proyecto"""
        if not self.cost_model:
            self.cost_model = joblib.load('models/cost_prediction.joblib')
        
        # Preparar features del proyecto
        project_data = self._get_project_features(project_id)
        
        # Generar predicción con intervalos de confianza
        prediction = self.cost_model.predict([project_data])[0]
        
        # Calcular intervalo de confianza (usando quantile regression)
        confidence_interval = self._calculate_confidence_interval(project_data, prediction)
        
        # Guardar predicción en BD
        pred_record = PrediccionML(
            project_id=project_id,
            tipo='costo',
            valor_predicho=prediction,
            intervalo_confianza=confidence_interval,
            score=self._calculate_prediction_score(project_data),
            modelo_version='cost_v1.0'
        )
        db.session.add(pred_record)
        db.session.commit()
        
        return {
            'predicted_cost': prediction,
            'confidence_interval': confidence_interval,
            'horizon_months': horizon_months,
            'model_version': 'cost_v1.0'
        }
```

#### 2.2 Simulaciones Monte Carlo

```python
# backend/analytics/monte_carlo.py
import numpy as np
from scipy import stats

class MonteCarloSimulation:
    def simulate_project_cashflow(self, project_id, scenarios=10000):
        """Simulación Monte Carlo de cashflow por proyecto"""
        project_data = self._get_project_baseline(project_id)
        
        # Variables de entrada con distribuciones
        budget_dist = stats.norm(project_data['budget'], project_data['budget'] * 0.15)
        timeline_dist = stats.norm(project_data['planned_months'], 2)
        collection_rate_dist = stats.beta(8, 2)  # optimista en cobranza
        
        results = []
        for _ in range(scenarios):
            # Samplear variables aleatorias
            simulated_budget = budget_dist.rvs()
            simulated_timeline = max(1, timeline_dist.rvs())
            simulated_collection_rate = collection_rate_dist.rvs()
            
            # Calcular cashflow neto mensual
            monthly_outflow = simulated_budget / simulated_timeline
            monthly_inflow = project_data['contracted_value'] / simulated_timeline * simulated_collection_rate
            net_cashflow = monthly_inflow - monthly_outflow
            
            # Acumular resultado
            results.append({
                'net_monthly_cashflow': net_cashflow,
                'total_margin': (project_data['contracted_value'] * simulated_collection_rate) - simulated_budget,
                'timeline_months': simulated_timeline
            })
        
        # Estadísticas resumidas
        cashflows = [r['net_monthly_cashflow'] for r in results]
        margins = [r['total_margin'] for r in results]
        
        return {
            'scenarios': scenarios,
            'cashflow_stats': {
                'mean': np.mean(cashflows),
                'std': np.std(cashflows),
                'p5': np.percentile(cashflows, 5),
                'p50': np.percentile(cashflows, 50),
                'p95': np.percentile(cashflows, 95)
            },
            'margin_stats': {
                'mean': np.mean(margins),
                'var': np.percentile(margins, 5),  # Value at Risk
                'probability_loss': sum(1 for m in margins if m < 0) / scenarios
            }
        }
```

### 3. Copilots Conversacionales

**Archivos:** `backend/copilots/`, `frontend/components/CopilotWidget.tsx`

#### 3.1 Copilot Base

```python
# backend/copilots/base_copilot.py
from openai import OpenAI

class BaseCopilot:
    def __init__(self, domain, system_prompt):
        self.domain = domain
        self.system_prompt = system_prompt
        self.client = OpenAI()
    
    def answer_question(self, question, user_context):
        """Responder pregunta con contexto específico del dominio"""
        # Obtener datos relevantes desde vistas canónicas
        context_data = self._get_domain_context(user_context)
        
        # Construir prompt con contexto
        full_prompt = f"""
        {self.system_prompt}
        
        Contexto de datos (solo usa información de aquí):
        {json.dumps(context_data, indent=2)}
        
        Pregunta del usuario: {question}
        
        Responde de forma concisa y precisa, citando números específicos cuando sea relevante.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": full_prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content

class FinancesCopilot(BaseCopilot):
    def __init__(self):
        super().__init__(
            domain='finanzas',
            system_prompt="""Eres un asistente especializado en finanzas de construcción.
            Responde preguntas sobre costos, presupuestos, flujo de caja, aging y rentabilidad.
            Usa solo los datos proporcionados en el contexto."""
        )
    
    def _get_domain_context(self, user_context):
        """Obtener contexto específico de finanzas"""
        with db_conn() as conn:
            # Control financiero
            control_data = self._query_control_financiero(conn, user_context.get('project_id'))
            
            # Aging AR/AP
            aging_data = self._query_aging_summary(conn)
            
            # Cashflow reciente
            cashflow_data = self._query_recent_cashflow(conn)
            
            return {
                'control_financiero': control_data,
                'aging': aging_data,
                'cashflow': cashflow_data,
                'fecha_consulta': datetime.now().isoformat()
            }
```

#### 3.2 Widget Frontend

```tsx
// frontend/components/CopilotWidget.tsx
export default function CopilotWidget({ domain = 'finanzas' }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage = { role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    
    try {
      const response = await fetch('/api/copilot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain,
          question: input,
          user_context: {
            project_id: getCurrentProjectId(),
            user_role: getCurrentUserRole()
          }
        })
      });
      
      const data = await response.json();
      const assistantMessage = { 
        role: 'assistant', 
        content: data.answer, 
        timestamp: new Date() 
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="bg-white rounded-2xl border p-4 h-96 flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 bg-lime-100 rounded-full flex items-center justify-center">
          🤖
        </div>
        <span className="font-medium">Copilot {domain.charAt(0).toUpperCase() + domain.slice(1)}</span>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-3">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl ${
              msg.role === 'user' 
                ? 'bg-lime-600 text-white' 
                : 'bg-slate-100 text-slate-900'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 p-3 rounded-2xl">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Pregunta sobre finanzas..."
          className="flex-1 border rounded-lg px-3 py-2"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-lime-600 text-white rounded-lg disabled:opacity-50"
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
```

## APIs Requeridas

### Autenticación y Usuarios
- `POST /api/auth/login` - Login con SSO o local
- `POST /api/auth/mfa/verify` - Verificar MFA  
- `POST /api/users/invite` - Enviar invitaciones
- `GET /api/users` - Gestión de usuarios (admin)
- `PATCH /api/users/:id` - Actualizar roles/permisos

### Portal Cliente
- `GET /api/portal/projects` - Proyectos del cliente
- `GET /api/portal/documents` - Documentos filtrados
- `GET /api/portal/financial` - Estados financieros
- `POST /api/portal/messages` - Mensajería

### Analítica y Predicciones
- `GET /api/analytics/predictions` - Predicciones ML
- `POST /api/analytics/simulate` - Simulaciones Monte Carlo
- `GET /api/analytics/trends` - Tendencias históricas

### Copilots
- `POST /api/copilot/ask` - Preguntas conversacionales
- `GET /api/copilot/history` - Historial de conversaciones

## Criterios de Aceptación

- [ ] Sistema de autenticación con SSO funcionando
- [ ] Portal cliente con proyectos, documentos y estados financieros
- [ ] Gestión granular de roles y permisos por recurso
- [ ] Predicciones ML de costos y plazos con intervalos de confianza
- [ ] Simulaciones Monte Carlo para análisis de riesgos
- [ ] Copilots conversacionales por módulo (finanzas, proyectos, HSE)
- [ ] MFA obligatorio para roles críticos (Admin, CFO)
- [ ] Auditoría completa de accesos y cambios

## Riesgos y Mitigaciones

- **Riesgo:** Calidad de predicciones ML con pocos datos
- **Mitigación:** Validación cruzada y intervalos de confianza amplios

- **Riesgo:** Copilots dando información incorrecta
- **Mitigación:** Restricción a datos contextuales y disclaimers

## Estimación: 22 días

## Dependencias

- Sprint 3 completado (conciliación y matching)
- Datos históricos suficientes para entrenamiento ML
- Credenciales SSO configuradas