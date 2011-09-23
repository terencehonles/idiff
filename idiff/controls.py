# vi: encoding=utf-8
# -*- coding: utf-8 -*-

from PySide import QtCore as core, QtGui as gui


class Viewport(gui.QGraphicsView):
    viewport_change = core.Signal()

    def __init__(self, parent=None):
        super(Viewport, self).__init__(parent)
        self.setRenderHints(gui.QPainter.SmoothPixmapTransform)
        self.setFrameStyle(gui.QFrame.NoFrame)

        self.__mouse_pressed = False
        self.__zoom = 1

        self.zoom_offset = 0
        self.max_zoom = 32
        self.min_zoom = 0.5

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
        'mouse wheel acts as zoom'

        self.zoom *= 2 ** (event.delta() / 240.0)
        self.viewport_change.emit()


    @property
    def zoom(self):
        return self.__zoom

    @zoom.setter
    def zoom(self, zoom):
        zoom = min(self.max_zoom, max(self.min_zoom, zoom))

        if zoom != self.__zoom:
            self.__zoom = zoom
            offset = self.zoom_offset

            # zoom only matrix (translation is done via scroll bars)
            matrix = gui.QMatrix(zoom + offset, 0, 0, zoom + offset, 0, 0)
            self.setMatrix(matrix)
