"""Application factory for the protocol compliance Flask backend."""

from __future__ import annotations

from flask import Flask

try:
    # Support running as a module (python -m backend_flask) and as a script (uv run app.py).
    from .protocol_compliance.routes import bp as protocol_compliance_blueprint
except ImportError:
    from protocol_compliance.routes import bp as protocol_compliance_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
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
