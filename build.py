"""우선주-본주 페어 이동 z-score 페이지 빌드.

네이버 일봉 종가를 받아 페어별 비율(우선주 ÷ 본주 × 100)과
60/120/250거래일 이동 평균·표준편차·z를 계산한다.
z_t는 t일을 포함한 직전 N거래일만 쓰므로 미래 정보가 섞이지 않는다.

사용: python build.py [출력 폴더=site]
  - <출력 폴더>/index.html, <출력 폴더>/data.json 생성
  - data/prices.csv 갱신 (종가 원본 기록)
"""
import json
import math
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

FETCH_FROM = "2023-11-01"  # 250일 구간을 SHOW_FROM부터 채우기 위한 워밍업
SHOW_FROM = "2025-01-01"
WINDOWS = [60, 120, 250]
KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent

PAIRS = [
    ("삼성전자", "005930", "삼성전자우", "005935"),
    ("현대차", "005380", "현대차2우B", "005387"),
    ("삼성전기", "009150", "삼성전기우", "009155"),
    ("삼성화재", "000810", "삼성화재우", "000815"),
    ("미래에셋증권", "006800", "미래에셋증권2우B", "00680K"),
    ("두산", "000150", "두산우", "000155"),
    ("LG전자", "066570", "LG전자우", "066575"),
]


def fetch_close(code: str) -> pd.Series:
    r = requests.get(
        "https://fchart.stock.naver.com/sise.nhn",
        params={"symbol": code, "timeframe": "day", "count": 2000, "requestType": 0},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    r.raise_for_status()
    rows = re.findall(r'data="([^"]+)"', r.text)
    if not rows:
        raise RuntimeError(f"{code}: 네이버에서 데이터를 받지 못함")
    s = pd.Series({pd.Timestamp(row.split("|")[0]): float(row.split("|")[4]) for row in rows}).sort_index()
    # 장 마감(15:30) 전에 돌면 오늘 봉은 장중 가격이라 뺀다
    now = datetime.now(KST)
    if now.strftime("%H:%M") < "15:40":
        s = s[s.index < pd.Timestamp(now.date())]
    return s[s.index >= FETCH_FROM]


def clean(values, ndigits):
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), ndigits) for v in values]


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs, csv_rows = [], []
    for common, common_code, pref, pref_code in PAIRS:
        df = pd.concat({"common": fetch_close(common_code), "pref": fetch_close(pref_code)}, axis=1).dropna()
        df["ratio"] = df["pref"] / df["common"] * 100
        show = df.index >= SHOW_FROM
        entry = {
            "pair": common, "pref": pref, "commonCode": common_code, "prefCode": pref_code,
            "dates": [d.strftime("%Y-%m-%d") for d in df.index[show]],
            "ratio": clean(df["ratio"][show], 4),
            "commonClose": df["common"][show].astype(int).tolist(),
            "prefClose": df["pref"][show].astype(int).tolist(),
            "w": {},
        }
        for w in WINDOWS:
            roll = df["ratio"].rolling(w)
            mean, std = roll.mean(), roll.std(ddof=1)
            z = (df["ratio"] - mean) / std
            entry["w"][str(w)] = {"mean": clean(mean[show], 4), "std": clean(std[show], 4), "z": clean(z[show], 3)}
        pairs.append(entry)
        for d, row in df.iterrows():
            csv_rows.append({"date": d.strftime("%Y-%m-%d"), "pair": common, "pref": pref,
                             "commonClose": int(row["common"]), "prefClose": int(row["pref"])})
        last = {w: entry["w"][str(w)]["z"][-1] for w in WINDOWS}
        print(f"{pref:<12} {entry['dates'][-1]}  ratio={entry['ratio'][-1]:6.2f}%  z={last}")

    data = {
        "updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "windows": WINDOWS,
        "pairs": pairs,
    }
    (out_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(ROOT / "page" / "index.html", out_dir / "index.html")

    (ROOT / "data").mkdir(exist_ok=True)
    pd.DataFrame(csv_rows).to_csv(ROOT / "data" / "prices.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "site"))
