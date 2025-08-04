from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from . import resources_rc

class QgsServiceConfPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        if self.action is None:
            self.action = QAction(QIcon(":/plugins/qgs_service_conf/icon.svg"), "Service Conf", self.iface.mainWindow())
            self.action.triggered.connect(self.run)
            self.iface.addPluginToMenu("&ServiceConf", self.action)
            self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&ServiceConf", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None  

    def run(self):
        from .plugin_dialog import PluginDialog
        if self.dialog is None:
            self.dialog = PluginDialog()
        self.dialog.show()
        self.dialog.exec_()

def classFactory(iface):
    plugin = QgsServiceConfPlugin(iface)
    plugin.initGui()
    return plugin
