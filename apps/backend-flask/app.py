"""Flask application factory for the mock backend replacement."""

from __future__ import annotations

from logging.config import dictConfig

from flask import Flask
from flask_cors import CORS

from auth import bp as auth_blueprint
from custom.routes import bp as custom_blueprint
from demo import bp as demo_blueprint
from menu import bp as menu_blueprint
from misc import bp as misc_blueprint
from protocol_compliance.routes import bp as protocol_compliance_blueprint
from system import bp as system_blueprint
from table import bp as table_blueprint
from upload import bp as upload_blueprint
from user import bp as user_blueprint


def _configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": "DEBUG",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO",
            },
            "loggers": {
                "protocol_compliance": {
                    "level": "DEBUG",
                    "propagate": True,
                },
                "werkzeug": {
                    "level": "WARNING",
                    "propagate": True,
                },
                "watchdog": {
                    "level": "WARNING",
                    "propagate": True,
                },
            },
        }
    )


def create_app() -> Flask:
    _configure_logging()

    app = Flask(__name__)

    # 配置文件上传大小限制（例如 100MB）
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

    # 启用 CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type"]
        }
    })

    # 注册所有 blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(user_blueprint)
    app.register_blueprint(menu_blueprint)
    app.register_blueprint(system_blueprint)
    app.register_blueprint(table_blueprint)
    app.register_blueprint(upload_blueprint)
    app.register_blueprint(demo_blueprint)
    app.register_blueprint(misc_blueprint)
    app.register_blueprint(custom_blueprint)
    app.register_blueprint(protocol_compliance_blueprint)

    @app.get("/api/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app


def main():
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
