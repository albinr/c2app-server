import aiofiles
import asyncio
from quart import Blueprint, render_template, redirect, url_for, flash, jsonify, request, current_app, websocket
from quart_auth import AuthUser, login_user, logout_user, current_user, login_required, Unauthorized
from sqlalchemy.future import select
from sqlalchemy import func
from config import Config
from models import Device, User
from nominatim import get_location_from_coordinates


log_connections = set()

routes = Blueprint('routes', __name__)

@routes.route("/")
async def main():
    return await render_template("index.html")

@routes.route('/signup', methods=['GET', 'POST'])
async def signup():
    """
    Verify async!!!
    """
    async with Config.AsyncSessionLocal() as session:
        if request.method == 'POST':
            form_data = await request.form
            username = form_data['username']
            password = form_data['password']

            result = await session.execute(select(User).filter_by(username=username))
            existing_user = result.scalars().first()

            if existing_user:
                await flash('Username already exists. Please choose another one.')
                return redirect(url_for('routes.signup'))

            new_user = User(username=username)
            new_user.set_password(password)
            session.add(new_user)
            await session.commit()

            await flash('User created successfully! You can now log in.')
            return redirect(url_for('routes.login'))

    return await render_template("signup.html")

@routes.route('/login', methods=['GET', 'POST'])
async def login():
    """
    Verify async!!!
    """
    async with Config.AsyncSessionLocal() as session:
        if request.method == 'POST':
            form_data = await request.form
            username = form_data['username']
            password = form_data['password']

            result = await session.execute(select(User).filter_by(username=username))
            user = result.scalars().first()

            if user and user.check_password(password):
                login_user(AuthUser(user.id))
                await flash('Login successful!')
                current_app.logger.info(f"User {user.username} logged in.")
                return redirect(url_for('routes.devices'))
            else:
                await flash('Invalid username or password')
                current_app.logger.info(f"Failed login with {username}")

    return await render_template("login.html")

@routes.route('/logout')
@login_required
async def logout():
    current_app.logger.info(f"User {current_user.auth_id} logged out.")
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('routes.login'))

@routes.route('/devices')
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

@routes.route('/devices/<int:id>')
@login_required
async def single_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        if device.geo_location:
            device.country, device.city = get_location_from_coordinates(device.geo_location)
        else:
            device.address = "Location not available"
    return await render_template("single-device.html", device=device)

@routes.route('/device/<int:id>/delete', methods=['POST'])
@login_required
async def post_delete_device(id):
    async with Config.AsyncSessionLocal() as session:
        device = await session.get(Device, id)
        await session.delete(device)
        await session.commit()
        current_app.logger.info(f"User {current_user.auth_id} deleted device {device.device_name}.")
        await flash(f"Device {device.device_name} deleted successfully!")
    return redirect(url_for('routes.devices'))

@routes.route('/device/<int:id>/toggle_watchlist', methods=['POST'])
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
    return redirect(url_for('routes.devices'))


@routes.route('/device/<int:id>/toggle_restrict', methods=['POST'])
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
    return redirect(url_for('routes.devices'))

@routes.route('/logs')
@login_required
async def view_logs():
    try:
        async with aiofiles.open('logs/server.log', 'r') as log_file:
            logs = await log_file.readlines()
        return await render_template('logs.html', logs=logs)
    except Exception as e:
        await flash(f"Could not open log file: {str(e)}", 'error')
        return redirect(url_for('routes.main'))

@routes.websocket('/ws/logs')
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

@routes.route('/device/info', methods=['GET'])
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

@routes.route('/device/update', methods=['POST'])
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

@routes.route('/device', methods=['POST'])
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

@routes.route('/device/heartbeat', methods=['POST'])
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

@routes.route('/device/can_view', methods=['POST'])
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

@routes.errorhandler(Unauthorized)
async def redirect_to_login(*_):
    return redirect(url_for("routes.login"))

@routes.route('/ping', methods=['GET'])
async def ping():
    current_app.logger.info(f"Server was pinged.")
    return jsonify({"message": "Server is running"}), 200

# @routes.route('/command', methods=['POST'])
# async def send_command():
#     data = request.json
#     hardware_id = data.get('hardware_id')
#     command = data.get('command')

#     if not hardware_id or not command:
#         return jsonify({"error": "Missing hardware_id or command"}), 400

#     # Store the command for the hardware_id
#     command_store[hardware_id] = command
#     return jsonify({"message": "Command sent to the device."}), 200

# @routes.route('/command', methods=['GET'])
# async def get_command():
#     data = request.json
#     hardware_id = data.get('hardware_id')

#     if not hardware_id:
#         return jsonify({"error": "Missing hardware_id"}), 400

#     # Retrieve the command for the hardware_id
#     command = command_store.get(hardware_id)
#     if not command:
#         return jsonify({"error": "No command available"}), 404

#     return jsonify({"command": command}), 200

@routes.route('/upload', methods=['POST'])
async def upload_file():
    try:
        data = await request.form
        file = (await request.files).get('file')
        hardware_id = data.get('hardware_id')

        if not hardware_id or not file:
            return jsonify({"error": "Missing hardware_id or file"}), 400

        async with Config.AsyncSessionLocal() as session:
            result = await session.execute(select(Device).filter_by(hardware_id=hardware_id))
            device = result.scalars().first()

            if not device:
                return jsonify({"error": "Device not found"}), 404

            if not device.on_watchlist:
                return jsonify({"error": "Device is off the watchlist"}), 403

            file_path = f"uploads/{hardware_id}_{file.filename}"
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file.read())

            current_app.logger.info(f"File {file.filename} uploaded for device {device.device_name}.")
            return jsonify({"message": f"File {file.filename} uploaded successfully!"}), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


