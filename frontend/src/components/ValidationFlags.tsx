/**
 * Componente para mostrar flags de validación financiera.
 * 
 * Muestra los resultados de validaciones con colores y iconos
 * apropiados según la severidad (error, warning, info).
 */

import React from 'react';
import { ValidationFlag, ValidationResult } from '../hooks/useFinancialValidation';

interface ValidationFlagsProps {
  result: ValidationResult | null;
  className?: string;
}

interface ValidationFlagItemProps {
  flag: ValidationFlag;
}

const ValidationFlagItem: React.FC<ValidationFlagItemProps> = ({ flag }) => {
  const getSeverityStyles = (severity: ValidationFlag['severity']) => {
    switch (severity) {
      case 'error':
        return {
          container: 'bg-red-50 border-red-200 text-red-800',
          icon: '❌',
          iconColor: 'text-red-500'
        };
      case 'warning':
        return {
          container: 'bg-yellow-50 border-yellow-200 text-yellow-800',
          icon: '⚠️',
          iconColor: 'text-yellow-500'
        };
      case 'info':
        return {
          container: 'bg-blue-50 border-blue-200 text-blue-800',
          icon: 'ℹ️',
          iconColor: 'text-blue-500'
        };
      default:
        return {
          container: 'bg-gray-50 border-gray-200 text-gray-800',
          icon: '📋',
          iconColor: 'text-gray-500'
        };
    }
  };

  const styles = getSeverityStyles(flag.severity);

  return (
    <div className={`p-3 rounded-lg border ${styles.container} mb-2`}>
      <div className="flex items-start space-x-3">
        <span className={`text-lg ${styles.iconColor}`}>
          {styles.icon}
        </span>
        <div className="flex-1">
          <p className="text-sm font-medium">
            {flag.message}
          </p>
          {flag.details && Object.keys(flag.details).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs cursor-pointer hover:underline">
                Ver detalles
              </summary>
              <div className="mt-1 text-xs font-mono bg-white bg-opacity-50 p-2 rounded">
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(flag.details, null, 2)}
                </pre>
              </div>
            </details>
          )}
          <div className="mt-1 text-xs opacity-75">
            Tipo: {flag.flag_type} • Severidad: {flag.severity}
          </div>
        </div>
      </div>
    </div>
  );
};

const ValidationFlags: React.FC<ValidationFlagsProps> = ({ result, className = '' }) => {
  if (!result) {
    return null;
  }

  const { flags, is_valid, validation_type, validated_at } = result;

  if (flags.length === 0 && is_valid) {
    return (
      <div className={`p-4 bg-green-50 border border-green-200 rounded-lg ${className}`}>
        <div className="flex items-center space-x-2">
          <span className="text-green-600 text-lg">✅</span>
          <p className="text-green-800 font-medium">
            Validación exitosa
          </p>
        </div>
        <p className="text-green-700 text-sm mt-1">
          Todas las reglas se cumplieron correctamente.
        </p>
      </div>
    );
  }

  const errorFlags = flags.filter(flag => flag.severity === 'error');
  const warningFlags = flags.filter(flag => flag.severity === 'warning');
  const infoFlags = flags.filter(flag => flag.severity === 'info');

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Resumen del estado de validación */}
      <div className={`p-4 rounded-lg border ${
        !is_valid 
          ? 'bg-red-50 border-red-200' 
          : errorFlags.length > 0
          ? 'bg-yellow-50 border-yellow-200'
          : 'bg-green-50 border-green-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">
              {!is_valid ? '❌' : errorFlags.length > 0 ? '⚠️' : '✅'}
            </span>
            <h3 className={`font-semibold ${
              !is_valid 
                ? 'text-red-800' 
                : errorFlags.length > 0
                ? 'text-yellow-800'
                : 'text-green-800'
            }`}>
              {is_valid ? 'Validación Completada' : 'Validación Fallida'}
            </h3>
          </div>
          <div className="text-xs opacity-75">
            {validation_type}
          </div>
        </div>
        
        {flags.length > 0 && (
          <div className="mt-2 flex space-x-4 text-sm">
            {errorFlags.length > 0 && (
              <span className="text-red-700">
                {errorFlags.length} error{errorFlags.length !== 1 ? 'es' : ''}
              </span>
            )}
            {warningFlags.length > 0 && (
              <span className="text-yellow-700">
                {warningFlags.length} advertencia{warningFlags.length !== 1 ? 's' : ''}
              </span>
            )}
            {infoFlags.length > 0 && (
              <span className="text-blue-700">
                {infoFlags.length} informativo{infoFlags.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Listado de flags */}
      {flags.length > 0 && (
        <div className="space-y-2">
          {/* Errores primero */}
          {errorFlags.map((flag, index) => (
            <ValidationFlagItem key={`error-${index}`} flag={flag} />
          ))}
          
          {/* Advertencias */}
          {warningFlags.map((flag, index) => (
            <ValidationFlagItem key={`warning-${index}`} flag={flag} />
          ))}
          
          {/* Informativos */}
          {infoFlags.map((flag, index) => (
            <ValidationFlagItem key={`info-${index}`} flag={flag} />
          ))}
        </div>
      )}

      {/* Timestamp */}
      {validated_at && (
        <div className="text-xs text-gray-500 text-right">
          Validado: {new Date(validated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default ValidationFlags;