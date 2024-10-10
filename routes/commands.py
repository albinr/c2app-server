from quart import Blueprint, request, jsonify

command_routes = Blueprint('command_routes', __name__)

# command_store = {}

# @command_routes.route('/command', methods=['POST'])
# async def send_command():
#     data = await request.json
#     hardware_id = data.get('hardware_id')
#     command = data.get('command')

#     if not hardware_id or not command:
#         return jsonify({"error": "Missing hardware_id or command"}), 400

#     command_store[hardware_id] = command
#     return jsonify({"message": "Command sent to the device."}), 200

# @command_routes.route('/command', methods=['GET'])
# async def get_command():
#     data = await request.json
#     hardware_id = data.get('hardware_id')

#     if not hardware_id:
#         return jsonify({"error": "Missing hardware_id"}), 400

#     command = command_store.get(hardware_id)
#     if not command:
#         return jsonify({"error": "No command available"}), 404

#     return jsonify({"command": command}), 200
