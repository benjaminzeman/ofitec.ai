#!/usr/bin/env python3
"""
Comprehensive Code Analysis Script for Ofitec.ai
Detects issues in Python code including:
- Missing imports and blueprint issues
- SQL syntax problems
- Function usage inconsistencies  
- Table/View detection issues
- Security and best practices violations
"""

import os
import re
import ast
import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import subprocess
import sys

class CodeAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_path = self.project_root / "backend"
        self.issues: List[Dict] = []
        
    def analyze_all(self) -> List[Dict]:
        """Run all analysis checks"""
        print("🔍 Starting comprehensive code analysis...")
        
        # Core analysis checks
        self.check_import_issues()
        self.check_table_exists_usage()
        self.check_sql_syntax_issues()
        self.check_blueprint_registrations()
        self.check_hardcoded_values()
        self.check_security_issues()
        self.check_docker_issues()
        self.check_database_schema_issues()
        
        # Generate summary
        self.print_summary()
        return self.issues
    
    def add_issue(self, severity: str, category: str, description: str, 
                  file_path: str = "", line_num: int = 0, solution: str = ""):
        """Add an issue to the issues list"""
        self.issues.append({
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "category": category,
            "description": description,
            "file": file_path,
            "line": line_num,
            "solution": solution
        })
    
    def check_import_issues(self):
        """Check for missing imports and blueprint registration issues"""
        print("📦 Checking import issues...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            self.add_issue("CRITICAL", "imports", "server.py not found", str(server_py))
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for blueprint import issues
        blueprint_patterns = [
            (r'from backend\.', "Incorrect relative import with 'backend.' prefix"),
            (r'import backend\.', "Incorrect import with 'backend.' prefix"),
            (r'WARNING.*No module named \'backend\'', "Blueprint loading failures detected in logs")
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, issue_desc in blueprint_patterns:
                if re.search(pattern, line):
                    self.add_issue("HIGH", "imports", 
                                 f"{issue_desc}: {line.strip()}", 
                                 str(server_py), i,
                                 "Remove 'backend.' prefix from imports in Docker environment")
                                 
        # Check for missing critical imports
        required_imports = ['sqlite3', 'flask', 'os', 'logging']
        for imp in required_imports:
            if f"import {imp}" not in content and f"from {imp}" not in content:
                self.add_issue("MEDIUM", "imports", 
                             f"Missing critical import: {imp}", 
                             str(server_py))
    
    def check_table_exists_usage(self):
        """Check for inconsistent table/view detection"""
        print("🗄️ Checking table exists usage...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all _table_exists calls
        table_exists_calls = re.findall(r'_table_exists\([^)]+\)', content)
        view_or_table_exists_calls = re.findall(r'_view_or_table_exists\([^)]+\)', content)
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if '_table_exists(' in line and '_view_or_table_exists(' not in line:
                self.add_issue("MEDIUM", "database", 
                             f"Using _table_exists() instead of _view_or_table_exists(): {line.strip()}", 
                             str(server_py), i,
                             "Replace with _view_or_table_exists() for view compatibility")
                             
        print(f"  Found {len(table_exists_calls)} _table_exists() calls")
        print(f"  Found {len(view_or_table_exists_calls)} _view_or_table_exists() calls")
    
    def check_sql_syntax_issues(self):
        """Check for SQL syntax issues"""
        print("🔍 Checking SQL syntax...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Common SQL syntax issues
        sql_issues = [
            (r'WHERE\s+\w+\s+IS\s+AND', "Malformed WHERE clause with 'IS AND'"),
            (r'SELECT\s+[^,]*,\s*$', "SQL query ending with comma"),
            (r'\?\s*\)\s*AND', "Missing parameter in SQL query"),
            (r'WHERE.*=\s*\?.*AND.*=\s*\?.*AND.*=\s*\?\s*$', "Potential parameter mismatch in WHERE clause")
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, issue_desc in sql_issues:
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue("HIGH", "sql", 
                                 f"{issue_desc}: {line.strip()}", 
                                 str(server_py), i,
                                 "Fix SQL syntax and parameter binding")
    
    def check_blueprint_registrations(self):
        """Check blueprint registration status"""
        print("🧩 Checking blueprint registrations...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find blueprint registration patterns
        blueprint_files = [
            "ep_api.py", "sales_invoices.py", "ap_match.py", 
            "sii_service.py", "matching_metrics.py"
        ]
        
        for blueprint_file in blueprint_files:
            # Check if blueprint is imported and registered
            import_pattern = f"from.*{blueprint_file.replace('.py', '')}"
            register_pattern = f"app.register_blueprint"
            
            has_import = bool(re.search(import_pattern, content))
            
            if not has_import:
                self.add_issue("HIGH", "blueprints", 
                             f"Blueprint {blueprint_file} not properly imported/registered", 
                             str(server_py),
                             solution="Add proper blueprint import and registration")
    
    def check_hardcoded_values(self):
        """Check for hardcoded values that should be configurable"""
        print("🔢 Checking hardcoded values...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for hardcoded fallback values
        hardcoded_patterns = [
            (r'return\s+\d{9,}\.\d+,\s+\d{9,}\.\d+\s*#.*[Hh]ardcoded', "Hardcoded revenue fallback values"),
            (r'PORT\s*=\s*\d+', "Hardcoded port number"),
            (r'DB_PATH\s*=.*\.db', "Hardcoded database path")
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, issue_desc in hardcoded_patterns:
                if re.search(pattern, line):
                    self.add_issue("MEDIUM", "config", 
                                 f"{issue_desc}: {line.strip()}", 
                                 str(server_py), i,
                                 "Move to environment variables or config file")
    
    def check_security_issues(self):
        """Check for security issues"""
        print("🔒 Checking security issues...")
        
        server_py = self.backend_path / "server.py"
        if not server_py.exists():
            return
            
        with open(server_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        security_issues = [
            (r'debug\s*=\s*True', "Debug mode enabled in production"),
            (r'app\.run\(.*debug\s*=\s*True', "Flask debug mode enabled"),
            (r'eval\s*\(', "Use of dangerous eval() function"),
            (r'exec\s*\(', "Use of dangerous exec() function"),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, issue_desc in security_issues:
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue("HIGH", "security", 
                                 f"{issue_desc}: {line.strip()}", 
                                 str(server_py), i,
                                 "Remove debug mode and dangerous functions")
    
    def check_docker_issues(self):
        """Check Docker-related issues"""
        print("🐳 Checking Docker configuration...")
        
        dockerfile = self.backend_path / "Dockerfile"
        if dockerfile.exists():
            with open(dockerfile, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for potential Docker issues
            if "WORKDIR /app" not in content:
                self.add_issue("MEDIUM", "docker", 
                             "Missing WORKDIR directive in Dockerfile", 
                             str(dockerfile))
                             
            if "EXPOSE" not in content:
                self.add_issue("LOW", "docker", 
                             "Missing EXPOSE directive in Dockerfile", 
                             str(dockerfile))
    
    def check_database_schema_issues(self):
        """Check database schema consistency issues"""
        print("🗃️ Checking database schema issues...")
        
        # Check if database file exists
        db_path = self.project_root / "data" / "chipax_data.db"
        if not db_path.exists():
            self.add_issue("CRITICAL", "database", 
                         f"Database file not found: {db_path}", 
                         str(db_path),
                         solution="Ensure database file exists or create it")
            return
        
        try:
            # Check database structure
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all tables and views
            cursor.execute("""
                SELECT name, type FROM sqlite_master 
                WHERE type IN ('table', 'view') 
                ORDER BY name
            """)
            schema_objects = cursor.fetchall()
            
            # Check for critical tables/views
            critical_objects = [
                'bank_movements', 'v_facturas_venta', 'purchase_orders_unified'
            ]
            
            existing_objects = [obj[0] for obj in schema_objects]
            
            for critical_obj in critical_objects:
                if critical_obj not in existing_objects:
                    self.add_issue("HIGH", "database", 
                                 f"Critical table/view missing: {critical_obj}", 
                                 str(db_path),
                                 solution=f"Create or import {critical_obj}")
            
            conn.close()
            print(f"  Found {len(schema_objects)} database objects")
            
        except Exception as e:
            self.add_issue("HIGH", "database", 
                         f"Could not analyze database: {str(e)}", 
                         str(db_path))
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("📊 CODE ANALYSIS SUMMARY")
        print("="*60)
        
        if not self.issues:
            print("✅ No issues found!")
            return
        
        # Group by severity
        by_severity = {}
        for issue in self.issues:
            severity = issue['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)
        
        # Print summary stats
        total_issues = len(self.issues)
        critical = len(by_severity.get('CRITICAL', []))
        high = len(by_severity.get('HIGH', []))
        medium = len(by_severity.get('MEDIUM', []))
        low = len(by_severity.get('LOW', []))
        
        print(f"Total Issues Found: {total_issues}")
        print(f"🔴 Critical: {critical}")
        print(f"🟠 High: {high}")  
        print(f"🟡 Medium: {medium}")
        print(f"🟢 Low: {low}")
        print()
        
        # Print detailed issues
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity not in by_severity:
                continue
                
            print(f"\n{severity} ISSUES:")
            print("-" * 40)
            
            for i, issue in enumerate(by_severity[severity], 1):
                print(f"{i}. [{issue['category'].upper()}] {issue['description']}")
                if issue['file']:
                    print(f"   📁 {issue['file']}")
                    if issue['line']:
                        print(f"   📍 Line {issue['line']}")
                if issue['solution']:
                    print(f"   💡 Solution: {issue['solution']}")
                print()


def main():
    """Main analysis function"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    analyzer = CodeAnalyzer(project_root)
    issues = analyzer.analyze_all()
    
    # Return appropriate exit code
    critical_issues = [i for i in issues if i['severity'] == 'CRITICAL']
    high_issues = [i for i in issues if i['severity'] == 'HIGH']
    
    if critical_issues:
        print(f"\n❌ Analysis failed: {len(critical_issues)} critical issues found")
        return 1
    elif high_issues:
        print(f"\n⚠️ Analysis completed with {len(high_issues)} high priority issues")
        return 2
    elif issues:
        print(f"\n✅ Analysis completed with {len(issues)} minor issues")
        return 0
    else:
        print("\n🎉 Analysis passed: No issues found!")
        return 0


if __name__ == "__main__":
    exit(main())