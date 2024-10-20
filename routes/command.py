import aiofiles
import asyncio
from quart import Blueprint, render_template, websocket, flash, redirect, url_for, current_app
from quart_auth import login_required

command_connections = set()

command_routes = Blueprint('command_routes', __name__)

@command_routes.route('/logs')
@login_required
async def view_logs():
    try:
        async with aiofiles.open('logs/server.log', 'r') as log_file:
            logs = await log_file.readlines()
        return await render_template('logs.html', logs=logs)
    except Exception as e:
        await flash(f"Could not open log file: {str(e)}", 'error')
        return redirect(url_for('routes.main'))

@command_routes.websocket('/ws/logs')
@login_required
async def ws_logs():
    log_connections.add(websocket._get_current_object())
    try:
        while True:
            await asyncio.sleep(1)
            async with aiofiles.open('logs/server.log', 'r') as log_file:
                logs = await log_file.readlines()
                await websocket.send_json({"logs": logs})
    except Exception as e:
        current_app.logger.error(f"WebSocket error: {str(e)}")
    finally:
        log_connections.remove(websocket._get_current_object())