from __future__ import annotations
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class _ImageView(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 150)
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


class PreviewWidget(QWidget):
    image_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Side-by-side image views
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._orig_view  = _ImageView("원본 없음")
        self._result_view = _ImageView("미리보기 없음")

        for view, title in ((self._orig_view, "원본"), (self._result_view, "결과")):
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(2, 2, 2, 2)
            wl.setSpacing(2)
            hdr = QLabel(title)
            hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr.setStyleSheet("font-weight: bold;")
            wl.addWidget(hdr)
            wl.addWidget(view)
            splitter.addWidget(wrap)

        splitter.setSizes([500, 500])
        root.addWidget(splitter, stretch=1)

        # Image file list
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

    def set_result(self, image_bgr: np.ndarray) -> None:
        self._result_view.set_image(image_bgr)

    def clear_result(self) -> None:
        self._result_view.clear_image("미리보기 없음")

    def _on_select(self, filename: str) -> None:
        if filename:
            self.image_selected.emit(filename)
