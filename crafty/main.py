import os
import sys
import json
from threading import Thread
import time
import argparse
import logging.config
import signal
import peewee
from packaging import version as pkg_version

from app.classes.shared.file_helpers import FileHelpers
from app.classes.shared.import3 import Import3
from app.classes.shared.console import Console
from app.classes.shared.helpers import Helpers
from app.classes.models.users import HelperUsers
from app.classes.models.management import HelpersManagement
from app.classes.shared.import_helper import ImportHelpers
from app.classes.shared.websocket_manager import WebSocketManager
from app.classes.logging.log_formatter import JsonFormatter

console = Console()
helper = Helpers()
# Get the path our application is running on.
if getattr(sys, "frozen", False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
    RUNNING_MODE = "Frozen/executable"
else:
    try:
        app_full_path = os.path.realpath(__file__)
        APPLICATION_PATH = os.path.dirname(app_full_path)
        RUNNING_MODE = "Non-interactive (e.g. 'python main.py')"
    except NameError:
        APPLICATION_PATH = os.getcwd()
        RUNNING_MODE = "Interactive"
if helper.check_root():
    Console.critical(
        "Root detected. Root/Admin access denied. "
        "Run Crafty again with non-elevated permissions."
    )
    time.sleep(5)
    Console.critical("Crafty shutting down. Root/Admin access denied.")
    sys.exit(0)
if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
    Console.critical(
        "Python version mismatch. Python "
        f"{sys.version_info.major}.{sys.version_info.minor} detected."
    )
    Console.critical("Crafty requires Python 3.9 or above. Please upgrade python.")
    time.sleep(5)
    Console.critical("Crafty shutting down.")
    time.sleep(3)
    Console.info("Crafty stopped. Exiting...")
    sys.exit(0)

# pylint: disable=wrong-import-position
try:
    from app.classes.models.base_model import database_proxy
    from app.classes.shared.main_models import DatabaseBuilder
    from app.classes.shared.tasks import TasksManager
    from app.classes.shared.main_controller import Controller
    from app.classes.shared.migration import MigrationManager
    from app.classes.shared.command import MainPrompt
except ModuleNotFoundError as err:
    helper.auto_installer_fix(err)


def internet_check():
    """
    This checks to see if the Crafty host is connected to the
    internet. This will show a warning in the console if no interwebs.
    """
    print()
    logger.info("Checking Internet. This may take a minute.")
    Console.info("Checking Internet. This may take a minute.")

    if not helper.check_internet():
        logger.warning(
            "We have detected the machine running Crafty has no "
            "connection to the internet. Client connections to "
            "the server may be limited."
        )
        Console.warning(
            "We have detected the machine running Crafty has no "
            "connection to the internet. Client connections to "
            "the server may be limited."
        )


def controller_setup():
    """
    Method sets up the software controllers.
    This also sets the application path as well as the
    master server dir (if not set).

    This also clears the support logs status.
    """
    if not controller.check_system_user():
        controller.add_system_user()

    master_server_dir = controller.management.get_master_server_dir()
    if master_server_dir == "":
        logger.debug("Could not find master server path. Setting default")
        controller.set_master_server_dir(
            os.path.join(controller.project_root, "servers")
        )
    else:
        helper.servers_dir = master_server_dir

    logger.info(f"Execution Mode: {RUNNING_MODE}")
    logger.info(f"Application path: '{APPLICATION_PATH}'")
    Console.info(f"Execution Mode: {RUNNING_MODE}")
    Console.info(f"Application path: '{APPLICATION_PATH}'")

    controller.clear_support_status()


def get_migration_notifications():
    migration_notifications = []
    for file in os.listdir(
        os.path.join(APPLICATION_PATH, "app", "migrations", "status")
    ):
        if os.path.isfile(file):
            with open(
                os.path.join(APPLICATION_PATH, "app", "migrations", "status", file),
                encoding="utf-8",
            ) as status_file:
                status_json = json.load(status_file)
            for item in status_json:
                if not status_json[item].get("status"):
                    migration_notifications.append(item)
    return migration_notifications


def tasks_starter():
    """
    Method starts stats recording, app scheduler, and
    big bucket/steamCMD cache refreshers
    """
    # start stats logging
    tasks_manager.start_stats_recording()

    # once the controller is up and stats are logging, we can kick off
    # the scheduler officially
    tasks_manager.start_scheduler()

    # refresh our cache and schedule for every 12 hoursour cache refresh
    # for big bucket.com
    tasks_manager.big_bucket_cache_refresher()


def signal_handler(signum, _frame):
    """
    Method handles sigterm and shuts the app down.
    """
    if not args.daemon:
        print()  # for newline after prompt
    signame = signal.Signals(signum).name
    logger.info(f"Recieved signal {signame} [{signum}], stopping Crafty...")
    Console.info(f"Recieved signal {signame} [{signum}], stopping Crafty...")
    tasks_manager._main_graceful_exit()
    crafty_prompt.universal_exit()


def do_cleanup():
    """
    Checks Crafty's temporary directory and clears it out on boot.
    """
    try:
        logger.info("Removing old temp dirs")
        FileHelpers.del_dirs(os.path.join(controller.project_root, "temp"))
    except:
        logger.info("Did not find old temp dir.")
    os.mkdir(os.path.join(controller.project_root, "temp"))


def do_version_check():
    """
    Checks for remote version differences.

    Prints in terminal with differences if true.

    Also sets helper variable to update available when pages
    are served.
    """

    # Check if new version available
    remote_ver = helper.check_remote_version()
    if remote_ver:
        notice = f"""
            A new version of Crafty is available!
            {'/' * 37}
            New version available: {remote_ver}
            Current version: {pkg_version.parse(helper.get_version_string())}
            {'/' * 37}
            """
        Console.yellow(notice)

    crafty_prompt.prompt = f"Crafty Controller v{helper.get_version_string()} > "


def setup_starter():
    """
    This method starts our setup threads.
    (tasks scheduler, internet checks, controller setups)

    Once our threads complete we will set our startup
    variable to false and send a reload to any clients waiting.


    """
    if not args.daemon:
        time.sleep(0.01)  # Wait for the prompt to start
        print()  # Make a newline after the prompt so logs are on an empty line
    else:
        time.sleep(0.01)  # Wait for the daemon info message

    Console.info("Setting up Crafty's internal components...")
    # Start the setup threads
    web_sock.broadcast("update", {"section": "tasks"})
    time.sleep(2)
    tasks_starter_thread.start()
    web_sock.broadcast("update", {"section": "internet"})
    time.sleep(2)
    internet_check_thread.start()
    web_sock.broadcast(
        "update",
        {"section": "internals"},
    )
    time.sleep(2)
    controller_setup_thread.start()

    web_sock.broadcast("update", {"section": "cache"})
    controller.big_bucket.manual_refresh_cache()
    # Wait for the setup threads to finish
    web_sock.broadcast(
        "update",
        {"section": "almost"},
    )
    tasks_starter_thread.join()
    internet_check_thread.join()
    controller_setup_thread.join()
    helper.crafty_starting = False
    web_sock.broadcast("send_start_reload", "")
    do_version_check()
    Console.info("Crafty has fully started and is now ready for use!")

    do_cleanup()

    if not args.daemon:
        # Put the prompt under the cursor
        crafty_prompt.print_prompt()


def do_intro():
    """
    Runs the Crafty Controller Terminal Intro with information about the software
    This method checks for a "settings file" or config.json. If it does not find
    one it will create one.
    """
    logger.info("***** Crafty Controller Started *****")

    version = helper.get_version_string()

    intro = f"""
    {'/' * 75}
    #{("Welcome to Crafty Controller - v." + version).center(73, " ")}#
    {'/' * 75}
    #{"Server Manager / Web Portal for your Minecraft server".center(73, " ")}#
    #{"Homepage: www.craftycontrol.com".center(73, " ")}#
    {'/' * 75}
    """

    Console.magenta(intro)
    if not helper.check_file_exists(helper.settings_file):
        Console.debug("No settings file detected. Creating one.")
        helper.set_settings(Helpers.get_master_config())


def setup_logging(debug=True):
    """
    This method sets up our logging for Crafty. It takes
    one optional (defaulted to True) parameter which
    determines whether or not the logging level is "debug" or verbose.
    """
    logging_config_file = os.path.join(
        APPLICATION_PATH, "app", "config", "logging.json"
    )
    if not helper.check_file_exists(
        os.path.join(APPLICATION_PATH, "logs", "auth_tracker.log")
    ):
        open(
            os.path.join(APPLICATION_PATH, "logs", "auth_tracker.log"),
            "a",
            encoding="utf-8",
        ).close()

    if not helper.check_file_exists(
        os.path.join(APPLICATION_PATH, "logs", "audit.log")
    ):
        open(
            os.path.join(APPLICATION_PATH, "logs", "audit.log"),
            "a",
            encoding="utf-8",
        ).close()

    if os.path.exists(logging_config_file):
        # open our logging config file
        with open(logging_config_file, "rt", encoding="utf-8") as f:
            logging_config = json.load(f)
            if debug:
                logging_config["loggers"][""]["level"] = "DEBUG"

            logging.config.dictConfig(logging_config)

            # Apply JSON formatting to the "audit" handler
            for handler in logging.getLogger().handlers:
                if handler.name == "audit_log_handler":
                    handler.setFormatter(JsonFormatter())

    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning(f"Unable to read logging config from {logging_config_file}")
        Console.critical(f"Unable to read logging config from {logging_config_file}")


# Our Main Starter
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Crafty Controller - A Server Management System")

    parser.add_argument(
        "-i", "--ignore", action="store_true", help="Ignore session.lock files"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Sets logging level to debug."
    )

    parser.add_argument(
        "-d",
        "--daemon",
        action="store_true",
        help="Runs Crafty in daemon mode (no prompt)",
    )

    args = parser.parse_args()
    helper.ensure_logging_setup()
    helper.crafty_starting = True
    # Init WebSocket Manager Here
    web_sock = WebSocketManager()
    setup_logging(debug=args.verbose)
    if args.verbose:
        Console.level = "debug"

    # setting up the logger object
    logger = logging.getLogger(__name__)
    Console.cyan(f"Logging set to: {logger.level}")
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.INFO)

    # print our pretty start message
    do_intro()
    # our session file, helps prevent multiple controller agents on the same machine.
    helper.create_session_file(ignore=args.ignore)
    # start the database
    database = peewee.SqliteDatabase(
        helper.db_path, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
    )
    database_proxy.initialize(database)
    Helpers.ensure_dir_exists(
        os.path.join(APPLICATION_PATH, "app", "migrations", "status")
    )
    migration_manager = MigrationManager(database, helper)
    migration_manager.up()  # Automatically runs migrations

    # init classes
    # now the tables are created, we can load the tasks_manager and server controller
    user_helper = HelperUsers(database, helper)
    management_helper = HelpersManagement(database, helper)
    installer = DatabaseBuilder(database, helper, user_helper, management_helper)
    FRESH_INSTALL = installer.is_fresh_install()

    if FRESH_INSTALL:
        Console.debug("Fresh install detected")
        Console.warning(
            f"We have detected a fresh install. Please be sure to forward "
            f"Crafty's port, {helper.get_setting('https_port')}, "
            f"through your router/firewall if you would like to be able "
            f"to access Crafty remotely."
        )
        PASSWORD = helper.create_pass()
        installer.default_settings(PASSWORD)
        with open(
            os.path.join(APPLICATION_PATH, "app", "config", "default-creds.txt"),
            "w",
            encoding="utf-8",
        ) as cred_file:
            cred_file.write(
                json.dumps(
                    {
                        "username": "admin",
                        "password": PASSWORD,
                        "info": "This is NOT where you change your password."
                        " This file is only a means to give you a default password.",
                    },
                    indent=4,
                )
            )
        os.chmod(
            os.path.join(APPLICATION_PATH, "app", "config", "default-creds.txt"), 0o600
        )
    else:
        Console.debug("Existing install detected")
    Console.info("Checking for reset secret flag")
    if helper.get_setting("reset_secrets_on_next_boot"):
        Console.info("Found Reset")
        management_helper.set_secret_api_key(str(helper.random_string_generator(64)))
        management_helper.set_cookie_secret(str(helper.random_string_generator(32)))
        helper.set_setting("reset_secrets_on_next_boot", False)
    else:
        Console.info("No flag found. Secrets are staying")

    # now we've initialized our database for fresh install we
    # can finishing initializing our controllers/modules
    file_helper = FileHelpers(helper)
    import_helper = ImportHelpers(helper, file_helper)
    controller = Controller(database, helper, file_helper, import_helper)
    controller.set_project_root(APPLICATION_PATH)
    tasks_manager = TasksManager(helper, controller, file_helper)
    import3 = Import3(helper, controller)
    helper.migration_notifications = get_migration_notifications()
    # Check to see if client config.json version is different than the
    # Master config.json in helpers.py
    Console.info("Checking for remote changes to config.json")
    controller.get_config_diff()
    # Delete anti-lockout-user
    controller.users.stop_anti_lockout()
    Console.info("Remote change complete.")

    # startup the web server
    tasks_manager.start_webserver()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # init servers
    logger.info("Initializing all servers defined")
    Console.info("Initializing all servers defined")
    web_sock.broadcast(
        "update",
        {"section": "serverInit"},
    )
    controller.servers.init_all_servers()

    # start up our tasks handler in tasks.py
    tasks_starter_thread = Thread(target=tasks_starter, name="tasks_starter")

    # check to see if instance has internet
    internet_check_thread = Thread(target=internet_check, name="internet_check")

    # start the Crafty console.
    crafty_prompt = MainPrompt(
        helper, tasks_manager, migration_manager, controller, import3
    )

    # set up all controllers
    controller_setup_thread = Thread(target=controller_setup, name="controller_setup")

    setup_starter_thread = Thread(target=setup_starter, name="setup_starter")

    setup_starter_thread.start()

    if not args.daemon:
        # Start the Crafty prompt
        crafty_prompt.cmdloop()
    else:
        Console.info("Crafty started in daemon mode, no shell will be printed")
        print()
        while True:
            if tasks_manager.get_main_thread_run_status():
                break
            time.sleep(1)
        tasks_manager._main_graceful_exit()
        crafty_prompt.universal_exit()
