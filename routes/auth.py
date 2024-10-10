from quart import Blueprint, render_template, redirect, url_for, flash, request, current_app
from sqlalchemy.future import select
from config import Config
from models import User
from quart_auth import AuthUser, login_user, logout_user, current_user, login_required

auth_routes = Blueprint('auth_routes', __name__)

@auth_routes.route('/signup', methods=['GET', 'POST'])
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
                return redirect(url_for('routes.auth_routes.signup'))

            new_user = User(username=username)
            new_user.set_password(password)
            session.add(new_user)
            await session.commit()

            await flash('User created successfully! You can now log in.')
            return redirect(url_for('routes.login'))

    return await render_template("signup.html")

@auth_routes.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('routes.device_routes.devices'))
            else:
                await flash('Invalid username or password')
                current_app.logger.info(f"Failed login with {username}")

    return await render_template("login.html")

@auth_routes.route('/logout')
@login_required
async def logout():
    current_app.logger.info(f"User {current_user.auth_id} logged out.")
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('routes.auth_routes.login'))
