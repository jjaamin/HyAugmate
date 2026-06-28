from __future__ import annotations
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QSplitter, QSizePolicy, QScrollArea, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class _ImageView(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(80, 60)
        self.setStyleSheet("background-color: #1e1e1e; color: #666;")
        self.setText(title)
        self._pixmap: Optional[QPixmap] = None

    def set_image(self, image_bgr: np.ndarray) -> None:
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg)
        self._refresh()
        self.setText("")

    def clear_image(self, text: str = "결과 없음") -> None:
        self._pixmap = None
        self.setText(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)


class _ResultGrid(QScrollArea):
    _COLS = 3

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet("background-color: #1e1e1e;")
        self._container = QWidget()
        self._container.setStyleSheet("background-color: #1e1e1e;")
        self.setWidget(self._container)
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(2)
        self._grid.setContentsMargins(2, 2, 2, 2)
        self._thumbs: list[_ImageView] = []
        self._show_placeholder()

    def set_images(self, images: list) -> None:
        self._clear()
        self._thumbs = []
        if images:
            h0, w0 = images[0].shape[:2]
            self._aspect = h0 / w0 if w0 > 0 else 0.75
        else:
            self._aspect = 0.75
        for idx, img in enumerate(images):
            row, col = divmod(idx, self._COLS)
            thumb = _ImageView(f"#{idx + 1}")
            thumb.set_image(img)
            self._thumbs.append(thumb)
            self._grid.addWidget(thumb, row, col)
        self._update_thumb_heights()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_thumb_heights()

    def _update_thumb_heights(self) -> None:
        if not self._thumbs:
            return
        margins = self._grid.contentsMargins()
        spacing = self._grid.spacing()
        avail_w = (self.viewport().width()
                   - margins.left() - margins.right()
                   - spacing * (self._COLS - 1))
        cell_w = max(60, avail_w // self._COLS)
        cell_h = max(60, int(cell_w * getattr(self, "_aspect", 0.75)))
        for thumb in self._thumbs:
            thumb.setFixedHeight(cell_h)

    def clear(self) -> None:
        self._clear()
        self._thumbs = []
        self._show_placeholder()

    def _clear(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_placeholder(self) -> None:
        lbl = QLabel("미리보기 없음")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #555;")
        self._grid.addWidget(lbl, 0, 0, 1, self._COLS)


class PreviewWidget(QWidget):
    image_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 원본 (작게)
        orig_wrap = QWidget()
        ol = QVBoxLayout(orig_wrap)
        ol.setContentsMargins(2, 2, 2, 2)
        ol.setSpacing(2)
        hdr_orig = QLabel("원본")
        hdr_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_orig.setStyleSheet("font-weight: bold;")
        self._orig_view = _ImageView("원본 없음")
        ol.addWidget(hdr_orig)
        ol.addWidget(self._orig_view)
        splitter.addWidget(orig_wrap)

        # 결과 그리드 (크게)
        result_wrap = QWidget()
        rl = QVBoxLayout(result_wrap)
        rl.setContentsMargins(2, 2, 2, 2)
        rl.setSpacing(2)
        hdr_result = QLabel("결과")
        hdr_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_result.setStyleSheet("font-weight: bold;")
        self._result_grid = _ResultGrid()
        rl.addWidget(hdr_result)
        rl.addWidget(self._result_grid)
        splitter.addWidget(result_wrap)

        splitter.setSizes([250, 750])
        root.addWidget(splitter, stretch=1)

        # 이미지 목록
        bottom = QWidget()
        bottom.setFixedHeight(130)
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("이미지 목록")
        lbl.setFixedWidth(75)
        lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list = QListWidget()
        self._list.currentTextChanged.connect(self._on_select)
        bl.addWidget(lbl)
        bl.addWidget(self._list)
        root.addWidget(bottom)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_image_list(self, files: list) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for f in files:
            self._list.addItem(f)
        self._list.blockSignals(False)

    def select_image(self, filename: str) -> None:
        items = self._list.findItems(filename, Qt.MatchFlag.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])

    def set_original(self, image_bgr: np.ndarray) -> None:
        self._orig_view.set_image(image_bgr)

    def set_results(self, images: list) -> None:
        self._result_grid.set_images(images)

    def clear_result(self) -> None:
        self._result_grid.clear()

    def _on_select(self, filename: str) -> None:
        if filename:
            self.image_selected.emit(filename)
