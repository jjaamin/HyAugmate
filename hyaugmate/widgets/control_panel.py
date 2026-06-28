from __future__ import annotations

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QCheckBox, QSlider, QLabel, QSpinBox, QPushButton, QLineEdit,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal


class ControlPanel(QScrollArea):
    src_folder_changed = pyqtSignal(str)
    out_folder_changed = pyqtSignal(str)
    preview_requested  = pyqtSignal()
    generate_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.setWidget(container)
        vl = QVBoxLayout(container)
        vl.setSpacing(8)
        vl.setContentsMargins(6, 6, 6, 6)

        vl.addWidget(self._build_folder_group())
        vl.addWidget(self._build_aug_group())
        vl.addWidget(self._build_generate_group())
        vl.addStretch()

    # ── Folder group ───────────────────────────────────────────────────────────

    def _build_folder_group(self) -> QGroupBox:
        grp = QGroupBox("폴더 설정")
        vl = QVBoxLayout(grp)
        vl.setSpacing(4)

        vl.addWidget(QLabel("소스 폴더 (이미지 + JSON)"))
        self._src_edit = QLineEdit()
        self._src_edit.setReadOnly(True)
        self._src_edit.setPlaceholderText("폴더 선택...")
        btn = QPushButton("...")
        btn.setFixedWidth(30)
        btn.clicked.connect(self._browse_src)
        row = QHBoxLayout()
        row.addWidget(self._src_edit)
        row.addWidget(btn)
        vl.addLayout(row)

        vl.addWidget(QLabel("출력 폴더"))
        self._out_edit = QLineEdit()
        self._out_edit.setReadOnly(True)
        self._out_edit.setPlaceholderText("폴더 선택...")
        btn2 = QPushButton("...")
        btn2.setFixedWidth(30)
        btn2.clicked.connect(self._browse_out)
        row2 = QHBoxLayout()
        row2.addWidget(self._out_edit)
        row2.addWidget(btn2)
        vl.addLayout(row2)

        return grp

    def _browse_src(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "소스 폴더 선택")
        if d:
            self._src_edit.setText(d)
            self.src_folder_changed.emit(d)

    def _browse_out(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if d:
            self._out_edit.setText(d)
            self.out_folder_changed.emit(d)

    def set_src_folder(self, path: str) -> None:
        self._src_edit.setText(path)

    def set_out_folder(self, path: str) -> None:
        self._out_edit.setText(path)

    # ── Augmentation group ─────────────────────────────────────────────────────

    def _build_aug_group(self) -> QGroupBox:
        grp = QGroupBox("Augmentation")
        vl = QVBoxLayout(grp)
        vl.setSpacing(4)

        self._aug = {}  # key → (QCheckBox, {param_key: QSlider})

        self._add_check(vl, "hflip", "Horizontal Flip")
        self._add_check(vl, "vflip", "Vertical Flip")
        self._add_check_sliders(vl, "rotate", "Rotation", [
            ("rotate_limit", "각도 범위 ±°", 1, 90, 45, 1),
        ])
        self._add_check_sliders(vl, "color_jitter", "Color Jitter", [
            ("cj_brightness", "밝기 변화 %", 0, 80, 20, 1),
            ("cj_contrast",   "대비 변화 %", 0, 80, 20, 1),
            ("cj_saturation", "채도 변화 %", 0, 80, 20, 1),
            ("cj_hue",        "색조 변화 %", 0, 30, 5,  1),
        ])
        self._add_check_sliders(vl, "blur", "Gaussian Blur", [
            ("blur_ksize", "커널 크기 px", 1, 21, 5, 1),
        ])
        self._add_check_sliders(vl, "noise", "Gaussian Noise", [
            ("noise_var", "강도 (std px)", 1, 30, 8, 1),
        ])
        self._add_check_sliders(vl, "elastic", "Elastic Transform", [
            ("elastic_alpha", "변형 강도", 10, 200, 80, 1),
            ("elastic_sigma", "변형 부드러움", 10, 100, 50, 1),
        ])
        self._add_check(vl, "hist_eq", "Histogram Equalization")
        self._add_check_sliders(vl, "clahe", "CLAHE", [
            ("clahe_clip", "Clip Limit ×0.1", 5, 80, 20, 1),
        ])
        self._add_check_sliders(vl, "gamma", "Gamma Correction", [
            ("gamma_min", "Min gamma", 10, 100, 80, 1),
            ("gamma_max", "Max gamma", 100, 200, 120, 1),
        ])

        return grp

    def _add_check(self, parent_layout, key: str, label: str) -> None:
        cb = QCheckBox(label)
        parent_layout.addWidget(cb)
        self._aug[key] = (cb, {})

    def _add_check_sliders(
        self, parent_layout, key: str, label: str, sliders: list
    ) -> None:
        cb = QCheckBox(label)
        parent_layout.addWidget(cb)

        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setContentsMargins(18, 0, 0, 2)
        cl.setSpacing(2)

        slider_map: dict = {}
        for s_key, s_label, s_min, s_max, s_default, _step in sliders:
            row = QHBoxLayout()
            lbl = QLabel(f"{s_label}: {s_default}")
            lbl.setMinimumWidth(150)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setMinimum(s_min)
            sl.setMaximum(s_max)
            sl.setValue(s_default)

            def _make_updater(l: QLabel, text: str):
                def _update(v: int) -> None:
                    l.setText(f"{text}: {v}")
                return _update

            sl.valueChanged.connect(_make_updater(lbl, s_label))
            row.addWidget(lbl)
            row.addWidget(sl)
            cl.addLayout(row)
            slider_map[s_key] = sl

        container.setVisible(False)
        cb.toggled.connect(container.setVisible)
        parent_layout.addWidget(container)

        self._aug[key] = (cb, slider_map)

    # ── Generate group ─────────────────────────────────────────────────────────

    def _build_generate_group(self) -> QGroupBox:
        grp = QGroupBox("생성")
        vl = QVBoxLayout(grp)
        vl.setSpacing(6)

        row = QHBoxLayout()
        row.addWidget(QLabel("이미지당 생성 수:"))
        self._count = QSpinBox()
        self._count.setRange(1, 200)
        self._count.setValue(5)
        row.addWidget(self._count)
        row.addStretch()
        vl.addLayout(row)

        btn_prev = QPushButton("미리보기")
        btn_prev.clicked.connect(self.preview_requested)
        vl.addWidget(btn_prev)

        btn_gen = QPushButton("생성 시작")
        btn_gen.setStyleSheet(
            "QPushButton { background-color: #3a6ea5; color: white; font-weight: bold; padding: 4px; }"
        )
        btn_gen.clicked.connect(self.generate_requested)
        vl.addWidget(btn_gen)

        return grp

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_params(self) -> dict:
        params: dict = {}
        for key, (cb, slider_map) in self._aug.items():
            params[key] = cb.isChecked()
            for s_key, sl in slider_map.items():
                v = sl.value()
                if s_key in ("cj_brightness", "cj_contrast", "cj_saturation", "cj_hue"):
                    params[s_key] = v / 100.0
                elif s_key == "clahe_clip":
                    params[s_key] = v / 10.0
                else:
                    params[s_key] = v
        return params

    def get_count(self) -> int:
        return self._count.value()
