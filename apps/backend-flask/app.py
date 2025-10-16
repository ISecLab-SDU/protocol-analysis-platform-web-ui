"""Application factory for the protocol compliance Flask backend."""

from __future__ import annotations

from flask import Flask

from .protocol_compliance.routes import bp as protocol_compliance_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(protocol_compliance_blueprint)

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
