"""
Live time-domain and frequency-domain plot with level triggers.

Adapted from file generated by GnuRadio Companion. Requires GnuRadio >= 3.7.7.
"""
#pylint: skip-file

import argparse

from PyQt4 import Qt
from gnuradio import blocks
from gnuradio import gr
from gnuradio import qtgui
from gnuradio.filter import firdes
from gnuradio.qtgui import Range, RangeWidget
import osmosdr
import sip

from thrifty import settings


class scope(gr.top_block, Qt.QWidget):

    def __init__(self, samp_rate, gain, freq, block_size):
        gr.top_block.__init__(self, "Scope")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Scope")

        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        ##################################################
        # Variables
        ##################################################
        trigger_level_time = 0.4
        trigger_level_freq = -40
        self.samp_rate = samp_rate
        self.gain = gain
        self.freq = freq
        self.block_size = block_size

        ##################################################
        # Blocks
        ##################################################
        # Time level trigger slider
        trigger_level_time_range = Range(0, 1.5, 0.02, 0.4, 200)
        trigger_level_time_win = RangeWidget(trigger_level_time_range,
                                             self.set_trigger_level_time,
                                             "Trigger level (time)",
                                             "counter_slider",
                                             float)
        self.top_grid_layout.addWidget(trigger_level_time_win, 1, 0, 1, 2)

        # Freq level trigger slider
        trigger_level_freq_range = Range(-50, 0, 1, -40, 200)
        trigger_level_freq_win = RangeWidget(trigger_level_freq_range,
                                             self.set_trigger_level_freq,
                                             "Trigger level (freq)",
                                             "counter_slider",
                                             float)
        self.top_grid_layout.addWidget(trigger_level_freq_win, 1, 2, 1, 2)

        # Gain slider
        gain_range = Range(0, 55, 1, gain, 200)
        gain_win = RangeWidget(gain_range,
                               self.set_gain,
                               "Gain",
                               "counter_slider",
                               float)
        self.top_grid_layout.addWidget(gain_win, 0, 0, 1, 2)

        freq_range = Range(430e6, 435e6, 0.1e6, freq, 200)
        freq_win = RangeWidget(freq_range,
                               self.set_freq,
                               "Center Frequency",
                               "counter_slider",
                               float)
        self.top_grid_layout.addWidget(freq_win, 0, 2, 1, 2)

        # RTL-SDR
        self.rtlsdr_source = osmosdr.source()
        self.rtlsdr_source.set_sample_rate(samp_rate)
        self.rtlsdr_source.set_center_freq(freq, 0)
        self.rtlsdr_source.set_gain_mode(False, 0)
        self.rtlsdr_source.set_gain(gain, 0)

        # Time plot
        self.time_sink = qtgui.time_sink_f(size=block_size/2,
                                           samp_rate=samp_rate,
                                           name="")
        self.time_sink.set_update_time(0.10)
        self.time_sink.set_y_axis(-0.2, 1.5)
        self.time_sink.set_y_label("Amplitude", "")
        self.set_trigger_level_time(trigger_level_time)
        self.time_sink.enable_autoscale(False)
        self.time_sink.enable_grid(False)
        self.time_sink.enable_axis_labels(True)
        self.time_sink.enable_control_panel(False)
        self.time_sink.disable_legend()

        self._time_sink_win = sip.wrapinstance(self.time_sink.pyqwidget(),
                                               Qt.QWidget)
        self.top_grid_layout.addWidget(self._time_sink_win, 2, 0, 1, 4)

        # Freq plot
        self.freq_sink = qtgui.freq_sink_c(
            fftsize=block_size/2,
            wintype=firdes.WIN_BLACKMAN_hARRIS,
            fc=freq,
            bw=samp_rate,
            name="")
        self.freq_sink.set_update_time(0.10)
        self.freq_sink.set_y_axis(-140, 10)
        self.freq_sink.set_y_label("Relative Gain", "dB")
        self.set_trigger_level_freq(trigger_level_freq)
        self.freq_sink.enable_autoscale(False)
        self.freq_sink.enable_grid(False)
        self.freq_sink.set_fft_average(1.0)
        self.freq_sink.enable_axis_labels(True)
        self.freq_sink.enable_control_panel(False)
        self.freq_sink.disable_legend()

        self._freq_sink_win = sip.wrapinstance(self.freq_sink.pyqwidget(),
                                               Qt.QWidget)
        self.top_grid_layout.addWidget(self._freq_sink_win, 3, 0, 1, 4)

        # Histogram plot
        self.histogram_sink = qtgui.histogram_sink_f(
            size=block_size*2,
            bins=256,
            xmin=-1,
            xmax=1,
            name="")

        self.histogram_sink.set_update_time(0.10)
        self.histogram_sink.enable_autoscale(True)
        self.histogram_sink.enable_accumulate(False)
        self.histogram_sink.enable_grid(False)
        self.histogram_sink.enable_axis_labels(True)
        self.histogram_sink.disable_legend()

        self._histogram_sink_win = sip.wrapinstance(
            self.histogram_sink.pyqwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._histogram_sink_win, 4, 0, 1, 4)

        self.interleave = blocks.interleave(gr.sizeof_float*1, 1)
        self.complex_to_mag = blocks.complex_to_mag(1)
        self.complex_to_float = blocks.complex_to_float(1)

        ##################################################
        # Connections
        ##################################################
        self.connect(self.rtlsdr_source, self.complex_to_mag, self.time_sink)
        self.connect((self.rtlsdr_source, 0), (self.freq_sink, 0))

        self.connect(self.rtlsdr_source, self.complex_to_float)
        self.connect((self.complex_to_float, 0), (self.interleave, 0))
        self.connect((self.complex_to_float, 1), (self.interleave, 1))
        self.connect(self.interleave, self.histogram_sink)

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "scope")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def get_trigger_level_time(self):
        return self.trigger_level_time

    def set_trigger_level_time(self, trigger_level_time):
        self.trigger_level_time = trigger_level_time
        self.time_sink.set_trigger_mode(mode=qtgui.TRIG_MODE_NORM,
                                        slope=qtgui.TRIG_SLOPE_POS,
                                        level=self.trigger_level_time,
                                        delay=200e-6,
                                        channel=0)

    def get_trigger_level_freq(self):
        return self.trigger_level_freq

    def set_trigger_level_freq(self, trigger_level_freq):
        self.trigger_level_freq = trigger_level_freq
        self.freq_sink.set_trigger_mode(mode=qtgui.TRIG_MODE_NORM,
                                        level=self.trigger_level_freq,
                                        channel=0)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rtlsdr_source.set_sample_rate(self.samp_rate)
        self.time_sink.set_samp_rate(self.samp_rate)
        self.freq_sink.set_frequency_range(self.freq, self.samp_rate)

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.rtlsdr_source.set_gain(self.gain, 0)

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.rtlsdr_source.set_center_freq(self.freq, 0)
        self.freq_sink.set_frequency_range(self.freq, self.samp_rate)

    def get_block_size(self):
        return self.block_size

    def set_block_size(self, block_size):
        self.block_size = block_size


def gnuradio_main(samp_rate, gain, freq, block_size):
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"

    from distutils.version import StrictVersion
    if StrictVersion(Qt.qVersion()) >= StrictVersion("4.5.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)

    qapp = Qt.QApplication([])

    tb = scope(samp_rate, gain, freq, block_size)
    tb.start()
    tb.show()

    def quitting():
        tb.stop()
        tb.wait()
    qapp.connect(qapp, Qt.SIGNAL("aboutToQuit()"), quitting)
    qapp.exec_()


def _main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    setting_keys = ['tuner_freq', 'tuner_gain', 'sample_rate', 'block_size']
    config, _ = settings.load_args(parser, setting_keys)

    gnuradio_main(samp_rate=config.sample_rate,
                  gain=config.tuner_gain,
                  freq=config.tuner_freq,
                  block_size=config.block_size)


if __name__ == '__main__':
    _main()