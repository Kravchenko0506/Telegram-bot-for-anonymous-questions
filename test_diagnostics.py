#!/usr/bin/env python3
"""
Test Infrastructure Diagnostics

Сканирует тестовую инфраструктуру на наличие проблем и предлагает исправления.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess


class TestDiagnostics:
    """Диагностика тестовой инфраструктуры."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.tests_dir = self.project_root / "Tests"
        self.pytest_ini = self.project_root / "pytest.ini"
        
        # Найденные проблемы
        self.issues = []
        self.warnings = []
        self.suggestions = []
    
    def scan_all(self) -> Dict[str, any]:
        """Полное сканирование тестовой инфраструктуры."""
        print("🔍 Запуск диагностики тестовой инфраструктуры...")
        print("=" * 60)
        
        results = {
            'pytest_config': self.check_pytest_config(),
            'test_files': self.scan_test_files(),
            'markers': self.check_markers(),
            'naming': self.check_naming_issues(),
            'imports': self.check_imports(),
            'fixtures': self.check_fixtures()
        }
        
        self.generate_report(results)
        return results
    
    def check_pytest_config(self) -> Dict[str, any]:
        """Проверка конфигурации pytest.ini."""
        print("\n📋 Проверка pytest.ini...")
        
        issues = []
        if not self.pytest_ini.exists():
            issues.append("pytest.ini не найден")
            return {'status': 'error', 'issues': issues}
        
        content = self.pytest_ini.read_text(encoding='utf-8')
        
        # Проверка секций
        required_sections = ['[tool:pytest]', 'markers']
        for section in required_sections:
            if section not in content:
                issues.append(f"Отсутствует секция: {section}")
        
        # Проверка asyncio_mode
        if 'asyncio_mode = auto' not in content:
            issues.append("Не настроен asyncio_mode")
        
        # Проверка testpaths
        if 'testpaths = Tests' not in content:
            issues.append("Не настроен testpaths")
        
        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} pytest.ini: {status}")
        
        return {'status': status, 'issues': issues}
    
    def scan_test_files(self) -> Dict[str, any]:
        """Сканирование всех тестовых файлов."""
        print("\n📁 Сканирование тестовых файлов...")
        
        if not self.tests_dir.exists():
            print("   ❌ Директория Tests не найдена")
            return {'status': 'error', 'files': []}
        
        test_files = list(self.tests_dir.glob("test_*.py"))
        test_files.extend(self.tests_dir.glob("*_test.py"))
        
        file_results = []
        for test_file in test_files:
            result = self.analyze_test_file(test_file)
            file_results.append(result)
        
        total_issues = sum(len(r['issues']) for r in file_results)
        status = 'error' if total_issues > 0 else 'ok'
        
        print(f"   {'❌' if total_issues else '✅'} Найдено файлов: {len(test_files)}, проблем: {total_issues}")
        
        return {
            'status': status,
            'files': file_results,
            'total_files': len(test_files),
            'total_issues': total_issues
        }
    
    def analyze_test_file(self, file_path: Path) -> Dict[str, any]:
        """Анализ одного тестового файла."""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            issues = []
            methods = []
            classes = []
            markers = set()
            
            # Поиск тестовых классов и методов
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    classes.append(node.name)
                    
                    # Проверка методов в классе
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                            methods.append(f"{node.name}::{item.name}")
                            
                            # Проверка на "_FIXED" в названии
                            if "_FIXED" in item.name:
                                issues.append(f"Метод содержит '_FIXED' в названии: {item.name}")
                            
                            # Поиск маркеров
                            for decorator in item.decorator_list:
                                if isinstance(decorator, ast.Attribute):
                                    if (isinstance(decorator.value, ast.Attribute) and
                                        decorator.value.attr == 'mark'):
                                        markers.add(decorator.attr)
                
                # Поиск функций уровня модуля
                elif isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    methods.append(node.name)
                    
                    if "_FIXED" in node.name:
                        issues.append(f"Функция содержит '_FIXED' в названии: {node.name}")
            
            # Проверка импортов
            import_issues = self.check_file_imports(content)
            issues.extend(import_issues)
            
            return {
                'file': file_path.name,
                'path': str(file_path),
                'classes': classes,
                'methods': methods,
                'markers': list(markers),
                'issues': issues,
                'status': 'error' if issues else 'ok'
            }
            
        except Exception as e:
            return {
                'file': file_path.name,
                'path': str(file_path),
                'error': str(e),
                'status': 'error',
                'issues': [f"Ошибка парсинга: {e}"]
            }
    
    def check_file_imports(self, content: str) -> List[str]:
        """Проверка импортов в файле."""
        issues = []
        
        # Проверка основных импортов для тестов
        required_imports = ['pytest']
        for imp in required_imports:
            if f"import {imp}" not in content and f"from {imp}" not in content:
                issues.append(f"Отсутствует импорт: {imp}")
        
        return issues
    
    def check_markers(self) -> Dict[str, any]:
        """Проверка маркеров pytest."""
        print("\n🏷️  Проверка маркеров pytest...")
        
        # Получение зарегистрированных маркеров
        registered_markers = self.get_registered_markers()
        
        # Получение используемых маркеров
        used_markers = self.get_used_markers()
        
        # Найти незарегистрированные маркеры
        unregistered = used_markers - registered_markers
        unused = registered_markers - used_markers
        
        issues = []
        if unregistered:
            issues.append(f"Незарегистрированные маркеры: {', '.join(unregistered)}")
        
        warnings = []
        if unused:
            warnings.append(f"Неиспользуемые маркеры: {', '.join(unused)}")
        
        status = 'error' if issues else ('warning' if warnings else 'ok')
        print(f"   {'❌' if issues else '⚠️' if warnings else '✅'} Маркеры: {len(registered_markers)} зарегистрировано, {len(used_markers)} используется")
        
        return {
            'status': status,
            'registered': list(registered_markers),
            'used': list(used_markers),
            'unregistered': list(unregistered),
            'unused': list(unused),
            'issues': issues,
            'warnings': warnings
        }
    
    def get_registered_markers(self) -> Set[str]:
        """Получить зарегистрированные маркеры из pytest.ini."""
        if not self.pytest_ini.exists():
            return set()
        
        content = self.pytest_ini.read_text(encoding='utf-8')
        markers = set()
        
        # Поиск секции markers
        in_markers_section = False
        for line in content.split('\n'):
            line = line.strip()
            
            if line == 'markers =':
                in_markers_section = True
                continue
            
            if in_markers_section:
                if line.startswith('[') or (line and not line.startswith(' ') and '=' in line):
                    break
                
                if ':' in line:
                    marker = line.split(':')[0].strip()
                    if marker:
                        markers.add(marker)
        
        return markers
    
    def get_used_markers(self) -> Set[str]:
        """Получить используемые маркеры из тестовых файлов."""
        markers = set()
        
        if not self.tests_dir.exists():
            return markers
        
        for test_file in self.tests_dir.glob("*.py"):
            try:
                content = test_file.read_text(encoding='utf-8')
                
                # Поиск @pytest.mark.xxx
                marker_pattern = r'@pytest\.mark\.(\w+)'
                found_markers = re.findall(marker_pattern, content)
                markers.update(found_markers)
                
            except Exception:
                continue
        
        return markers
    
    def check_naming_issues(self) -> Dict[str, any]:
        """Проверка проблем с именованием."""
        print("\n📝 Проверка именования...")
        
        issues = []
        fixed_methods = []
        
        if not self.tests_dir.exists():
            return {'status': 'error', 'issues': ['Директория Tests не найдена']}
        
        for test_file in self.tests_dir.glob("*.py"):
            try:
                content = test_file.read_text(encoding='utf-8')
                
                # Поиск методов с _FIXED
                fixed_pattern = r'def (test_\w*_FIXED\w*)\('
                found_fixed = re.findall(fixed_pattern, content)
                
                for method in found_fixed:
                    fixed_methods.append(f"{test_file.name}::{method}")
                    issues.append(f"Метод {method} в {test_file.name} содержит '_FIXED'")
                
            except Exception:
                continue
        
        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} Именование: найдено {len(fixed_methods)} методов с '_FIXED'")
        
        return {
            'status': status,
            'issues': issues,
            'fixed_methods': fixed_methods
        }
    
    def check_imports(self) -> Dict[str, any]:
        """Проверка импортов."""
        print("\n📦 Проверка импортов...")
        
        issues = []
        missing_modules = []
        
        # Проверка основных модулей
        required_modules = ['pytest', 'asyncio', 'unittest.mock']
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
                issues.append(f"Отсутствует модуль: {module}")
        
        status = 'error' if issues else 'ok'
        print(f"   {'❌' if issues else '✅'} Импорты: {len(missing_modules)} отсутствующих модулей")
        
        return {
            'status': status,
            'issues': issues,
            'missing_modules': missing_modules
        }
    
    def check_fixtures(self) -> Dict[str, any]:
        """Проверка фикстур."""
        print("\n🔧 Проверка фикстур...")
        
        conftest_path = self.tests_dir / "conftest.py"
        
        if not conftest_path.exists():
            return {
                'status': 'warning',
                'issues': ['conftest.py не найден'],
                'fixtures': []
            }
        
        try:
            content = conftest_path.read_text(encoding='utf-8')
            
            # Поиск фикстур
            fixture_pattern = r'@pytest\.fixture[^\n]*\ndef (\w+)'
            fixtures = re.findall(fixture_pattern, content)
            
            issues = []
            if len(fixtures) == 0:
                issues.append("Фикстуры не найдены в conftest.py")
            
            status = 'warning' if issues else 'ok'
            print(f"   {'⚠️' if issues else '✅'} Фикстуры: найдено {len(fixtures)}")
            
            return {
                'status': status,
                'issues': issues,
                'fixtures': fixtures
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"Ошибка чтения conftest.py: {e}"],
                'fixtures': []
            }
    
    def generate_report(self, results: Dict[str, any]):
        """Генерация итогового отчета."""
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("=" * 60)
        
        total_issues = 0
        total_warnings = 0
        
        for category, result in results.items():
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                issues = result.get('issues', [])
                warnings = result.get('warnings', [])
                
                total_issues += len(issues)
                total_warnings += len(warnings)
                
                icon = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}.get(status, '❓')
                print(f"{icon} {category.upper()}: {status}")
                
                for issue in issues:
                    print(f"   🔴 {issue}")
                for warning in warnings:
                    print(f"   🟡 {warning}")
        
        print("\n" + "=" * 60)
        print(f"📈 ИТОГО: {total_issues} проблем, {total_warnings} предупреждений")
        
        if total_issues == 0 and total_warnings == 0:
            print("🎉 Тестовая инфраструктура в отличном состоянии!")
        elif total_issues == 0:
            print("👍 Критических проблем не найдено, есть незначительные предупреждения")
        else:
            print("⚠️  Найдены проблемы, требующие исправления")
        
        # Рекомендации
        self.generate_recommendations(results)
    
    def generate_recommendations(self, results: Dict[str, any]):
        """Генерация рекомендаций по исправлению."""
        print("\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        print("-" * 40)
        
        # Проблемы с именованием
        naming = results.get('naming', {})
        if naming.get('fixed_methods'):
            print("1. Исправить названия методов:")
            for method in naming['fixed_methods']:
                clean_name = method.replace('_FIXED', '')
                print(f"   {method} → {clean_name}")
        
        # Проблемы с маркерами
        markers = results.get('markers', {})
        if markers.get('unregistered'):
            print("2. Зарегистрировать маркеры в pytest.ini:")
            for marker in markers['unregistered']:
                print(f"   {marker}: описание маркера")
        
        # Проблемы с импортами
        imports = results.get('imports', {})
        if imports.get('missing_modules'):
            print("3. Установить отсутствующие модули:")
            for module in imports['missing_modules']:
                print(f"   pip install {module}")
        
        print("\n🔧 Для автоматического исправления некоторых проблем запустите:")
        print("   python test_diagnostics.py --fix")
    
    def auto_fix(self):
        """Автоматическое исправление простых проблем."""
        print("🔧 Автоматическое исправление проблем...")
        
        fixed_count = 0
        
        # Исправление методов с _FIXED
        for test_file in self.tests_dir.glob("*.py"):
            try:
                content = test_file.read_text(encoding='utf-8')
                original_content = content
                
                # Замена _FIXED в именах методов
                content = re.sub(r'def (test_\w*)_FIXED(\w*)\(', r'def \1\2(', content)
                
                if content != original_content:
                    test_file.write_text(content, encoding='utf-8')
                    fixed_count += 1
                    print(f"   ✅ Исправлен файл: {test_file.name}")
                    
            except Exception as e:
                print(f"   ❌ Ошибка при исправлении {test_file.name}: {e}")
        
        print(f"\n🎉 Автоматически исправлено проблем: {fixed_count}")
    
    def run_test_discovery(self):
        """Проверка обнаружения тестов pytest."""
        print("\n🔍 Проверка обнаружения тестов pytest...")
        
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', '--collect-only', '-q'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                test_count = len([l for l in lines if '::' in l])
                print(f"   ✅ pytest обнаружил {test_count} тестов")
            else:
                print(f"   ❌ Ошибка обнаружения тестов:")
                print(f"      {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Ошибка запуска pytest: {e}")


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Диагностика тестовой инфраструктуры")
    parser.add_argument('--fix', action='store_true', help='Автоматически исправить простые проблемы')
    parser.add_argument('--test-discovery', action='store_true', help='Проверить обнаружение тестов')
    
    args = parser.parse_args()
    
    diagnostics = TestDiagnostics()
    
    if args.fix:
        diagnostics.auto_fix()
    elif args.test_discovery:
        diagnostics.run_test_discovery()
    else:
        diagnostics.scan_all()


if __name__ == "__main__":
    main()