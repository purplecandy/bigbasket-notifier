import time
import schedule
import functools
from plyer import notification
from src.notifier import Notifier
from src.telegram_notifier import TelegramNotifier
from src.utils.logger import logger
from src.utils.configurer import config


def catch_exceptions(cancel_on_failure=False):
    def catch_exceptions_decorator(job_func):
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):
            try:
                return job_func(*args, **kwargs)
            except:
                import traceback
                logger.log("critical", traceback.format_exc())
                if cancel_on_failure:
                    logger.log("warning", "Job Cancelled due to an error.")
                    return schedule.CancelJob
        return wrapper
    return catch_exceptions_decorator


@catch_exceptions(cancel_on_failure=True)
def job(notifier: Notifier, system_notifier: notification, delay, telegram_notifier: TelegramNotifier):
    """
    Job to check if a delivery slot gets available for the default selected address in your bigbasket website.
    @param notifier: Notifier - Notifier class - To monitor bigbasket website.
    @param system_notifier: notification - To notify users (cross-platform) via balloon tiles.
    @param delay: int - Just a preventive measure to not make too many requests at the same time.
    @param telegram_notifier: Telegram integration to notify via bot.
    """
    notifier.visit_main_page()
    time.sleep(delay)
    addr_id = notifier.visit_cart_page_and_get_address_id()
    time.sleep(delay)
    initial_status, resp = notifier.check_if_delivery_slot_available(addr_id)
    if initial_status:
        telegram_notifier.notify(config.get_configuration('chat_id', "TELEGRAM"), "A delivery slot is maybe found.")
        logger.log("warning", "Maybe a delivery slot is found.")
        status = notifier.visit_extra_delivery_slot_check()
        if status:
            logger.log("critical", "Delivery slot is found!")
            system_notifier.notify(
                title='BigBasket Notifier',
                message='A free delivery slot is found for your address',
                app_name='bigbasket-notifier'
            )
        else:
            logger.log("warning", "No delivery slot was found.")


if __name__ == "__main__":
    n = Notifier(
        config.get_configuration('phone_number', "APP"),
        config.get_configuration('session_pickle_filename', "SYSTEM"),
        load_session=True
    )
    telegram_n = TelegramNotifier(config.get_configuration('token', "TELEGRAM"))
    job(n, notification, 2, telegram_n)
    schedule.every(
        int(config.get_configuration("interval", "APP"))
    ).minutes.do(job, n, notification, 2, telegram_n)
    while True:
        schedule.run_pending()
        time.sleep(1)
