import time
import logging
from .shared import status_log

# Configure main application logging
logging.basicConfig(
    filename='vmware_manager.log',
    level=logging.INFO,  # Changed to INFO to reduce noise
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a separate logger for UI queue operations
ui_logger = logging.getLogger('ui_queue')
ui_handler = logging.FileHandler('ui_queue.log')
ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
ui_logger.addHandler(ui_handler)
ui_logger.setLevel(logging.DEBUG)

# Create a separate logger for VM status updates
refresh_logger = logging.getLogger('vm_refresh')
refresh_handler = logging.FileHandler('vm_refresh.log')
refresh_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
refresh_logger.addHandler(refresh_handler)
refresh_logger.setLevel(logging.INFO)

DEBUG = False  # Set to True to enable console printing

def log_message(message: str, level: str = "INFO", refresh: bool = False) -> None:
    """Log a message to both the status queue and file."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{level}] {timestamp} - {message}"
    
    # Log to appropriate file based on message type
    if refresh:
        if level == "ERROR":
            refresh_logger.error(message)
        else:
            refresh_logger.info(message)
        return  # Don't add refresh messages to UI queue
    
    # Log non-refresh messages to main log
    if level == "ERROR":
        logging.error(message)
    else:
        logging.info(message)
    
    if DEBUG:
        print(formatted_msg)
    
    # Add message to UI queue
    try:
        status_log.put_nowait(formatted_msg)
        ui_logger.debug(f"Added to UI queue: {formatted_msg}")
    except:
        try:
            status_log.get_nowait()
            status_log.put_nowait(formatted_msg)
            ui_logger.debug(f"Replaced in UI queue: {formatted_msg}")
        except:
            ui_logger.error(f"Failed to add to UI queue: {formatted_msg}") 