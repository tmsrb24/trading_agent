import sys
import os
import threading
import queue
import configparser
from PyQt6.QtWidgets import QApplication

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from gui import TradingApp
from agent import TradingAgent

def main():
    """
    Main entry point for the application.
    Starts the backend agent in a separate thread and the GUI in the main thread.
    """
    # --- Queues for communication ---
    log_queue = queue.Queue()
    config_queue = queue.Queue()

    # --- Load Initial Config ---
    config = configparser.ConfigParser()
    config.read('configs/config.ini')

    # --- Initialize Backend Agent ---
    agent = TradingAgent(log_queue, config_queue, config)
    
    # --- Start GUI ---
    app = QApplication(sys.argv)
    main_win = TradingApp(log_queue, config_queue)
    
    # Pass the agent object to the GUI so it can be started/stopped
    # This is a simple way to connect them.
    main_win.agent = agent 
    
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
