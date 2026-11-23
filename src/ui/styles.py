"""
Modern QSS Stylesheets for Light and Dark Themes
Regex Stripper (RegexStripper)
"""

from src.config import AppTheme

LIGHT_STYLESHEET = """
/* Base Window & Global Font */
QMainWindow, QDialog, QWidget {
    background-color: #F8F9FA;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    color: #0F172A;
}

/* Group Boxes & Panels */
QFrame#topPanel {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px;
}

QFrame#bottomBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    padding: 8px 8px;
}

/* Pattern ComboBox */
QComboBox#patternCombo {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #0F172A;
    min-height: 24px;
}
QComboBox#patternCombo:focus {
    border: 1px solid #3B82F6;
    background-color: #F8FAFC;
}
QComboBox#patternCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left-width: 1px;
    border-left-color: #E2E8F0;
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #F1F5F9;
}
QComboBox#patternCombo::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748B;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
    padding: 4px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
}

/* Replace LineEdit */
QLineEdit#replaceInput {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #0F172A;
    min-height: 24px;
}
QLineEdit#replaceInput:focus {
    border: 1px solid #3B82F6;
    background-color: #F8FAFC;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #334155;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QRadioButton::indicator {
    border-radius: 8px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    border: 1px solid #2563EB;
    background-color: #2563EB;
}
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
    border: 1px solid #94A3B8;
    background-color: #FFFFFF;
}

/* Central Text Editor */
QPlainTextEdit#editor, QPlainTextEdit#previewEditor {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    line-height: 1.5;
    selection-background-color: #93C5FD;
    selection-color: #0F172A;
}
QPlainTextEdit#previewEditor {
    background-color: #F8FAFC;
    border: 1px dashed #94A3B8;
}
QPlainTextEdit#editor:focus {
    border: 1px solid #3B82F6;
}

/* Buttons */
QPushButton {
    border-radius: 6px;
    padding: 4px 5px;
    font-size: 13px;
    font-weight: 500;
}

/* Theme Toggle Button */
QPushButton#themeBtn {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 3px 3px;
    min-width: 28px;
    min-height: 28px;
}
QPushButton#themeBtn:hover {
    background-color: #E2E8F0;
}

/* Replace Button */
QPushButton#replaceBtn {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #0369A1;
    font-weight: 600;
}
QPushButton#replaceBtn:hover {
    background-color: #0369A1;
}
QPushButton#replaceBtn:pressed {
    background-color: #075985;
}
QPushButton#replaceBtn:disabled {
    background-color: #BAE6FD;
    border: 1px solid #BAE6FD;
    color: #F0F9FF;
}

/* Delete / Strip Button (Primary Action) */
QPushButton#deleteBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
    font-weight: bold;
}
QPushButton#deleteBtn:hover {
    background-color: #B91C1C;
}
QPushButton#deleteBtn:pressed {
    background-color: #991B1B;
}
QPushButton#deleteBtn:disabled {
    background-color: #FCA5A5;
    border: 1px solid #FCA5A5;
    color: #FEF2F2;
}

/* Delete Duplicates Button */
QPushButton#deleteDupBtn {
    background-color: #D97706;
    color: #FFFFFF;
    border: 1px solid #B45309;
    font-weight: bold;
}
QPushButton#deleteDupBtn:hover {
    background-color: #B45309;
}
QPushButton#deleteDupBtn:pressed {
    background-color: #92400E;
}
QPushButton#deleteDupBtn:disabled {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    color: #94A3B8;
}

/* Copy Button */
QPushButton#copyBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: bold;
}
QPushButton#copyBtn:hover {
    background-color: #1D4ED8;
}
QPushButton#copyBtn:pressed {
    background-color: #1E40AF;
}
QPushButton#copyBtn:disabled {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    color: #94A3B8;
}

/* Save Button (Light Theme: Dark emerald green for maximum contrast with white text) */
QPushButton#saveBtn {
    background-color: #047857;
    color: #FFFFFF;
    border: 1px solid #065F46;
    font-weight: bold;
}
QPushButton#saveBtn:hover {
    background-color: #065F46;
}
QPushButton#saveBtn:pressed {
    background-color: #064E3B;
}
QPushButton#saveBtn:disabled {
    background-color: #D1FAE5;
    border: 1px solid #A7F3D0;
    color: #6EE7B7;
}

/* Navigation Buttons (Light Theme) */
QPushButton#navBtn {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
    padding: 2px 3px;
    font-size: 11px;
}
QPushButton#navBtn:hover {
    background-color: #E2E8F0;
}
QPushButton#navBtn:disabled {
    color: #94A3B8;
    background-color: #F8FAFC;
}

/* Menus (Light Theme) */
QMenu {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    padding: 4px;
}
QMenu::item {
    padding: 6px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #E2E8F0;
    color: #0F172A;
}

/* Secondary / Utility Buttons */
QPushButton#utilBtn {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#utilBtn:hover {
    background-color: #E2E8F0;
    color: #0F172A;
}
QPushButton#utilBtn:pressed {
    background-color: #CBD5E1;
}

/* Status Label */
QLabel#statusLabel {
    font-size: 12px;
    font-weight: 500;
    padding: 2px 4px;
}
"""

DARK_STYLESHEET = """
/* Base Window & Global Font */
QMainWindow, QDialog, QWidget {
    background-color: #181825;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    color: #CDD6F4;
}

/* Group Boxes & Panels */
QFrame#topPanel {
    background-color: #1E1E2E;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
}

QFrame#bottomBar {
    background-color: #1E1E2E;
    border-top: 1px solid #313244;
    padding: 8px 8px;
}

/* Pattern ComboBox */
QComboBox#patternCombo {
    background-color: #181825;
    border: 1px solid #45475A;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #CDD6F4;
    min-height: 24px;
}
QComboBox#patternCombo:focus {
    border: 1px solid #89B4FA;
    background-color: #1E1E2E;
}
QComboBox#patternCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left-width: 1px;
    border-left-color: #313244;
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #313244;
}
QComboBox#patternCombo::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #A6ADC8;
}
QComboBox QAbstractItemView {
    background-color: #1E1E2E;
    border: 1px solid #45475A;
    border-radius: 6px;
    selection-background-color: #313244;
    selection-color: #CDD6F4;
    padding: 4px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
}

/* Replace LineEdit */
QLineEdit#replaceInput {
    background-color: #181825;
    border: 1px solid #45475A;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #CDD6F4;
    min-height: 24px;
}
QLineEdit#replaceInput:focus {
    border: 1px solid #89B4FA;
    background-color: #1E1E2E;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #BAC2DE;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QRadioButton::indicator {
    border-radius: 8px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    border: 1px solid #89B4FA;
    background-color: #89B4FA;
}
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
    border: 1px solid #585B70;
    background-color: #181825;
}

/* Central Text Editor */
QPlainTextEdit#editor, QPlainTextEdit#previewEditor {
    background-color: #11111B;
    color: #CDD6F4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 10px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    line-height: 1.5;
    selection-background-color: #45475A;
    selection-color: #CDD6F4;
}
QPlainTextEdit#previewEditor {
    background-color: #181825;
    border: 1px dashed #45475A;
}
QPlainTextEdit#editor:focus {
    border: 1px solid #89B4FA;
}

/* Buttons */
QPushButton {
    border-radius: 6px;
    padding: 4px 5px;
    font-size: 13px;
    font-weight: 500;
}

/* Theme Toggle Button */
QPushButton#themeBtn {
    background-color: #313244;
    border: 1px solid #45475A;
    border-radius: 6px;
    padding: 3px 3px;
    min-width: 28px;
    min-height: 28px;
}
QPushButton#themeBtn:hover {
    background-color: #45475A;
}

/* Replace Button */
QPushButton#replaceBtn {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #0369A1;
    font-weight: 600;
}
QPushButton#replaceBtn:hover {
    background-color: #0369A1;
}
QPushButton#replaceBtn:pressed {
    background-color: #075985;
}
QPushButton#replaceBtn:disabled {
    background-color: #1E293B;
    border: 1px solid #334155;
    color: #475569;
}

/* Delete / Strip Button (Primary Action) */
QPushButton#deleteBtn {
    background-color: #EF4444;
    color: #FFFFFF;
    border: 1px solid #DC2626;
    font-weight: bold;
}
QPushButton#deleteBtn:hover {
    background-color: #DC2626;
}
QPushButton#deleteBtn:pressed {
    background-color: #B91C1C;
}
QPushButton#deleteBtn:disabled {
    background-color: #450A0A;
    border: 1px solid #7F1D1D;
    color: #7F1D1D;
}

/* Delete Duplicates Button (Dark Theme) */
QPushButton#deleteDupBtn {
    background-color: #B45309;
    color: #FFFFFF;
    border: 1px solid #92400E;
    font-weight: bold;
}
QPushButton#deleteDupBtn:hover {
    background-color: #D97706;
}
QPushButton#deleteDupBtn:pressed {
    background-color: #78350F;
}
QPushButton#deleteDupBtn:disabled {
    background-color: #1E1E2E;
    border: 1px solid #313244;
    color: #585B70;
}

/* Copy Button */
QPushButton#copyBtn {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: 1px solid #2563EB;
    font-weight: bold;
}
QPushButton#copyBtn:hover {
    background-color: #2563EB;
}
QPushButton#copyBtn:pressed {
    background-color: #1D4ED8;
}
QPushButton#copyBtn:disabled {
    background-color: #313244;
    border: 1px solid #45475A;
    color: #6C7086;
}

/* Save Button (Light Theme: Dark emerald green for maximum contrast with white text) */
QPushButton#saveBtn {
    background-color: #047857;
    color: #FFFFFF;
    border: 1px solid #065F46;
    font-weight: bold;
}
QPushButton#saveBtn:hover {
    background-color: #065F46;
}
QPushButton#saveBtn:pressed {
    background-color: #064E3B;
}
QPushButton#saveBtn:disabled {
    background-color: #052E16;
    border: 1px solid #064E3B;
    color: #3F6B56;
}

/* Navigation Buttons (Dark Theme) */
QPushButton#navBtn {
    background-color: #313244;
    color: #CDD6F4;
    border: 1px solid #45475A;
    padding: 2px 3px;
    font-size: 11px;
}
QPushButton#navBtn:hover {
    background-color: #45475A;
    color: #FFFFFF;
}
QPushButton#navBtn:disabled {
    color: #585B70;
    background-color: #1E1E2E;
    border: 1px solid #313244;
}

/* Menus (Dark Theme) */
QMenu {
    background-color: #1E1E2E;
    color: #CDD6F4;
    border: 1px solid #45475A;
    padding: 4px;
}
QMenu::item {
    padding: 6px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #313244;
    color: #FFFFFF;
}

/* Secondary / Utility Buttons */
QPushButton#utilBtn {
    background-color: #313244;
    color: #CDD6F4;
    border: 1px solid #45475A;
}
QPushButton#utilBtn:hover {
    background-color: #45475A;
    color: #FFFFFF;
}
QPushButton#utilBtn:pressed {
    background-color: #585B70;
}

/* Status Label */
QLabel#statusLabel {
    font-size: 12px;
    font-weight: 500;
    padding: 2px 4px;
}
"""


def get_stylesheet(theme: AppTheme) -> str:
    """Returns the QSS stylesheet for the requested theme."""
    return DARK_STYLESHEET if theme == AppTheme.DARK else LIGHT_STYLESHEET
