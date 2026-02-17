# scripts/build_results.py
import os, json, pathlib, urllib.request, urllib.error, time

REPO = os.environ.get("GITHUB_REPOSITORY", "")
PREDICTION_ENDPOINT = (os.environ.get("PREDICTION_ENDPOINT") or "").strip()
PREDICTION_KEY = (os.environ.get("PREDICTION_KEY") or "").strip()

IMG_DIR = pathlib.Path("images")
OUT_DIR = pathlib.Path("docs") / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

def list_images():
    if not IMG_DIR.exists():
        return []
    files = [p for p in IMG_DIR.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files

def predict(img_path: pathlib.Path):
    if not PREDICTION_ENDPOINT or not PREDICTION_KEY:
        return {"error": True, "message": "Prediction endpoint/key not configured"}
    with open(img_path, "rb") as f:
        body = f.read()
    req = urllib.request.Request(
        PREDICTION_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Prediction-Key": PREDICTION_KEY,
            "Content-Type": "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode("utf-8", "ignore")}
    except Exception as e:
        return {"error": True, "message": str(e)}

def ensure_result(img: pathlib.Path):
    out_file = OUT_DIR / f"{img.name}.json"
    if not out_file.exists():
        res = predict(img)
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{img.as_posix()}" if REPO else None
        payload = {
            "source": {"file": img.name, "path": img.as_posix(), "raw_url": raw_url, "ts": int(time.time())},
            "cv_result": res,
        }
        out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file

def rebuild_index(json_files):
    items = sorted([p.name for p in json_files], key=lambda n: (OUT_DIR / n).stat().st_mtime, reverse=True)
    (OUT_DIR / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    imgs = list_images()
    jfs = [ensure_result(p) for p in imgs]
    rebuild_index([OUT_DIR / jf.name for jf in jfs])

if __name__ == "__main__":
    main()
