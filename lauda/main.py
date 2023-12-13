# -*- coding :utf-8 -*-
# lauda/main.py
'''This module provides LAUDA Thermostat application.'''

import sys
from PyQt6.QtWidgets import QApplication
import lauda.views

def main():
    """Project main function"""
    # Create the application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Run the event loop
    splash_screen = lauda.views.SplashScreen()
    splash_screen.exec()

    mainWindow = lauda.views.MainWindow()
    mainWindow.show()
    # Create and show the checklist window (assuming modality is not required)
    checklist = lauda.views.ChecklistWindow(mainWindow, app)
    checklist.show()


    sys.exit(app.exec())


