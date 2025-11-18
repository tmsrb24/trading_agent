# Advanced Crypto Trading Agent with GUI

This project is a sophisticated, autonomous trading agent for cryptocurrencies, built in Python and controlled via a PyQt6 graphical user interface. It actively analyzes the market, applies configurable trading strategies, and manages risk according to a detailed ruleset.

## Core Architecture

The application is composed of two main parts: a backend **Trading Agent** that runs in a separate thread, and a frontend **GUI** for control and monitoring.

### Backend Components (`src/` directory):

-   **`agent.py`**: The core of the backend. Contains the `TradingAgent` class that orchestrates the entire trading loop, manages state, and communicates with the GUI.
-   **`api_client.py`**: Handles all communication with the **Alpaca API** for fetching market data, account information, and placing trades.
-   **Scanners**:
    -   `coingecko_scanner.py`: Finds trading opportunities by fetching a list of currently trending coins from the **CoinGecko API**.
    -   `technical_scanner.py`: Finds opportunities by scanning for coins with the highest trading volume on Alpaca.
-   **Strategies**:
    -   `scalping_strategy.py`: A fast-paced strategy designed for scalping, based on EMA crossovers and the Stochastic Oscillator.
    -   `strategy.py` (contains `PullbackStrategy`): A more traditional trend-following strategy that enters on pullbacks.
-   **`risk_manager.py`**: Enforces all risk rules defined in the configuration, including position sizing, max open trades, and daily loss limits.
-   **`order_executor.py`**: Handles the execution of trades, placing market orders with attached stop-losses.
-   **`logger.py`**: A professional-grade logger that outputs to both the console and a log file (`logs/trading_agent.log`).
-   **`indicators.py`**: A utility module with functions to calculate technical indicators (EMA, ATR, ADX, RSI, Stochastics).

### Frontend Components:

-   **`main.py`**: The main entry point for the entire application. It launches the GUI and starts the backend agent thread.
-   **`gui.py`**: A comprehensive dashboard built with **PyQt6**. It provides:
    -   Start/Stop controls for the agent.
    -   Real-time display of KPI's (Portfolio Value, P/L, etc.).
    -   A live log stream from the agent.
    -   A table of open positions.
    -   A settings window to configure every aspect of the agent without touching the code.
-   **`configs/config.ini`**: A configuration file where all strategies, scanners, and risk parameters can be tuned.

## Technologies Used

-   **Python 3.9+**
-   **PyQt6**: For the graphical user interface.
-   **Alpaca API**: For paper trading and market data.
-   **CoinGecko API**: For finding trending coins.
-   **Libraries**: `pandas`, `numpy`, `pyqt6`, `pyqtgraph`, `alpaca-trade-api`, `pycoingecko`.

## Setup and Usage

1.  **Set up the environment:**
    ```bash
    # Navigate into the project directory
    cd trading_agent

    # Create and activate a Python virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install the required dependencies
    pip install -r requirements.txt
    ```

2.  **Configure API Keys:**
    -   Open the `.env` file.
    -   Fill in your `API_KEY` and `SECRET_KEY` from your **Alpaca paper trading account**.

3.  **Run the Application:**
    ```bash
    python3 main.py
    ```
    This will launch the GUI. From there, click the **"Start Agent"** button to begin trading. All activity will be displayed in the GUI's log window.
