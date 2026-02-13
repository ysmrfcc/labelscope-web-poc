# scripts/run_cv.py
import os, json, pathlib, urllib.request, urllib.error, time, sys

endpoint = os.environ["AZURE_CV_ENDPOINT"].rstrip("/")
key      = os.environ["AZURE_CV_KEY"]
img_path = os.environ["INPUT_IMAGE"]

def analyze(pth: str):
    url = f"{endpoint}/computervision/imageanalysis:analyze?api-version=2023-10-01&features=caption,tags,objects"
    with open(pth, "rb") as f:
        body = f.read()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "message": e.read().decode("utf-8", "ignore")}
    except Exception as e:
        return {"error": True, "message": str(e)}

result = analyze(img_path)

outdir = pathlib.Path("docs") / "data"
outdir.mkdir(parents=True, exist_ok=True)

name = pathlib.Path(img_path).name + ".json"
payload = {
    "source": {
        "file": pathlib.Path(img_path).name,
        "ts": int(time.time())
    },
    "cv_result": result
}
(outdir / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

# index.json 更新（先頭に今回分、最大100件、重複排除）
index = outdir / "index.json"
lst = []
if index.exists():
    try:
        lst = json.loads(index.read_text(encoding="utf-8"))
    except Exception:
        lst = []
if name in lst:
    lst.remove(name)
lst.insert(0, name)
index.write_text(json.dumps(lst[:100], ensure_ascii=False, indent=2), encoding="utf-8")
