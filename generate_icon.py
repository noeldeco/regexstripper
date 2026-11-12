import os
import sys

# Ensure QApplication is initialized for font metrics and image plugins
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QBrush, QLinearGradient, QPen

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])

def generate_icon():
    size = 256
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#3B82F6"))
    grad.setColorAt(1.0, QColor("#1D4ED8"))

    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(16, 16, 224, 224), 48, 48)

    # Outer border glow
    border_pen = QPen(QColor(255, 255, 255, 100), 4)
    painter.setPen(border_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(16, 16, 224, 224), 48, 48)

    # Symbol text
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Cascadia Code", 86)
    font.setStyleHint(QFont.Monospace)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, ".*")
    painter.end()

    ico_path = "f:/DEV/regexstripper/assets/app.ico"
    png_path = "f:/DEV/regexstripper/assets/app.png"
    img.save(png_path, "PNG")
    img.save(ico_path, "ICO")
    print(f"Generated {ico_path} and {png_path} successfully!")

if __name__ == "__main__":
    generate_icon()

