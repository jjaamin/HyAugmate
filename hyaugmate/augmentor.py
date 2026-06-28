from __future__ import annotations
from typing import Tuple

import cv2
import numpy as np
import albumentations as A


def _build_transform(params: dict) -> A.Compose:
    ops: list = []

    if params.get("hflip"):
        ops.append(A.HorizontalFlip(p=1.0))
    if params.get("vflip"):
        ops.append(A.VerticalFlip(p=1.0))
    if params.get("rotate"):
        limit = int(params.get("rotate_limit", 45))
        ops.append(A.Rotate(limit=limit, p=1.0, border_mode=cv2.BORDER_CONSTANT, value=0, mask_value=0))
    if params.get("color_jitter"):
        ops.append(A.ColorJitter(
            brightness=float(params.get("cj_brightness", 0.2)),
            contrast=float(params.get("cj_contrast", 0.2)),
            saturation=float(params.get("cj_saturation", 0.2)),
            hue=float(params.get("cj_hue", 0.05)),
            p=1.0,
        ))
    if params.get("blur"):
        k = int(params.get("blur_ksize", 5))
        if k % 2 == 0:
            k += 1
        ops.append(A.GaussianBlur(blur_limit=(k, k), p=1.0))
    if params.get("hist_eq"):
        ops.append(A.Equalize(p=1.0))
    if params.get("clahe"):
        clip = float(params.get("clahe_clip", 2.0))
        ops.append(A.CLAHE(clip_limit=clip, p=1.0))
    if params.get("gamma"):
        g_min = int(params.get("gamma_min", 80))
        g_max = int(params.get("gamma_max", 120))
        ops.append(A.RandomGamma(gamma_limit=(g_min, g_max), p=1.0))

    return A.Compose(ops, additional_targets={"mask": "mask"})


def _apply_noise(image_bgr: np.ndarray, std: float) -> np.ndarray:
    """Apply Gaussian noise directly in pixel space (0-255). std = pixel std deviation."""
    noise = np.random.normal(0, std, image_bgr.shape).astype(np.float32)
    noisy = image_bgr.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def augment_once(
    image_bgr: np.ndarray,
    label_map: np.ndarray,
    params: dict,
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply augmentation to image and label map. Returns (aug_image_bgr, aug_label_map)."""
    transform = _build_transform(params)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = transform(image=image_rgb, mask=label_map)
    aug_bgr = cv2.cvtColor(result["image"], cv2.COLOR_RGB2BGR)

    if params.get("noise"):
        std = float(params.get("noise_var", 8.0))
        aug_bgr = _apply_noise(aug_bgr, std)

    return aug_bgr, result["mask"]
