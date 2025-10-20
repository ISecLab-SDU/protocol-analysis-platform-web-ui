"""Flask application factory for the mock backend replacement."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

# ✅ 绝对导入（删除所有 try-except 和相对导入）
from auth import bp as auth_blueprint
from demo import bp as demo_blueprint
from menu import bp as menu_blueprint
from misc import bp as misc_blueprint
from protocol_compliance.routes import bp as protocol_compliance_blueprint
from system import bp as system_blueprint
from table import bp as table_blueprint
from upload import bp as upload_blueprint
from user import bp as user_blueprint
from formalgpt.routes import bp as formal_gpt_bp


def create_app() -> Flask:
    app = Flask(__name__)

        # ✅ 新增：配置文件上传大小限制（例如 16MB）
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
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
    app.register_blueprint(protocol_compliance_blueprint)
    app.register_blueprint(formal_gpt_bp)

    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    return app


def main():
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
