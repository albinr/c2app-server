from quart import Quart
from quart_auth import QuartAuth
from config import Config
from models import Base
from logging_config import setup_logging
from routes import routes

def create_app():
    app = Quart(__name__)
    app.config.from_object(Config)

    QuartAuth(app)

    setup_logging()

    async def init_db():
        async with Config.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    app.before_serving(init_db)

    app.register_blueprint(routes)

    return app

if __name__ == '__main__':
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    app = create_app()

    async def run():
        config = HyperConfig()
        config.bind = ["0.0.0.0:5000"]
        await hypercorn.asyncio.serve(app, config)

    asyncio.run(run())
