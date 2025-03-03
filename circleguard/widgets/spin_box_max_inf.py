from PyQt6.QtWidgets import QSpinBox

class SpinBoxMaxInf(QSpinBox):

    def textFromValue(self, value):
        if value == self.maximum():
            return "inf"
        return super().textFromValue(value)

    def valueFromText(self, text):
        if text == "inf":
            # can't use `sys.maxsize` because it overflows qt / c's 32bit int
            return 2147483647
        return super().valueFromText(text)
