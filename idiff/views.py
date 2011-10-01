# vi: encoding=utf-8
# -*- coding: utf-8 -*-

from PySide import QtCore as core, QtGui as gui
from collections import OrderedDict

from idiff.controls import MAX_ZOOM, MIN_ZOOM, message_box, CompositeImage, \
                           Viewport

import os
import sys

BACKGROUND_COLOR = gui.QColor(0x999999)
SLIDER_MULTIPLIER = 100.0


class View(gui.QWidget):
    BACKGROUND_BRUSH = gui.QBrush(BACKGROUND_COLOR)

    @classmethod
    def _init_viewport(cls, image):
        'creates a viewport which contains the specified image'

        viewport = Viewport()
        viewport.setBackgroundBrush(cls.BACKGROUND_BRUSH)

        pixmap = gui.QPixmap(image)
        scene = gui.QGraphicsScene(pixmap.rect(), viewport)
        scene.addPixmap(pixmap)
        viewport.setScene(scene)

        return viewport

    def _link_viewport(self):
        'links the viewport to the slider'

        slider = self.zoom_slider
        viewport = self.viewport

        def slide():
            viewport.zoom = slider.value() / SLIDER_MULTIPLIER

        def viewport_changed():
            # don't create an update loop
            slider.blockSignals(True)
            slider.setValue(viewport.zoom * 100)
            slider.blockSignals(False)

        slider.valueChanged.connect(slide)
        viewport.viewport_change.connect(viewport_changed)

    def __init__(self, zoom_slider, parent=None):
        super(View, self).__init__(parent)
        self.zoom_slider = zoom_slider

    def showEvent(self, event):
        self.viewport.zoom = self.zoom_slider.value() / SLIDER_MULTIPLIER
        super(View, self).showEvent(event)


class SideBySideView(View):
    'show images side by side with linked zoom and panning'

    def _link_viewports(self):
        'links the viewport controls to their viewport actions'

        slider = self.zoom_slider
        def slide():
            source = self.viewports[0]
            source.zoom = slider.value() / SLIDER_MULTIPLIER
            self._update_zoom(source)
            self._update_offset(source)

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

    def __init__(self, images, zoom_slider, parent=None):
        super(SideBySideView, self).__init__(zoom_slider, parent)
        layout = gui.QHBoxLayout()
        self.setLayout(layout)

        self.viewports = [self._init_viewport(image) for image in images]
        for viewport in self.viewports: layout.addWidget(viewport)
        self._link_viewports()

    def showEvent(self, event):
        source = self.viewports[0]
        source.zoom = self.zoom_slider.value() / SLIDER_MULTIPLIER
        self._update_zoom(source)
        self._update_offset(source)
        super(View, self).showEvent(event)


class SliceView(View):
    def __init__(self, images, zoom_slider, parent=None):
        super(SliceView, self).__init__(zoom_slider, parent)
        layout = gui.QHBoxLayout()
        self.setLayout(layout)

        painter = gui.QPainter
        composite = CompositeImage(painter.CompositionMode_Multiply, *images)
        self.viewport = self._init_viewport(composite)
        layout.addWidget(self.viewport)
        self._link_viewport()


class MergedView(View):
    def __init__(self, images, zoom_slider, parent=None):
        super(MergedView, self).__init__(zoom_slider, parent)
        layout = gui.QHBoxLayout()
        self.setLayout(layout)

        painter = gui.QPainter
        composite = CompositeImage(painter.CompositionMode_Difference, *images)
        self.viewport = self._init_viewport(composite)
        layout.addWidget(self.viewport)
        self._link_viewport()


class Window(gui.QMainWindow):
    DEFAULT_FLICKER = '1s'
    VIEWS = OrderedDict((
        ('2up', SideBySideView),
        ('slice', SliceView),
        ('merged', MergedView)
    ))

    DEFAULT_VIEW = VIEWS.keys()[0]


    def _bind_controls(self):
        'binds the controls to the show view method'

        # returns a bound view selector
        def select_view(name): return lambda: self.select_view(name)

        for name in self.VIEWS.keys():
            self.controls[name].clicked.connect(select_view(name))

        # TODO: we need to pick which image is considered the "main" image
        max_width = max(self.images, key=lambda x: x.width())
        max_height = max(self.images, key=lambda x: x.height())
        self.slider.setRange(MIN_ZOOM * SLIDER_MULTIPLIER,
                             MAX_ZOOM * SLIDER_MULTIPLIER)
        self.slider.setValue(1)

    def _init_controls(self):
        'builds the controls'

        controls = gui.QWidget()
        controls_layout = gui.QHBoxLayout()
        controls.setLayout(controls_layout)

        self.controls = {}
        for name in self.VIEWS.keys():
            # TODO: change these to custom buttons
            self.controls[name] = button = gui.QPushButton(name)
            controls_layout.addWidget(button)

        self.slider = slider = gui.QSlider(core.Qt.Orientation.Horizontal)
        controls_layout.addWidget(slider)

        return controls

    def _init_views(self, filenames):
        'builds the views'

        self.view_layout = view_layout = gui.QStackedLayout()
        view_container = gui.QWidget()
        view_container.setLayout(view_layout)

        # add the different views
        self.images = images = list(self._load_images(filenames))
        self.views = {}
        for name, view in self.VIEWS.items():
            self.views[name] = widget = view(images, self.slider, self)
            view_layout.addWidget(widget)

        return view_container

    def _load_image_fallback(self, filename):
        from StringIO import StringIO

        def error(info):
            _ = self.tr
            message_box(parent=self, title=_('Image not recognized'),
                        text=_('Image "%s" not recognized.')
                            % os.path.basename(filename),
                        info=_(info),
                        icon=gui.QMessageBox.Critical).exec_()

            # this doesn't work because we haven't called exec_ on the
            # application yet
            # core.QCoreApplication.exit(1)
            sys.exit(1)

        try: import Image
        except ImportError:
            error('PIL was also not found when trying to convert it')
            return

        try:
            buffer = StringIO()
            Image.open(filename).save(buffer, 'png')
            buffer.seek(0)

            array = core.QByteArray.fromRawData(buffer.read())
            return gui.QImage.fromData(array)
        except IOError:
            error('PIL could not convert the image to a suitable format')

    def _load_images(self, filenames):
        for filename in filenames:
            image = gui.QImage(filename)
            if image.isNull():
                image = self._load_image_fallback(filename)

            yield image

    def __init__(self, filenames, options, parent=None):
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
        widget_layout.addWidget(self._init_views(filenames))
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
