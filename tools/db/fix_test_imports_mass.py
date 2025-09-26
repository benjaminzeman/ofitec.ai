#!/usr/bin/env python3
"""
FASE 5.1: Script de corrección masiva de imports en tests
Auto-aprobado por Copilot configuration
"""

import os
import re
import glob
from pathlib import Path

def fix_import_in_file(file_path):
    """Corrige los imports de backend en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrón 1: from backend import server
        content = re.sub(r'^from backend import server$', 'import server', content, flags=re.MULTILINE)
        
        # Patrón 2: from backend import server  # comment
        content = re.sub(r'^from backend import server  # (.*)$', r'import server  # \1', content, flags=re.MULTILINE)
        
        # Patrón 3: from backend import module as alias
        content = re.sub(r'^from backend import (\w+) as (\w+)$', r'import \1 as \2', content, flags=re.MULTILINE)
        
        # Patrón 4: from backend import module
        content = re.sub(r'^from backend import (\w+)$', r'import \1', content, flags=re.MULTILINE)
        
        # Patrón 5: indented imports (dentro de funciones o try/except)
        content = re.sub(r'^(\s+)from backend import server$', r'\1import server', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s+)from backend import server  # (.*)$', r'\1import server  # \2', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s+)from backend import (\w+)$', r'\1import \2', content, flags=re.MULTILINE)
        
        # Si hubo cambios, escribir el archivo
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    backend_dir = Path(__file__).parent / "backend"
    tests_dir = backend_dir / "tests"
    
    if not tests_dir.exists():
        print("Directorio tests no encontrado")
        return
    
    # Obtener todos los archivos de test
    test_files = list(tests_dir.glob("test_*.py"))
    
    fixed_count = 0
    total_count = len(test_files)
    
    print(f"🔄 Iniciando corrección masiva de {total_count} archivos de test...")
    
    for test_file in test_files:
        if fix_import_in_file(test_file):
            print(f"✅ Corregido: {test_file.name}")
            fixed_count += 1
        else:
            print(f"⏭️  Sin cambios: {test_file.name}")
    
    print(f"\n🎉 COMPLETADO: {fixed_count}/{total_count} archivos corregidos")
    
    if fixed_count > 0:
        print("\n🧪 Ejecutando test de verificación...")
        # Probar un archivo corregido
        import subprocess
        import sys
        
        os.chdir(backend_dir)
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_health_endpoint.py", "-v"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Verificación exitosa: Los imports funcionan correctamente")
        else:
            print("❌ Error en verificación:")
            print(result.stdout)
            print(result.stderr)

if __name__ == "__main__":
    main()