"""Lightweight test runner for the repository to avoid external pytest dependency.

This runner imports test modules under `tests` and executes functions whose
names start with `test_`. It will print a short report and exit with non-zero
status if any test fails.
"""
import importlib
import pkgutil
import sys
import traceback


def find_test_modules(package_name="tests"):
    mods = []
    pkg = importlib.import_module(package_name)
    prefix = pkg.__name__ + "."
    for _, modname, ispkg in pkgutil.iter_modules(pkg.__path__, prefix):
        if not ispkg:
            mods.append(modname)
    return mods


def run_tests():
    failures = []
    modules = find_test_modules()
    if not modules:
        print("No test modules found under 'tests' package.")
        return 0

    for modname in modules:
        mod = importlib.import_module(modname)
        for name in dir(mod):
            if name.startswith("test_"):
                obj = getattr(mod, name)
                if callable(obj):
                    try:
                        obj()
                        print(f"PASS: {modname}.{name}")
                    except AssertionError as e:
                        print(f"FAIL: {modname}.{name} -- AssertionError: {e}")
                        failures.append((modname, name, e, traceback.format_exc()))
                    except Exception as e:
                        print(f"ERROR: {modname}.{name} -- Exception: {e}")
                        failures.append((modname, name, e, traceback.format_exc()))

    if failures:
        print(f"\n{len(failures)} test(s) failed.")
        for modname, name, exc, tb in failures:
            print("---")
            print(modname, name)
            print(tb)
        return 1

    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
