from __future__ import annotations
import contextlib
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
_AUG_KEYS   = ["hflip", "vflip", "rotate", "elastic", "color_jitter",
               "blur", "noise", "hist_eq", "clahe", "gamma"]


@contextlib.contextmanager
def _suppress_native_stderr():
    """libtiff 등이 fd 2에 직접 쓰는 'unknown field with tag' 경고 억제 (Python warnings로 안 잡힘)."""
    try:
        saved_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        yield
        return
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(saved_fd, 2)
        os.close(devnull_fd)
        os.close(saved_fd)


def _imread_quiet(path: str):
    with _suppress_native_stderr():
        return cv2.imread(path)


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

        # 미리보기 캐시
        self._cache_image:  Optional[str] = None   # 어떤 이미지를 미리봤는지
        self._cache_params: dict = {}              # 당시 파라미터
        self._cache_count:  int  = 0              # 당시 생성 수
        self._cache_data:   list = []             # [(aug_image, aug_shapes, h, w), ...]

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
        image = _imread_quiet(image_path)
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
        if not any(params.get(k) for k in _AUG_KEYS):
            self._status.showMessage("Augmentation을 하나 이상 선택하세요.")
            return

        image, shapes, h, w = self._load_image_and_shapes(self._current_image)
        if image is None:
            return

        n = self._control.get_count()
        label_map, ann_info = coco_io.shapes_to_label_map(shapes, h, w)

        cache_data = []
        overlays   = []
        for _ in range(n):
            aug_image, aug_map = augmentor.augment_once(image, label_map, params)
            aug_shapes = coco_io.label_map_to_shapes(aug_map, ann_info)
            overlay = coco_io.draw_overlay(aug_image, aug_shapes) if aug_shapes else aug_image
            cache_data.append((aug_image.copy(), aug_shapes, h, w))
            overlays.append(overlay)
            QApplication.processEvents()

        # 캐시 저장
        self._cache_image  = self._current_image
        self._cache_params = params
        self._cache_count  = n
        self._cache_data   = cache_data

        self._preview.set_results(overlays)
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
        if not any(params.get(k) for k in _AUG_KEYS):
            QMessageBox.warning(self, "경고", "Augmentation을 하나 이상 선택하세요.")
            return

        n = self._control.get_count()
        os.makedirs(self._out_folder, exist_ok=True)

        total = len(self._image_files) * n
        done  = 0

        for filename in self._image_files:
            stem = os.path.splitext(filename)[0]
            ext = ".png"

            # 미리보기 캐시 사용 여부 판단
            use_cache = (
                self._cache_data
                and filename == self._cache_image
                and self._cache_params == params
                and self._cache_count  == n
            )

            if use_cache:
                for i, (aug_image, aug_shapes, img_h, img_w) in enumerate(self._cache_data):
                    out_stem = f"{stem}_aug{i + 1:03d}"
                    coco_io.save_result(
                        os.path.join(self._out_folder, out_stem + ext),
                        os.path.join(self._out_folder, out_stem + ".json"),
                        aug_image, aug_shapes, img_h, img_w,
                    )
                    done += 1
                    self._status.showMessage(f"생성 중 (캐시 사용)... {done}/{total}")
                    QApplication.processEvents()
            else:
                image, shapes, h, w = self._load_image_and_shapes(filename)
                if image is None:
                    continue
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
        image = _imread_quiet(image_path)
        if image is None:
            self._status.showMessage(f"이미지 로드 실패: {filename}")
            return None, [], 0, 0
        h, w = image.shape[:2]
        shapes = self._load_shapes(filename)
        return image, shapes, h, w
