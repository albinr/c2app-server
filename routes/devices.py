from quart import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from sqlalchemy.future import select
from sqlalchemy import func
from models import Device
from config import Config
from nominatim import get_location_from_coordinates
from quart_auth import login_required, current_user

device_routes = Blueprint('device_routes', __name__)

@device_routes.route('/devices')
@login_required
async def devices():
    async with Config.AsyncSessionLocal() as session:
        result = await session.execute(select(Device))
        devices = result.scalars().all()
        def sort_key(device):
            if not device.on_watchlist:
                return 2
            elif device.is_online():
                return 0
            elif not device.is_online():
                return 1

        devices.sort(key=sort_key)
    return await render_template("devices.html", devices=devices)

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

# @device_routes.route('/device/update', methods=['POST'])
# async def api_update_device():
#     try:
#         data = await request.json
#         hardware_id = data.get('hardware_id')

#         if not hardware_id:
#             return jsonify({"error": "Hardware ID is required"}), 400

#         async with Config.AsyncSessionLocal() as session:
#             result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
#             device = result.scalars().first()

#             if not device:
#                 return jsonify({"error": "Device not found."}), 404

#             if not device.on_watchlist:
#                 return jsonify({"error": "Device is off the watchlist."}), 403

#             device.device_name = data.get('device_name', device.device_name)
#             device.os_version = data.get('os_version', device.os_version)
#             await session.commit()

#             return jsonify({"message": f"Device {device.device_name} updated successfully."}), 200

#     except Exception as e:
#         current_app.logger.error(f"An error occurred: {str(e)}")
#         return jsonify({"error": f"An error occurred: {str(e)}"}), 500

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
                return jsonify({"error": "This device is off the watchlist."}), 403

            device.last_heartbeat = func.current_timestamp()
            await session.commit()

            current_app.logger.info(f"Received heartbeat from {device.device_name}.")
            return jsonify({"message": f"Heartbeat for device {device.device_name} received!"}), 200

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
