from __future__ import annotations
import os
from typing import Optional

import cv2
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStatusBar, QMessageBox,
)
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from . import coco_io, augmentor
from .widgets.control_panel import ControlPanel
from .widgets.preview_widget import PreviewWidget

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HyAugmate")
        self.resize(1400, 850)

        self._settings = QSettings("HyAugmate", "HyAugmate")
        self._src_folder: str = self._settings.value("srcFolder", "")
        self._out_folder: str = self._settings.value("outFolder", "")
        self._image_files: list[str] = []
        self._current_image: Optional[str] = None

        central = QWidget()
        self.setCentralWidget(central)
        hl = QHBoxLayout(central)
        hl.setContentsMargins(4, 4, 4, 4)
        hl.setSpacing(4)

        self._control = ControlPanel()
        self._control.setFixedWidth(300)
        self._preview = PreviewWidget()

        hl.addWidget(self._control)
        hl.addWidget(self._preview, stretch=1)

        self._status = QStatusBar()
        self.setStatusBar(self._status)

        self._control.src_folder_changed.connect(self._on_src_folder)
        self._control.out_folder_changed.connect(self._on_out_folder)
        self._control.preview_requested.connect(self._on_preview)
        self._control.generate_requested.connect(self._on_generate)
        self._preview.image_selected.connect(self._on_image_selected)

        if self._src_folder:
            self._control.set_src_folder(self._src_folder)
            self._load_folder(self._src_folder)
        if self._out_folder:
            self._control.set_out_folder(self._out_folder)

    # ── Folder ─────────────────────────────────────────────────────────────────

    def _on_src_folder(self, folder: str) -> None:
        self._src_folder = folder
        self._settings.setValue("srcFolder", folder)
        self._load_folder(folder)

    def _on_out_folder(self, folder: str) -> None:
        self._out_folder = folder
        self._settings.setValue("outFolder", folder)

    def _load_folder(self, folder: str) -> None:
        if not os.path.isdir(folder):
            return
        all_images = sorted(
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in _IMAGE_EXTS
        )
        files = [
            f for f in all_images
            if os.path.isfile(os.path.join(folder, os.path.splitext(f)[0] + ".json"))
        ]
        self._image_files = files
        self._preview.set_image_list(files)
        self._status.showMessage(
            f"{len(files)}개 이미지 로드됨 (전체 {len(all_images)}개 중 JSON 있는 것) — {folder}"
        )
        if files:
            self._preview.select_image(files[0])

    # ── Image selection ────────────────────────────────────────────────────────

    def _on_image_selected(self, filename: str) -> None:
        self._current_image = filename
        self._show_original(filename)
        self._preview.clear_result()

    def _show_original(self, filename: str) -> None:
        image_path = os.path.join(self._src_folder, filename)
        image = cv2.imread(image_path)
        if image is None:
            return
        shapes = self._load_shapes(filename)
        overlay = coco_io.draw_overlay(image, shapes) if shapes else image
        self._preview.set_original(overlay)

    def _load_shapes(self, filename: str) -> list:
        stem = os.path.splitext(filename)[0]
        json_path = os.path.join(self._src_folder, stem + ".json")
        result = coco_io.load_shapes(json_path)
        return result[0] if result else []

    # ── Preview ────────────────────────────────────────────────────────────────

    def _on_preview(self) -> None:
        if not self._current_image:
            self._status.showMessage("이미지를 먼저 선택하세요.")
            return

        params = self._control.get_params()
        aug_keys = ["hflip", "vflip", "rotate", "color_jitter", "blur", "noise",
                    "hist_eq", "clahe", "gamma"]
        if not any(params.get(k) for k in aug_keys):
            self._status.showMessage("Augmentation을 하나 이상 선택하세요.")
            return

        image, shapes, h, w = self._load_image_and_shapes(self._current_image)
        if image is None:
            return

        n = self._control.get_count()
        label_map, ann_info = coco_io.shapes_to_label_map(shapes, h, w)
        results = []
        for _ in range(n):
            aug_image, aug_map = augmentor.augment_once(image, label_map, params)
            aug_shapes = coco_io.label_map_to_shapes(aug_map, ann_info)
            overlay = coco_io.draw_overlay(aug_image, aug_shapes) if aug_shapes else aug_image
            results.append(overlay)
            QApplication.processEvents()
        self._preview.set_results(results)
        self._status.showMessage(f"미리보기 완료 ({n}개)")

    # ── Generate ───────────────────────────────────────────────────────────────

    def _on_generate(self) -> None:
        if not self._src_folder:
            QMessageBox.warning(self, "경고", "소스 폴더를 선택하세요.")
            return
        if not self._out_folder:
            QMessageBox.warning(self, "경고", "출력 폴더를 선택하세요.")
            return
        if not self._image_files:
            QMessageBox.warning(self, "경고", "소스 폴더에 이미지가 없습니다.")
            return

        params = self._control.get_params()
        aug_keys = ["hflip", "vflip", "rotate", "color_jitter", "blur", "noise",
                    "hist_eq", "clahe", "gamma"]
        if not any(params.get(k) for k in aug_keys):
            QMessageBox.warning(self, "경고", "Augmentation을 하나 이상 선택하세요.")
            return

        n = self._control.get_count()
        os.makedirs(self._out_folder, exist_ok=True)

        total = len(self._image_files) * n
        done = 0

        for filename in self._image_files:
            image, shapes, h, w = self._load_image_and_shapes(filename)
            if image is None:
                continue

            stem, ext = os.path.splitext(filename)
            label_map, ann_info = coco_io.shapes_to_label_map(shapes, h, w)

            for i in range(n):
                aug_image, aug_map = augmentor.augment_once(image, label_map, params)
                aug_shapes = coco_io.label_map_to_shapes(aug_map, ann_info)

                out_stem = f"{stem}_aug{i + 1:03d}"
                coco_io.save_result(
                    os.path.join(self._out_folder, out_stem + ext),
                    os.path.join(self._out_folder, out_stem + ".json"),
                    aug_image, aug_shapes, h, w,
                )
                done += 1
                self._status.showMessage(f"생성 중... {done}/{total}")
                QApplication.processEvents()

        self._status.showMessage(f"완료! {done}개 파일 생성 → {self._out_folder}")
        QMessageBox.information(self, "완료", f"{done}개 파일이 생성되었습니다.\n\n{self._out_folder}")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _load_image_and_shapes(self, filename: str):
        image_path = os.path.join(self._src_folder, filename)
        image = cv2.imread(image_path)
        if image is None:
            self._status.showMessage(f"이미지 로드 실패: {filename}")
            return None, [], 0, 0
        h, w = image.shape[:2]
        shapes = self._load_shapes(filename)
        return image, shapes, h, w
