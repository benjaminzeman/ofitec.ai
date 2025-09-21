/**
 * ofitec.ai - Data Service
 * Manejo de datos desde SQLite con 34,428 registros integrados
 */

/**
 * Configuración de base de datos
 */
const DB_CONFIG = {
  database: 'ofitec_dev.db',
  endpoint: '/api/portal/data', // Endpoint Odoo para consultas SQL
  cache: new Map(),
  cacheTimeout: 5 * 60 * 1000 // 5 minutos
};

/**
 * Ejecutar query SQL contra la base de datos SQLite
 */
async function executeQuery(query, params = []) {
  try {
    const cacheKey = `${query}_${JSON.stringify(params)}`;
    const cached = DB_CONFIG.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < DB_CONFIG.cacheTimeout) {
      return cached.data;
    }
    
    const response = await fetch(DB_CONFIG.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        query,
        params,
        database: DB_CONFIG.database
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // Cache result
    DB_CONFIG.cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });
    
    return result;
    
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
}

/**
 * Service para datos financieros (Cartola Bancaria)
 */
export const FinanceService = {
  /**
   * Obtener resumen financiero
   */
  async getResumenFinanciero() {
    const query = `
      SELECT 
        COUNT(*) as total_ordenes,
        SUM(CAST(net_amount AS REAL)) as monto_total,
        AVG(CAST(net_amount AS REAL)) as promedio_orden,
        COUNT(DISTINCT provider_rut) as proveedores_activos
      FROM orders 
      WHERE net_amount IS NOT NULL AND net_amount != ''
    `;
    
    const result = await executeQuery(query);
    return result[0] || {};
  },
  
  /**
   * Obtener flujo de caja por período
   */
  async getFlujoCompras(fechaInicio, fechaFin) {
    const query = `
      SELECT 
        strftime('%Y-%m', order_date) as periodo,
        COUNT(*) as cantidad_ordenes,
        SUM(CAST(net_amount AS REAL)) as monto_total,
        COUNT(DISTINCT provider_rut) as proveedores
      FROM orders 
      WHERE order_date BETWEEN ? AND ?
        AND net_amount IS NOT NULL 
        AND net_amount != ''
      GROUP BY strftime('%Y-%m', order_date)
      ORDER BY periodo DESC
    `;
    
    return await executeQuery(query, [fechaInicio, fechaFin]);
  },
  
  /**
   * Obtener transacciones recientes
   */
  async getTransaccionesRecientes(limit = 50) {
    const query = `
      SELECT 
        o.order_number,
        o.order_date,
        p.name as proveedor_nombre,
        p.rut as proveedor_rut,
        o.net_amount,
        o.status
      FROM orders o
      LEFT JOIN providers p ON o.provider_rut = p.rut
      WHERE o.net_amount IS NOT NULL AND o.net_amount != ''
      ORDER BY o.order_date DESC
      LIMIT ?
    `;
    
    return await executeQuery(query, [limit]);
  }
};

/**
 * Service para gestión de proveedores
 */
export const ProviderService = {
  /**
   * Obtener todos los proveedores con estadísticas
   */
  async getProveedores() {
    const query = `
      SELECT 
        p.*,
        COUNT(o.id) as total_ordenes,
        SUM(CAST(o.net_amount AS REAL)) as monto_total,
        MAX(o.order_date) as ultima_orden
      FROM providers p
      LEFT JOIN orders o ON p.rut = o.provider_rut
      GROUP BY p.id
      ORDER BY monto_total DESC
    `;
    
    return await executeQuery(query);
  },
  
  /**
   * Obtener proveedor por RUT
   */
  async getProveedorPorRUT(rut) {
    const query = `
      SELECT 
        p.*,
        COUNT(o.id) as total_ordenes,
        SUM(CAST(o.net_amount AS REAL)) as monto_total,
        AVG(CAST(o.net_amount AS REAL)) as promedio_orden,
        MIN(o.order_date) as primera_orden,
        MAX(o.order_date) as ultima_orden
      FROM providers p
      LEFT JOIN orders o ON p.rut = o.provider_rut
      WHERE p.rut = ?
      GROUP BY p.id
    `;
    
    const result = await executeQuery(query, [rut]);
    return result[0] || null;
  },
  
  /**
   * Obtener top proveedores por monto
   */
  async getTopProveedores(limit = 10) {
    const query = `
      SELECT 
        p.name,
        p.rut,
        COUNT(o.id) as total_ordenes,
        SUM(CAST(o.net_amount AS REAL)) as monto_total
      FROM providers p
      INNER JOIN orders o ON p.rut = o.provider_rut
      WHERE o.net_amount IS NOT NULL AND o.net_amount != ''
      GROUP BY p.rut
      ORDER BY monto_total DESC
      LIMIT ?
    `;
    
    return await executeQuery(query, [limit]);
  }
};

/**
 * Service para gestión de proyectos
 */
export const ProjectService = {
  /**
   * Obtener todos los proyectos con estadísticas
   */
  async getProyectos() {
    const query = `
      SELECT 
        pr.*,
        COUNT(o.id) as total_ordenes,
        SUM(CAST(o.net_amount AS REAL)) as monto_asignado,
        COUNT(DISTINCT o.provider_rut) as proveedores_involucrados
      FROM projects pr
      LEFT JOIN orders o ON pr.id = o.project_id
      GROUP BY pr.id
      ORDER BY monto_asignado DESC
    `;
    
    return await executeQuery(query);
  },
  
  /**
   * Obtener proyecto específico
   */
  async getProyecto(projectId) {
    const query = `
      SELECT 
        pr.*,
        COUNT(o.id) as total_ordenes,
        SUM(CAST(o.net_amount AS REAL)) as monto_total,
        COUNT(DISTINCT o.provider_rut) as proveedores_count,
        MIN(o.order_date) as primera_orden,
        MAX(o.order_date) as ultima_orden
      FROM projects pr
      LEFT JOIN orders o ON pr.id = o.project_id
      WHERE pr.id = ?
      GROUP BY pr.id
    `;
    
    const result = await executeQuery(query, [projectId]);
    return result[0] || null;
  }
};

/**
 * Service para análisis y reportes
 */
export const AnalyticsService = {
  /**
   * Dashboard principal - métricas clave
   */
  async getDashboardMetrics() {
    const queries = {
      ordenes: `
        SELECT 
          COUNT(*) as total,
          SUM(CAST(net_amount AS REAL)) as monto_total,
          AVG(CAST(net_amount AS REAL)) as promedio
        FROM orders 
        WHERE net_amount IS NOT NULL AND net_amount != ''
      `,
      proveedores: `
        SELECT COUNT(*) as total FROM providers
      `,
      proyectos: `
        SELECT COUNT(*) as total FROM projects
      `,
      tendencia: `
        SELECT 
          strftime('%Y-%m', order_date) as mes,
          COUNT(*) as ordenes,
          SUM(CAST(net_amount AS REAL)) as monto
        FROM orders 
        WHERE order_date >= date('now', '-6 months')
          AND net_amount IS NOT NULL AND net_amount != ''
        GROUP BY strftime('%Y-%m', order_date)
        ORDER BY mes
      `
    };
    
    const [ordenes, proveedores, proyectos, tendencia] = await Promise.all([
      executeQuery(queries.ordenes),
      executeQuery(queries.proveedores),
      executeQuery(queries.proyectos),
      executeQuery(queries.tendencia)
    ]);
    
    return {
      ordenes: ordenes[0] || {},
      proveedores: proveedores[0] || {},
      proyectos: proyectos[0] || {},
      tendencia: tendencia || []
    };
  },
  
  /**
   * Análisis de gastos por categoría
   */
  async getGastosPorCategoria() {
    const query = `
      SELECT 
        CASE 
          WHEN CAST(net_amount AS REAL) >= 10000000 THEN 'Alto (>10M)'
          WHEN CAST(net_amount AS REAL) >= 1000000 THEN 'Medio (1M-10M)'
          ELSE 'Bajo (<1M)'
        END as categoria,
        COUNT(*) as cantidad,
        SUM(CAST(net_amount AS REAL)) as monto_total
      FROM orders 
      WHERE net_amount IS NOT NULL AND net_amount != ''
      GROUP BY categoria
      ORDER BY monto_total DESC
    `;
    
    return await executeQuery(query);
  }
};

/**
 * Service para gestión documental
 */
export const DocumentService = {
  /**
   * Obtener documentos por tipo
   */
  async getDocumentosPorTipo() {
    // Esta implementación dependería de qué documentos están asociados a órdenes
    const query = `
      SELECT 
        'Orden de Compra' as tipo,
        COUNT(*) as cantidad
      FROM orders
      UNION ALL
      SELECT 
        'Proveedor' as tipo,
        COUNT(*) as cantidad
      FROM providers
      UNION ALL
      SELECT 
        'Proyecto' as tipo,
        COUNT(*) as cantidad
      FROM projects
    `;
    
    return await executeQuery(query);
  }
};

/**
 * Limpiar cache
 */
export function clearCache() {
  DB_CONFIG.cache.clear();
}

/**
 * Obtener estadísticas de cache
 */
export function getCacheStats() {
  return {
    entries: DB_CONFIG.cache.size,
    timeout: DB_CONFIG.cacheTimeout
  };
}
