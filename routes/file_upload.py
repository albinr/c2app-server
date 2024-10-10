import aiofiles
from quart import Blueprint, request, jsonify, current_app
from sqlalchemy.future import select
from models import Device
from config import Config

file_upload_routes = Blueprint('file_upload_routes', __name__)

@file_upload_routes.route('/upload', methods=['POST'])
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