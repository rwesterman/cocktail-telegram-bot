import json
import os
# import logging
import logging.config

class Secrets:

    def __init__(self):
        self.client_secret = ""
        self.sheet_name = ""
        self.ftp_host = ""
        self.ftp_user = ""
        self.ftp_pass = ""
        self.debug_token = ""
        self.bottender_token = ""
        self.json_log = logging.getLogger('warn.' + __name__)
        try:
            self.open_json()
        except FileNotFoundError as e:
            self.json_log.error("secrets.json does not exist on this system, certain methods cannot be used.")

    def open_json(self):
        telegram_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(telegram_path, "json", "secret.json")
        with open(path, 'r') as f:
            data = json.load(f)
            self.client_secret = data["sheets"]["client_secret"]
            self.sheet_name = data["sheets"]["name"]
            self.debug_token = data["telegram"]["debug_token"]
            self.bottender_token = data["telegram"]["bottender_token"]
            self.ftp_host = data["ftp"]["host"]
            self.ftp_user = data["ftp"]["username"]
            self.ftp_pass = data["ftp"]["password"]

class Loggers:

    def setup_logging(self,
            default_path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "json", "config.json"),
            default_level=logging.INFO,
            env_key='LOG_CFG'):
        """
        Set up logging configuration from json file
        :param default_path:
        :param default_level:
        :param env_key:
        :return:
        """
        # if no log folder exists, create the path
        log_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")
        if not os.path.exists(log_path):
            os.mkdir(log_path)

        path = default_path
        value = os.getenv(env_key, None)
        if value:
            path = value
        if os.path.exists(path):
            with open(path, 'rt') as f:
                # config holds the dictionary object.
                config = json.load(f)

                # get the filenames for the handlers. Will prepend the "logs" folder to filepath
                info_filename = config["handlers"]["info_file_handler"]["filename"]
                error_filename = config["handlers"]["error_file_handler"]["filename"]

                # move files into "logs" folder, make platform unspecific with os.path.join
                config["handlers"]["info_file_handler"]["filename"] = os.path.join("logs", info_filename)
                config["handlers"]["error_file_handler"]["filename"] = os.path.join("logs", error_filename)

                logging.config.dictConfig(config)
        else:
            logging.basicConfig(level=default_level)
            logging.error("Wasn't able to configure loggers from file!")
            raise Exception("Logging config failed, raising exception for debug!")
