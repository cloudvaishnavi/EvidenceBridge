import json

queries = [
    ("Find the prescription for bipolar mood disorder and its QTRIPIL and VALPARIN medicines.", 1),
    ("Find the laboratory report containing HbA1c 9.4 and liver function profile results.", 2),
    ("Find the complete blood count report with haemoglobin 12.4 and leucocyte count 3700.", 3),
    ("Find the liver profile report containing total protein, albumin and globulin results.", 4),
    ("Find the November 2020 glycocylated haemoglobin report with HbA1c 5.0.", 5),
    ("Find the December 2023 liver function test report with historical protein and bilirubin values.", 6),
    ("Find the pre-medical examination report containing blood group AB positive and fasting blood sugar.", 7),
    ("Find the laboratory report with glucose PP 442 and HbA1c 11.40.", 8),
    ("Find the lower lip biopsy histopathology report describing a non-specific ulcerative lesion.", 9),
    ("Find the lipid profile report containing triglycerides, cholesterol, HDL and LDL.", 10),
    ("Find the typhoid fever prescription containing Rabekind DSR, Dolo and Zifi AZ.", 11),
    ("Find the paediatric prescription for cough and acute moderate spasm with Ospamox and nebulisation advice.", 12),
    ("Find the November 2018 electrolyte report with sodium, potassium and chloride results.", 13),
    ("Find the May 2019 laboratory report containing a CPK result.", 14),
    ("Find the March 2023 serum laboratory report and its specimen processing details.", 15),
    ("Find the December 2023 fasting blood sugar report with historical glucose readings.", 16),
    ("Find the March 2021 report containing eGFR, creatinine, sodium and CBC results.", 17),
    ("Find the August 2020 general body profile with glucose, sodium, potassium and chloride.", 18),
    ("Find the November 2021 prescription containing Pan D, Enzoflam and Novamox.", 19),
    ("Find the March 2022 report containing creatinine, potassium, TSH, PSA and testosterone.", 20)
]

data = [
    {"query": query, "relevant_doc_id": f"ekacare_{i:02d}"}
    for query, i in queries
]

path = "data/bge/evaluation/ekacare_retrieval_queries.json"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Queries created:", len(data))
print("Unique target documents:", len(set(q["relevant_doc_id"] for q in data)))
print("Saved:", path)
