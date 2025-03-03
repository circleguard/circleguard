from wizard.page import WizardPage
from wizard.label import WizardLabel

from widgets import LineEditSetting
from PyQt6.QtWidgets import QGridLayout


class ApiKeyPage(WizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("API Key")
        label = WizardLabel(
            "<p>Circleguard needs your api key to make requests and download replays. "
            "<p>If you've created an api key before, paste it into the box below. If you don't have one yet, go to "
            '<a href="https://osu.ppy.sh/home/account/edit#legacy-api">https://osu.ppy.sh/home/account/edit</a> '
            'and scroll to the "Legacy API" section. Click "New Legacy API Key". Enter <b>Circleguard</b> '
            'for the application name, and <a href="https://github.com/circleguard/circleguard">https://github.com/circleguard/circleguard</a> '
            'for the application url. Click "Show Key" and paste the api key into the box below.</p>'
            "<p>Your api key will be stored locally, and is never sent anywhere but osu! servers.</p>"
            "<p>If you skip this step, you will not be able to use Circleguard.</p>"
        )

        apikey_widget = LineEditSetting("Api Key", "", "normal", "api_key")

        layout = QGridLayout()
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(apikey_widget, 1, 0, 1, 1)
        self.setLayout(layout)
