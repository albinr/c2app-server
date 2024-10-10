from quart import Quart
from quart_auth import QuartAuth
from config import Config
from models import Base
from logging_config import setup_logging
from routes import routes

app = Quart(__name__)
app.config.from_object(Config)

auth_manager = QuartAuth(app)

setup_logging()

async def init_db():
    async with Config.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.before_serving
async def startup():
    await init_db()

app.register_blueprint(routes)

if __name__ == '__main__':
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    async def run():
        config = HyperConfig()
        config.bind = ["0.0.0.0:5000"]
        
        
        await hypercorn.asyncio.serve(app, config)

    asyncio.run(run())
