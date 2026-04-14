import os
from flask import Flask
from flask_mysqldb import MySQL
from flask_mail import Mail
from flask_session import Session
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
from datetime import timedelta

# 1. Load the secrets from your .env file
load_dotenv()

# 2. Create un-configured extensions
mysql = MySQL()
mail = Mail()
sess = Session()
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def create_app():
    # Initialize the Flask app
    app = Flask(__name__)

    # --- Configuration ---
    # Pulling from .env for security!
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-key')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_COOKIE_SAMESITE'] = "None"
    app.config['SESSION_COOKIE_SECURE'] = True

    # MySQL Configuration
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'Bravia'
    app.config['MYSQL_PORT'] = 3306
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
    app.config['MYSQL_DB'] = 'quizapp'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

    # Mail Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465                     # Changed from 587
    app.config['MAIL_USERNAME'] = 'braviadprogrammer@gmail.com'
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_USE_TLS'] = False                # Changed from True
    app.config['MAIL_USE_SSL'] = True                 # Changed from False

    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # --- Initialize Extensions with the app ---
    mysql.init_app(app)
    mail.init_app(app)
    sess.init_app(app)
    CORS(app)
    socketio.init_app(app)

    # --- Register Blueprints (We will build these next!) ---
    from .routes.auth import auth_bp
    from .routes.professor import professor_bp
    from .routes.student import student_bp
    from .routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(professor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(main_bp)

    return app