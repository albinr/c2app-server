from quart import Blueprint, render_template, jsonify, current_app

main_routes = Blueprint('main_routes', __name__)

@main_routes.route("/")
async def main():
    return await render_template("index.html")

@main_routes.route('/ping', methods=['GET'])
async def ping():
    current_app.logger.info(f"Server was pinged.")
    return jsonify({"message": "Server is running"}), 200
