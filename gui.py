import sys
import configparser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QLabel, QTextEdit, QFrame, QPushButton, QLineEdit,
                             QComboBox, QDialog, QScrollArea)
from PyQt6.QtGui import QFont, QPalette, QColor, QAction
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
import pyqtgraph as pg
import queue

class Communicate(QObject):
    message_received = pyqtSignal(dict)

class SettingsWindow(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        container = QWidget()
        scroll_area.setWidget(container)
        
        self.grid_layout = QGridLayout(container)
        self.widgets = {}

        # --- Main Settings ---
        self.grid_layout.addWidget(self.create_header("Main"), 0, 0, 1, 2)
        self.add_config_row("strategy_to_use", "Strategy", 1, QComboBox(), ["pullback", "scalping"], section="main")
        self.add_config_row("scanner_to_use", "Scanner", 2, QComboBox(), ["technical_volume", "coingecko_trending"], section="main")
        self.add_config_row("symbols_to_trade", "Symbols to Trade (CSV)", 3, section="main")
        self.add_config_row("rr_ratio", "Risk/Reward Ratio", 4, section="main")
        
        # --- Risk Settings ---
        self.grid_layout.addWidget(self.create_header("Risk Management"), 4, 0, 1, 2)
        self.add_config_row("risk_per_trade", "Risk Per Trade (%)", 5, section="risk")
        self.add_config_row("max_open_trades", "Max Open Trades", 6, section="risk")

        # --- Pullback Strategy Settings ---
        self.grid_layout.addWidget(self.create_header("Pullback Strategy"), 7, 0, 1, 2)
        self.add_config_row("ema_fast_len", "EMA Fast", 8, section="pullback_strategy")
        self.add_config_row("ema_slow_len", "EMA Slow", 9, section="pullback_strategy")
        
        # --- Scalping Strategy Settings ---
        self.grid_layout.addWidget(self.create_header("Scalping Strategy"), 10, 0, 1, 2)
        self.add_config_row("ema_fast_len", "EMA Fast", 11, section="scalping_strategy")
        self.add_config_row("ema_slow_len", "EMA Slow", 12, section="scalping_strategy")
        self.add_config_row("stoch_oversold", "Stoch Oversold", 13, section="scalping_strategy")
        self.add_config_row("stoch_overbought", "Stoch Overbought", 14, section="scalping_strategy")

        # --- Buttons ---
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_changes)
        button_layout.addWidget(apply_button)
        layout.addLayout(button_layout)

    def create_header(self, text):
        label = QLabel(text)
        label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        label.setStyleSheet("margin-top: 10px; margin-bottom: 5px;")
        return label

    def add_config_row(self, key, label_text, row, widget=None, options=None, section="main"):
        label = QLabel(label_text)
        self.grid_layout.addWidget(label, row, 0)

        if widget is None:
            widget = QLineEdit()
        
        if isinstance(widget, QLineEdit):
            widget.setText(self.config[section][key])
        elif isinstance(widget, QComboBox):
            widget.addItems(options)
            widget.setCurrentText(self.config[section][key])

        self.grid_layout.addWidget(widget, row, 1)
        self.widgets[(section, key)] = widget

    def apply_changes(self):
        new_config = {}
        for (section, key), widget in self.widgets.items():
            if section not in new_config:
                new_config[section] = {}
            
            if isinstance(widget, QLineEdit):
                new_config[section][key] = widget.text()
            elif isinstance(widget, QComboBox):
                new_config[section][key] = widget.currentText()
        
        self.parent().update_config(new_config)
        self.accept()


class TradingApp(QMainWindow):
    def __init__(self, log_queue, config_queue):
        super().__init__()
        self.log_queue = log_queue
        self.config_queue = config_queue
        self.load_config()
        self.init_ui()
        self.setup_queue_listener()

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('configs/config.ini')

    def init_ui(self):
        self.setWindowTitle("Crypto Trading Agent Dashboard")
        self.setGeometry(100, 100, 1400, 900)
        self.set_dark_theme()

        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        main_layout.addWidget(self.create_controls_widget()) # Add controls
        main_layout.addWidget(self.create_kpi_widgets())
        main_layout.addWidget(self.create_chart_widget(), 1)
        main_layout.addWidget(self.create_bottom_widgets())

    def create_controls_widget(self):
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        
        self.startButton = QPushButton("Start Agent")
        self.startButton.clicked.connect(self.start_agent)
        
        self.stopButton = QPushButton("Stop Agent")
        self.stopButton.clicked.connect(self.stop_agent)
        
        controls_layout.addWidget(self.startButton)
        controls_layout.addWidget(self.stopButton)
        controls_layout.addStretch()
        return controls_container

    def start_agent(self):
        if hasattr(self, 'agent') and self.agent:
            self.log_queue.put({'type': 'log', 'data': "GUI: Start button clicked."})
            self.agent.start()
        else:
            print("GUI Error: Agent object not attached.")

    def stop_agent(self):
        if hasattr(self, 'agent') and self.agent:
            self.log_queue.put({'type': 'log', 'data': "GUI: Stop button clicked."})
            self.agent.stop()
        else:
            print("GUI Error: Agent not attached.")

    def open_settings(self):
        settings_win = SettingsWindow(self.config, self)
        settings_win.exec()

    def update_config(self, new_config_dict):
        # Update the in-memory config parser
        for section, params in new_config_dict.items():
            for key, value in params.items():
                self.config.set(str(section), str(key), str(value))
        
        # Save to file
        with open('configs/config.ini', 'w') as configfile:
            self.config.write(configfile)
            
        # Send to bot thread
        self.config_queue.put(self.config)
        print("GUI: Sent updated config to bot.")

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(dark_palette)

    def create_kpi_widgets(self):
        kpi_container = QFrame()
        kpi_layout = QHBoxLayout(kpi_container)
        kpi_container.setObjectName("kpiContainer")
        kpi_container.setStyleSheet("#kpiContainer { border: 1px solid #444; border-radius: 8px; }")

        self.kpi_labels = {}
        kpi_data = {
            "Portfolio Value": "$0.00",
            "Today's P/L": "$0.00 (0.00%)",
            "Buying Power": "$0.00",
            "Open Positions": "0"
        }

        for title, value in kpi_data.items():
            card = QFrame()
            card_layout = QVBoxLayout(card)
            
            title_label = QLabel(title)
            title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            value_label = QLabel(value)
            value_label.setFont(QFont("Arial", 24))
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            kpi_layout.addWidget(card)
            self.kpi_labels[title] = value_label
        
        return kpi_container

    def create_chart_widget(self):
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground((35, 35, 35))
        self.plot_widget.setTitle("Portfolio Value Over Time", color="w", size="16pt")
        styles = {"color": "w", "font-size": "12px"}
        self.plot_widget.setLabel("left", "Value ($)", **styles)
        self.plot_widget.setLabel("bottom", "Time", **styles)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        self.portfolio_curve = self.plot_widget.plot([1,2,3], [100,110,105], pen=pg.mkPen(color=(66, 147, 245), width=2))
        return self.plot_widget

    def create_bottom_widgets(self):
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)

        # --- Terminal ---
        terminal_container = QFrame()
        terminal_container.setFrameShape(QFrame.Shape.StyledPanel)
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_label = QLabel("Live Log")
        terminal_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.terminal_text = QTextEdit()
        self.terminal_text.setReadOnly(True)
        self.terminal_text.setFont(QFont("Courier", 11))
        terminal_layout.addWidget(terminal_label)
        terminal_layout.addWidget(self.terminal_text)

        # --- Positions Table ---
        positions_container = QFrame()
        positions_container.setFrameShape(QFrame.Shape.StyledPanel)
        positions_layout = QVBoxLayout(positions_container)
        positions_label = QLabel("Open Positions")
        positions_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.positions_text = QTextEdit()
        self.positions_text.setReadOnly(True)
        self.positions_text.setFont(QFont("Courier", 11))
        positions_layout.addWidget(positions_label)
        positions_layout.addWidget(self.positions_text)

        bottom_layout.addWidget(terminal_container, 1)
        bottom_layout.addWidget(positions_container, 1)
        
        return bottom_container

    def setup_queue_listener(self):
        self.communicator = Communicate()
        self.communicator.message_received.connect(self.handle_message)

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_queue)
        self.timer.start(100) # Check queue every 100ms

    def process_queue(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.communicator.message_received.emit(message)
        except queue.Empty:
            pass

    def handle_message(self, message):
        msg_type = message.get('type')
        data = message.get('data')

        if msg_type == 'log':
            self.terminal_text.append(data)
        elif msg_type == 'kpi_update':
            self.update_kpis(data)
        elif msg_type == 'positions_update':
            self.update_positions(data)

    def update_kpis(self, data):
        for title, value in data.items():
            if title in self.kpi_labels:
                self.kpi_labels[title].setText(value)
                if title == "Today's P/L":
                    if "-" in value:
                        self.kpi_labels[title].setStyleSheet("color: red;")
                    else:
                        self.kpi_labels[title].setStyleSheet("color: lightgreen;")

    def update_positions(self, positions):
        self.positions_text.clear()
        header = f"{'Symbol':<15}{'Qty':<10}{'Entry Price':<15}{'Current P/L (%)':<20}"
        separator = "-"*60
        self.positions_text.append(header)
        self.positions_text.append(separator)
        
        if not positions:
            self.positions_text.append("No open positions.")
            return

        for p in positions:
            try:
                pl_pct = float(p.unrealized_plpc) * 100
                row = f"{p.symbol:<15}{p.qty:<10}{float(p.avg_entry_price):<15.2f}{pl_pct:<+20.2f}%"
                self.positions_text.append(row)
            except Exception as e:
                print(f"Error processing position for GUI: {p} - {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_log_queue = queue.Queue()
    test_config_queue = queue.Queue()
    main_win = TradingApp(test_log_queue, test_config_queue)
    main_win.show()
    sys.exit(app.exec())
