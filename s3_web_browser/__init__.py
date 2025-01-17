import os

from flask import Flask

from s3_web_browser.routes import register_routes


def create_app(config_class: str = "config.Config") -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    register_routes(app)

    return app
