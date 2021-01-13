import logging
import logging.handlers
'''
日志模块
'''
LOG_FILENAME = 'jd_seckill.log'
logger = logging.getLogger("jd_seckill")


def set_logger():
    logger.setLevel(logging.INFO)
    fmt = '%(asctime)s - %(process)d-%(threadName)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
    formatter = logging.Formatter(fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME, maxBytes=1024*1024*20, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
