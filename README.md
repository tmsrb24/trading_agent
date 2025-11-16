# Advanced Crypto Trading Agent

This project is a sophisticated, autonomous trading agent for cryptocurrencies, built in Python. It actively scans the market for opportunities, applies a complex trading strategy, and manages risk according to predefined rules.

## Core Architecture

The agent is built with a modular architecture, separating different concerns into dedicated components:

-   **`main.py`**: The main entry point and orchestration loop for the agent.
-   **`src/api_client.py`**: Handles all communication with the Alpaca API for market data and trading.
-   **`src/scanner.py`**: Scans the market for opportunities. It uses the **CoinGecko API** to find currently trending coins, ensuring the agent focuses on assets with high market interest.
-   **`src/strategy.py`**: Contains the `PullbackStrategy`, which implements the core trading logic based on a combination of technical indicators.
-   **`src/indicators.py`**: A utility module with functions to calculate technical indicators like EMA, ATR, ADX, and RSI from scratch.
-   **`src/sentiment_analyzer.py`**: Integrates with the **Santiment API** to fetch social sentiment scores for cryptocurrencies, which are used as a final filter in the trading strategy.
-   **`src/risk_manager.py`**: Enforces all risk management rules, including position sizing based on stop-loss distance, a maximum value per trade, and portfolio-level limits (e.g., max open trades).
-   **`src/order_executor.py`**: Handles the execution of trades, placing market orders with attached stop-losses.
-   **`src/logger.py`**: Logs all executed trades to a `trades.csv` file for later analysis.

## Technologies Used

-   **Python 3.9+**
-   **Alpaca API**: For paper trading execution and market data.
-   **CoinGecko API**: Used by the scanner to find trending coins.
-   **Santiment API**: Used to get social sentiment data as a strategy filter.
-   **Libraries**: `pandas`, `numpy`, `python-dotenv`, `sanpy`, `pycoingecko`, `alpaca-trade-api`.

## Setup and Usage

1.  **Clone the repository.**

2.  **Set up the environment:**
    ```bash
    # Navigate into the project directory
    cd trading_agent

    # Create and activate a Python virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install the required dependencies
    pip install -r requirements.txt
    ```

3.  **Configure API Keys:**
    -   Rename the `.env.example` file (if present) to `.env`.
    -   Open the `.env` file and fill in your API keys:
        -   `API_KEY` and `SECRET_KEY` from your **Alpaca paper trading account**.
        -   `SANTIMENT_API_KEY` from your **free Santiment account**.

4.  **Run the Agent:**
    ```bash
    python3 main.py
    ```
    The agent will start running in your terminal, scanning the market in cycles and executing trades when all conditions are met. To stop the agent, press `Ctrl+C`.
