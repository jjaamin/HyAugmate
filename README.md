# HyAugmate

세그멘테이션 데이터셋 증강 GUI 툴 · HyLabel LabelMe JSON 형식 호환

DMI 영상응용계측기술팀 구자민 TL

---

## 개요

HyLabel로 라벨링한 이미지와 JSON 어노테이션을 불러와 다양한 Augmentation을 적용하고,
증강된 이미지와 JSON을 저장합니다.

---

## 설치

```bash
pip install -r requirements.txt
```

---

## 실행

```bash
python run_hyaugmate.py
```

---

## 화면 구성

```
┌─────────────────┬──────────────────────────────────────┐
│  좌측 패널       │  우측 프리뷰                           │
│                  │                                      │
│  [폴더 설정]     │   원본              결과              │
│  소스 폴더       │  [이미지+마스크]    [이미지+마스크]    │
│  출력 폴더       │                                      │
│                  │  이미지 목록                          │
│  [Augmentation] │                                      │
│  각 항목 체크박스 │                                      │
│  + 파라미터 슬라이더                                     │
│                  │                                      │
│  [생성 설정]     │                                      │
│  이미지당 생성 수 │                                      │
│  [미리보기]      │                                      │
│  [생성 시작]     │                                      │
└─────────────────┴──────────────────────────────────────┘
```

---

## 사용 방법

1. **소스 폴더** 선택 — 이미지와 HyLabel JSON이 함께 있는 폴더
2. **출력 폴더** 선택 — 증강된 파일을 저장할 폴더
3. 적용할 **Augmentation** 체크 및 파라미터 조정
4. **미리보기** 클릭으로 결과 확인
5. **이미지당 생성 수** 설정 후 **생성 시작**

> JSON이 없는 이미지는 목록에서 자동 제외됩니다.

---

## Augmentation 목록

| 기능 | 파라미터 |
|------|---------|
| Horizontal Flip | — |
| Vertical Flip | — |
| Rotation | 각도 범위 ± ° |
| Color Jitter | 밝기 / 대비 / 채도 / 색조 변화 % |
| Gaussian Blur | 커널 크기 px |
| Gaussian Noise | 강도 (std px) |
| Histogram Equalization | — |
| CLAHE | Clip Limit |
| Gamma Correction | Min / Max gamma |

- **기하학적 변환** (Flip, Rotation): 이미지와 마스크 동시 적용
- **픽셀 변환** (Color Jitter, Blur 등): 이미지에만 적용, 마스크 유지
- Rotation 패딩: Zero padding (검은색)

---

## 입출력 형식

- **입력**: 이미지 (jpg/png/bmp 등) + HyLabel LabelMe JSON (같은 폴더, 같은 파일명)
- **출력**: `{원본파일명}_aug001.jpg` + `{원본파일명}_aug001.json`

---

## 파일 구조

```
HyAugmate/
├── run_hyaugmate.py
├── requirements.txt
└── hyaugmate/
    ├── main.py               # QApplication 진입점
    ├── window.py             # 메인 윈도우
    ├── augmentor.py          # Albumentations 래퍼
    ├── coco_io.py            # JSON 로드/저장, 폴리곤↔마스크 변환
    └── widgets/
        ├── control_panel.py  # 좌측 컨트롤 패널
        └── preview_widget.py # 우측 프리뷰
```

---

## 연관 프로젝트

- [HyLabel](https://github.com/jjaamin/HyLabel) — 세그멘테이션 라벨링 툴
