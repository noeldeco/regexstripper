"""
Application Bootstrap for Regex Stripper
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.config import APP_NAME, APP_VERSION
from src.ui.main_window import MainWindow


def create_app() -> QApplication:
    """Creates and configures the QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    return app


def main() -> int:
    """Main application entry point."""
    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

