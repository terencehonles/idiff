# vi: encoding=utf-8
# -*- coding: utf-8 -*-

from PySide import QtCore as core, QtGui as gui
from collections import OrderedDict

from idiff.controls import Viewport

BACKGROUND_COLOR = gui.QColor(0x99, 0x99, 0x99)


class SideBySideView(gui.QWidget):
    BACKGROUND_BRUSH = gui.QBrush(BACKGROUND_COLOR)

    @classmethod
    def _init_viewport(cls, filename):
        viewport = Viewport()
        viewport.setBackgroundBrush(cls.BACKGROUND_BRUSH)

        pixmap = gui.QPixmap(filename)
        scene = gui.QGraphicsScene(pixmap.rect(), viewport)
        scene.addPixmap(pixmap)
        viewport.setScene(scene)

        return viewport

    def __init__(self, filenames, parent=None):
        super(SideBySideView, self).__init__(parent)

        layout = gui.QHBoxLayout()
        self.setLayout(layout)

        self.viewports = viewports = []
        for filename in filenames:
            viewport = self._init_viewport(filename)
            layout.addWidget(viewport)
            viewports.append(viewport)

        self._link_viewports()

    def _link_viewports(self):
        'links the viewport controls to their viewport actions'

        slider = self.parentWidget().slider
        max_width = max(self.viewports, key=lambda x: x.sceneRect().width())
        max_height = max(self.viewports, key=lambda x: x.sceneRect().height())

        slider.setRange(max_width.min_zoom * 100, max_width.max_zoom * 100)

        def slide():
            max_width.zoom = slider.value() / 100.0
            self._update_zoom(max_width)
            self._update_offset(max_width)

        def viewport_changed(source):
            def update():
                self._update_zoom(source)
                self._update_offset(source)

                # don't create an update loop
                slider.blockSignals(True)
                slider.setValue(source.zoom * 100)
                slider.blockSignals(False)

            return update

        slider.valueChanged.connect(slide)
        for viewport in self.viewports:
            viewport.viewport_change.connect(viewport_changed(viewport))

    def _update_offset(self, source):
        'updates all the viewports to have the same offset (scroll position)'

        h = source.horizontalScrollBar()
        v = source.verticalScrollBar()
        h_range = h.maximum() - h.minimum()
        v_range = v.maximum() - v.minimum()
        h_percent = h.value() / float(h_range) if h_range != 0 else 0
        v_percent = v.value() / float(v_range) if v_range != 0 else 0

        for viewport in self.viewports:
            if viewport is not source:
                viewport.horizontalScrollBar().setValue(h_percent * h_range)
                viewport.verticalScrollBar().setValue(v_percent * v_range)

    def _update_zoom(self, source):
        'updates all the viewports to be at the same zoom level'

        zoom = source.zoom
        for viewport in self.viewports:
            if viewport is not source: viewport.zoom = zoom


class SliceView(gui.QWidget):
    def __init__(self, images, parent=None):
        super(SliceView, self).__init__(parent)

        layout = gui.QHBoxLayout()
        self.setLayout(layout)
        self.large_shadow = gui.QGraphicsDropShadowEffect(self)

        for image in images[:1]:
            pixmap = gui.QPixmap(image)
            image = gui.QLabel()
            image.setPixmap(pixmap)
            layout.addWidget(image)


class MergedView(gui.QWidget):
    def __init__(self, images, parent=None):
        from subprocess import check_output

        super(MergedView, self).__init__(parent)

        layout = gui.QHBoxLayout()
        self.setLayout(layout)
        self.large_shadow = gui.QGraphicsDropShadowEffect(self)

        output = check_output(['compare', '-highlight-color', 'blue',
                               '-fuzz', '2%'] + images[:2] + ['-'])
        data = core.QByteArray.fromRawData(output)
        pixmap = gui.QPixmap()
        pixmap.loadFromData(data)
        image = gui.QLabel()
        image.setPixmap(pixmap)
        layout.addWidget(image)


class Window(gui.QMainWindow):
    DEFAULT_FLICKER = '1s'
    VIEWS = OrderedDict((
        ('2up', SideBySideView),
        ('slice', SliceView),
        ('merged', MergedView)
    ))

    DEFAULT_VIEW = VIEWS.keys()[0]


    def _init_controls(self):
        'builds the controls'

        controls = gui.QWidget()
        controls_layout = gui.QHBoxLayout()
        controls.setLayout(controls_layout)

        self.controls = {}
        for name in self.VIEWS.keys():
            self.controls[name] = button = gui.QPushButton(name)
            controls_layout.addWidget(button)

        self.slider = slider = gui.QSlider(core.Qt.Orientation.Horizontal)
        controls_layout.addWidget(slider)

        return controls


    def _init_views(self, images):
        'builds the views'

        self.view_layout = view_layout = gui.QStackedLayout()
        view_container = gui.QWidget()
        view_container.setLayout(view_layout)

        # add the different views
        self.views = {}
        for name, view in self.VIEWS.items():
            self.views[name] = widget = view(images, self)
            view_layout.addWidget(widget)

        return view_container


    def _bind_controls(self):
        'binds the controls to the show view method'

        # returns a bound view selector
        def select_view(name): return lambda: self.select_view(name)

        for name in self.VIEWS.keys():
            self.controls[name].clicked.connect(select_view(name))


    def __init__(self, images, options, parent=None):
        'creates the different views and moves to the specified view'

        super(Window, self).__init__(parent)
        palette = self.palette()
        palette.setColor(gui.QPalette.Window, BACKGROUND_COLOR)
        self.setPalette(palette)

        # top level widget contains the controls and the view port
        widget = gui.QWidget()
        widget_layout = gui.QVBoxLayout()
        widget.setLayout(widget_layout)
        self.setCentralWidget(widget)

        widget_layout.addWidget(self._init_controls())
        widget_layout.addWidget(self._init_views(images))
        self._bind_controls()

        # make the selected view visible
        self.select_view(options.view) or self.select_view(self.DEFAULT_VIEW)


    def select_view(self, view):
        'changes the selected view by name'

        selected = self.views.get(view)
        if selected and selected is not self.view_layout.currentWidget():
            self.view_layout.setCurrentWidget(selected)

            return True

        return False
