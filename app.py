import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import sentry_sdk
import yaml

from backup import BackupHandler

logger = logging.getLogger("automated_backup_utilities")
logger.setLevel(logging.INFO)
logger_handler = logging.StreamHandler()
logger_handler.setFormatter(
    logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(logger_handler)


def _execute_backup(config):
    try:
        handler = BackupHandler.from_config(config)
        handler.backup()
        handler.clean_previous_backups()
    except Exception as exc:
        logger.error(exc, stack_info=True)


def main():
    if os.path.isfile(".env"):
        print("Loading .env")
        load_dotenv(".env")

    config_path = os.environ["CONFIG_PATH"]
    sentry_dsn = os.environ.get("SENTRY_DSN", None)

    if sentry_dsn is not None:
        sentry_sdk.init(dsn=sentry_dsn)

    scheduler = BlockingScheduler()

    configs = []

    with open(config_path, "r", encoding="utf-8") as file:
        configs = yaml.safe_load(file)

    for config in configs:
        scheduler.add_job(
            _execute_backup,
            CronTrigger.from_crontab(config["schedule"]),
            [config],
            misfire_grace_time=None,
        )

    logger.info("Starting automated backup utility")
    scheduler.start()


if __name__ == '__main__':
    main()
