"""Central thread/task manager used by the application UI and diagnostics."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable

from PyQt5.QtCore import QObject, QThread, pyqtSignal


class ManagedTaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ThreadSnapshot:
    """Runtime information exposed to the diagnostics UI."""

    name: str
    status: ManagedTaskStatus = ManagedTaskStatus.IDLE
    started_at: float | None = None
    finished_at: float | None = None
    last_duration_s: float | None = None
    total_runtime_s: float = 0.0
    start_count: int = 0
    last_error: str | None = None
    is_asyncio_loop: bool = False
    origin: str = "managed"


class Worker(QObject):
    """Execute a callable in a dedicated Qt thread."""

    status = pyqtSignal(str)
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.abort = False

    def run(self) -> None:
        logger = logging.getLogger("RSPdx.ThreadManager.Worker")
        func_name = getattr(self.func, "__name__", str(self.func))
        try:
            self.status.emit(f"START {func_name}")
            logger.info("START %s", func_name)
            if not self.abort:
                result = self.func(*self.args, **self.kwargs)
                self.result.emit(result)
        except Exception as exc:  # pragma: no cover - driven by runtime failures
            logger.exception("ERROR %s", func_name)
            self.error.emit(str(exc))
        finally:
            self.status.emit(f"FINISH {func_name}")
            logger.info("FINISH %s", func_name)
            self.finished.emit()


class ThreadManager(QObject):
    """Manage background Qt workers and expose diagnostics to the GUI."""

    diagnostics_changed = pyqtSignal()
    thread_registered = pyqtSignal(str)
    thread_finished = pyqtSignal(str)
    thread_failed = pyqtSignal(str, str)
    worker_status = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.threads: dict[str, QThread] = {}
        self.workers: dict[str, Worker] = {}
        self.asyncio_loops: dict[str, Any] = {}
        self.stats: dict[str, ThreadSnapshot] = {}
        self._external_threads: dict[str, threading.Thread] = {}
        self.logger = logging.getLogger("RSPdx.ThreadManager")

    def start_thread(self, thread_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Worker:
        """Start a callable in a Qt-managed worker thread."""
        if thread_name in self.asyncio_loops and self.asyncio_loops.get(thread_name) is not None:
            self.logger.info("Asyncio loop '%s' already active", thread_name)
            return self.workers.get(thread_name)

        existing = self.threads.get(thread_name)
        if existing is not None:
            if existing.isRunning():
                self.logger.info("Thread '%s' already running", thread_name)
                return self.workers[thread_name]
            try:
                existing.quit()
                existing.wait(500)
            except Exception:
                pass
            self.threads.pop(thread_name, None)
            self.workers.pop(thread_name, None)

        thread = QThread()
        worker = Worker(func, *args, **kwargs)
        worker.moveToThread(thread)

        snapshot = self._ensure_snapshot(thread_name, origin="managed")
        snapshot.status = ManagedTaskStatus.RUNNING
        snapshot.started_at = time.time()
        snapshot.finished_at = None
        snapshot.start_count += 1
        snapshot.last_error = None

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda name=thread_name: self._cleanup_thread(name))
        worker.error.connect(lambda msg, name=thread_name: self._record_error(name, msg))
        worker.status.connect(lambda msg, name=thread_name: self._on_worker_status(name, msg))

        self.threads[thread_name] = thread
        self.workers[thread_name] = worker

        thread.start()
        self.thread_registered.emit(thread_name)
        self.diagnostics_changed.emit()
        self.logger.info("Thread '%s' started", thread_name)
        return worker

    def stop_thread(self, thread_name: str) -> None:
        """Stop a managed worker thread if it exists."""
        if thread_name in self.asyncio_loops:
            self.stop_asyncio_loop(thread_name)

        worker = self.workers.get(thread_name)
        thread = self.threads.get(thread_name)
        if worker is not None and thread is not None:
            worker.abort = True
            thread.quit()
            thread.wait(1000)
            snapshot = self._ensure_snapshot(thread_name)
            snapshot.status = ManagedTaskStatus.STOPPED
            snapshot.finished_at = time.time()
            if snapshot.started_at:
                snapshot.last_duration_s = max(0.0, snapshot.finished_at - snapshot.started_at)
                snapshot.total_runtime_s += snapshot.last_duration_s
            self.diagnostics_changed.emit()
            self.logger.info("Thread '%s' stopped", thread_name)

        self.unregister_external_thread(thread_name)

    def stop_all_threads(self) -> None:
        """Stop all managed and externally tracked threads."""
        for loop_name in list(self.asyncio_loops.keys()):
            self.stop_asyncio_loop(loop_name)
        for thread_name in list(self.threads.keys()):
            self.stop_thread(thread_name)
        for thread_name in list(self._external_threads.keys()):
            self.unregister_external_thread(thread_name, status=ManagedTaskStatus.STOPPED)
        self.logger.info("All threads stopped")

    def get_worker(self, thread_name: str) -> Worker | None:
        return self.workers.get(thread_name)

    def register_external_thread(self, thread_name: str, thread: threading.Thread | None = None) -> None:
        """Track a non-Qt thread for diagnostics purposes."""
        snapshot = self._ensure_snapshot(thread_name, origin="external")
        snapshot.status = ManagedTaskStatus.RUNNING
        snapshot.started_at = time.time()
        snapshot.finished_at = None
        snapshot.start_count += 1
        snapshot.last_error = None
        if thread is not None:
            self._external_threads[thread_name] = thread
        self.thread_registered.emit(thread_name)
        self.diagnostics_changed.emit()

    def unregister_external_thread(
        self,
        thread_name: str,
        status: ManagedTaskStatus = ManagedTaskStatus.FINISHED,
        error: str | None = None,
    ) -> None:
        """Mark an externally managed thread as finished."""
        snapshot = self.stats.get(thread_name)
        if snapshot is None:
            return
        if snapshot.status != ManagedTaskStatus.RUNNING and error is None and status == ManagedTaskStatus.FINISHED:
            self._external_threads.pop(thread_name, None)
            return
        if snapshot.status == ManagedTaskStatus.RUNNING and snapshot.started_at:
            snapshot.finished_at = time.time()
            snapshot.last_duration_s = max(0.0, snapshot.finished_at - snapshot.started_at)
            snapshot.total_runtime_s += snapshot.last_duration_s
        snapshot.status = status
        if error:
            snapshot.last_error = error
        self._external_threads.pop(thread_name, None)
        self.thread_finished.emit(thread_name)
        self.diagnostics_changed.emit()

    def get_diagnostics(self) -> dict[str, dict[str, Any]]:
        output: dict[str, dict[str, Any]] = {}
        for name, snapshot in self.stats.items():
            data = asdict(snapshot)
            data["status"] = snapshot.status.value
            output[name] = data
        return output

    def diagnostics_summary(self) -> str:
        if not self.stats:
            return "No thread diagnostics available."
        lines = []
        for name, snapshot in sorted(self.stats.items()):
            last = "-" if snapshot.last_duration_s is None else f"{snapshot.last_duration_s:.3f}s"
            total = f"{snapshot.total_runtime_s:.3f}s"
            lines.append(
                f"- {name} [{snapshot.origin}] {snapshot.status.value.upper()} | "
                f"starts={snapshot.start_count} | last={last} | total={total} | "
                f"last_error={snapshot.last_error or '-'}"
            )
        return "Thread diagnostics:\n" + "\n".join(lines)

    def ensure_asyncio_loop(self, loop_name: str = "AxisCoreLoop", timeout: float = 5.0) -> None:
        """Start and track a persistent asyncio loop inside a managed Qt thread."""
        if loop_name in self.asyncio_loops and self.asyncio_loops.get(loop_name) is not None:
            return
        if loop_name in self.threads:
            self.stop_thread(loop_name)
            self.threads.pop(loop_name, None)
            self.workers.pop(loop_name, None)

        import asyncio as _asyncio

        ready_event = threading.Event()

        def loop_entry() -> None:
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            self.asyncio_loops[loop_name] = loop
            ready_event.set()
            try:
                loop.run_forever()
            finally:
                try:
                    loop.close()
                finally:
                    self.asyncio_loops.pop(loop_name, None)

        self.start_thread(loop_name, loop_entry)
        self._ensure_snapshot(loop_name).is_asyncio_loop = True
        if not ready_event.wait(timeout=timeout):
            self.logger.error("Asyncio loop '%s' did not start in time", loop_name)

    def run_coro(self, loop_name: str, coro_or_factory: Any, timeout: float | None = None) -> Any:
        import asyncio as _asyncio

        self.ensure_asyncio_loop(loop_name)
        loop = self.asyncio_loops.get(loop_name)
        if loop is None:
            raise RuntimeError(f"Asyncio loop '{loop_name}' is not available")
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        future = _asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout) if timeout is not None else future.result()

    def stop_asyncio_loop(self, loop_name: str) -> None:
        loop = self.asyncio_loops.get(loop_name)
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass

    def _ensure_snapshot(self, thread_name: str, origin: str | None = None) -> ThreadSnapshot:
        snapshot = self.stats.get(thread_name)
        if snapshot is None:
            snapshot = ThreadSnapshot(name=thread_name)
            self.stats[thread_name] = snapshot
        if origin is not None:
            snapshot.origin = origin
        return snapshot

    def _cleanup_thread(self, thread_name: str) -> None:
        snapshot = self.stats.get(thread_name)
        if snapshot and snapshot.status == ManagedTaskStatus.RUNNING:
            snapshot.finished_at = time.time()
            if snapshot.started_at:
                snapshot.last_duration_s = max(0.0, snapshot.finished_at - snapshot.started_at)
                snapshot.total_runtime_s += snapshot.last_duration_s
            snapshot.status = ManagedTaskStatus.FINISHED if snapshot.last_error is None else ManagedTaskStatus.FAILED

        self.threads.pop(thread_name, None)
        self.workers.pop(thread_name, None)
        self.thread_finished.emit(thread_name)
        self.diagnostics_changed.emit()

    def _record_error(self, thread_name: str, msg: str) -> None:
        snapshot = self._ensure_snapshot(thread_name)
        snapshot.last_error = msg
        snapshot.status = ManagedTaskStatus.FAILED
        self.thread_failed.emit(thread_name, msg)
        self.diagnostics_changed.emit()
        self.logger.error("[%s] %s", thread_name, msg)

    def _on_worker_status(self, thread_name: str, message: str) -> None:
        self.worker_status.emit(thread_name, message)
        self.diagnostics_changed.emit()
