"""Stub de IPython embebido — DESACTIVADO en la migracion a Python 3.

El widget original (Accerciser, ~2008) usaba IPython.Shell.InteractiveShell
y una API que ya no existe. El cliente confirmo no necesitar esta
funcionalidad (solo usa la GUI). Si en el futuro se quiere reactivar,
considerar jupyter_client + un widget de terminal GTK3.
"""


class IPythonView:
    """Placeholder que no hace nada. Mantiene la API minima para no romper imports."""

    def __init__(self, *args, **kwargs):
        pass

    def modify_font(self, *args, **kwargs):
        pass

    def set_wrap_mode(self, *args, **kwargs):
        pass

    def updateNamespace(self, *args, **kwargs):
        pass

    def show(self):
        pass
