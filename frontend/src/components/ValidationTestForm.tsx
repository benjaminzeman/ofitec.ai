/**
 * Formulario de prueba para el sistema de validaciones financieras.
 * 
 * Permite probar las diferentes validaciones implementadas:
 * - Factura vs Orden de Compra
 * - Pago vs Factura
 * - Orden de Compra vs Presupuesto
 */

import React, { useState } from 'react';
import { useFinancialValidation } from '../hooks/useFinancialValidation';
import ValidationFlags from './ValidationFlags';

type ValidationType = 'invoice_vs_po' | 'payment_vs_invoice' | 'po_vs_budget' | 'invoice_complete';

interface FormData {
  // Campos comunes
  po_number: string;
  invoice_amount: string;
  po_line_id: string;
  
  // Para validación de pagos
  invoice_id: string;
  payment_amount: string;
  
  // Para validación de presupuesto
  po_amount: string;
  budget_center: string;
  cost_center: string;
}

const initialFormData: FormData = {
  po_number: '',
  invoice_amount: '',
  po_line_id: '',
  invoice_id: '',
  payment_amount: '',
  po_amount: '',
  budget_center: '',
  cost_center: '',
};

const ValidationTestForm: React.FC = () => {
  const [validationType, setValidationType] = useState<ValidationType>('invoice_vs_po');
  const [formData, setFormData] = useState<FormData>(initialFormData);
  
  const {
    loading,
    error,
    lastResult,
    validateInvoiceVsPO,
    validatePaymentVsInvoice,
    validatePOVsBudget,
    validateInvoiceComplete,
    clearState,
    hasErrors,
    hasWarnings,
    isValid,
  } = useFinancialValidation();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      switch (validationType) {
        case 'invoice_vs_po':
          await validateInvoiceVsPO({
            po_number: formData.po_number,
            invoice_amount: parseFloat(formData.invoice_amount),
            po_line_id: formData.po_line_id || undefined,
          });
          break;
          
        case 'payment_vs_invoice':
          await validatePaymentVsInvoice({
            invoice_id: formData.invoice_id,
            payment_amount: parseFloat(formData.payment_amount),
          });
          break;
          
        case 'po_vs_budget':
          await validatePOVsBudget({
            po_number: formData.po_number,
            po_amount: parseFloat(formData.po_amount),
            budget_center: formData.budget_center || undefined,
          });
          break;
          
        case 'invoice_complete':
          await validateInvoiceComplete({
            po_number: formData.po_number,
            invoice_amount: parseFloat(formData.invoice_amount),
            cost_center: formData.cost_center || undefined,
            po_line_id: formData.po_line_id || undefined,
          });
          break;
      }
    } catch (err) {
      console.error('Error en validación:', err);
    }
  };

  const handleClear = () => {
    setFormData(initialFormData);
    clearState();
  };

  const getFormFields = () => {
    switch (validationType) {
      case 'invoice_vs_po':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de OC *
              </label>
              <input
                type="text"
                name="po_number"
                value={formData.po_number}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: PO-00001"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monto Factura *
              </label>
              <input
                type="number"
                name="invoice_amount"
                value={formData.invoice_amount}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="150000"
                step="0.01"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Línea OC (Opcional)
              </label>
              <input
                type="text"
                name="po_line_id"
                value={formData.po_line_id}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Dejar vacío para validar OC completa"
              />
            </div>
          </>
        );
        
      case 'payment_vs_invoice':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Factura *
              </label>
              <input
                type="text"
                name="invoice_id"
                value={formData.invoice_id}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: FAC001"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monto Pago *
              </label>
              <input
                type="number"
                name="payment_amount"
                value={formData.payment_amount}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="50000"
                step="0.01"
                required
              />
            </div>
          </>
        );
        
      case 'po_vs_budget':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de OC *
              </label>
              <input
                type="text"
                name="po_number"
                value={formData.po_number}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: PO-00001"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monto OC *
              </label>
              <input
                type="number"
                name="po_amount"
                value={formData.po_amount}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="200000"
                step="0.01"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Centro de Presupuesto (Opcional)
              </label>
              <select
                name="budget_center"
                value={formData.budget_center}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Detectar automáticamente</option>
                <option value="IT">IT - Tecnología e Informática</option>
                <option value="HR">HR - Recursos Humanos</option>
                <option value="OPS">OPS - Operaciones</option>
                <option value="MKT">MKT - Marketing y Ventas</option>
                <option value="FIN">FIN - Finanzas</option>
              </select>
            </div>
          </>
        );
        
      case 'invoice_complete':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Número de OC *
              </label>
              <input
                type="text"
                name="po_number"
                value={formData.po_number}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: PO-00001"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Monto Factura *
              </label>
              <input
                type="number"
                name="invoice_amount"
                value={formData.invoice_amount}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="150000"
                step="0.01"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Centro de Costo (Opcional)
              </label>
              <input
                type="text"
                name="cost_center"
                value={formData.cost_center}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: IT, HR, OPS"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ID Línea OC (Opcional)
              </label>
              <input
                type="text"
                name="po_line_id"
                value={formData.po_line_id}
                onChange={handleInputChange}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Dejar vacío para validar OC completa"
              />
            </div>
          </>
        );
        
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Pruebas de Validación Financiera
        </h1>
        <p className="text-gray-600">
          Sistema de validación de reglas de negocio en tiempo real
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formulario */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Validación
            </label>
            <select
              value={validationType}
              onChange={(e) => {
                setValidationType(e.target.value as ValidationType);
                handleClear();
              }}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="invoice_vs_po">Factura vs Orden de Compra</option>
              <option value="payment_vs_invoice">Pago vs Factura</option>
              <option value="po_vs_budget">OC vs Presupuesto</option>
              <option value="invoice_complete">Validación Completa de Factura</option>
            </select>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {getFormFields()}

            <div className="flex space-x-3 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Validando...' : 'Validar'}
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Limpiar
              </button>
            </div>
          </form>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800 font-medium">Error de Conexión</p>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          )}
        </div>

        {/* Resultados */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Resultados de Validación
          </h2>
          
          {lastResult ? (
            <ValidationFlags result={lastResult} />
          ) : (
            <div className="p-8 text-center text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
              <p>Los resultados de validación aparecerán aquí</p>
              <p className="text-sm mt-1">Selecciona un tipo de validación y completa el formulario</p>
            </div>
          )}

          {/* Estado de validación */}
          {lastResult && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-medium text-gray-900 mb-2">Estado Actual</h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className={`p-2 rounded ${isValid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  <div className="font-semibold">{isValid ? 'VÁLIDO' : 'INVÁLIDO'}</div>
                  <div className="text-xs">Estado general</div>
                </div>
                <div className={`p-2 rounded ${hasErrors ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'}`}>
                  <div className="font-semibold">{hasErrors ? 'SÍ' : 'NO'}</div>
                  <div className="text-xs">Errores críticos</div>
                </div>
                <div className={`p-2 rounded ${hasWarnings ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'}`}>
                  <div className="font-semibold">{hasWarnings ? 'SÍ' : 'NO'}</div>
                  <div className="text-xs">Advertencias</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ValidationTestForm;