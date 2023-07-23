from pathlib import Path

import imagesize
from PySide6.QtCore import (QAbstractListModel, QPersistentModelIndex,
                            QSettings, QSize, Qt)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QMessageBox

from image import Image
from settings import get_separator


class ImageListModel(QAbstractListModel):
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.images = []

    def rowCount(self, parent=None):
        return len(self.images)

    def data(self, index, role=None):
        image = self.images[index.row()]
        if role == Qt.UserRole:
            return image
        if role == Qt.DisplayRole:
            # The text shown next to the thumbnail in the image list.
            return image.path.name
        image_width = int(self.settings.value('image_list_image_width'))
        if role == Qt.DecorationRole:
            # The thumbnail.
            pixmap = QPixmap(str(image.path)).scaledToWidth(image_width)
            return QIcon(pixmap)
        if role == Qt.SizeHintRole:
            dimensions = image.dimensions
            if dimensions:
                width, height = dimensions
                # Scale the dimensions to the image width.
                return QSize(image_width, int(image_width * height / width))
            return QSize(image_width, image_width)

    def load_directory(self, path: Path):
        self.images.clear()
        file_paths = set(path.glob('*'))
        text_file_paths = set(path.glob('*.txt'))
        image_paths = file_paths - text_file_paths
        text_file_stems = {path.stem for path in text_file_paths}
        image_stems = {path.stem for path in image_paths}
        image_stems_with_captions = image_stems & text_file_stems
        for image_path in image_paths:
            try:
                dimensions = imagesize.get(image_path)
            except ValueError:
                dimensions = None
            if image_path.stem in image_stems_with_captions:
                text_file_path = path / f'{image_path.stem}.txt'
                caption = text_file_path.read_text()
                if caption:
                    tags = caption.split(get_separator(self.settings))
                else:
                    tags = []
                image = Image(image_path, dimensions, tags)
            else:
                image = Image(image_path, dimensions)
            self.images.append(image)
        self.images.sort(key=lambda image_: image_.path.name)
        self.dataChanged.emit(self.index(0), self.index(len(self.images) - 1))

    def update_tags(self, image_index: QPersistentModelIndex, tags: list[str]):
        image = self.data(image_index, Qt.UserRole)
        image.tags = tags
        self.dataChanged.emit(image_index, image_index)
        try:
            image.path.with_suffix('.txt').write_text(
                get_separator(self.settings).join(tags))
        except OSError:
            error_message_box = QMessageBox()
            error_message_box.setWindowTitle('Error')
            error_message_box.setIcon(QMessageBox.Icon.Critical)
            error_message_box.setText(f'An error occurred while saving the '
                                      f'tags for {image.path.name}.')
            error_message_box.exec()