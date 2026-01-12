import json
import logging
import os
from collections import OrderedDict
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket Connection Manager.

    Tracks active connections and allows broadcasting messages by run_id/job_id.
    Includes a ring-buffer for message persistence to support reconnection.

    Memory Management:
    - LRU eviction (max runs in memory, configurable via FAIC_WS_RUN_LOG_MAX_RUNS)
    - Per-run event limits (configurable via FAIC_WS_RUN_LOG_MAX_EVENTS_PER_RUN)
    """
    def __init__(self, max_history: int = None, max_runs: int = None):
        # run_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

        # Memory management configuration
        self.max_history = max_history or int(os.getenv("FAIC_WS_RUN_LOG_MAX_EVENTS_PER_RUN", "1000"))
        self.max_runs = max_runs or int(os.getenv("FAIC_WS_RUN_LOG_MAX_RUNS", "100"))

        # run_id -> list of recent messages (ring-buffer)
        # OrderedDict for LRU tracking (insertion order = access order via move_to_end)
        self.history: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()

        logger.info(
            f"ConnectionManager initialized: max_runs={self.max_runs}, "
            f"max_events_per_run={self.max_history}"
        )

    async def connect(self, websocket: WebSocket, run_id: str, last_event_id: str = None):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        logger.info(f"WebSocket connected for run_id: {run_id}")

        # Mark run as recently accessed (LRU)
        if run_id in self.history:
            self.history.move_to_end(run_id)

        # If last_event_id is provided, send missed messages from history
        if last_event_id and run_id in self.history:
            missed_messages = []
            found = False
            for msg in self.history[run_id]:
                if found:
                    missed_messages.append(msg)
                elif msg.get("event_id") == last_event_id:
                    found = True

            # If not found (or was the last one), we might have missed some if it was purged
            # For now, if not found, we send nothing or could send all
            for msg in missed_messages:
                await websocket.send_text(json.dumps(msg))

    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
                # Keep history for a while even after last disconnect?
                # For now, let's keep it until explicitly cleared or memory management kicks in
        logger.info(f"WebSocket disconnected for run_id: {run_id}")

    def _evict_oldest_run(self) -> None:
        """
        Evict the oldest run from history (LRU policy).

        Prioritizes evicting runs with no active connections.
        """
        # First, try to evict runs without active connections
        for run_id in list(self.history.keys()):
            if run_id not in self.active_connections or not self.active_connections[run_id]:
                # Evict this run (no active clients)
                del self.history[run_id]
                logger.debug(
                    f"[ConnectionManager] LRU eviction: run_id={run_id} (no active connections), "
                    f"new_size={len(self.history)}"
                )
                return

        # If all runs have active connections, evict oldest anyway
        if self.history:
            evicted_run_id, _ = self.history.popitem(last=False)  # Remove oldest
            logger.warning(
                f"[ConnectionManager] LRU eviction: run_id={evicted_run_id} (had active connections), "
                f"new_size={len(self.history)}"
            )

    def _enforce_run_limit(self) -> None:
        """
        Enforce max runs in memory limit via LRU eviction.

        Called before adding new runs to ensure we stay under the limit.
        """
        while len(self.history) >= self.max_runs:
            self._evict_oldest_run()

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_run(self, run_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all clients interested in a specific run_id.

        Enforces run limit via LRU eviction before adding new run.
        """
        # Enforce run limit before adding new run
        if run_id not in self.history:
            self._enforce_run_limit()

        # Mark run as recently accessed (LRU)
        if run_id in self.history:
            self.history.move_to_end(run_id)

        # Store in history first
        if run_id not in self.history:
            self.history[run_id] = []

        self.history[run_id].append(message)

        # Enforce per-run event limit (FIFO eviction)
        if len(self.history[run_id]) > self.max_history:
            evicted = self.history[run_id].pop(0)
            logger.debug(
                f"[ConnectionManager] Run {run_id} history full ({self.max_history}), evicted oldest event"
            )

        if run_id in self.active_connections:
            msg_json = json.dumps(message)
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_text(msg_json)
                except Exception as e:
                    logger.error(f"Error sending websocket message: {e}")
                    # Disconnect will happen when the connection is closed

manager = ConnectionManager()
