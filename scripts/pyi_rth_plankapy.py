# PyInstaller runtime hook: stub out plankapy.v1 to avoid circular import issues
import sys
import types


class _DummyPlanka:
    """Stub for plankapy.v1.Planka to satisfy root __init__.py"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "plankapy.v1 is not available in this build; use plankapy.v2"
        )


class _DummyPasswordAuth:
    """Stub for plankapy.v1.PasswordAuth to satisfy root __init__.py"""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "plankapy.v1 is not available in this build; use plankapy.v2"
        )


# Create a dummy v1 module to satisfy plankapy's root __init__.py
v1_stub = types.ModuleType("plankapy.v1")
v1_stub.Planka = _DummyPlanka
v1_stub.PasswordAuth = _DummyPasswordAuth
sys.modules["plankapy.v1"] = v1_stub
