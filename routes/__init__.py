from quart import Blueprint, redirect, url_for
from quart_auth import Unauthorized
from routes.auth import auth_routes
from routes.devices import device_routes
from routes.file_upload import file_upload_routes
from routes.logs import logs_routes
from routes.command import command_routes
from routes.main import main_routes

routes = Blueprint('routes', __name__)

@routes.errorhandler(Unauthorized)
async def redirect_to_login(*_):
    return redirect(url_for("routes.auth_routes.login"))

routes.register_blueprint(auth_routes)
routes.register_blueprint(device_routes)
routes.register_blueprint(file_upload_routes)
routes.register_blueprint(logs_routes)
routes.register_blueprint(command_routes)
routes.register_blueprint(main_routes)
