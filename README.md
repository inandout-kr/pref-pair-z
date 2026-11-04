# 우선주 페어 이동 Z

우선주 ÷ 본주 종가 비율의 60·120·250거래일 이동 z-score 차트.
z는 그날을 포함한 직전 N거래일만으로 계산해 미래 정보가 섞이지 않는다.

- 페어: 삼성전자, 현대차(2우B), 삼성전기, 삼성화재, 미래에셋증권(2우B), 두산, LG전자
- 데이터: 네이버 금융 일봉 종가 (2023-11부터 받아 2025-01부터 표시)
- 갱신: GitHub Actions가 평일 16:40 KST에 `build.py`를 돌려 GitHub Pages에 배포하고, `data/prices.csv`를 커밋

## 로컬 실행

```bash
pip install -r requirements.txt
python build.py site
python -m http.server 8765 --directory site
```

수동 갱신은 Actions 탭의 `update` 워크플로에서 Run workflow.
