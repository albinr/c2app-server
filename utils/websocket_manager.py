import asyncio

connected_clients = {}
client_lock = asyncio.Lock()

async def add_client(hardware_id, websocket):
    """Add a client connection to the manager."""
    async with client_lock:
        connected_clients[hardware_id] = websocket

async def remove_client(hardware_id):
    """Remove a client connection from the manager."""
    async with client_lock:
        connected_clients.pop(hardware_id, None)

async def get_client(hardware_id):
    """Retrieve a client connection."""
    async with client_lock:
        return connected_clients.get(hardware_id)

async def is_client_connected(hardware_id):
    """Check if a device is connected via WebSocket."""
    async with client_lock:
        return hardware_id in connected_clients
