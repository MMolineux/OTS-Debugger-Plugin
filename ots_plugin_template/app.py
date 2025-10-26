import os
import pathlib
import traceback

import yaml
from flask import Blueprint, render_template, jsonify, Flask, current_app as app, send_from_directory, request
from flask_security import roles_accepted
from opentakserver.plugins.Plugin import Plugin
from opentakserver.extensions import *

from .default_config import DefaultConfig
import importlib.metadata


# TODO: Rename this class
class PluginTemplate(Plugin):
    # TODO: Change the Blueprint name to YourPluginBlueprint
    metadata = pathlib.Path(__file__).resolve().parent.name
    url_prefix = f"/api/plugins/{metadata.lower()}"
    blueprint = Blueprint("PluginTemplate", __name__, url_prefix=url_prefix)
                                       #^
                                       #|
                            # TODO: Change this to your plugin's name

    # This is your plugin's entry point. It will be called from OpenTAKServer to start the plugin
    def activate(self, app: Flask):
        # Do not change these three lines
        self._app = app
        self._load_config()
        self.load_metadata()

        try:
            # TODO: If your plugin needs to run in the background, do that here.
            # See OTS-AISStream-Plugin for an example
            logger.info(f"Successfully Loaded {self._name}")
        except BaseException as e:
            logger.error(f"Failed to load {self._name}: {e}")
            logger.error(traceback.format_exc())

    # Do not change this
    def load_metadata(self):
        try:
            self.distro = pathlib.Path(__file__).resolve().parent.name
            self.metadata = importlib.metadata.metadata(self.distro).json
            self.name = self.metadata['name']
            self.metadata['distro'] = self.distro
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
        with open(os.path.join(self._app.config.get("OTS_DATA_FOLDER"), "config.yml")) as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            for key in self._config.keys():
                value = yaml_config.get(key)
                if value:
                    self._config[key] = value
                    self._app.config.update({key: value})

    def get_info(self):
        self.load_metadata()
        self.get_plugin_routes(self.url_prefix)
        return {'name': self.name, 'distro': self.distro, 'routes': self.routes}

    def stop(self):
        # TODO: If your plugin runs in the background, shut down your plugin gracefully here
        # See OTS-AISStream-Plugin for an example
        pass

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
                return jsonify({'success': False, 'error': 'Plugin not found'}), 404
        except BaseException as e:
            logger.error(e)
            return jsonify({'success': False, 'error': e}), 500

    # OpenTAKServer's web UI will display your plugin's UI in an iframe
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route("/ui")
    def ui():
        # TODO: Uncomment the following line if your plugin does not require a UI
        # return '', 200

        # TODO: Otherwise use this line if your plugin requires a UI
        return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui", "index.html", as_attachment=False)

    # Endpoint to serve static UI files. Does not need to be changed in most cases
    @staticmethod
    @roles_accepted("administrator")
    @blueprint.route('/assets/<file_name>')
    @blueprint.route("/ui/<file_name>")
    def serve(file_name):
        logger.debug(f"Path: {file_name}")
        logger.warning(os.path.join(pathlib.Path(__file__).parent.resolve(), "ui", "assets", file_name))
        if file_name != "" and os.path.exists(
                os.path.join(pathlib.Path(__file__).parent.resolve(), "ui", "assets", file_name)):
            logger.info(f"Serving {file_name}")
            return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui/assets", file_name)
        elif file_name != "" and os.path.exists(os.path.join(pathlib.Path(__file__).parent.resolve(), "ui", file_name)):
            return send_from_directory(f"../{pathlib.Path(__file__).parent.resolve().name}/ui", file_name)
        else:
            return '', 404

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

    # TODO: Add more routes here. Make sure to use try/except blocks around all of your code. Otherwise, an exception in a plugin
    # could cause the whole server to crash. Also make sure to properly protect your routes with @auth_required or @roles_accepted
