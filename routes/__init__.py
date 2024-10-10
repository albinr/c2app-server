from quart import Blueprint
from routes.auth import auth_routes
from routes.devices import device_routes
from routes.file_upload import file_upload_routes
from routes.logs import logs_routes
from routes.commands import command_routes

routes = Blueprint('routes', __name__)

# Register individual route blueprints
routes.register_blueprint(auth_routes)
routes.register_blueprint(device_routes)
routes.register_blueprint(file_upload_routes)
routes.register_blueprint(logs_routes)
routes.register_blueprint(command_routes)
