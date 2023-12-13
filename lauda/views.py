# -*- coding :utf-8 -*-
'''
This module provides interfaces for managing the visualization and storage of temperatures
and pressures during a hydrothermal carbonization process. Additionally, it facilitates input handling for
control parameters and program inputs to the LAUDA High Temperature Thermostat USH."
'''
import collections
import csv
import os
import sys
import time
from datetime import datetime
import pyqtgraph as pg
import serial
from PyQt6.QtCore import QDateTime, QSize, QThread, pyqtSignal, QUrl
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (QMainWindow, QCheckBox, QPushButton, QDialog, QFileDialog, QMessageBox, QHBoxLayout,
                             QFormLayout, QLineEdit, QGroupBox, QDoubleSpinBox, QComboBox, QSpinBox,
                             QRadioButton,
                             QButtonGroup, QSpacerItem, QSizePolicy)
from PyQt6.QtWidgets import QWidget, QProgressBar, QLabel, QVBoxLayout

#Global variables for serial connection
ser = None
ser_p = None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class SplashScreen(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Splash Screen')
        self.setFixedSize(400, 200)  # Größe des Fortschrittsbalkens ändern
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet('QDialog{border: 1px solid #888888}')  # Add thin black border

        self.counter = 0
        self.n = 100  # Gesamtanzahl von Instanzen

        self.initUI()

        self.timer = QTimer()
        self.timer.timeout.connect(self.loading)
        self.timer.start(20)

    def initUI(self):

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Überschrift
        label_welcome = QLabel('Willkommen bei LAUDA Thermostat')
        label_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_welcome.setFont(QFont("Arial", 16))  # Textgröße ändern
        layout.addWidget(label_welcome)

        # Versionsnummer
        label_version = QLabel('Version 1.0')
        label_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_version.setFont(QFont("Arial", 14))  # Textgröße ändern
        layout.addWidget(label_version)

        # Zusätzlicher Text
        label_author = QLabel('by David Gansterer-Heider')
        label_date = QLabel('20.11.2023 IVET')
        label_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_author)
        layout.addWidget(label_date)

        # Fortschrittsbalken
        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setFixedHeight(10)  # Höhe des Fortschrittsbalkens
        self.progressBar.setTextVisible(False)  # Text im Fortschrittsbalken ausblenden
        self.progressBar.setRange(0, self.n)
        self.progressBar.setValue(20)
        self.progressBar.setStyleSheet(
            "QProgressBar {"
            "    background-color: lightgray;"
            "    border: 1px solid gray;"
            "    border-radius: 5px;"
            "}"
            "QProgressBar::chunk {"
            "    background-color:darkgray;"
            "    width: 10px;"  # Breite des blauen Balkens
            "}"
        )
        layout.addWidget(self.progressBar)

    def loading(self):
        self.progressBar.setValue(self.counter)

        if self.counter >= self.n:
            self.timer.stop()
            self.close()

            time.sleep(1)

        self.counter += 1


class ChecklistWindow(QDialog):
    def __init__(self, mainWindow, app):
        super().__init__(None, Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet('QDialog{border: 1px solid #888888}')  # Add thin black border
        self.setWindowTitle('LAUDA Thermostat')
        self.setFixedSize(400, 300)
        self.check = False
        self.mainWindow = mainWindow
        self.app = app
        self.setModal(True)  # Die Checkliste ist modal

        layout = QVBoxLayout()

        label = QLabel("Checkliste", self)
        label.setFont(QFont("Arial", 18))
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.kaltwasserhahn_checkbox = QCheckBox("Kaltwasserhahn geöffnet")
        self.berstscheibe_checkbox = QCheckBox("Berstscheibe & Schläuche inspiziert")
        self.ventile_checkbox = QCheckBox("Ventile geschlossen")
        self.reaktor_checkbox = QCheckBox("Reaktor sicher verschlossen")

        self.status_check = QLabel('')
        self.status_check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_check.setStyleSheet('font-size: 16px; color: red;')

        layout.addWidget(label)
        layout.addSpacing(20)
        layout.addWidget(self.kaltwasserhahn_checkbox)
        layout.addSpacing(10)
        layout.addWidget(self.berstscheibe_checkbox)
        layout.addSpacing(10)
        layout.addWidget(self.ventile_checkbox)
        layout.addSpacing(10)
        layout.addWidget(self.reaktor_checkbox)
        layout.addSpacing(10)
        layout.addWidget(self.status_check)

        weiter_button = QPushButton("Next")
        weiter_button.clicked.connect(self.check_checkboxes)
        layout.addWidget(weiter_button)


        self.setLayout(layout)
        self.check = False
        self.adjustSize()
        self.setFixedSize(self.size())

    def check_checkboxes(self):
        if (self.kaltwasserhahn_checkbox.isChecked() and
            self.berstscheibe_checkbox.isChecked() and
            self.ventile_checkbox.isChecked() and
            self.reaktor_checkbox.isChecked()):
            self.check = True
            self.status_check.setText('Succesful!')
            time.sleep(1)
            self.accept()
            serial_port = SerialPortGui(self.mainWindow)
            serial_port.exec()

        else:
            self.check = False
            self.status_check.setText('Please check all!')


class SerialPortGui(QDialog):

    def __init__(self,mainWindow):
        super().__init__()

        self.mainWindow = mainWindow

        self.setWindowTitle("Serial Port")
        self.setFixedSize(500, 400)

        self.layout = QVBoxLayout()

        lauda_groupbox = self.create_lauda_groupbox("RS 232 C LAUDA")
        pressure_groupbox = self.create_pressure_groupbox("RS 232 C PRESSURE")

        self.layout.addWidget(lauda_groupbox)
        self.layout.addWidget(pressure_groupbox)

        button_box = self.create_button_box()
        self.layout.addLayout(button_box)

        self.setLayout(self.layout)

        self.connect_button.clicked.connect(self.connect_button_clicked)
        self.disconnect_button.clicked.connect(self.disconnect_button_clicked)
        self.close_button.clicked.connect(self.close_button_clicked)

    def create_lauda_groupbox(self, title):
        groupbox = QGroupBox(title)
        layout = QHBoxLayout()

        radio_button = QRadioButton()
        radio_button.setText('')

        self.lauda_port_combobox = QComboBox()
        self.lauda_port_combobox.addItems(
            ['COM3','COM2','COM1','COM4'])

        self.lauda_baudrate_combobox = QComboBox()
        self.lauda_baudrate_combobox.addItems(['9600', '4800'])

        layout.addWidget(QLabel("Port:"))
        layout.addWidget(self.lauda_port_combobox)
        layout.addWidget(QLabel("Baudrate:"))
        layout.addWidget(self.lauda_baudrate_combobox)
        layout.addWidget(radio_button)

        groupbox.setLayout(layout)

        return groupbox

    def create_pressure_groupbox(self, title):
        groupbox = QGroupBox(title)
        layout = QHBoxLayout()

        radio_button = QRadioButton()
        radio_button.setText('')

        self.pressure_port_combobox = QComboBox()
        self.pressure_port_combobox.addItems(
            ['COM4', 'COM3', 'COM2', 'COM1'])

        self.pressure_baudrate_combobox = QComboBox()
        self.pressure_baudrate_combobox.addItems(['9600','4800'])

        layout.addWidget(QLabel("Port:"))
        layout.addWidget(self.pressure_port_combobox)
        layout.addWidget(QLabel("Baudrate:"))
        layout.addWidget(self.pressure_baudrate_combobox)
        layout.addWidget(radio_button)

        groupbox.setLayout(layout)

        return groupbox

    def create_button_box(self):
        button_layout = QVBoxLayout()

        self.connect_button = QPushButton(" Connect ")
        self.disconnect_button = QPushButton("Disconnect")
        self.close_button = QPushButton("Close")
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addWidget(self.close_button)

        return button_layout

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')  # Add thin black border
        msg_box.setText(message)
        msg_box.exec()

    def display_error_message(self, group_name, error_message):
        message = f"{group_name} - {error_message}"
        self.display_message(message)

    def connect_button_clicked(self):
        selected_radio_button = None
        self.connection_status_temp = False  # Hinzugefügte Variable, um den Verbindungsstatus zu verfolgen
        self.connection_status_pres = False

        # Extrahiere die Werte aus den benannten Comboboxes
        lauda_port = self.lauda_port_combobox.currentText()
        lauda_baudrate = self.lauda_baudrate_combobox.currentText()
        pressure_port = self.pressure_port_combobox.currentText()
        pressure_baudrate = self.pressure_baudrate_combobox.currentText()

        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if isinstance(item.widget(), QGroupBox):
                group_box = item.widget()
                for widget in group_box.findChildren(QRadioButton):
                    if widget.isChecked():
                        selected_radio_button = widget
                        selected_group = group_box.title()
                        break

                if selected_radio_button:
                    # Implement the connection logic based on the selected_group
                    if selected_group == "RS 232 C LAUDA":
                        try:
                            global ser
                            if ser and ser.is_open and i == 0:
                                    self.display_error_message("Lauda Thermostat already connected:", ser.name)

                            if not ser:
                                ser = serial.Serial(lauda_port, baudrate=lauda_baudrate, bytesize=8,
                                                    parity=serial.PARITY_NONE,
                                                    stopbits=2, timeout=1)

                                # Überprüfen, ob die Verbindung erfolgreich war
                                if all([ser.is_open, ser.dtr, ser.rts, ser.cts]):
                                    self.display_message("Connection to Lauda Thermostat established")
                                    self.connection_status_temp = True

                        except Exception as e:
                            if i == 0:
                                self.display_error_message(selected_group, str(e))


                    elif selected_group == "RS 232 C PRESSURE":
                        self.connection_status = False

                        try:
                            global ser_p
                            if ser_p:
                                if ser_p.is_open:
                                    self.display_error_message("Pressure Transducer already connected:", self.ser_p.name)

                            if not ser_p:
                                ser_p = serial.Serial(pressure_port, baudrate=pressure_baudrate, timeout=1)

                                # Überprüfen, ob die Verbindung erfolgreich war
                                if all([ser_p.is_open, ser_p.dtr, ser_p.rts]):
                                    self.display_message("Connection to Pressure transducer established")
                                    self.connection_status_pres = True

                        except Exception as e:
                            self.display_error_message(selected_group, str(e))

        if self.connection_status_temp == True and self.connection_status_pres == True:
            self.accept()

        if not selected_radio_button:
            self.display_message("No device selected!")
    def close_button_clicked(self):
        self.accept()

    def disconnect_button_clicked(self):
        global ser
        global ser_p

        if ser:
            ser.close()
            ser = None
            self.display_message("Disconnect button clicked for Lauda.")
        if ser_p:
            ser_p.close()
            ser_p = None
            self.display_message("Disconnect button clicked for Pressure.")

        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initializeUI()


    def initializeUI(self):
        self.setWindowTitle("LAUDA Thermostat")
        self.setMinimumSize(1000, 550)
        self.initializePlot()
        self.setUpMainWindow()
        self.createMenu()
        global ser
        global ser_p

    def initializePlot(self):
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Temperature [°C] and Pressure [bar]')
        self.plot_widget.setLabel('bottom', 'time')
        # Deaktivieren der horizontalen Verschiebung für die x-Achse
        self.plot_widget.getViewBox().setMouseEnabled(x=False)

        self.plot_widget.setLimits(yMin=0, yMax=None)

        self.max_data_points = 2000  # Beispiel: Maximal 2000 Datenpunkte

        # Initialisieren des Ringpuffers für Daten mit deque
        self.time = collections.deque(maxlen=self.max_data_points)
        self.Ti = collections.deque(maxlen=self.max_data_points)
        self.T1 = collections.deque(maxlen=self.max_data_points)
        self.Ts = collections.deque(maxlen=self.max_data_points)
        self.p = collections.deque(maxlen=self.max_data_points)

        self.serial_thread = SerialThread()
        self.serial_thread.dataReceived.connect(self.update_data)

        self.plot_widget.addLegend()
        self.plot_widget.setAxisItems({'bottom': pg.DateAxisItem()})
        self.receiving = False

    def setUpMainWindow(self):

        self.filepath = ''
        self.running = False
        self.pressure_exceeded = False
        self.statusWindow = StatusWindow()

        main_layout = QVBoxLayout()

        self.createtemperaturGroupbox()
        main_layout.addWidget(self.groupbox)

        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.plot_widget)
        main_layout.addLayout(plot_layout)

        bottom_layout = QHBoxLayout()
        date_time_groupbox = self.createDateTimeGroupBox()
        bottom_layout.addWidget(date_time_groupbox)
        control_groupbox = self.createControlGroupBox()
        bottom_layout.addWidget(control_groupbox)

        main_layout.addLayout(bottom_layout)
        reset_box = QHBoxLayout()
        reset_button = QPushButton('Reset')
        reset_button.clicked.connect(self.reset_pressure_exceeded)
        reset_box.addStretch(1)
        reset_box.addWidget(reset_button)
        main_layout.addLayout(reset_box)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def start_data_receiving(self):
        if not ser:
            self.display_message("No connection to LAUDA Thermostat!")

        sign = ''

        if ser:
            if not self.pressure_exceeded:
                current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
                self.start_time = time.time()
                self.start_line_edit.setText(current_time)

            self.start_button.setObjectName("startbutton")
            if self.program_radio_button.isChecked():
                self.running = False
                ser.flushInput()
                ser_p.flushInput()
                ser.write(b'START\r\n')
                sign = ser.readline().decode().strip()
                time.sleep(1)
                ser.flushInput()
                self.setRestriction()
                #print(sign)

            if self.no_program_radio_button.isChecked():
                self.buttonStyle()
                self.start_button.setText("No Programm")
                self.setRestriction()
                self.program_radio_button.setEnabled(False)
                if self.filepath != '':
                    self.start_button.setText("Saving...")

            if not self.receiving:
                self.receiving = True
                self.serial_thread.start()
                self.running = True

            if sign == 'OK' and not self.pressure_exceeded:
                self.display_message("Programm started!")
                self.start_button.setText("Programm...")
                self.buttonStyle()
                self.no_program_radio_button.setEnabled(False)
                if self.filepath != '':
                    # Hier wird der Start-Button auf Grün und der Text auf "Saving..." geändert
                    self.start_button.setText("Programm saving")
                    self.display_message("Programm started and recorded!")
                    ser.flushInput()
                    ser_p.flushInput()

                self.running = True

    def setRestriction(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.serialAction.setEnabled(False)
        self.reglerAction.setEnabled(False)
        self.programmeingabeAction.setEnabled(False)
        self.save.setEnabled(False)

    def buttonStyle(self):
        self.start_button.setStyleSheet(
            "QPushButton#startbutton {"
            "background-color: green;"
            "border-style: outset;"
            "border-width: 2px;"
            "border-radius: 10px;"
            "border-color: beige;"
            "font: bold 14px;"
            "color: black;"
            "max-width: 8em;"  # Maximale Breite auf 8em setzen
            "max-height: 2em;"  # Maximale Höhe auf 2em setzen
            "padding: 6px;"
            "}"
        )

    def stop_data_receiving(self):
        if self.receiving:
            current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
            self.stop_line_edit.setText(current_time)
            if self.filepath != '' and not self.pressure_exceeded:
                self.file = ''
                self.display_message("Saving stopped!")

            if ser and self.program_radio_button.isChecked():
                self.running = False
                self.serial_thread.stop()
                time.sleep(3)
                ser.write(b'STOP\r\n')
                sign = ser.readline().decode().strip()

                if sign == 'OK' and not self.pressure_exceeded:
                    self.display_message("Programm stopped!")
                    ser.flushInput()
                    ser_p.flushInput()


        elif not ser:
            self.display_message("Not connected to LAUDA Thermostat")

        if self.receiving:
            self.receiving = False
            self.serial_thread.stop()
            self.running = False
            self.enable_buttons()  # Rufen Sie die Funktion auf, um die Buttons zu aktivieren und Stile zurückzusetzen

    def enable_buttons(self):
        self.start_button.setEnabled(True)
        self.no_program_radio_button.setEnabled(True)
        self.program_radio_button.setEnabled(True)
        self.serialAction.setEnabled(True)
        self.reglerAction.setEnabled(True)
        self.programmeingabeAction.setEnabled(True)
        self.save.setEnabled(True)
        self.reset_button_styles()  # Rufen Sie die Funktion auf, um die Stile der Buttons zurückzusetzen

    def reset_button_styles(self):
        self.program_radio_button.setStyleSheet("")
        self.no_program_radio_button.setStyleSheet("")
        self.start_button.setStyleSheet("")
        self.start_button.setText("Start")

    def reset_pressure_exceeded(self):
        self.pressure_exceeded = False
        self.filepath = ''
        self.start_line_edit.setText('Process startet...')
        self.stop_line_edit.setText('Process stopped...')

    def checkHighP(self, p):
        if p > 50 and not self.pressure_exceeded:  # Nur wenn der Druck zum ersten Mal den Schwellenwert überschreitet            self.pressure_exceeded = True  # Setzen Sie den Zustand auf True, um zu verhindern, dass dies erneut ausgeführt wird
            self.pressure_exceeded = True
            self.stop_data_receiving()
            ser.write(b'OUT_30\r\n')
            out = ser.readline().decode().strip()
            if out == 'OK':
                self.no_program_radio_button.setChecked(True)
                self.start_data_receiving()
                self.display_message("Programm stopped and Ts reset to 30 °C due to pressure > 50 bar!")

    def update_data(self, Ti, T1, Ts, p, status_sign, Tu, To, Xp, Tn, Tv):
        if self.receiving:
            # Fügen Sie neue Daten an den Ringpuffer an
            self.time.append(time.time())
            self.Ti.append(Ti)
            self.T1.append(T1)
            self.Ts.append(Ts)
            self.p.append(p)

            self.checkHighP(p)

            # Aktualisieren Sie den Plot mit dem Ringpuffer
            self.update_plot()
            self.updateStatusInfo(status_sign, Tu, To, Xp, Tn, Tv)
            # Update digital output
            self.ti_edit.setText(str(Ti))
            self.t1_edit.setText(str(T1))
            self.ts_edit.setText(str(Ts))
            self.p_edit.setText(str(p))

            # Erstellen Sie ein neues Datenobjekt für den CSV-Speicher
            new_data = {"time": [datetime.now()], "Ti": [Ti], "T1": [T1], "Ts": [Ts], "p": [p]}

            # Speichern Sie neue Daten in der CSV-Datei
            if self.filepath != '':
                self.saveCSV(new_data, self.filepath)

    def update_plot(self):
        # Umwandlung von deque in eine Liste für die Verwendung in der Visualisierung
        time_data = list(self.time)
        Ti_data = list(self.Ti)
        T1_data = list(self.T1)
        Ts_data = list(self.Ts)
        p_data = list(self.p)

        # Aktualisieren Sie den Plot mit den Daten im Ringpuffer
        self.plot_widget.clear()
        self.plot_widget.plot(time_data, Ti_data, pen='#009999', name='Ti')
        self.plot_widget.plot(time_data, T1_data, pen={'color': 'r', 'width': 2}, name='T1')
        self.plot_widget.plot(time_data, Ts_data, pen='#33FF33', name='Ts')
        self.plot_widget.plot(time_data, p_data, pen={'color': 'b', 'width': 2}, name='p')

    def updateStatusInfo(self, status_sign, Tu, To, Xp, Tn, Tv):

        status_info = [
            "Störung" if int(status_sign[0]) else "Keine Störung",
            "Störung" if int(status_sign[1]) else "Niveau o.k.",
            "Läuft" if int(status_sign[2]) else "AUS",
            f"{int(status_sign[3])}",
            "Vorgegeben" if int(status_sign[4]) else "Analogeingänge AUS",
            "Angeschlossen" if int(status_sign[5]) else "Nicht angeschlossen",
            "Angeschlossen" if int(status_sign[6]) else "Nicht angeschlossen"
        ]
        # Anpassung basierend auf den Bedingungen
        if int(status_sign[3]) == 0:
            status_info[3] = "Ti (Vorlauf)"
        elif int(status_sign[3]) == 1:
            status_info[3] = "T1 (im Reaktor)"
        elif int(status_sign[3]) == 2:
            status_info[3] = "T2"

        for i in range(7):
            self.statusWindow.status_edits[i].setText(status_info[i])

        self.statusWindow.parameter_edits[0].setText(str(Tu))
        self.statusWindow.parameter_edits[1].setText(str(To))
        self.statusWindow.parameter_edits[2].setText(str(Xp))
        self.statusWindow.parameter_edits[3].setText(str(Tn))
        self.statusWindow.parameter_edits[4].setText(str(Tv))

    def saveCSV(self, new_data, filepath):
        with open(filepath, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([new_data['time'][0].strftime("%Y-%m-%d %H:%M:%S"),
                             new_data['Ti'][0],
                             new_data['T1'][0],
                             new_data['Ts'][0],
                             new_data['p'][0]])

    def createMenu(self):
        self.menuBar = self.menuBar()
        self.menuBar.setNativeMenuBar(False)

        # Lauda menu
        self.laudaMenu = self.menuBar.addMenu("&LAUDA")
        self.quit = QAction("Quit all", self)
        self.quit.setShortcut("Ctrl+Q")
        self.quit.triggered.connect(self.showExit)
        self.laudaMenu.addAction(self.quit)

        # Settings menu
        self.settingsMenu = self.menuBar.addMenu("&Settings")

        self.serialAction = QAction("Serial Port", self)
        self.serialAction.setShortcut("Ctrl+P")
        self.serialAction.triggered.connect(self.openSerialDialog)
        self.settingsMenu.addAction(self.serialAction)

        self.reglerAction = QAction("Reglerparameter", self)
        self.reglerAction.setShortcut("Ctrl+R")
        self.reglerAction.triggered.connect(self.openReglerParameterWindow)
        self.settingsMenu.addAction(self.reglerAction)

        self.programmeingabeAction = QAction("Programm Input", self)
        self.programmeingabeAction.setShortcut("Ctrl+P")
        self.programmeingabeAction.triggered.connect(self.openNewProgrammDialog)
        self.settingsMenu.addAction(self.programmeingabeAction)

        # File menu
        self.fileMenu = self.menuBar.addMenu("&File")
        self.save = QAction("Save", self)
        self.save.setShortcut("Ctrl+S")
        self.save.triggered.connect(self.showSaveFile)
        self.fileMenu.addAction(self.save)

        # Information menu
        self.infoMenu = self.menuBar.addMenu("&Information")
        self.programmInfoAction = QAction("Programm Info", self)
        self.programmInfoAction.setShortcut("Ctrl+K")
        self.programmInfoAction.triggered.connect(self.openInfoProgrammDialog)
        self.infoMenu.addAction(self.programmInfoAction)

        # Status menu item
        self.statusAction = QAction("Status", self)
        self.statusAction.setShortcut("Ctrl+S")  # Tastenkombination kann nach Bedarf geändert werden
        self.statusAction.triggered.connect(self.openStatusWindow)
        self.infoMenu.addAction(self.statusAction)

        # Help menu
        self.helpMenu = self.menuBar.addMenu("&Help")
        self.info = QAction("Info", self)
        self.info.setShortcut("Ctrl+H")
        self.info.triggered.connect(self.openHelpWindow)
        self.helpMenu.addAction(self.info)

    def showExit(self):
        reply = QMessageBox.question(self, 'Message',
                                     "Are you sure to quit?", QMessageBox.StandardButton.Yes |
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self:
                self.close()

            try:
                self.mainWindow.close()
            except:
                pass
            try:
                self.newProgramm.close()
            except:
                pass
            try:
                self.infoProgramm.close()
            except:
                pass
            try:
                self.reglerParameter.close()
            except:
                pass
            try:
                self.statusWindow.close()
            except:
                pass
            try:
                self.helpWindow.close()
            except:
                pass

        else:
            pass

    def showSaveFile(self):
        self.filename = ''
        file_filter = 'Data File (*.csv)'
        response = QFileDialog.getSaveFileName(
            parent=self,
            caption='Select a data file',
            directory=r'C:\Users\Ivet17\OneDrive\Desktop\HTC_Process_Data',
            filter=file_filter,
            initialFilter='Excel File (*.csv)'
        )
        self.filepath = response[0]

    def createtemperaturGroupbox(self):
        self.groupbox = QGroupBox("Temperaturen und Druck")

        topLayout = QHBoxLayout()

        # QLineEdit-Instanzen initialisieren
        self.ti_edit = QLineEdit()
        self.t1_edit = QLineEdit()
        self.ts_edit = QLineEdit()
        self.p_edit = QLineEdit()


        fields = [
            ("Ti (Vorlauf):", self.ti_edit, "°C", 90),
            ("T1 (im Reaktor):", self.t1_edit, "°C", 90),
            ("Ts (Sollwert):", self.ts_edit, "°C", 90),
            ("p:", self.p_edit, "bar", 90)
        ]

        for label_text, line_edit, unit, width in fields:

            label = QLabel(label_text)
            line_edit.setFixedWidth(width)
            line_edit.setReadOnly(True)
            line_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            unit_label = QLabel(unit)

            # Fügen Sie Abstand (Leerzeichen) zwischen den Widgets hinzu
            spacer_item = QSpacerItem(40, 30, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            topLayout.addWidget(label)
            topLayout.addWidget(line_edit)
            topLayout.addWidget(unit_label)
            topLayout.addItem(spacer_item)
        topLayout.addStretch(1)
        self.groupbox.setFixedHeight(120)
        self.groupbox.setLayout(topLayout)

    def createDateTimeGroupBox(self):
        datetime_groupbox = QGroupBox("Date and Time")
        datetime_layout = QHBoxLayout()

        # QLineEdit für "Prozess startet:"
        self.start_line_edit = QLineEdit()
        self.start_line_edit.setMinimumWidth(100)
        self.start_line_edit.setReadOnly(True)
        self.start_line_edit.setText("Prozess startet: ...")  # Setze den anfänglichen Text

        # QLineEdit für "Prozess stopped:"
        self.stop_line_edit = QLineEdit()
        self.stop_line_edit.setMinimumWidth(100)
        self.stop_line_edit.setReadOnly(True)
        self.stop_line_edit.setText("Prozess stopped: ...")  # Setze den anfänglichen Text

        datetime_layout.addWidget(QLabel("Process start:"))
        datetime_layout.addWidget(self.start_line_edit)
        datetime_layout.addWidget(QLabel("Process stopp:"))
        datetime_layout.addWidget(self.stop_line_edit)
        datetime_layout.addStretch(1)
        datetime_groupbox.setLayout(datetime_layout)
        return datetime_groupbox

    def createControlGroupBox(self):
        control_groupbox = QGroupBox("Control")
        control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.start_button.clicked.connect(self.start_data_receiving)
        self.stop_button.clicked.connect(self.stop_data_receiving)

        self.program_radio_button = QRadioButton("Program")
        self.no_program_radio_button = QRadioButton("No Program")
        self.program_radio_button.setChecked(True)

        self.program_button_group = QButtonGroup()
        self.program_button_group.addButton(self.program_radio_button)
        self.program_button_group.addButton(self.no_program_radio_button)

        control_layout.addWidget(self.program_radio_button)
        control_layout.addWidget(self.no_program_radio_button)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_groupbox.setFixedSize(500,120)
        control_groupbox.setLayout(control_layout)

        return control_groupbox
    #Open Menu
    def openSerialDialog(self):
        self.serialPort= SerialPortGui(self)
        self.serialPort.exec()

    def openReglerParameterWindow(self):
        self.reglerParameter = ReglerParameterDialog()
        self.reglerParameter.exec()

    def openNewProgrammDialog(self):
        self.newProgramm = NewProgramEnterDialog()
        self.newProgramm.exec()

    def openInfoProgrammDialog(self):
        self.infoProgramm = ProgrammInfoDialog()
        self.infoProgramm.show()

    def openStatusWindow(self):
        global ser
        self.statusWindow = StatusWindow()
        self.statusWindow.exec()

    def openHelpWindow(self):
        self.helpWindow = HelpWindow()
        self.helpWindow.show()

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')
        msg_box.setText(message)
        msg_box.exec()


class ReglerParameterDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reglerparameter")
        self.setFixedSize(280, 450)
        self.setupUI()

        self.status_window = StatusWindow()


    def setupUI(self):
        layout = QVBoxLayout()

        regelgrossen_groupbox = QGroupBox("Regelgrößen")
        regelgrossen_layout = QFormLayout()

        spinbox_width = 100

        self.sollwert_input = QDoubleSpinBox()
        self.sollwert_input.setRange(0.0, 250.0)
        self.sollwert_input.setValue(30.0)
        self.sollwert_input.setFixedWidth(spinbox_width)

        self.tu_input = QDoubleSpinBox()
        self.tu_input.setRange(-10.0, 250.0)
        self.tu_input.setValue(-10.0)
        self.tu_input.setFixedWidth(spinbox_width)

        self.uebertemperatur_input = QDoubleSpinBox()
        self.uebertemperatur_input.setRange(0.0, 300.0)
        self.uebertemperatur_input.setValue(280.0)
        self.uebertemperatur_input.setFixedWidth(spinbox_width)

        self.regel_quelle_dropdown = QComboBox()
        self.regel_quelle_dropdown.addItems(['T1 (im Reaktor)', 'Ti (im Vorlauf)'])
        self.regel_quelle_dropdown.setCurrentText('T1 (im Reaktor)')

        regelgrossen_layout.addRow('Ts:', self.sollwert_input)
        regelgrossen_layout.addRow('Tu:', self.tu_input)
        regelgrossen_layout.addRow('To:', self.uebertemperatur_input)
        regelgrossen_layout.addRow('Sw Quelle:', self.regel_quelle_dropdown)

        regelgrossen_groupbox.setLayout(regelgrossen_layout)
        regelgrossen_groupbox.setFixedHeight(200)

        regelparameter_groupbox = QGroupBox("Regelparameter")
        regelparameter_layout = QFormLayout()

        self.xp_input = QDoubleSpinBox()
        self.xp_input.setRange(0.0, 5.0)
        self.xp_input.setValue(2.0)
        self.xp_input.setFixedWidth(spinbox_width)

        self.tn_input = QDoubleSpinBox()
        self.tn_input.setRange(0.0, 30.0)
        self.tn_input.setValue(25.0)
        self.tn_input.setFixedWidth(spinbox_width)

        self.tv_input = QDoubleSpinBox()
        self.tv_input.setRange(0.0, 10.0)
        self.tv_input.setValue(5.0)
        self.tv_input.setFixedWidth(spinbox_width)

        regelparameter_layout.addRow('Xp:', self.xp_input)
        regelparameter_layout.addRow('Tn:', self.tn_input)
        regelparameter_layout.addRow('Tv:', self.tv_input)

        regelparameter_groupbox.setLayout(regelparameter_layout)
        regelparameter_groupbox.setFixedHeight(150)

        enter_button = QPushButton("Enter")
        enter_button.clicked.connect(self.enter_button_clicked)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        layout.addWidget(regelgrossen_groupbox)
        layout.addWidget(regelparameter_groupbox)
        layout.addWidget(enter_button)
        layout.addWidget(close_button)
        self.setLayout(layout)

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')
        msg_box.setText(message)
        msg_box.exec()

    def enter_button_clicked(self):
        global ser
        if ser and ser.is_open:
            # Eingabewerte aus den Textfeldern lesen
            Ts = self.sollwert_input.value()
            Tu = self.tu_input.value()
            To = self.uebertemperatur_input.value()
            regel_quelle = self.regel_quelle_dropdown.currentText()
            Xp = self.xp_input.value()
            Tn = self.tn_input.value()
            Tv = self.tv_input.value()

            # Befehle erstellen und an das Serielle Interface senden
            ser.write(f'OUT_{Ts:.2f}\r\n'.encode())  # Sollwertübergabe
            out = ser.readline().decode().strip()

            ser.write(f'OUT_L{Tu:.2f}\r\n'.encode())  # Schaltpunkt für den Untertemperaturwert Tu
            out_l = ser.readline().decode().strip()

            ser.write(f'OUT_H{To:.2f}\r\n'.encode())  # Übertemperaturschaltpunkt
            out_h = ser.readline().decode().strip()

            out_rt1, out_rti = "", ""
            if regel_quelle == 'T1 (im Reaktor)':
                ser.write(b'OUT_RT1\r\n')  # Schaltet Regelgrößen auf die Quelle externes Pt 100 T1
                out_rt1 = ser.readline().decode().strip()
            elif regel_quelle == 'Ti (im Vorlauf)':
                ser.write(
                    b'OUT_RTi\r\n')  # Schaltet Regelgrößen auf die Quelle externes Ti (Badfühler). Regelung nach Badtemperatur
                out_rti = ser.readline().decode().strip()

            ser.write(f'OUT_XP{Xp:.2f}\r\n'.encode())  # Einstellung des Regelparameters Xp für den Regler
            out_xp = ser.readline().decode().strip()

            ser.write(f'OUT_TN{Tn:.2f}\r\n'.encode())  # Einstellung des Regelparameters Tn für den Regler
            out_tn = ser.readline().decode().strip()

            ser.write(f'OUT_TV{Tv:.2f}\r\n'.encode())  # Einstellung des Regelparameters Tn für den Regler
            out_tv = ser.readline().decode().strip()

            out_all = [out, out_l, out_h, out_rt1, out_rti, out_xp, out_tn, out_tv]
            out_ok = [out for out in out_all if out == 'OK']

            if not out_ok:
                self.display_message("Error: Not entered")
            else:
                self.display_message("New Values entered")
                self.accept()
        else:
            self.display_message("No connection to LAUDA Thermostat")


class NewProgramEnterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Enter New Program")
        self.setFixedSize(QSize(400, 600))
        self.programmInfo = ProgrammInfoDialog()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        # Create and add Start Temperature
        start_temperature_label = QLabel("Start Temperature:")
        self.start_temperature_spinbox = QSpinBox()
        self.start_temperature_spinbox.setFixedWidth(40)
        self.start_temperature_spinbox.setRange(0, 250)
        self.start_temperature_unit_label = QLabel("°C")


        start_temperature_layout = QHBoxLayout()
        start_temperature_layout.addWidget(start_temperature_label)
        start_temperature_layout.addWidget(self.start_temperature_spinbox)
        start_temperature_layout.addWidget(self.start_temperature_unit_label)
        start_temperature_layout.addStretch(1)

        main_layout.addLayout(start_temperature_layout)
        main_layout.addStretch(1)

        # Create GroupBox for Segments
        segment_groupbox = QGroupBox("Segments")
        segment_layout = QVBoxLayout()

        # Create and add SpinBoxes for Segment parameters
        self.segment_temperature_inputs = []
        self.segment_hour_inputs = []
        self.segment_minute_inputs = []


        # Create and add GroupBoxes for Segment parameters
        for i in range(1, 6):
            segment_param_groupbox = QGroupBox(f"Segment {i}")
            segment_param_layout = QHBoxLayout()

            # Create and add SpinBox for Temperature
            self.temperature_label = QLabel("Temperature:")
            self.temperature_spinbox = QSpinBox()
            self.temperature_spinbox.setRange(0, 250)
            self.temperature_unit_label = QLabel("°C")
            segment_param_layout.addWidget(self.temperature_label)
            segment_param_layout.addWidget(self.temperature_spinbox)
            segment_param_layout.addWidget(self.temperature_unit_label)

            # Create and add SpinBoxes for Hours and Minute
            self.hour_spinbox = QSpinBox()
            self.hour_label = QLabel("h")
            self.hour_spinbox.setRange(0, 9)
            self.minute_spinbox = QSpinBox()
            self.minute_spinbox.setRange(0, 59)
            self.minute_label = QLabel("min")
            segment_param_layout.addWidget(self.hour_spinbox)
            segment_param_layout.addWidget(self.hour_label)
            segment_param_layout.addWidget(self.minute_spinbox)
            segment_param_layout.addWidget(self.minute_label)

            segment_param_groupbox.setLayout(segment_param_layout)
            segment_layout.addWidget(segment_param_groupbox)

            # Fügen Sie die Spinboxen den entsprechenden Listen hinzu
            self.segment_temperature_inputs.append(self.temperature_spinbox)
            self.segment_hour_inputs.append(self.hour_spinbox)
            self.segment_minute_inputs.append(self.minute_spinbox)

        segment_groupbox.setLayout(segment_layout)

        main_layout.addWidget(segment_groupbox)

        # Create GroupBox for Tolerance Band and Cycles
        tolerance_cycles_groupbox = QGroupBox("Tolerance Band and Cycles")
        tolerance_cycles_layout = QVBoxLayout()

        # Create and add SpinBox for Tolerance Band with unit "K" in the first line
        tolerance_band_layout = QHBoxLayout()
        self.tolerance_band_label = QLabel("Tolerance Band:")
        self.tolerance_band_spinbox = QDoubleSpinBox()
        self.tolerance_band_spinbox.setFixedWidth(80)  # Set the width of the SpinBox
        self.tolerance_band_spinbox.setRange(0.1, 9.9)
        self.tolerance_band_spinbox.setValue(5.0)
        self.tolerance_band_unit_label = QLabel("K")
        tolerance_band_layout.addWidget(self.tolerance_band_label)
        tolerance_band_layout.addWidget(self.tolerance_band_spinbox)
        tolerance_band_layout.addWidget(self.tolerance_band_unit_label)

        # Create and add SpinBox for Cycles in the second line
        cycles_layout = QHBoxLayout()
        self.cycles_label = QLabel("Cycles:")
        self.cycles_spinbox = QSpinBox()
        self.cycles_spinbox.setFixedWidth(80)  # Set the width of the SpinBox
        self.cycles_spinbox.setRange(1, 10)
        self.cycles_label_unit_label = QLabel(" ")
        cycles_layout.addWidget(self.cycles_label)
        cycles_layout.addWidget(self.cycles_spinbox)
        cycles_layout.addWidget(self.cycles_label_unit_label)

        # Add both lines to the layout
        tolerance_cycles_layout.addLayout(tolerance_band_layout)
        tolerance_cycles_layout.addLayout(cycles_layout)

        tolerance_cycles_groupbox.setLayout(tolerance_cycles_layout)
        main_layout.addWidget(tolerance_cycles_groupbox)

        # Create the Enter Button
        enter_button = QPushButton("Enter")
        enter_button.clicked.connect(self.enter_button_clicked)

        main_layout.addWidget(enter_button)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        main_layout.addWidget(close_button)

        self.setLayout(main_layout)

    def enter_button_clicked(self):
        global ser
        if not ser:
            self.display_message("No connection to LAUDA Thermostat!")
        # Sollwertübergabe
        else:
           #

            Ts = self.start_temperature_spinbox.value()
            ser.write(f'OUT_{Ts:.2f}\r\n'.encode())
            out = ser.readline().decode().strip()

            # Eingabewerte aus den Textfeldern lesen
            segment_temperature_inputs = [self.segment_temperature_inputs[i] for i in range(5)]
            segment_hour_inputs = [self.segment_hour_inputs[i] for i in range(5)]
            segment_minute_inputs = [self.segment_minute_inputs[i] for i in range(5)]

            segment_values = []
            for i in range(5):
                temperature = segment_temperature_inputs[i].value()
                hours = segment_hour_inputs[i].value()
                minutes = segment_minute_inputs[i].value()
                segment_values.append((temperature, hours, minutes))

            # Überprüfen, ob Temperaturwerte ungleich null sind
            valid_segments = [(temp, hours, minutes) for temp, hours, minutes in segment_values if temp != 0]

            programm_ok = []

            # Befehle erstellen und an das Serielle Interface senden
            for i, (temperature, hours, minutes) in enumerate(valid_segments, start=0):
                segment_command = f'SEG_({i:02d})_{temperature:03d}.{hours:02d}:{minutes:02d}\r\n'
                ser.write(segment_command.encode())
                sign = ser.readline().decode().strip()
                programm_ok.append(sign)
                #print(segment_command.encode())
                time.sleep(1)

            # Toleranzband und Zyklenzahl
            tolerance_band = self.tolerance_band_spinbox.value()
            cycles = self.cycles_spinbox.value()

            if tolerance_band != 0:
                tolerance_band_command = f'OUT_TB{tolerance_band}\r\n'
                ser.write(tolerance_band_command.encode())
                sign = ser.readline().decode().strip()
                programm_ok.append(sign)
                #print(tolerance_band_command.encode())
                time.sleep(1)

            if cycles != 0:
                cycles_command = f'OUT_CY{cycles}\r\n'
                ser.write(cycles_command.encode())
                sign = ser.readline().decode().strip()
                programm_ok.append(sign)
                #print(cycles_command.encode())
                time.sleep(1)

            if len(programm_ok) > 2:
                self.saveLastentered() #saves last entered program
                self.display_message('New Program entered!')
                self.accept()
            else:
                self.display_message('No new Program entered!')

    def saveLastentered(self):

        entered_data = {
            'Last Updated': QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"),
            'Start Temperature': self.start_temperature_spinbox.value()
        }

        segment_values = []
        for i in range(5):
            temperature = self.segment_temperature_inputs[i].value()
            hours = self.segment_hour_inputs[i].value()
            minutes = self.segment_minute_inputs[i].value()
            if temperature != 0:
                segment_values.append((f"Segment {i + 1}", temperature, hours, minutes))

        # Speichern der Segmentdaten in die CSV
        for i, segment_data in enumerate(segment_values, start=1):
            segment_key = f"Segment {i}"
            entered_data[segment_key] = f"Temp: {segment_data[1]}, Hours: {segment_data[2]}, minutes: {segment_data[3]}"


        programm_data_path = resource_path(r'res\programm_data.csv')
        # print(programm_data_path)
        # CSV-Datei öffnen und Daten speichern
        with open(programm_data_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=entered_data.keys())
            writer.writeheader()
            writer.writerow(entered_data)

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')
        msg_box.setText(message)
        msg_box.exec()

class ProgrammInfoDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Program Info")
        self.setMinimumSize(350, 200)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        programm_data_path = resource_path(r'res\programm_data.csv')

        try:
            # Anzeigen der Daten aus der CSV-Datei im Info-Dialog
            with open(programm_data_path, mode='r') as file:
                reader = csv.DictReader(file)
                data = next(reader)

                # Hinzufügen von Titeln und Daten zum Layout
                title_label = QLabel("<h2>Last Entered Program</h2>")
                title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                main_layout.addWidget(title_label)
                main_layout.setSpacing(15)

            for key, value in data.items():
                label = QLabel(f"<b>{key}:</b> {value}")
                main_layout.addWidget(label)

        except StopIteration:
            label = QLabel("No program data found!")
            main_layout.addWidget(label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        main_layout.addStretch(1)
        main_layout.addWidget(close_button)

        self.setLayout(main_layout)


class HelpWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("LAUDA Operating Instructions")
        self.resize(640, 480)

        layout = QVBoxLayout(self)

        filename = resource_path(r'res\ush_400.pdf')

        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.search_text)
        self.search_input.returnPressed.connect(self.continue_search)

        self.view = QWebEngineView()
        settings = self.view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, True
        )
        url = QUrl.fromLocalFile(filename)
        self.view.load(url)

        layout.addWidget(self.view)
        layout.addWidget(self.search_input)

        self.text_to_search = ""

    def search_text(self, text):
        self.text_to_search = text
        if text:
            flag = QWebEnginePage.FindFlag.FindCaseSensitively
            self.view.findText(text, flag)

    def continue_search(self):
        if self.text_to_search:
            flag = QWebEnginePage.FindFlag.FindBackward | QWebEnginePage.FindFlag.FindCaseSensitively
            self.view.findText(self.text_to_search, flag)



class SerialThread(QThread):
    dataReceived = pyqtSignal(float, float, float, float, str, float, float, float, float, float)

    def __init__(self):
        super().__init__()

        global ser
        global ser_p
        self.running = False

    def run(self):

        self.running = True

        if not ser:
            self.display_message("Not connected.")
            self.running = False

        while self.running:
            try:
                ser.write(b'IN_1\r\n')
                Ti = ser.readline().strip().decode()
                ser.write(b'IN_2\r\n')
                T1 = ser.readline().strip().decode()
                ser.write(b'IN_3\r\n')
                Ts = ser.readline().strip().decode()
                ser_p.write(b'P')
                p = ser_p.readline().strip().decode('ISO-8859-1', errors='replace')

                ser.write(b'IN_4\r\n')
                status_sign = ser.readline().decode().strip()
                ser.write(b'IN_8\r\n')
                Tu = float(ser.readline().strip().decode())
                ser.write(b'IN_9\r\n')
                To = float(ser.readline().strip().decode())
                ser.write(b'IN_A\r\n')
                Xp = float(ser.readline().strip().decode())
                ser.write(b'IN_B\r\n')
                Tn = float(ser.readline().strip().decode())
                ser.write(b'IN_C\r\n')
                Tv = float(ser.readline().strip().decode())
            except:
                pass

            try:
                Ti = float(Ti)
            except ValueError:
                pass
            try:
                T1 = float(T1)
            except ValueError:
                pass

            try:
                Ts = float(Ts)
            except ValueError:
                pass

            try:
                p = float(p)
            except ValueError:
                pass
            try:
                status_sign = str(status_sign)
            except ValueError:
                pass
            try:
                Tu = float(Tu)
            except ValueError:
                pass
            try:
                To = float(To)
            except ValueError:
                pass
            try:
                Xp = float(Xp)
            except ValueError:
                pass
            try:
                Tn = float(Tn)
            except ValueError:
                pass
            try:
                Tv = float(Tv)
            except ValueError:
                pass

            except (ValueError, serial.SerialException) as e:
                print(f"Error updating status information: {e}")


            if type(Ti) == float and type(T1) == float and type(Ts) == float and type(p) == float:

                    self.dataReceived.emit(Ti, T1, Ts, p, status_sign, Tu, To, Xp, Tn, Tv)




    def stop(self):
        self.running = False

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')
        msg_box.setText(message)
        msg_box.exec()



class StatusWindow(QDialog):
    def __init__(self):
        super().__init__()

        #self.running = False
        self.setWindowTitle("Status Window")
        self.setFixedSize(600, 600)
        self.initUI()


    def initUI(self):
        layout = QVBoxLayout()

        # GroupBox für den allgemeinen Status
        self.groupbox_status = QGroupBox("Status")
        self.groupbox_layout_status = QVBoxLayout()

        self.status_labels = [
            "Übertemperaturstörung: ",
            "Unterniveaustörung: ",
            "Programmgebersegment läuft: ",
            "Regelung der Temperatur (Ti/T1/T2): ",
            "Solwert durch Analogeingänge vorgegeben: ",
            "Externes Pt100 T1 angeschlossen: ",
            "Externes Pt100 T2 angeschlossen: "
        ]

        self.status_edits = []  # Liste für die QLineEdit-Widgets

        for i in range(7):
            label = QLabel(self.status_labels[i])
            edit = QLineEdit()
            edit.setReadOnly(True)
            self.groupbox_layout_status.addWidget(label)
            self.groupbox_layout_status.addWidget(edit)
            self.status_edits.append(edit)

        self.groupbox_status.setLayout(self.groupbox_layout_status)

        # GroupBox für Reglerparameter
        self.groupbox_parameters = QGroupBox("Reglerparameter")
        self.groupbox_layout_parameters = QVBoxLayout()

        self.parameter_labels = [
            "Tu: ",
            "To: ",
            "Xp: ",
            "Tn: ",
            "Tv: "
        ]

        self.parameter_edits = []  # Liste für die QLineEdit-Widgets

        for i in range(5):
            label = QLabel(self.parameter_labels[i])
            edit = QLineEdit()
            edit.setReadOnly(True)
            self.groupbox_layout_parameters.addWidget(label)
            self.groupbox_layout_parameters.addWidget(edit)
            self.parameter_edits.append(edit)

        self.groupbox_parameters.setLayout(self.groupbox_layout_parameters)

        # Horizontal Box Layout für beide GroupBoxes
        hbox = QHBoxLayout()
        hbox.addWidget(self.groupbox_status)
        hbox.addWidget(self.groupbox_parameters)

        layout.addLayout(hbox)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def display_message(self, message):
        msg_box = QMessageBox()
        msg_box.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        msg_box.setStyleSheet('QDialog{border: 1px solid #888888;}')
        msg_box.setText(message)
        msg_box.exec()
