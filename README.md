# MedSupply AI – Starter Project

A working MVP for medical inventory shortage detection and procurement planning.

## Features
- Upload hospital inventory CSV.
- Upload supplier quotation CSV.
- Upload procurement guideline `.txt` / `.md` file.
- Identify stock below minimum stock.
- Estimate remaining days using daily usage.
- Compare supplier quotations.
- Generate a draft purchase plan and estimated cost.
- Retrieve relevant guideline passages (starter keyword-based retrieval).

## Requirements
- Python 3.10+
- Node.js 18+

## Run backend
Open a terminal:
```bash
cd backend
python -m venv venv
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

## Run frontend
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the Vite URL, normally http://localhost:5173.

## CSV formats

Inventory CSV must contain:
`item,current_stock,minimum_stock,daily_usage`

Supplier quotation CSV must contain:
`item,supplier,unit_price,delivery_days`

Sample files are in `backend/data/`.

## Important project notes
- This is an educational prototype, not a clinical or production procurement system.
- The current guideline retrieval is a lightweight keyword-based RAG placeholder. Upgrade it to embeddings + FAISS/Chroma and connect a vetted LLM to call it a true semantic RAG workflow.
- The current four agent roles are implemented as separate functions: inventory analysis, supplier comparison, guideline retrieval and purchase planning.
- The purchase plan is only a recommendation. A hospital procurement officer must verify specifications, supplier credentials, expiry dates, certifications and approve all orders.
- Do not upload real patient data. The demo does not need patient information.
