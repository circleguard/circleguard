from widgets.slider_box_setting import SliderBoxSetting
from widgets.spin_box_max_inf import SpinBoxMaxInf


class SliderBoxMaxInfSetting(SliderBoxSetting):
    """
    a `SliderBoxSetting` which has special behavior when the slider or spinbox
    is at its max value - namely that it sets the associated setting to infinity
    (or an equivalently large value).
    """

    def spin_box(self):
        return SpinBoxMaxInf()
