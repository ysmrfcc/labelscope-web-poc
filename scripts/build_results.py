# scripts/build_results.py
import os, json, pathlib, urllib.request, urllib.error, time

REPO = os.environ.get("GITHUB_REPOSITORY", "")
ENDPOINT = (os.environ.get("AZURE_CV_ENDPOINT") or "").rstrip("/")
KEY = os.environ.get("AZURE_CV_KEY") or ""

IMG_DIR = pathlib.Path("images")
OUT_DIR = pathlib.Path("docs") / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {".jpg",".jpeg",".png",".webp",".bmp",".tif",".tiff"}

def list_images():
    if not IMG_DIR.exists():
        return []
    files = [p for p in IMG_DIR.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED]
    # なるべく新しい順（mtime降順）
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files

def analyze(pth: pathlib.Path):
    """Azure CV を呼び出し。失敗してもエラー内容を返し、結果JSONは必ず作る。"""
    if not ENDPOINT or not KEY:
        return {"error": True, "message": "CV endpoint/key not configured"}
    url = f"{ENDPOINT}/computervision/imageanalysis:analyze?api-version=2023-10-01&features=caption,tags,objects"
    with open(pth, "rb") as f:
        body = f.read()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Ocp-Apim-Subscription-Key": KEY,
        "Content-Type": "application/octet-stream"
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode("utf-8", "ignore")}
    except Exception as e:
        return {"error": True, "message": str(e)}

def ensure_result_for(img: pathlib.Path):
    name = img.name + ".json"
    out = OUT_DIR / name
    if not out.exists():
        cv = analyze(img)
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{img.as_posix()}" if REPO else None
        payload = {
            "source": {"file": img.name, "path": img.as_posix(), "raw_url": raw_url, "ts": int(time.time())},
            "cv_result": cv
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def rebuild_index(json_files):
    # mtime 降順で .json ファイル名（ベース名+.json）を配列に
    items = sorted([p.name for p in json_files], key=lambda p: (OUT_DIR / p).stat().st_mtime, reverse=True)
    (OUT_DIR / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    imgs = list_images()
    json_files = []
    for img in imgs:
        jf = ensure_result_for(img)
        json_files.append(jf.name)
    # 結果が0件でも index.json は必ず作る（空配列）
    rebuild_index([OUT_DIR / n for n in json_files])

if __name__ == "__main__":
    main()
