#!/usr/bin/env python3
"""
Analizador de Patrones de Conciliación Inteligente
==============================================

Este script analiza 6 años de conciliaciones ya realizadas para:
1. Extraer patrones de matching exitosos
2. Identificar aliases de proveedores
3. Generar reglas de negocio automáticas
4. Entrenar la IA con decisiones históricas reales

Autor: Benjamin Zeman & GitHub Copilot
Fecha: Septiembre 2025
"""

import os
import csv
import sqlite3
import pandas as pd
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import re
from datetime import datetime
import json


class ConciliationPatternAnalyzer:
    """Analizador avanzado de patrones de conciliación histórica."""
    
    def __init__(self, raw_data_path: str, db_path: str):
        self.raw_data_path = raw_data_path
        self.db_path = db_path
        self.patterns = {
            'vendor_aliases': defaultdict(set),  # RUT -> {nombres}
            'amount_tolerances': defaultdict(list),  # tipo_doc -> tolerancias
            'matching_rules': defaultdict(int),  # regla -> count
            'timing_patterns': defaultdict(list),  # dias_diferencia -> count
            'description_patterns': defaultdict(set)  # patron -> documentos
        }
        
    def analyze_all_files(self) -> Dict:
        """Analiza todos los archivos CSV de conciliación."""
        print("🔍 ANALIZANDO 6 AÑOS DE CONCILIACIONES...")
        
        chipax_path = os.path.join(self.raw_data_path, 'chipax')
        if not os.path.exists(chipax_path):
            print(f"❌ No se encuentra: {chipax_path}")
            return {}
        
        csv_files = [f for f in os.listdir(chipax_path) if f.endswith('_conciliacion.csv')]
        
        results = {
            'files_processed': 0,
            'total_reconciliations': 0,
            'vendor_aliases': {},
            'matching_patterns': {},
            'timing_analysis': {},
            'amount_tolerances': {},
            'categories': defaultdict(int)
        }
        
        for csv_file in csv_files:
            file_path = os.path.join(chipax_path, csv_file)
            print(f"📄 Procesando: {csv_file}")
            
            file_results = self.analyze_csv_file(file_path)
            if file_results:
                results['files_processed'] += 1
                results['total_reconciliations'] += file_results['reconciliations_count']
                
                # Agregar categoría
                category = self.extract_category_from_filename(csv_file)
                results['categories'][category] += file_results['reconciliations_count']
        
        # Consolidar patrones
        results['vendor_aliases'] = self.consolidate_vendor_aliases()
        results['matching_patterns'] = self.consolidate_matching_patterns()
        results['timing_analysis'] = self.analyze_timing_patterns()
        results['amount_tolerances'] = self.analyze_amount_tolerances()
        
        return results
    
    def analyze_csv_file(self, file_path: str) -> Dict:
        """Analiza un archivo CSV específico."""
        try:
            # Detectar encoding
            encodings = ['utf-8', 'latin1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                print(f"❌ No se pudo leer: {file_path}")
                return {}
            
            # Filtrar solo registros conciliados
            reconciled_mask = df['Conciliación'].str.contains('Conciliación', na=False)
            reconciled_df = df[reconciled_mask]
            
            if reconciled_df.empty:
                return {'reconciliations_count': 0}
            
            # Analizar patrones en este archivo
            self.extract_vendor_patterns(reconciled_df)
            self.extract_amount_patterns(reconciled_df)
            self.extract_timing_patterns(reconciled_df)
            self.extract_description_patterns(reconciled_df)
            
            return {
                'reconciliations_count': len(reconciled_df),
                'total_rows': len(df)
            }
            
        except Exception as e:
            print(f"❌ Error procesando {file_path}: {e}")
            return {}
    
    def extract_vendor_patterns(self, df: pd.DataFrame):
        """Extrae patrones de proveedores/clientes."""
        # Mapear RUT -> nombres para crear aliases
        for _, row in df.iterrows():
            rut = row.get('RUT', '')
            razon_social = row.get('Razón Social', '')
            
            if rut and razon_social:
                rut_clean = self.clean_rut(rut)
                name_clean = self.clean_company_name(razon_social)
                if rut_clean and name_clean:
                    self.patterns['vendor_aliases'][rut_clean].add(name_clean)
    
    def extract_amount_patterns(self, df: pd.DataFrame):
        """Analiza tolerancias de montos."""
        for _, row in df.iterrows():
            try:
                monto_original = float(row.get('Monto Moneda Original', 0))
                monto_conciliado = float(row.get('Monto Conciliado', 0))
                
                if monto_original > 0 and monto_conciliado > 0:
                    diferencia_pct = abs(monto_original - monto_conciliado) / monto_original
                    tipo_doc = row.get('Tipo Documento Conciliado', 'unknown')
                    self.patterns['amount_tolerances'][tipo_doc].append(diferencia_pct)
            except (ValueError, TypeError):
                continue
    
    def extract_timing_patterns(self, df: pd.DataFrame):
        """Analiza patrones de tiempo entre documento y conciliación."""
        for _, row in df.iterrows():
            try:
                fecha_doc = pd.to_datetime(row.get('Fecha Documento Conciliado', ''), errors='coerce')
                fecha_mov = pd.to_datetime(row.get('Fecha', ''), errors='coerce')
                
                if pd.notna(fecha_doc) and pd.notna(fecha_mov):
                    dias_diff = (fecha_mov - fecha_doc).days
                    plazo_efectivo = row.get('Plazo Pago Efectivo (días)', 0)
                    
                    self.patterns['timing_patterns'][dias_diff].append(plazo_efectivo)
            except Exception:
                continue
    
    def extract_description_patterns(self, df: pd.DataFrame):
        """Extrae patrones de descripción para matching inteligente."""
        for _, row in df.iterrows():
            descripcion_mov = str(row.get('Descripción', '')).lower()
            descripcion_doc = str(row.get('Descripción Documento Conciliado', '')).lower()
            
            if descripcion_mov and descripcion_doc:
                # Buscar palabras comunes
                words_mov = set(self.clean_words(descripcion_mov))
                words_doc = set(self.clean_words(descripcion_doc))
                common_words = words_mov & words_doc
                
                if common_words:
                    pattern_key = f"{len(common_words)}_common_words"
                    self.patterns['description_patterns'][pattern_key].add('|'.join(sorted(common_words)))
    
    def consolidate_vendor_aliases(self) -> Dict:
        """Consolida aliases de proveedores."""
        consolidated = {}
        for rut, names in self.patterns['vendor_aliases'].items():
            if len(names) > 1:  # Solo proveedores con múltiples nombres
                consolidated[rut] = {
                    'primary_name': max(names, key=len),  # Nombre más largo como principal
                    'aliases': list(names),
                    'alias_count': len(names)
                }
        return consolidated
    
    def consolidate_matching_patterns(self) -> Dict:
        """Consolida patrones de matching."""
        return dict(self.patterns['matching_rules'])
    
    def analyze_timing_patterns(self) -> Dict:
        """Analiza patrones de timing."""
        timing_stats = {}
        for dias_diff, plazos in self.patterns['timing_patterns'].items():
            if plazos:
                timing_stats[dias_diff] = {
                    'count': len(plazos),
                    'avg_plazo': sum(plazos) / len(plazos),
                    'min_plazo': min(plazos),
                    'max_plazo': max(plazos)
                }
        return timing_stats
    
    def analyze_amount_tolerances(self) -> Dict:
        """Analiza tolerancias de montos por tipo de documento."""
        tolerance_stats = {}
        for tipo_doc, tolerancias in self.patterns['amount_tolerances'].items():
            if tolerancias:
                tolerance_stats[tipo_doc] = {
                    'count': len(tolerancias),
                    'avg_tolerance': sum(tolerancias) / len(tolerancias),
                    'max_tolerance': max(tolerancias),
                    'p95_tolerance': sorted(tolerancias)[int(len(tolerancias) * 0.95)] if tolerancias else 0
                }
        return tolerance_stats
    
    def extract_category_from_filename(self, filename: str) -> str:
        """Extrae categoría del nombre del archivo."""
        if 'banco' in filename.lower():
            return 'movimientos_bancarios'
        elif 'facturas_compra' in filename.lower():
            return 'facturas_compra'
        elif 'facturas_venta' in filename.lower():
            return 'facturas_venta'
        elif 'gastos' in filename.lower():
            return 'gastos'
        elif 'honorarios' in filename.lower():
            return 'honorarios'
        elif 'impuestos' in filename.lower():
            return 'impuestos'
        elif 'remuneraciones' in filename.lower():
            return 'remuneraciones'
        elif 'previred' in filename.lower():
            return 'previred'
        elif 'boletas' in filename.lower():
            return 'boletas_terceros'
        else:
            return 'otros'
    
    def clean_rut(self, rut: str) -> str:
        """Limpia y normaliza RUT."""
        if not rut:
            return ''
        # Remover puntos y guiones, mantener solo números y K
        cleaned = re.sub(r'[^\d\-kK]', '', str(rut))
        return cleaned.upper()
    
    def clean_company_name(self, name: str) -> str:
        """Limpia nombre de empresa."""
        if not name:
            return ''
        # Normalizar espacios y caracteres especiales
        cleaned = re.sub(r'\s+', ' ', str(name)).strip().upper()
        return cleaned
    
    def clean_words(self, text: str) -> List[str]:
        """Extrae palabras limpias para análisis de texto."""
        if not text:
            return []
        # Remover caracteres especiales y split por espacios
        words = re.findall(r'\b[a-záéíóúñ]+\b', text.lower())
        # Filtrar palabras muy cortas o muy comunes
        stop_words = {'de', 'la', 'el', 'en', 'y', 'a', 'que', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del'}
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def save_results(self, results: Dict, output_path: str):
        """Guarda resultados del análisis."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Resultados guardados en: {output_path}")
    
    def generate_training_data_for_ai(self, results: Dict) -> List[Dict]:
        """Genera datos de entrenamiento para la IA."""
        training_data = []
        
        # Generar reglas de alias
        for rut, alias_info in results['vendor_aliases'].items():
            training_data.append({
                'type': 'vendor_alias',
                'rut': rut,
                'primary_name': alias_info['primary_name'],
                'aliases': alias_info['aliases'],
                'confidence': min(1.0, alias_info['alias_count'] / 10.0)  # Más aliases = más confianza
            })
        
        # Generar reglas de tolerancia
        for tipo_doc, tolerance_info in results['amount_tolerances'].items():
            training_data.append({
                'type': 'amount_tolerance',
                'document_type': tipo_doc,
                'recommended_tolerance': tolerance_info['p95_tolerance'],
                'max_tolerance': tolerance_info['max_tolerance'],
                'confidence': min(1.0, tolerance_info['count'] / 100.0)
            })
        
        return training_data


def main():
    """Función principal."""
    print("🚀 INICIANDO ANÁLISIS DE PATRONES DE CONCILIACIÓN")
    print("=" * 60)
    
    # Configurar rutas
    raw_data_path = r'c:\Ofitec\ofitec.ai\data\raw'
    db_path = r'c:\Ofitec\ofitec.ai\data\chipax_data.db'
    output_path = r'c:\Ofitec\ofitec.ai\data\conciliation_patterns.json'
    
    # Crear analizador
    analyzer = ConciliationPatternAnalyzer(raw_data_path, db_path)
    
    # Ejecutar análisis
    results = analyzer.analyze_all_files()
    
    # Mostrar resumen
    print("\n🎯 RESUMEN DEL ANÁLISIS:")
    print(f"  📁 Archivos procesados: {results['files_processed']}")
    print(f"  ✅ Total conciliaciones: {results['total_reconciliations']:,}")
    print(f"  🏢 Aliases de proveedores: {len(results['vendor_aliases'])}")
    print(f"  📊 Patrones de timing: {len(results['timing_analysis'])}")
    print(f"  💰 Tolerancias de monto: {len(results['amount_tolerances'])}")
    
    print("\n📋 CATEGORÍAS:")
    for category, count in results['categories'].items():
        print(f"  • {category}: {count:,} conciliaciones")
    
    # Guardar resultados
    analyzer.save_results(results, output_path)
    
    # Generar datos de entrenamiento para IA
    training_data = analyzer.generate_training_data_for_ai(results)
    training_path = r'c:\Ofitec\ofitec.ai\data\ai_training_data.json'
    
    with open(training_path, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"🤖 Datos de entrenamiento IA: {len(training_data)} reglas generadas")
    print(f"💾 Guardado en: {training_path}")
    
    print("\n✨ ¡ANÁLISIS COMPLETADO!")
    return results


if __name__ == "__main__":
    main()