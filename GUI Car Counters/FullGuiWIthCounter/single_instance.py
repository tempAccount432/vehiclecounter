import win32event
import win32api
import sys
import logging

from winerror import ERROR_ALREADY_EXISTS

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class SingleInstance:
    """Ensures only one instance of the application runs at a time."""
    
    def __init__(self, mutex_name="Global\\MyUniqueAppMutex"):
        self.mutex_name = mutex_name
        self.mutex = None

    def acquire(self):
        """Tries to acquire the mutex. If it already exists, exits the application."""
        try:
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
            if win32api.GetLastError() == ERROR_ALREADY_EXISTS:
                logging.warning("Another instance of the application is already running. Exiting.")
                sys.exit(0)
            logging.info("Application started successfully. Mutex acquired.")
        except Exception as e:
            logging.error(f"Error acquiring mutex: {e}")
            sys.exit(1)

    def release(self):
        """Releases the mutex when the application exits."""
        if self.mutex:
            try:
                win32api.CloseHandle(self.mutex)
                logging.info("Mutex released successfully.")
            except Exception as e:
                logging.error(f"Error releasing mutex: {e}")