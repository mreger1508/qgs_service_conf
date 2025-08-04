from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from pathlib import Path
from .functions import (
    path_to_conf, os_is_windows,
    read_service_conf, write_service_conf,
    create_service, edit_service, delete_service,
    redact_sensitive,
)

UI_PATH = Path(__file__).parent / "qgs_service_conf.ui"

class PluginDialog(QDialog):
    def __init__(self):
        super().__init__()
        if not UI_PATH.exists():
            raise FileNotFoundError(f"UI-Datei nicht gefunden: {UI_PATH}")
        uic.loadUi(str(UI_PATH), self)

        self.cfg_path = path_to_conf(is_windows=os_is_windows())
        self.services = read_service_conf(self.cfg_path)

        # Signalverbindungen
        self.comboBoxServices.currentTextChanged.connect(self.on_service_selected)
        self.pushButtonCreate.clicked.connect(self.on_create)
        self.pushButtonSave.clicked.connect(self.on_save)
        self.pushButtonDelete.clicked.connect(self.on_delete)
        self.pushButtonClose.clicked.connect(self.close)
        self.pushButtonHelp.clicked.connect(self.show_help)

        self.load_services_into_combo()

    def load_services_into_combo(self):
        self.comboBoxServices.clear()
        for svc in sorted(self.services.keys()):
            self.comboBoxServices.addItem(svc)
        if self.services:
            first = list(self.services.keys())[0]
            self.comboBoxServices.setCurrentText(first)
            self.populate_fields(first)

    def on_service_selected(self, service_name: str):
        if service_name:
            self.populate_fields(service_name)

    def populate_fields(self, service_name: str):
        svc = self.services.get(service_name, {})
        self.lineEditService.setText(service_name)
        self.lineEditHost.setText(svc.get("host", ""))
        self.lineEditPort.setText(svc.get("port", ""))
        self.lineEditDatabase.setText(svc.get("dbname", ""))
        self.lineEditUsername.setText(svc.get("user", ""))
        self.lineEditPassword.setText(svc.get("password", ""))

    def gather_params_from_ui(self) -> dict:
        return {
            "host": self.lineEditHost.text().strip(),
            "port": self.lineEditPort.text().strip(),
            "dbname": self.lineEditDatabase.text().strip(),
            "user": self.lineEditUsername.text().strip(),
            "password": self.lineEditPassword.text(),
        }

    def on_create(self):
        name = self.lineEditService.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Servicenamen eingeben.")
            return
        params = self.gather_params_from_ui()
        try:
            create_service(self.services, name, params, overwrite=False)
            write_service_conf(self.cfg_path, self.services)
            QMessageBox.information(self, "Erfolg", f"Service '{name}' erstellt.")
            self.load_services_into_combo()
            self.comboBoxServices.setCurrentText(name)
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Erstellen", str(e))

    def on_save(self):
        current = self.comboBoxServices.currentText().strip()
        if not current:
            QMessageBox.warning(self, "Fehler", "Kein Service ausgewählt zum Speichern.")
            return
        params = self.gather_params_from_ui()
        try:
            edit_service(self.services, current, params)
            write_service_conf(self.cfg_path, self.services)
            QMessageBox.information(self, "Erfolg", f"Service '{current}' gespeichert.")
            self.load_services_into_combo()
            self.comboBoxServices.setCurrentText(current)
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", str(e))

    def on_delete(self):
        current = self.comboBoxServices.currentText().strip()
        if not current:
            QMessageBox.warning(self, "Fehler", "Kein Service ausgewählt zum Löschen.")
            return
        confirm = QMessageBox.question(
            self,
            "Löschen bestätigen",
            f"Service '{current}' wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            delete_service(self.services, current)
            write_service_conf(self.cfg_path, self.services)
            QMessageBox.information(self, "Erfolg", f"Service '{current}' gelöscht.")
            self.load_services_into_combo()
        except KeyError as e:
            QMessageBox.warning(self, "Nicht gefunden", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Löschen", str(e))

    def show_help(self):
        QMessageBox.information(
            self,
            "Hilfe",
            "Mit diesem Dialog kannst du PostgreSQL pg_service.conf-Services erstellen, bearbeiten und löschen.\n"
            "1. Service auswählen oder Namen eingeben.\n"
            "2. Felder ausfüllen.\n"
            "3. 'Neuen Service erstellen' / 'Serviceänderungen speichern' klicken.\n"
            "4. Löschen mit 'Ausgewählten Service löschen'.",
        )
