import pandas as pd
import json
import io
import time
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

parquet_path = "data/bge/documents/test-00000.parquet"
output_path = "data/bge/evaluation/ekacare_20_ocr.json"

df = pd.read_parquet(parquet_path)
ocr = RapidOCR()

results = []

for i, row in df.iterrows():
    try:
        image = Image.open(io.BytesIO(row["image"])).convert("RGB")
        image_array = np.array(image)

        start = time.time()
        detected, elapsed = ocr(image_array)

        lines = [item[1] for item in detected] if detected else []
        text = "\n".join(lines)

        results.append({
            "record_id": int(i),
            "document_type": str(row["document_type"]),
            "sample_prompt": str(row["sample_prompt"]),
            "rubrics": str(row["rubrics"]),
            "ocr_text": text,
            "ocr_line_count": len(lines),
            "processing_seconds": round(time.time() - start, 2),
            "status": "success"
        })

        print(f"{i+1}/20 | {row['document_type']} | {len(lines)} lines | SUCCESS")

    except Exception as e:
        results.append({
            "record_id": int(i),
            "document_type": str(row["document_type"]),
            "rubrics": str(row["rubrics"]),
            "ocr_text": "",
            "status": "failed",
            "error": str(e)
        })
        print(f"{i+1}/20 | FAILED | {e}")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nOCR BATCH COMPLETE")
print("Successful:", sum(r["status"] == "success" for r in results))
print("Failed:", sum(r["status"] == "failed" for r in results))
print("Saved:", output_path)
