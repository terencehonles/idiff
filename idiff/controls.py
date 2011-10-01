# vi: encoding=utf-8
# -*- coding: utf-8 -*-

from PySide import QtCore as core, QtGui as gui

MAX_ZOOM = 32
MIN_ZOOM = 0.5

def message_box(parent, title, text, info=None, icon=gui.QMessageBox.NoIcon,
        buttons=gui.QMessageBox.Ok, default=gui.QMessageBox.NoButton):

    '''
    emulates ``gui.QMessageBox.question`` and other message box static
    methods, but allows for setting the informative text via ``info``
    '''

    message = gui.QMessageBox()
    message.setIcon(icon)
    message.setText(text)
    message.setInformativeText(info)
    message.setWindowTitle(title)
    message.setStandardButtons(buttons)
    message.setDefaultButton(default)
    return message


class CompositeImage(gui.QImage):
    IMAGE_FORMAT = gui.QImage.Format_ARGB32_Premultiplied

    def __init__(self, mode, background, *additional, **kargs):
        bounds = kargs.get('bounds', background.rect())
        self.images = (background,) + additional
        self.composition_mode = mode
        self.opacity = kargs.get('opacity', 1)

        super(CompositeImage, self).__init__(bounds.size(), self.IMAGE_FORMAT)

        # paint the composite image now
        self.fill(0)
        self.paint(mode)

    def paint(self, mode=None):
        bounds = self.rect()

        painter = gui.QPainter(self)
        painter.setCompositionMode(mode or self.composition_mode)

        for image, opacity in zip(self.images, self.opacity):
            if opacity is not None: painter.setOpacity(opacity)
            painter.drawImage(bounds, image)

    @property
    def opacity(self): return self.__opacity

    @opacity.setter
    def opacity(self, opacity):
        try:
            opacity = tuple(opacity)
            difference = len(self.images) - len(opacity)

            # we have been given an iterable item, but it is too short
            if difference > 0:
                self.__opacity = opacity + opacity[-1:] * difference
            else:
                self.__opacity = opacity
        except TypeError:
            # we have not been given an iterable item
            self.__opacity = (opacity,) * len(self.images)


class Viewport(gui.QGraphicsView):
    '''
    QGraphicsView which is frameless and uses scroll dragging
    '''

    viewport_change = core.Signal()

    def __init__(self, parent=None):
        super(Viewport, self).__init__(parent)
        self.setRenderHints(gui.QPainter.SmoothPixmapTransform)
        self.setFrameStyle(gui.QFrame.NoFrame)

        self.__mouse_pressed = False
        self.__zoom = 1

        self.zoom_offset = 0
        self.wheel_zoom = core.QSettings().value('interface/wheel_zoom', True)

        # use dragging rather than scroll bars
        self.setDragMode(gui.QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(core.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(core.Qt.ScrollBarAlwaysOff)

        # resizing defaults (zoom with scroll wheel)
        self.setResizeAnchor(gui.QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(gui.QGraphicsView.AnchorUnderMouse)

    def mousePressEvent(self, event):
        super(Viewport, self).mousePressEvent(event)
        self.__mouse_pressed = True

    def mouseMoveEvent(self, event):
        super(Viewport, self).mouseMoveEvent(event)
        if self.__mouse_pressed:
            self.viewport_change.emit()

        return True

    def mouseReleaseEvent(self, event):
        super(Viewport, self).mouseReleaseEvent(event)
        self.__mouse_pressed = False

    def wheelEvent(self, event):
        'mouse wheel acts as zoom if ``self.wheel_zoom`` is ``True``'

        if self.wheel_zoom:
            self.zoom *= 2 ** (event.delta() / 240.0)
        else:
            super(Viewport, self).wheelEvent(event)

        self.viewport_change.emit()


    @property
    def zoom(self):
        return self.__zoom

    @zoom.setter
    def zoom(self, zoom):
        zoom = min(MAX_ZOOM, max(MIN_ZOOM, zoom))

        if zoom != self.__zoom:
            self.__zoom = zoom
            offset = self.zoom_offset

            # zoom only matrix (translation is done via scroll bars)
            matrix = gui.QMatrix(zoom + offset, 0, 0, zoom + offset, 0, 0)
            self.setMatrix(matrix)
