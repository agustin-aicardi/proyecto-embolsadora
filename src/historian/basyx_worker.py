"""Actualizacion de BaSyx en segundo plano, sin bloquear el historian."""

from __future__ import annotations

import threading
from typing import Any, Callable


class BaSyxWorker:
    def __init__(
        self,
        updater: Any,
        on_error: Callable[[Exception], None] | None = None,
    ):
        self.updater = updater
        self.on_error = on_error
        self._condition = threading.Condition()
        self._pending: dict[str, Any] | None = None
        self._stopping = False
        self._thread = threading.Thread(
            target=self._run,
            name="basyx-worker",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, values: dict[str, Any]) -> None:
        """Conserva los valores mas recientes sin bloquear por HTTP."""
        with self._condition:
            if self._stopping:
                return
            if self._pending is None:
                self._pending = dict(values)
            else:
                self._pending.update(values)
            self._condition.notify()

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._stopping:
                    self._condition.wait()

                if self._stopping:
                    return

                values = self._pending
                self._pending = None

            try:
                self.updater.update_from_dict(values)
            except Exception as ex:
                if self.on_error is not None:
                    try:
                        self.on_error(ex)
                    except Exception:
                        pass

    def stop(self) -> None:
        """Solicita detener el worker sin esperar solicitudes HTTP."""
        with self._condition:
            self._stopping = True
            self._pending = None
            self._condition.notify_all()
