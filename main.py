from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsView,
    QGraphicsScene,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QGraphicsTextItem,
    QTextEdit,
    QPushButton,
    QDialog,
    QStatusBar,
)
from PyQt5.QtGui import QPixmap, QBrush, QColor, QPen, QPainter
from PyQt5.QtCore import Qt, QPointF
import sys
import math
import pathlib
from fetch import do_fetch, junea_pic
import csv

"""
Several considerations:
    - Need to be able to navigate between sets of points
    - Within set of points
    - search for which set of points we're on
    - Highlight most recent point, current points on line, and all points that've been placed
    - Potentially display the point index, for easy correction
    - Save load sets of points
    - adjust the sizse of the visual marker
    - little shortcut display in corner
    - small terminal that tells you what you did
    - small display telling you what the index of your line is, and what number point you're on 

"""


class CustomView(QGraphicsView):
    def __init__(self, scene, pixmap, canvas):
        super().__init__(scene)
        self.all_sets_of_points = [[]]
        self.current_set_index = 0
        self.pixmap = pixmap
        self.removed_points = []
        self.panning_mode = False
        self.canvas = canvas

    def switch_set(self, index):
        if index == len(self.all_sets_of_points):
            self.add_set()
        if 0 <= index:
            print(
                "set index changed from ",
                self.current_set_index,
                " to ",
                self.current_set_index + 1,
            )
            self.current_set_index = index
            self.redraw_scene()

    def add_set(self):
        self.all_sets_of_points.append([])
        self.current_set_index = len(self.all_sets_of_points) - 1
        self.redraw_scene()

    def initUI(self):
        self.scene = QGraphicsScene()

        pixmap = QPixmap(junea_pic)

        self.view = CustomView(self.scene, pixmap)

        self.scene.addPixmap(pixmap)

    def draw_cross(self, x, y, size, angle, color):
        angle_rad = math.radians(angle)
        for dx, dy in [(size, 0), (0, size), (-size, 0), (0, -size)]:
            x1 = x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            y1 = y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
            self.scene().addLine(x, y, x1, y1, QPen(color))

    def redraw_scene(self):
        self.scene().clear()
        self.scene().addPixmap(self.pixmap)
        # self.display_hotkeys()

        for i, points in enumerate(self.all_sets_of_points):
            if i == self.current_set_index:
                color = Qt.red
            else:
                color = Qt.blue
            for j, (x, y) in enumerate(points):
                if j == len(self.all_sets_of_points[self.current_set_index]) - 1:
                    self.draw_cross(x, y, 10, 45, color)
                else:
                    cross_size = 10
                    self.scene().addLine(
                        x - cross_size, y, x + cross_size, y, QPen(color)
                    )
                    self.scene().addLine(
                        x, y - cross_size, x, y + cross_size, QPen(color)
                    )
        self.update()

    def mousePressEvent(self, event):
        # Get the position of the mouse click
        point = event.pos()
        scene_point = self.mapToScene(point)
        x, y = scene_point.x(), scene_point.y()

        if event.button() == Qt.LeftButton and not self.panning_mode:
            self.all_sets_of_points[self.current_set_index].append((x, y))
            self.removed_points.clear()
            self.redraw_scene()
            self.canvas.log_message("Dropped point")

        super().mousePressEvent(event)

    def undo(self):
        current_points = self.all_sets_of_points[self.current_set_index]
        if current_points:
            removed_point = current_points.pop()
            self.removed_points.append(removed_point)
            self.redraw_scene()
            self.canvas.log_message("Undo")

    def redo(self):
        if self.removed_points:
            restored_point = self.removed_points.pop()
            self.all_sets_of_points[self.current_set_index].append(restored_point)
            self.redraw_scene()
            self.canvas.log_message("Redo")

    def save_points(self, filename):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            for set_index, point_set in enumerate(self.all_sets_of_points):
                for x, y in point_set:
                    writer.writerow([set_index, x, y])
        self.canvas.log_message("Points saved to Juneau.csv")

    def load_points(self, filename):
        with open(filename, "r") as f:
            reader = csv.reader(f)
            self.all_sets_of_points = []
            for row in reader:
                set_index = int(row[0])
                x, y = map(float, row[1:3])  # Convert to float instead of int
                while set_index >= len(self.all_sets_of_points):
                    self.all_sets_of_points.append([])
                self.all_sets_of_points[set_index].append((x, y))
        self.redraw_scene()
        self.canvas.log_message("Points loaded from Juneau.csv")

    def wheelEvent(self, event):
        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.scale(zoom_factor, zoom_factor)

        elif event.angleDelta().y() < 0:
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            self.panning_mode = not self.panning_mode
            if self.panning_mode:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setDragMode(QGraphicsView.NoDrag)
                self.setCursor(Qt.ArrowCursor)
        if key == Qt.Key_U:
            self.undo()
        elif key == Qt.Key_R:
            self.redo()
        elif key == Qt.Key_S:
            self.switch_set(self.current_set_index - 1)
        elif key == Qt.Key_W:
            self.switch_set(self.current_set_index + 1)
        elif key == Qt.Key_L:
            self.load_points("juneau_points.csv")
        elif key == Qt.Key_O:
            self.save_points("juneau_points.csv")
        super().keyPressEvent(event)


class CanvasDemo(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Canvas Demo")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()
        self.initStatusBar()
        self.initTerminal()
        self.terminal_dialog = None

    def initUI(self):
        # Create QGraphicsScene
        self.scene = QGraphicsScene()

        # Load an image into QPixmap
        pixmap = QPixmap(junea_pic)

        # Add QPixmap to the scene
        self.scene.addPixmap(pixmap)

        # Create custom QGraphicsView widget
        self.view = CustomView(self.scene, pixmap, self)

        # Set the scene for the view
        self.view.setScene(self.scene)

        # Layout to hold the QGraphicsView
        layout = QVBoxLayout()
        layout.addWidget(self.view)

        # Create a central widget for QMainWindow and set layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    # Terminal methods
    def initStatusBar(self):
        self.statusBar = QStatusBar()
        self.terminal_button = QPushButton("show_terminal")
        self.terminal_button.clicked.connect(self.show_terminal)
        self.statusBar.addPermanentWidget(self.terminal_button)
        self.setStatusBar(self.statusBar)

    def initTerminal(self):
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.terminal)

    def show_terminal(self):
        if self.terminal_dialog is None:
            self.terminal_dialog = QDialog()
            self.terminal_dialog.setWindowTitle("Terminal")
            layout = QVBoxLayout()
            layout.addWidget(self.terminal)
            self.terminal_dialog.setLayout(layout)

        self.terminal_dialog.show()

    def log_message(self, message):
        self.terminal.append(message)


if __name__ == "__main__":
    if not pathlib.Path(junea_pic).exists():
        print("Doing fetch!")
        do_fetch()
    app = QApplication(sys.argv)
    demo = CanvasDemo()
    demo.show()
    sys.exit(app.exec_())
