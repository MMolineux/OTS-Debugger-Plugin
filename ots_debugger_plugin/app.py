import os
import pathlib
import threading
import traceback
from typing import Optional

import yaml
from flask import (
    Blueprint,
    render_template,
    jsonify,
    Flask,
    current_app as app,
    send_file,
    send_from_directory,
    request,
)
from flask_security import roles_accepted
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import logger, socketio

from ots_debugger_plugin.cot_listener import CoTListener

from .default_config import DefaultConfig
import importlib.metadata


class DebuggerPlugin(Plugin):
    metadata = pathlib.Path(__file__).resolve().parent.name
    url_prefix = f"/api/plugins/{metadata.lower()}"
    blueprint = Blueprint("DebuggerPlugin", __name__, url_prefix=url_prefix)

    # This is your plugin's entry point. It will be called from OpenTAKServer to start the plugin
    def activate(self, app: Flask, enabled: bool = True):
        # Do not change these three lines
        self._app = app
        self._load_config()
        self.load_metadata()
        self.really_shitty_idea = []

        if enabled:
            try:
                logger.info(f"Loading {self.name}")
                self._worker: Optional[CoTListener] = CoTListener(app)
                logger.info(f"Successfully Loaded {self.name}")
            except BaseException as e:
                logger.error(f"Failed to load {self.name}: {e}")
                logger.error(traceback.format_exc())
        else:
            logger.info(f"Plugin {self.name} is disabled")

    # Do not change this
    def load_metadata(self):
        try:
            self.distro = pathlib.Path(__file__).resolve().parent.name
            self.metadata = importlib.metadata.metadata(self.distro).json
            self.name = self.metadata["name"]
            self.metadata["distro"] = self.distro
            return self.metadata
        except BaseException as e:
            logger.error(e)
            logger.debug(traceback.format_exc())
            return None

    # Loads default config and user config from ~/ots/config.yml
    # Do not change
    def _load_config(self):
        # Gets default config key/value pairs from the plugin's default_config.py
        for key in dir(DefaultConfig):
            if key.isupper():
                self._config[key] = getattr(DefaultConfig, key)
                self._app.config.update({key: getattr(DefaultConfig, key)})

        # Get user overrides from config.yml
        with open(
            os.path.join(self._app.config.get("OTS_DATA_FOLDER"), "config.yml")
        ) as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            for key in self._config.keys():
                value = yaml_config.get(key)
                if value:
                    self._config[key] = value
                    self._app.config.update({key: value})

    def get_info(self):
        self.load_metadata()
        self.get_plugin_routes(self.url_prefix)
        return {"name": self.name, "distro": self.distro, "routes": self.routes}

    def stop(self): ...

    # Make route methods static to avoid "no-self-use" errors
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/")
    def plugin_info():  # Do not put "self" as a method parameter here
        # This method will return JSON with info about the plugin derived from pyproject.toml, please do not change it
        # Make sure that your plugin has a README.md to show in the UI's about page
        try:
            distribution = None
            distributions = importlib.metadata.packages_distributions()
            for distro in distributions:
                if str(__name__).startswith(distro):
                    distribution = distributions[distro][0]
                    break

            if distribution:
                info = importlib.metadata.metadata(distribution)
                return jsonify(info.json)
            else:
                return jsonify({"success": False, "error": "Plugin not found"}), 404
        except BaseException as e:
            logger.error(e)
            return jsonify({"success": False, "error": e}), 500

    # OpenTAKServer's web UI will display your plugin's UI in an iframe
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/ui")
    def ui():
        # TODO: Uncomment the following line if your plugin does not require a UI
        # return "<html><body>Some text</body></html>", 200

        logger.info(f"stat: {os.path.dirname(__file__)}")
        logger.info(f"ls: {os.listdir(os.path.dirname(__file__))}")

        # TODO: Otherwise use this line if your plugin requires a UI
        return send_from_directory(
            f"{os.path.dirname(__file__)}/ui",
            "index.html",
            as_attachment=False,
        )

    # Endpoint to serve static UI files. Does not need to be changed in most cases
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/assets/<file_name>")
    @blueprint.route("/ui/<file_name>")
    def serve(file_name):
        directory = os.path.join(os.path.dirname(__file__), "ui/assets")
        if not os.path.exists(os.path.join(directory, file_name)):
            logger.warning(
                f"trying to serve {file_name} from {directory} but the file does not exist"
            )
            directory = os.path.join(os.path.dirname(__file__), "ui")

        # if still can't find it, throw a 404
        if not os.path.exists(os.path.join(directory, file_name)):
            logger.warning(
                f"trying to serve {file_name} from {directory} but the file does not exist"
            )
            return "", 404

        return send_from_directory(directory, file_name)

    # Gets the plugin config for the web UI, do not change
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config")
    def config():
        config = {}

        for key in dir(DefaultConfig):
            if key.isupper():
                config[key] = app.config.get(key)

        return jsonify(config)

    # Updates the plugin config
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/config", methods=["POST"])
    def update_config():
        try:
            result = DefaultConfig.update_config(request.json)
            if result["success"]:
                DefaultConfig.update_config(request.json)
                return jsonify(result)
            else:
                return jsonify(result), 400
        except BaseException as e:
            logger.error("Failed to update config:" + str(e))
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 400

    @staticmethod
    @socketio.on("connect", namespace="/debugger")
    def socket_connect():
        logger.info(f"connected via socket io")

    @staticmethod
    @socketio.on("message", namespace="/debugger")
    def socket_message(msg):
        logger.info(f"message recieved {msg}")
