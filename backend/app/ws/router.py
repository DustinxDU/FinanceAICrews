"""WebSocket endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from AICrews.services.realtime_ws_manager import get_realtime_ws_manager
from backend.app.ws.run_log_manager import manager as run_log_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def _handle_run_log_ws(websocket: WebSocket, run_id: str) -> None:
    last_event_id = websocket.query_params.get("last_event_id")
    await run_log_ws_manager.connect(websocket, run_id, last_event_id=last_event_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        run_log_ws_manager.disconnect(websocket, run_id)
    except Exception as exc:
        logger.error("Run log WebSocket error for %s: %s", run_id, exc, exc_info=True)
        run_log_ws_manager.disconnect(websocket, run_id)


@router.websocket("/api/v1/realtime/ws/analysis/{run_id}")
async def websocket_analysis_realtime(websocket: WebSocket, run_id: str) -> None:
    """WebSocket 实时日志推送（推荐路径）"""
    await _handle_run_log_ws(websocket, run_id)


@router.websocket("/ws/analysis/{run_id}")
async def websocket_analysis_legacy(websocket: WebSocket, run_id: str) -> None:
    """WebSocket 实时日志推送（兼容旧路径）"""
    await _handle_run_log_ws(websocket, run_id)


def _parse_tickers_param(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    tickers = [t.strip().upper() for t in value.split(",") if t.strip()]
    return tickers or None


async def _handle_price_ws(websocket: WebSocket) -> None:
    ws_manager = get_realtime_ws_manager()
    tickers = _parse_tickers_param(websocket.query_params.get("tickers"))

    try:
        await ws_manager.connect_price(websocket, tickers=tickers)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_price(websocket)
    except Exception as exc:
        logger.error("Price WebSocket error: %s", exc, exc_info=True)
        ws_manager.disconnect_price(websocket)


@router.websocket("/api/v1/realtime/ws/price")
async def websocket_price_realtime(websocket: WebSocket) -> None:
    """实时价格推送 WebSocket（推荐路径）"""
    await _handle_price_ws(websocket)


@router.websocket("/ws/price")
async def websocket_price_legacy(websocket: WebSocket) -> None:
    """实时价格推送 WebSocket（兼容旧路径）"""
    await _handle_price_ws(websocket)

