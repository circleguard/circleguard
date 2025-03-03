from utils import resource_path
from PyQt6.QtWidgets import QWizard, QWizardPage
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize


class WizardPage(QWizardPage):
    def __init__(self):
        super().__init__()
        # "In ClassicStyle and ModernStyle, using subtitles is necessary to make the header appear"
        # https://doc.qt.io/qt-5/qwizardpage.html#subTitle-prop
        self.setSubTitle(" ")
        banner = QPixmap(resource_path("wizard/banner.png"))
        self.setPixmap(QWizard.WizardPixmap.BannerPixmap, banner)
        height = int(banner.height() * 0.85)
        width = int(banner.height() * 0.85)
        image = QPixmap(resource_path("logo/logo.png")).scaled(
            QSize(height, width),
            transformMode=Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(QWizard.WizardPixmap.LogoPixmap, image)
