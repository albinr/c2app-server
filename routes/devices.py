# routes/devices.py
import json
import asyncio

from quart import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, websocket
from quart_auth import login_required, current_user
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models import Device, DeviceRequest
from config import Config
from nominatim import get_location_from_coordinates
from utils.websocket_manager import add_client, get_client, remove_client, get_all_clients

device_routes = Blueprint('device_routes', __name__)

open_terminals = {}

@device_routes.route('/devices')
@login_required
async def devices():
    async with Config.AsyncSessionLocal() as session:
        deviceResult = await session.execute(select(Device))
        devices = deviceResult.scalars().all()

        requestResult = await session.execute(
            select(DeviceRequest).options(joinedload(DeviceRequest.device)).filter_by(status='pending', request_type='rejoin_watchlist')
        )
        requests = requestResult.scalars().all()

        def sort_key(device):
            if not device.on_watchlist:
                return 2
            elif device.is_online():
                return 0
            elif not device.is_online():
                return 1

        devices.sort(key=sort_key)

    return await render_template("devices.html", devices=devices, requests=requests)

@device_routes.route('/request/<int:id>/approve', methods=['POST'])
@login_required
async def approve_rejoin_request(id):
    async with Config.AsyncSessionLocal() as session:
        request_result = await session.execute(
            select(DeviceRequest).options(joinedload(DeviceRequest.device)).filter_by(id=id)
        )
        request = request_result.scalars().first()

        if request and request.status == 'pending':
            request.status = 'approved'
            request.resolved = True
            request.resolved_timestamp = func.current_timestamp()
            
            if request.device:
                request.device.on_watchlist = True

            await session.commit()

            await flash(f"Rejoin request for {request.device.device_name} approved.", 'success')
        else:
            await flash("Request not found or already processed.", 'error')

    return redirect(url_for('routes.device_routes.devices'))

@device_routes.route('/request/<int:id>/deny', methods=['POST'])
@login_required
async def deny_rejoin_request(id):
    async with Config.AsyncSessionLocal() as session:
        request_result = await session.execute(
            select(DeviceRequest).options(joinedload(DeviceRequest.device)).filter_by(id=id)
        )
        request = request_result.scalars().first()

        if request and request.status == 'pending':
            request.status = 'denied'
            request.resolved = True
            request.resolved_timestamp = func.current_timestamp()

            await session.commit()

            await flash(f"Rejoin request for {request.device.device_name} denied.", 'success')
        else:
            await flash("Request not found or already processed.", 'error')

    return redirect(url_for('routes.device_routes.devices'))

@device_routes.route('/devices/<int:id>')
@login_required
async def single_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        if device.geo_location:
            device.country, device.city = get_location_from_coordinates(device.geo_location)
        else:
            device.address = "Location not available"
    return await render_template("single-device.html", device=device)

@device_routes.route('/device/<int:id>/delete', methods=['POST'])
@login_required
async def post_delete_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        await session.delete(device)
        await session.commit()
        current_app.logger.info(f"User {current_user.auth_id} deleted device {device.device_name}.")
        await flash(f"Device {device.device_name} deleted successfully!")
    return redirect(url_for('routes.device_routes.devices'))

@device_routes.route('/device/<int:id>/toggle_watchlist', methods=['POST'])
@login_required
async def post_toggle_watchlist_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        if device:
            device.on_watchlist = not device.on_watchlist
            await session.commit()
            action = "added to" if device.on_watchlist else "removed from"
            current_app.logger.info(f"User {current_user.auth_id} {action} the watchlist for device {device.device_name}.")
            await flash(f"Device {device.device_name} has been {action} the watchlist successfully!")
        else:
            await flash(f"Device with ID {id} not found.", 'error')
    return redirect(url_for('routes.device_routes.devices'))

@device_routes.route('/device/<int:id>/toggle_restrict', methods=['POST'])
@login_required
async def post_toggle_restrict_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        if device:
            device.can_view_info = not device.can_view_info
            await session.commit()
            action = "unrestricted" if device.can_view_info else "restricted"
            current_app.logger.info(f"User {current_user.auth_id} {action} device {device.device_name}.")
            await flash(f"Device {device.device_name} has been {action} successfully!")
        else:
            await flash(f"Device with ID {id} not found.", 'error')
    return redirect(url_for('routes.device_routes.devices'))

@device_routes.route('/device/info', methods=['GET'])
async def get_device_info():
    hardware_id = request.args.get("hardware_id")
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, hardware_id)
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        if not device.on_watchlist:
            return jsonify({"error": "Device is off the watchlist"}), 403

        if not device.can_view_info:
            return jsonify({"error": "Device is restricted from viewing information"}), 403
        
        return jsonify({"device_info": device.to_dict()})

@device_routes.route('/device/update', methods=['POST'])
async def api_update_device():
    try:
        data = await request.json
        hardware_id = data.get('hardware_id')

        if not hardware_id:
            return jsonify({"error": "Hardware ID is required"}), 400

        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
            device = result.scalars().first()

            if not device:
                return jsonify({"error": "Device not found."}), 404

            if not device.on_watchlist:
                return jsonify({"error": "Device is off the watchlist."}), 403

            device.device_name = data.get('device_name', device.device_name)
            device.os_version = data.get('os_version', device.os_version)
            await session.commit()

            return jsonify({"message": f"Device {device.device_name} updated successfully."}), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@device_routes.route('/device', methods=['POST'])
async def api_add_device():
    try:
        data = await request.json
        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=data['hardware_id']))
            existing_device = result.scalars().first()

            if existing_device:
                return jsonify({"error": "A device with this hardware ID already exists."}), 400

            new_device = Device(
                device_name=data['device_name'],
                os_version=data['os_version'],
                hardware_id=data['hardware_id'],
                geo_location=data.get('geo_location'),
                installed_apps=','.join(data.get('installed_apps', []))
            )
            current_app.logger.info(f"New device: {new_device.device_name} added to database.")
            session.add(new_device)
            await session.commit()

            return jsonify({"message": "Device added successfully."}), 201

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 400
    
@device_routes.route('/device/heartbeat', methods=['POST'])
async def api_device_heartbeat():
    try:
        data = await request.json
        hardware_id = data.get('hardware_id')

        if not hardware_id:
            return jsonify({"error": "Hardware ID is required"}), 400

        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
            device = result.scalars().first()

            if not device:
                current_app.logger.info(f"Received heartbeat from unknown device.")
                return jsonify({"error": "Device not found"}), 404
            
            if not device.on_watchlist:
                current_app.logger.info(f"Device {device.device_name} off the watchlist tried to send heartbeat.")
                return jsonify({
                    "error": "This device is off the watchlist.",
                    "on_watchlist": device.on_watchlist,
                }), 403

            device.last_heartbeat = func.current_timestamp()
            await session.commit()

            # Check if the client is already connected via WebSocket
            is_socket_open = open_terminals.get(device.hardware_id, False)

            current_app.logger.info(f"Received heartbeat from {device.device_name}.")
            return jsonify({
                "message": f"Heartbeat for device {device.device_name} received!",
                "on_watchlist": device.on_watchlist,
                "open_socket": is_socket_open
            }), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@device_routes.route('/device/can_view', methods=['POST'])
async def api_can_device_view():
    try:
        data = await request.json
        hardware_id = data.get('hardware_id')

        if not hardware_id:
            return jsonify({"error": "Hardware ID is required"}), 400

        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
            device = result.scalars().first()

            if not device:
                return jsonify({"error": "Device not found"}), 404

            if not device.on_watchlist:
                return jsonify({"error": "Device is off the watchlist"}), 403

            current_app.logger.info(f"Can device view info? {device.can_view_info}")
            return jsonify({'can_view': device.can_view_info})

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@device_routes.route('/device/rejoin', methods=['POST'])
async def request_watchlist_rejoin():
    try:
        data = await request.get_json()
        hardware_id = data.get('hardware_id')
        
        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
            device = result.scalars().first()

            if device and not device.on_watchlist:
                existing_request = await session.execute(
                    select(DeviceRequest).filter_by(device_id=device.id, status='pending')
                )
                if existing_request.scalar():
                    return jsonify({"message": "A rejoin request is already pending."}), 400

                new_request = DeviceRequest(device_id=device.id, status='pending', request_type='rejoin_watchlist')
                session.add(new_request)
                await session.commit()

                current_app.logger.info(f"Device {device.device_name} requested to be re-added to the watchlist.")
                return jsonify({"message": "Rejoin request submitted."}), 200

            return jsonify({"message": "Device is already on the watchlist or does not exist."}), 400
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@device_routes.route('/devices/<int:id>/terminal')
@login_required
async def device_terminal(id):
    """Render a terminal interface for a specific device."""
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        
        if not device:
            await flash("Device not found.", 'error')
            return redirect(url_for('device_routes.devices'))
        
        open_terminals[device.hardware_id] = True

        current_app.logger.info(f"User {current_user} opened a terminal for {device.device_name}")
        
        return await render_template('device_terminal.html', device=device)

@device_routes.route('/devices/<int:id>/terminal/close', methods=['POST'])
@login_required
async def close_device_terminal(id):
    """Close the terminal interface for a specific device."""
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        if device:
            websocket_client = await get_client(device.hardware_id)
            if websocket_client:
                await websocket_client.send(json.dumps({
                    "type": "disconnect",
                    "message": "The terminal for this device has been closed."
                }))
                await websocket_client.close(code=1000)

            open_terminals[device.hardware_id] = False
            await remove_client(device.hardware_id)
            await flash(f"Terminal for {device.device_name} closed.", 'success')
        else:
            await flash("Device not found.", 'error')
        current_app.logger.info(f"User {current_user} closed a terminal for {device.device_name}")
    
    return redirect(url_for('routes.device_routes.devices'))


@device_routes.websocket('/ws/device/<hardware_id>')
async def device_websocket(hardware_id):
    client = websocket._get_current_object()
    await add_client(hardware_id, client)

    try:
        while True:
            message = await client.receive()
            if message:
                data = json.loads(message)
                if data.get("type") == "command":
                    command = data.get("command")
                    current_app.logger.info(f"Received command '{command}' for {hardware_id}")
                elif data.get("type") == "command_result":
                    result = data.get("result")
                    current_app.logger.info(f"Command result received for {hardware_id}: {result}")

                    admin_client = await get_client("admin")
                    if admin_client:
                        await admin_client.send(json.dumps({
                            "type": "command_result",
                            "hardware_id": hardware_id,
                            "result": result
                        }))
                    else:
                        current_app.logger.info("No admin client connected to receive command result")
                elif data.get("type") == "disconnect":
                    await client.send(json.dumps({"type": "disconnect", "message": "Server requested disconnect"}))
                    break

    except asyncio.CancelledError:
        current_app.logger.info(f"WebSocket connection cancelled for {hardware_id}.")
    except Exception as e:
        current_app.logger.error(f"WebSocket error with {hardware_id}: {str(e)}")
    finally:
        open_terminals.pop(hardware_id, None)
        await remove_client(hardware_id)
        if not client.close:
            try:
                await client.close(code=1000)
            except RuntimeError as e:
                current_app.logger.error(f"Error closing WebSocket for {hardware_id}: {e}")
        current_app.logger.info(f"WebSocket connection closed for {hardware_id}")

@device_routes.websocket('/ws/admin')
async def admin_websocket():
    admin_client = websocket._get_current_object()
    await add_client("admin", admin_client)
    try:
        while True:
            message = await admin_client.receive()
            if message:
                data = json.loads(message)
                if data.get("type") == "command":
                    hardware_id = data.get("hardware_id")
                    command = data.get("command")
                    current_app.logger.info(f"Admin sent command '{command}' to device {hardware_id}")

                    device_client = await get_client(hardware_id)
                    if device_client:
                        await device_client.send(json.dumps({"type": "command", "command": command}))
                        # await admin_client.send(json.dumps({"type": "success", "message": f"Command sent to {hardware_id}"}))
                    else:
                        await admin_client.send(json.dumps({"type": "error", "message": f"Device {hardware_id} not connected."}))

    except Exception as e:
        current_app.logger.error(f"WebSocket error with admin interface: {str(e)}")
    finally:
        await remove_client("admin") 
