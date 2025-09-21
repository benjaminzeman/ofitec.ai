/**
 * ofitec.ai - JavaScript Unificado
 * ============================================
 * Fusión de funcionalidades:
 * - CEO Copilot del plataforma
 * - Navegación SPA
 * - Carga de datos reales del Web plataforma
 * - UX profesional
 */

// Variables globales
let copilotPanelOpen = false;
let currentPage = window.location.pathname;
let dataCache = {};

// =============================================================================
// INICIALIZACIÓN DEL plataforma
// =============================================================================

function initPortal() {
    console.log('🔥 ofitec.ai iniciado');
    
    // Configurar eventos
    setupEventListeners();
    
    // Cargar datos iniciales según la página
    loadPageData();
    
    // Configurar navegación SPA
    setupSPANavigation();
    
    // Configurar CEO Copilot
    setupCopilot();
    
    console.log('✅ ofitec.ai completamente cargado');
}

function setupEventListeners() {
    // Enter en input de copilot
    const copilotInput = document.getElementById('copilot-query');
    if (copilotInput) {
        copilotInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendCopilotQuery();
            }
        });
    }
    
    // Click en enlaces de navegación
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[href^="/"]');
        if (link && !link.hasAttribute('target')) {
            e.preventDefault();
            navigateToPage(link.getAttribute('href'));
        }
    });
    
    // Resize window
    window.addEventListener('resize', function() {
        adjustLayoutForScreen();
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt + C para toggle Copilot
        if (e.altKey && e.key === 'c') {
            e.preventDefault();
            toggleCopilot();
        }
        
        // Escape para cerrar Copilot
        if (e.key === 'Escape' && copilotPanelOpen) {
            toggleCopilot();
        }
    });
}

function adjustLayoutForScreen() {
    const isMobile = window.innerWidth <= 768;
    const copilotPanel = document.getElementById('copilot-panel');
    
    if (copilotPanel && isMobile && copilotPanelOpen) {
        copilotPanel.style.width = '100%';
        copilotPanel.style.right = copilotPanelOpen ? '0' : '-100%';
    }
}

// =============================================================================
// NAVEGACIÓN SPA
// =============================================================================

function setupSPANavigation() {
    // Manejar botones del navegador
    window.addEventListener('popstate', function(e) {
        const path = window.location.pathname;
        loadPageContent(path, false);
    });
}

function navigateToPage(url) {
    if (url === currentPage) return;
    
    // Actualizar URL sin recargar
    history.pushState(null, '', url);
    
    // Cargar contenido
    loadPageContent(url, true);
    
    // Actualizar navegación activa
    updateActiveNavigation(url);
    
    currentPage = url;
}

function loadPageContent(url, showTransition = true) {
    if (showTransition) {
        showPageTransition();
    }
    
    // Simular carga de contenido dinámico
    setTimeout(() => {
        loadPageData();
        if (showTransition) {
            hidePageTransition();
        }
    }, 300);
}

function updateActiveNavigation(url) {
    // Remover clase active de todos los links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Agregar clase active al link actual
    const activeLink = document.querySelector(`a[href="${url}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

function showPageTransition() {
    const mainContent = document.querySelector('.main-content') || document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('page-exit');
        setTimeout(() => {
            mainContent.classList.remove('page-exit');
            mainContent.classList.add('page-enter');
        }, 150);
    }
}

function hidePageTransition() {
    const mainContent = document.querySelector('.main-content') || document.querySelector('main');
    if (mainContent) {
        mainContent.classList.remove('page-enter');
        mainContent.classList.add('page-enter-active');
    }
}

// =============================================================================
// CEO COPILOT
// =============================================================================

function setupCopilot() {
    // Agregar mensaje de bienvenida si no existe
    const messagesContainer = document.getElementById('copilot-messages');
    if (messagesContainer && messagesContainer.children.length === 0) {
        addWelcomeMessage();
    }
}

function toggleCopilot() {
    const panel = document.getElementById('copilot-panel');
    if (panel) {
        copilotPanelOpen = !copilotPanelOpen;
        
        if (copilotPanelOpen) {
            panel.classList.add('active');
            panel.style.display = 'flex';
            panel.style.animation = 'slideInFromRight 0.3s ease-out';
        } else {
            panel.style.animation = 'slideOutToRight 0.3s ease-out';
            setTimeout(() => {
                panel.classList.remove('active');
                if (window.innerWidth > 768) {
                    panel.style.display = 'none';
                }
            }, 300);
        }
        
        // Focus en input si se abre
        if (copilotPanelOpen) {
            setTimeout(() => {
                const input = document.getElementById('copilot-query');
                if (input) input.focus();
            }, 350);
        }
    }
}

function addWelcomeMessage() {
    const welcomeMessage = `
        <div class="message">
            <div class="copilot-message">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <p>¡Hola! Soy tu CEO Copilot de OFITEC 🤖</p>
                    <p>Ahora con acceso completo a datos reales de Chipax. Puedo ayudarte con:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>📊 Análisis financiero detallado</li>
                        <li>🏦 Conciliación bancaria inteligente</li>
                        <li>📈 Predicciones de flujo de caja</li>
                        <li>⚠️ Alertas de riesgo proactivas</li>
                        <li>💡 Recomendaciones estratégicas</li>
                    </ul>
                    <p>¿Qué te gustaría analizar?</p>
                </div>
            </div>
        </div>
    `;
    
    const container = document.getElementById('copilot-messages');
    if (container) {
        container.innerHTML = welcomeMessage;
    }
}

function sendCopilotQuery() {
    const input = document.getElementById('copilot-query');
    const query = input.value.trim();
    
    if (!query) return;
    
    // Mostrar loading
    showLoading('CEO Copilot procesando...');
    
    // Agregar mensaje del usuario
    addMessage('user', query);
    
    // Limpiar input
    input.value = '';
    
    // Llamada a API del CEO Copilot
    fetch('/api/copilot/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            query: query,
            context: {
                current_page: currentPage,
                timestamp: new Date().toISOString()
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            addMessage('copilot', data.data.response);
            
            // Si hay datos reales mejorados, mostrar indicador
            if (data.data.enhanced_with_real_data) {
                addMessage('system', '✅ Respuesta enriquecida con datos reales de Chipax');
            }
        } else {
            addMessage('copilot', '❌ Lo siento, hay un problema con el servidor. Intenta de nuevo.');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error en CEO Copilot:', error);
        addMessage('copilot', '🔌 Error de conexión. Verifica que el servidor esté funcionando.');
    });
}

function addMessage(type, content) {
    const container = document.getElementById('copilot-messages');
    if (!container) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    if (type === 'copilot') {
        messageDiv.innerHTML = `
            <div class="copilot-message">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    ${formatCopilotMessage(content)}
                </div>
            </div>
        `;
    } else if (type === 'system') {
        messageDiv.innerHTML = `
            <div class="system-message" style="text-align: center; padding: 10px; background: rgba(0, 212, 170, 0.1); border-radius: 8px; color: #00d4aa; font-size: 0.8rem;">
                ${content}
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="user-message" style="display: flex; justify-content: flex-end;">
                <div class="message-content user">
                    ${content}
                </div>
            </div>
        `;
    }
    
    container.appendChild(messageDiv);
    
    // Scroll al final con animación suave
    container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
    });
}

function formatCopilotMessage(content) {
    // Formatear mensaje del copilot con markdown básico
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/📊|📈|📉|💰|🏦|⚠️|💡|✅|❌|🔍|📋/g, '<span style="font-size: 1.2em;">$&</span>');
}

// =============================================================================
// CARGA DE DATOS
// =============================================================================

function loadPageData() {
    const path = window.location.pathname;
    
    switch(path) {
        case '/':
            loadDashboardData();
            break;
        case '/home-executive':
            loadExecutiveKPIs();
            break;
        case '/conciliacion':
            loadConciliacionData();
            break;
        case '/facturas-venta':
            loadFacturasVenta();
            break;
        case '/facturas-compra':
            loadFacturasCompra();
            break;
        case '/impuestos':
            loadImpuestosData();
            break;
        case '/cartola-bancaria':
            loadCartolaData();
            break;
        case '/finanzas':
            loadFinancialAnalytics();
            break;
        default:
            console.log(`Página ${path} cargada sin datos específicos`);
    }
}

function loadDashboardData() {
    if (dataCache.dashboard && isDataFresh('dashboard')) {
        updateDashboard(dataCache.dashboard);
        return;
    }
    
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                dataCache.dashboard = {
                    data: data.data,
                    timestamp: Date.now()
                };
                updateDashboard(data.data);
            }
        })
        .catch(error => {
            console.error('Error cargando dashboard:', error);
            showErrorAlert('Error cargando datos del dashboard');
        });
}

function loadExecutiveKPIs() {
    fetch('/api/kpis/executive')
        .then(response => response.json())
        .then(data => {
            updateExecutiveKPIs(data);
        })
        .catch(error => {
            console.error('Error cargando KPIs ejecutivos:', error);
        });
}

function loadConciliacionData() {
    Promise.all([
        fetch('/api/cartola/movimientos'),
        fetch('/api/copilot/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: 'Analiza la conciliación bancaria y detecta discrepancias' 
            })
        })
    ])
    .then(responses => Promise.all(responses.map(r => r.json())))
    .then(([movimientos, analisis]) => {
        updateConciliacionView(movimientos, analisis);
    })
    .catch(error => {
        console.error('Error cargando datos de conciliación:', error);
    });
}

function loadFacturasVenta() {
    fetch('/api/facturas/venta')
        .then(response => response.json())
        .then(data => {
            updateFacturasView('venta', data);
        })
        .catch(error => {
            console.error('Error cargando facturas de venta:', error);
        });
}

function loadFacturasCompra() {
    fetch('/api/facturas/compra')
        .then(response => response.json())
        .then(data => {
            updateFacturasView('compra', data);
        })
        .catch(error => {
            console.error('Error cargando facturas de compra:', error);
        });
}

function loadImpuestosData() {
    fetch('/api/impuestos/resumen')
        .then(response => response.json())
        .then(data => {
            updateImpuestosView(data);
        })
        .catch(error => {
            console.error('Error cargando datos de impuestos:', error);
        });
}

function loadCartolaData() {
    fetch('/api/cartola/movimientos')
        .then(response => response.json())
        .then(data => {
            updateCartolaView(data);
        })
        .catch(error => {
            console.error('Error cargando cartola bancaria:', error);
        });
}

function loadFinancialAnalytics() {
    fetch('/api/analytics/financial')
        .then(response => response.json())
        .then(data => {
            updateFinancialView(data);
        })
        .catch(error => {
            console.error('Error cargando análisis financiero:', error);
        });
}

// =============================================================================
// ACTUALIZACIÓN DE VISTAS
// =============================================================================

function updateDashboard(data) {
    // Actualizar KPIs
    if (data.kpis) {
        updateElement('proyectos-activos', data.kpis.proyectos_activos);
        updateElement('presupuesto-total', `$${(data.kpis.presupuesto_total / 1000000).toFixed(1)}M`);
        updateElement('avance-promedio', `${data.kpis.avance_promedio}%`);
        updateElement('cronograma', `${data.kpis.desviacion_cronograma} días`);
        updateElement('margen', `${data.kpis.margen_operacional}%`);
        updateElement('liquidez', `${data.kpis.liquidez_dias} días`);
    }
    
    // Actualizar health score
    if (data.health_score) {
        updateHealthScore(data.health_score);
    }
    
    // Actualizar alertas
    if (data.alerts) {
        updateAlerts(data.alerts);
    }
    
    // Actualizar predicciones
    if (data.predictions) {
        updatePredictions(data.predictions);
    }
    
    // Actualizar recomendaciones
    if (data.recommendations) {
        updateRecommendations(data.recommendations);
    }
    
    // Indicar fuente de datos
    if (data.data_source) {
        updateDataSourceIndicator(data.data_source);
    }
}

function updateExecutiveKPIs(data) {
    if (data.data_real) {
        // Mostrar indicador de datos reales
        showDataRealIndicator();
    }
    
    updateElement('margen-bruto', `${data.margen_bruto}%`);
    updateElement('dias-caja', `${data.dias_caja} días`);
    updateElement('backlog', `$${data.backlog_m}M`);
    updateElement('iva-pagar', `$${data.iva_pagar}M`);
    updateElement('cashflow-gap', `$${data.cashflow_gap}M`);
    updateElement('obras-activas', data.obras_activas);
}

function updateConciliacionView(movimientos, analisis) {
    // Actualizar tabla de movimientos
    const tbody = document.querySelector('#movimientos-table tbody');
    if (tbody && movimientos.movimientos) {
        tbody.innerHTML = '';
        movimientos.movimientos.slice(0, 20).forEach(mov => {
            const row = createMovimientoRow(mov);
            tbody.appendChild(row);
        });
    }
    
    // Mostrar análisis de IA si está disponible
    if (analisis.success) {
        showConciliacionAnalysis(analisis.data.response);
    }
}

function updateFacturasView(tipo, data) {
    const container = document.getElementById(`facturas-${tipo}-container`);
    if (container && data.data) {
        // Actualizar resumen
        const summary = data.data.summary;
        if (summary) {
            updateFacturasSummary(tipo, summary);
        }
        
        // Actualizar tabla
        updateFacturasTable(tipo, data.data.invoices || []);
    }
}

function updateImpuestosView(data) {
    if (data.success && data.data) {
        updateElement('iva-por-pagar', formatCurrency(data.data.iva_por_pagar));
        updateElement('retenciones', formatCurrency(data.data.retenciones));
        updateElement('renta-provisional', formatCurrency(data.data.renta_provisional));
    }
}

function updateCartolaView(data) {
    if (data.success && data.movimientos) {
        const tbody = document.querySelector('#cartola-table tbody');
        if (tbody) {
            tbody.innerHTML = '';
            data.movimientos.slice(0, 50).forEach(mov => {
                const row = createCartolaRow(mov);
                tbody.appendChild(row);
            });
        }
    }
}

function updateFinancialView(data) {
    if (data.success) {
        // Actualizar alertas financieras
        if (data.data.alertas) {
            updateFinancialAlerts(data.data.alertas);
        }
        
        // Actualizar KPIs financieros
        if (data.data.kpis) {
            updateFinancialKPIs(data.data.kpis);
        }
        
        // Mostrar datos reales si están disponibles
        if (data.data.real_data) {
            showRealDataEnhancement(data.data.real_data);
        }
    }
}

// =============================================================================
// UTILIDADES DE VISTA
// =============================================================================

function updateElement(id, text, html = null) {
    const element = document.getElementById(id);
    if (element) {
        if (html) {
            element.innerHTML = html;
        } else {
            element.textContent = text;
        }
        
        // Añadir animación de actualización
        element.classList.add('updated');
        setTimeout(() => element.classList.remove('updated'), 1000);
    }
}

function updateHealthScore(score) {
    const element = document.getElementById('health-score');
    if (element) {
        const scoreValue = element.querySelector('.score-value');
        if (scoreValue) {
            scoreValue.textContent = score;
            
            // Actualizar color según score
            const scoreCircle = element.closest('.score-circle');
            if (scoreCircle) {
                let color = score >= 80 ? 'var(--success-color)' : 
                           score >= 60 ? 'var(--warning-color)' : 
                           'var(--danger-color)';
                scoreValue.style.color = color;
            }
        }
    }
}

function updateAlerts(alerts) {
    const container = document.getElementById('financial-alerts');
    if (!container) return;
    
    container.innerHTML = '';
    
    alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${alert.prioridad}`;
        alertDiv.innerHTML = `
            <h4>${alert.mensaje}</h4>
            <p>${alert.recomendacion || ''}</p>
            <span class="badge badge-${alert.prioridad}">${alert.prioridad.toUpperCase()}</span>
        `;
        container.appendChild(alertDiv);
    });
}

function updatePredictions(predictions) {
    const container = document.getElementById('ai-predictions');
    if (!container) return;
    
    container.innerHTML = '';
    
    predictions.forEach(pred => {
        const predDiv = document.createElement('div');
        predDiv.className = 'prediction-item';
        predDiv.innerHTML = `
            <h4>${pred.mensaje}</h4>
            <p><strong>Acción sugerida:</strong> ${pred.accion_sugerida}</p>
            <div class="prediction-meta">
                <span class="badge badge-info">Probabilidad: ${Math.round(pred.probabilidad * 100)}%</span>
                <span class="badge badge-warning">Impacto: ${pred.impacto}</span>
            </div>
        `;
        container.appendChild(predDiv);
    });
}

function updateRecommendations(recommendations) {
    const container = document.getElementById('ai-recommendations');
    if (!container) return;
    
    container.innerHTML = '';
    
    recommendations.forEach(rec => {
        const li = document.createElement('li');
        li.textContent = rec;
        li.style.marginBottom = '8px';
        container.appendChild(li);
    });
}

function createMovimientoRow(movimiento) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${movimiento.fecha}</td>
        <td>${movimiento.descripcion}</td>
        <td>${movimiento.referencia}</td>
        <td>${formatCurrency(movimiento.cargo)}</td>
        <td>${formatCurrency(movimiento.abono)}</td>
        <td>
            <span class="badge badge-${getEstadoBadgeClass(movimiento.estado)}">
                ${movimiento.estado}
            </span>
        </td>
    `;
    return row;
}

function createCartolaRow(movimiento) {
    return createMovimientoRow(movimiento);
}

// =============================================================================
// UTILIDADES GENERALES
// =============================================================================

function showLoading(message = 'Cargando...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        const spinner = overlay.querySelector('.loading-spinner p');
        if (spinner) spinner.textContent = message;
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showErrorAlert(message) {
    // Crear alert temporal
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger';
    alert.style.position = 'fixed';
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '10000';
    alert.style.maxWidth = '400px';
    alert.innerHTML = `
        <strong>Error:</strong> ${message}
        <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; color: inherit; font-size: 18px;">&times;</button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

function formatCurrency(amount) {
    if (!amount || amount === 0) return '$0';
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency: 'CLP'
    }).format(amount);
}

function getEstadoBadgeClass(estado) {
    switch(estado) {
        case 'conciliado': return 'success';
        case 'pendiente': return 'warning';
        case 'observado': return 'danger';
        default: return 'info';
    }
}

function isDataFresh(key, maxAge = 30000) { // 30 segundos
    if (!dataCache[key]) return false;
    return (Date.now() - dataCache[key].timestamp) < maxAge;
}

function showDataRealIndicator() {
    const indicator = document.createElement('div');
    indicator.innerHTML = '✅ Datos reales de Chipax';
    indicator.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: var(--success-color);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.8rem;
        z-index: 1000;
        animation: slideInFromRight 0.5s ease-out;
    `;
    
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        indicator.remove();
    }, 3000);
}

function updateDataSourceIndicator(source) {
    let message = '';
    let color = '';
    
    switch(source) {
        case 'real_data_enhanced':
            message = '🔥 Datos reales + IA mejorada';
            color = 'var(--success-color)';
            break;
        case 'copilot_only':
            message = '🤖 CEO Copilot activo';
            color = 'var(--info-color)';
            break;
        default:
            message = '📊 Datos simulados';
            color = 'var(--warning-color)';
    }
    
    const indicator = document.getElementById('data-source-indicator');
    if (indicator) {
        indicator.textContent = message;
        indicator.style.color = color;
    }
}

// =============================================================================
// AUTO-REFRESH Y EVENTOS PERIÓDICOS
// =============================================================================

function setupAutoRefresh() {
    // Auto-refresh del dashboard cada 30 segundos
    if (window.location.pathname === '/') {
        setInterval(() => {
            loadDashboardData();
        }, 30000);
    }
    
    // Auto-refresh de KPIs ejecutivos cada 60 segundos
    if (window.location.pathname === '/home-executive') {
        setInterval(() => {
            loadExecutiveKPIs();
        }, 60000);
    }
}

// =============================================================================
// INICIALIZACIÓN
// =============================================================================

// Auto-inicializar cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    initPortal();
    setupAutoRefresh();
});

// Manejar navegación del navegador
window.addEventListener('popstate', function(e) {
    loadPageContent(window.location.pathname);
});

// Export para uso global
window.OfitecPortalFusion = {
    init: initPortal,
    navigateToPage,
    toggleCopilot,
    sendCopilotQuery,
    loadPageData,
    showLoading,
    hideLoading
};

console.log('🔥 ofitec.ai JavaScript cargado');

// CSS adicional para animaciones
const additionalCSS = `
    @keyframes slideOutToRight {
        0% { transform: translateX(0); opacity: 1; }
        100% { transform: translateX(100%); opacity: 0; }
    }
    
    .updated {
        animation: highlightUpdate 1s ease-out;
    }
    
    @keyframes highlightUpdate {
        0% { background-color: rgba(0, 212, 170, 0.3); }
        100% { background-color: transparent; }
    }
`;

// Agregar CSS dinámico
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);





