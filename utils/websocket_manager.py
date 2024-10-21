# utils/websocket_manager.py

import asyncio
from quart import current_app

connected_clients = {}
client_lock = asyncio.Lock()

async def add_client(hardware_id, websocket):
    async with client_lock:
        connected_clients[hardware_id] = websocket
        current_app.logger.info(f"Client added: {hardware_id}")

async def remove_client(hardware_id):
    """Remove a client connection from the manager."""
    async with client_lock:
        connected_clients.pop(hardware_id, None)

async def get_client(hardware_id):
    """Retrieve a client connection."""
    async with client_lock:
        return connected_clients.get(hardware_id)
    
async def get_all_clients():
    """Retrieve a client connection."""
    return connected_clients
