"""
Change Impact Analysis Tool

Analyzes proposed code changes to identify potential impacts on other components.
Run this BEFORE making changes to understand dependencies.

Usage:
    python tools/analyze_change_impact.py <file_to_change>
    python tools/analyze_change_impact.py spectral_edge/core/psd.py
    python tools/analyze_change_impact.py spectral_edge/utils/hdf5_loader.py

This tool:
1. Identifies what imports the target file
2. Identifies what the target file imports
3. Lists all public functions/classes
4. Shows where they're used
5. Estimates impact severity

Author: SpectralEdge Development Team
Date: 2025-01-28
"""

import sys
import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class CodeAnalyzer:
    """Analyzes Python code dependencies and usage."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.file_imports = {}  # file -> list of imports
        self.file_exports = {}  # file -> list of public symbols
        self.symbol_usage = defaultdict(list)  # symbol -> list of (file, line)
    
    def scan_project(self):
        """Scan entire project to build dependency graph."""
        print("Scanning project...")
        
        py_files = list(self.project_root.rglob("*.py"))
        py_files = [f for f in py_files if not str(f).startswith(str(self.project_root / "tests"))]
        
        for py_file in py_files:
            try:
                self._analyze_file(py_file)
            except Exception as e:
                print(f"Warning: Could not analyze {py_file}: {e}")
        
        print(f"Scanned {len(py_files)} files")
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        rel_path = file_path.relative_to(self.project_root)
        
        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
        
        self.file_imports[str(rel_path)] = imports
        
        # Extract public symbols (functions and classes)
        exports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not node.name.startswith('_'):  # Public symbol
                    exports.append(node.name)
        
        self.file_exports[str(rel_path)] = exports
        
        # Find symbol usage
        for line_no, line in enumerate(content.split('\n'), 1):
            for symbol in exports:
                if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                    self.symbol_usage[symbol].append((str(rel_path), line_no))
    
    def analyze_change_impact(self, target_file: str):
        """Analyze impact of changing a specific file."""
        # Handle both absolute and relative paths
        target_path = Path(target_file)
        if target_path.is_absolute():
            target_str = str(target_path.relative_to(self.project_root))
        else:
            target_str = str(target_path)
        
        print(f"\n{'='*70}")
        print(f"  CHANGE IMPACT ANALYSIS: {target_str}")
        print('='*70)
        
        # 1. Direct importers
        print(f"\n📥 FILES THAT IMPORT {target_str}:")
        print("-" * 70)
        
        importers = []
        for file, imports in self.file_imports.items():
            # Convert file path to module path for matching
            module_path = target_str.replace('/', '.').replace('.py', '')
            for imp in imports:
                if module_path in imp or target_str in file:
                    importers.append(file)
                    break
        
        if importers:
            for importer in sorted(set(importers)):
                print(f"  • {importer}")
            print(f"\n  Total: {len(set(importers))} files")
        else:
            print("  (No direct importers found)")
        
        # 2. Exported symbols
        print(f"\n📤 PUBLIC SYMBOLS EXPORTED BY {target_str}:")
        print("-" * 70)
        
        exports = self.file_exports.get(target_str, [])
        if exports:
            for symbol in sorted(exports):
                print(f"  • {symbol}")
            print(f"\n  Total: {len(exports)} public symbols")
        else:
            print("  (No public symbols found)")
        
        # 3. Symbol usage
        if exports:
            print(f"\n🔗 WHERE EXPORTED SYMBOLS ARE USED:")
            print("-" * 70)
            
            for symbol in sorted(exports):
                usages = self.symbol_usage.get(symbol, [])
                # Filter out self-references
                usages = [(f, l) for f, l in usages if f != target_str]
                
                if usages:
                    print(f"\n  {symbol}:")
                    for file, line in sorted(set(usages))[:10]:  # Limit to 10
                        print(f"    - {file}:{line}")
                    if len(usages) > 10:
                        print(f"    ... and {len(usages) - 10} more")
        
        # 4. Dependencies
        print(f"\n📦 DEPENDENCIES OF {target_str}:")
        print("-" * 70)
        
        deps = self.file_imports.get(target_str, [])
        if deps:
            # Group by package
            internal_deps = [d for d in deps if d.startswith('spectral_edge')]
            external_deps = [d for d in deps if not d.startswith('spectral_edge')]
            
            if internal_deps:
                print("\n  Internal:")
                for dep in sorted(set(internal_deps)):
                    print(f"    • {dep}")
            
            if external_deps:
                print("\n  External:")
                for dep in sorted(set(external_deps))[:20]:  # Limit to 20
                    print(f"    • {dep}")
        else:
            print("  (No dependencies found)")
        
        # 5. Impact assessment
        print(f"\n⚠️  IMPACT ASSESSMENT:")
        print("-" * 70)
        
        importer_count = len(set(importers))
        export_count = len(exports)
        
        # Calculate impact score
        impact_score = 0
        if importer_count > 10:
            impact_score += 3
        elif importer_count > 5:
            impact_score += 2
        elif importer_count > 0:
            impact_score += 1
        
        if export_count > 10:
            impact_score += 3
        elif export_count > 5:
            impact_score += 2
        elif export_count > 0:
            impact_score += 1
        
        # Determine severity
        if impact_score >= 5:
            severity = "🔴 HIGH"
            recommendation = "Requires extensive testing. Run all validation tests."
        elif impact_score >= 3:
            severity = "🟡 MEDIUM"
            recommendation = "Requires careful testing. Run contract and integration tests."
        else:
            severity = "🟢 LOW"
            recommendation = "Minimal impact. Run contract tests to verify."
        
        print(f"\n  Severity: {severity}")
        print(f"  Importers: {importer_count} files")
        print(f"  Exports: {export_count} symbols")
        print(f"\n  Recommendation: {recommendation}")
        
        # 6. Testing checklist
        print(f"\n✅ TESTING CHECKLIST:")
        print("-" * 70)
        print("  Before making changes:")
        print("    [ ] Run: python tests/test_data_contracts.py")
        print("    [ ] Document current behavior")
        print("    [ ] Review all importers listed above")
        print("\n  After making changes:")
        print("    [ ] Run: python tests/test_data_contracts.py")
        print("    [ ] Run: python tests/test_pyqt6_validation.py")
        print("    [ ] Test each importer manually")
        print("    [ ] Update documentation")
        
        if importer_count > 0:
            print("\n  Files to test manually:")
            for importer in sorted(set(importers))[:10]:
                print(f"    [ ] {importer}")
        
        print("\n" + "="*70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/analyze_change_impact.py <file_to_change>")
        print("\nExample:")
        print("  python tools/analyze_change_impact.py spectral_edge/core/psd.py")
        print("  python tools/analyze_change_impact.py spectral_edge/utils/hdf5_loader.py")
        sys.exit(1)
    
    target_file = sys.argv[1]
    project_root = Path(__file__).parent.parent
    
    # Verify file exists
    full_path = project_root / target_file
    if not full_path.exists():
        print(f"Error: File not found: {target_file}")
        sys.exit(1)
    
    # Analyze
    analyzer = CodeAnalyzer(project_root)
    analyzer.scan_project()
    analyzer.analyze_change_impact(target_file)


if __name__ == '__main__':
    main()
