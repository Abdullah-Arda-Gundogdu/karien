import logging
import colorlog

def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(name)s:%(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    logger = colorlog.getLogger()
    
    # Check if handlers already exist to avoid duplicate logs in reloads
    if not logger.handlers:
        logger.addHandler(handler)
        
    logger.setLevel(logging.INFO)
    
    # Quiet down some libs
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger

logger = setup_logging()
