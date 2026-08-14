import sys

from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from mietmanager.data import get_session_factory, init_db, seed_if_empty
from mietmanager.ui.abrechnung_tab import AbrechnungTab
from mietmanager.ui.avatar_button import ProfilAvatarButton
from mietmanager.ui.dashboard_tab import DashboardTab
from mietmanager.ui.immobilien_tab import ImmobilienTab
from mietmanager.ui.kosten_tab import KostenTab
from mietmanager.ui.mieter_tab import MieterTab
from mietmanager.ui.theme import apply_theme
from mietmanager.ui.vertraege_tab import VertraegeTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MietManager")
        self.resize(1000, 650)

        engine = init_db()
        self.session = get_session_factory(engine)()
        seed_if_empty(self.session)

        titel = QLabel("MietManager")
        titel.setObjectName("appTitle")

        header = QHBoxLayout()
        header.addWidget(titel)
        header.addStretch()
        header.addWidget(ProfilAvatarButton(self.session))

        tabs = QTabWidget()
        tabs.addTab(DashboardTab(self.session), "Dashboard")
        tabs.addTab(ImmobilienTab(self.session), "Immobilien")
        tabs.addTab(MieterTab(self.session), "Mieter")
        tabs.addTab(VertraegeTab(self.session), "Mietverträge")
        tabs.addTab(KostenTab(self.session), "Kostenpositionen")
        tabs.addTab(AbrechnungTab(self.session), "Nebenkostenabrechnung")

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.addLayout(header)
        container_layout.addSpacing(12)
        container_layout.addWidget(tabs)
        container.setLayout(container_layout)
        self.setCentralWidget(container)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt-Methodenname)
        self.session.close()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
