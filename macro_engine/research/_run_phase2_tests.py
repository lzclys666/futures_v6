"""运行 Phase 2 所有测试"""
import sys
sys.path.insert(0, r'D:\futures_v6\macro_engine\research')
import unittest

# Import by filename without extension trick
import importlib.util
spec = importlib.util.spec_from_file_location(
    "phase2_mod", 
    r'D:\futures_v6\macro_engine\research\phase2_statistical_modules.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Run tests
loader = unittest.TestLoader()
suite = loader.loadTestsFromModule(module)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Summary
passed = result.testsRun - len(result.failures) - len(result.errors)
failed = len(result.failures) + len(result.errors)
print(f'\n=== Summary: {passed} passed, {failed} failed, {result.testsRun} total ===')
if result.failures:
    print('FAILURES:')
    for test, tb in result.failures:
        print(f'  FAIL: {test}')
if result.errors:
    print('ERRORS:')
    for test, tb in result.errors:
        print(f'  ERROR: {test}')
