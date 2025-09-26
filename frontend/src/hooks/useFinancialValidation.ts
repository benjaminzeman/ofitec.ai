/**
 * Hook personalizado para manejar validaciones financieras.
 *
 * Este hook proporciona funcionalidades para ejecutar validaciones
 * de reglas de negocio en tiempo real a través de la API.
 */

import { useCallback, useState } from 'react';

export interface ValidationFlag {
  flag_type: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  details: Record<string, any>;
}

export interface ValidationResult {
  is_valid: boolean;
  flags: ValidationFlag[];
  validation_type: string;
  validated_at: string;
}

interface ValidationHookState {
  loading: boolean;
  error: string | null;
  lastResult: ValidationResult | null;
}

export function useFinancialValidation() {
  const [state, setState] = useState<ValidationHookState>({
    loading: false,
    error: null,
    lastResult: null,
  });

  const validateInvoiceVsPO = useCallback(
    async (data: {
      po_number: string;
      invoice_amount: number;
      po_line_id?: string;
    }): Promise<ValidationResult> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await fetch('/api/validation/invoice_vs_po', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result: ValidationResult = await response.json();

        setState((prev) => ({
          ...prev,
          loading: false,
          lastResult: result,
        }));

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Error desconocido';
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }));
        throw error;
      }
    },
    [],
  );

  const validatePaymentVsInvoice = useCallback(
    async (data: { invoice_id: string; payment_amount: number }): Promise<ValidationResult> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await fetch('/api/validation/payment_vs_invoice', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result: ValidationResult = await response.json();

        setState((prev) => ({
          ...prev,
          loading: false,
          lastResult: result,
        }));

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Error desconocido';
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }));
        throw error;
      }
    },
    [],
  );

  const validatePOVsBudget = useCallback(
    async (data: {
      po_number: string;
      po_amount: number;
      budget_center?: string;
    }): Promise<ValidationResult> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await fetch('/api/validation/po_vs_budget', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result: ValidationResult = await response.json();

        setState((prev) => ({
          ...prev,
          loading: false,
          lastResult: result,
        }));

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Error desconocido';
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }));
        throw error;
      }
    },
    [],
  );

  const validateInvoiceComplete = useCallback(
    async (data: {
      po_number: string;
      invoice_amount: number;
      cost_center?: string;
      po_line_id?: string;
    }): Promise<ValidationResult> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = await fetch('/api/validation/invoice_complete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result: ValidationResult = await response.json();

        setState((prev) => ({
          ...prev,
          loading: false,
          lastResult: result,
        }));

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Error desconocido';
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorMessage,
        }));
        throw error;
      }
    },
    [],
  );

  const clearState = useCallback(() => {
    setState({
      loading: false,
      error: null,
      lastResult: null,
    });
  }, []);

  return {
    // Estado
    loading: state.loading,
    error: state.error,
    lastResult: state.lastResult,

    // Acciones
    validateInvoiceVsPO,
    validatePaymentVsInvoice,
    validatePOVsBudget,
    validateInvoiceComplete,
    clearState,

    // Utilidades
    hasErrors: state.lastResult?.flags.some((flag) => flag.severity === 'error') ?? false,
    hasWarnings: state.lastResult?.flags.some((flag) => flag.severity === 'warning') ?? false,
    isValid: state.lastResult?.is_valid ?? null,
  };
}
