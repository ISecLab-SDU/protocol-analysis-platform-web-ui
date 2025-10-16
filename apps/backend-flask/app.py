"""Flask application factory for the mock backend replacement."""

from __future__ import annotations

from flask import Flask

try:
    # Support running as a module (python -m backend_flask) and as a script (uv run app.py).
    from .auth import bp as auth_blueprint
    from .demo import bp as demo_blueprint
    from .menu import bp as menu_blueprint
    from .misc import bp as misc_blueprint
    from .protocol_compliance.routes import bp as protocol_compliance_blueprint
    from .system import bp as system_blueprint
    from .table import bp as table_blueprint
    from .upload import bp as upload_blueprint
    from .user import bp as user_blueprint
except ImportError:
    from auth import bp as auth_blueprint
    from demo import bp as demo_blueprint
    from menu import bp as menu_blueprint
    from misc import bp as misc_blueprint
    from protocol_compliance.routes import bp as protocol_compliance_blueprint
    from system import bp as system_blueprint
    from table import bp as table_blueprint
    from upload import bp as upload_blueprint
    from user import bp as user_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(user_blueprint)
    app.register_blueprint(menu_blueprint)
    app.register_blueprint(system_blueprint)
    app.register_blueprint(table_blueprint)
    app.register_blueprint(upload_blueprint)
    app.register_blueprint(demo_blueprint)
    app.register_blueprint(misc_blueprint)
    app.register_blueprint(protocol_compliance_blueprint)

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app


def main():
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
