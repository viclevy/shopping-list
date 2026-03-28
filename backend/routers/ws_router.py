from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth import decode_token
from websocket_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    user_id = int(payload["sub"])
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; we don't expect client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
