from __future__ import annotations
import json
import os
from typing import List, Optional, Tuple

import cv2
import numpy as np

LABELME_VERSION = "1.0.1"
_DESCRIPTION = "HyAugmate COCO Dataset JSON - jamin"

_PALETTE_BGR = [
    (50,  50,  220), (50,  180, 50),  (220, 100, 50),  (50,  160, 220),
    (220, 50,  160), (50,  200, 200), (150, 100, 220),  (220, 180, 50),
    (100, 220, 100), (220, 120, 120),
]


def load_shapes(json_path: str) -> Optional[Tuple[list, int, int]]:
    """Returns (shapes, h, w) or None if file not found."""
    if not os.path.isfile(json_path):
        return None
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    shapes = [
        s for s in data.get("shapes", [])
        if s.get("shape_type") == "polygon" and len(s.get("points", [])) >= 3
    ]
    return shapes, data.get("imageHeight", 0), data.get("imageWidth", 0)


def shapes_to_label_map(
    shapes: list, h: int, w: int
) -> Tuple[np.ndarray, List[Tuple[int, str]]]:
    """
    Rasterize polygon shapes into a uint8 label map.
    Returns (label_map H×W, ann_info [(ann_id, label), ...]).
    ann_id starts from 1; 0 = background.
    """
    label_map = np.zeros((h, w), dtype=np.uint8)
    ann_info: List[Tuple[int, str]] = []

    for idx, shape in enumerate(shapes):
        points = shape.get("points", [])
        if len(points) < 3:
            continue
        ann_id = idx + 1
        if ann_id > 255:
            break  # uint8 limit
        label = shape.get("label", "unknown")
        pts = np.array([[round(x), round(y)] for x, y in points], dtype=np.int32)
        cv2.fillPoly(label_map, [pts], ann_id)
        ann_info.append((ann_id, label))

    return label_map, ann_info


def label_map_to_shapes(
    label_map: np.ndarray, ann_info: List[Tuple[int, str]]
) -> list:
    """Extract contours from augmented label map and rebuild shapes list."""
    id_to_label = {ann_id: label for ann_id, label in ann_info}
    shapes = []

    unique_ids = np.unique(label_map)
    unique_ids = unique_ids[unique_ids > 0]

    for ann_id in unique_ids:
        label = id_to_label.get(int(ann_id), "unknown")
        mask = (label_map == ann_id).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in contours:
            if len(c) < 3:
                continue
            pts = c.reshape(-1, 2).tolist()
            shapes.append({
                "label": label,
                "points": [[float(x), float(y)] for x, y in pts],
                "group_id": None,
                "description": _DESCRIPTION,
                "shape_type": "polygon",
                "flags": {},
                "mask": None,
            })

    return shapes


def save_result(
    out_image_path: str,
    out_json_path: str,
    aug_image: np.ndarray,
    shapes: list,
    h: int,
    w: int,
) -> None:
    cv2.imwrite(out_image_path, aug_image)
    if not shapes:
        return
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": LABELME_VERSION,
            "flags": {},
            "shapes": shapes,
            "imagePath": os.path.basename(out_image_path),
            "imageData": None,
            "imageHeight": h,
            "imageWidth": w,
        }, f, ensure_ascii=False, indent=2)


def draw_overlay(image_bgr: np.ndarray, shapes: list, alpha: float = 0.45) -> np.ndarray:
    """Draw filled polygon overlay with per-label colors."""
    labels = list(dict.fromkeys(s.get("label", "") for s in shapes))
    label_color = {lab: _PALETTE_BGR[i % len(_PALETTE_BGR)] for i, lab in enumerate(labels)}

    overlay = image_bgr.copy()
    for shape in shapes:
        pts = shape.get("points", [])
        if len(pts) < 3:
            continue
        color = label_color.get(shape.get("label", ""), (200, 200, 200))
        pts_arr = np.array([[round(x), round(y)] for x, y in pts], dtype=np.int32)
        cv2.fillPoly(overlay, [pts_arr], color)

    result = cv2.addWeighted(overlay, alpha, image_bgr, 1 - alpha, 0)

    for shape in shapes:
        pts = shape.get("points", [])
        if len(pts) < 3:
            continue
        color = label_color.get(shape.get("label", ""), (200, 200, 200))
        pts_arr = np.array([[round(x), round(y)] for x, y in pts], dtype=np.int32)
        cv2.polylines(result, [pts_arr], isClosed=True, color=color, thickness=2)

    return result
