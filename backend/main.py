
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import pandas as pd
import io

from agents import (
    analyze_inventory,
    compare_suppliers,
    retrieve_guidelines,
    answer_guidelines_question,
    build_purchase_plan,
    get_agent_status
)


# ==========================================================
# APP CONFIGURATION
# ==========================================================

app = FastAPI(
    title="MedSupply AI API",
    version="5.0.0",
    description=(
        "Nexus-powered Agentic Medical Procurement Assistant "
        "with Interactive RAG Chatbot"
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "data"
DATA.mkdir(exist_ok=True)


# ==========================================================
# CHAT REQUEST MODEL
# ==========================================================

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User question for MedSupply AI chatbot"
    )


# ==========================================================
# DEFAULT DATA
# ==========================================================

DEFAULT_INVENTORY = [
    {
        "item": "Surgical Gloves",
        "current_stock": 120,
        "minimum_stock": 200,
        "daily_usage": 20
    },
    {
        "item": "Syringes 5ml",
        "current_stock": 900,
        "minimum_stock": 500,
        "daily_usage": 60
    },
    {
        "item": "Oxygen Masks",
        "current_stock": 35,
        "minimum_stock": 80,
        "daily_usage": 8
    }
]

DEFAULT_SUPPLIERS = [
    {
        "item": "Surgical Gloves",
        "supplier": "MedCare Supplies",
        "unit_price": 4.5,
        "delivery_days": 2
    },
    {
        "item": "Surgical Gloves",
        "supplier": "HealthFirst Traders",
        "unit_price": 4.2,
        "delivery_days": 5
    },
    {
        "item": "Oxygen Masks",
        "supplier": "MedCare Supplies",
        "unit_price": 32,
        "delivery_days": 2
    },
    {
        "item": "Oxygen Masks",
        "supplier": "LifeLine Medical",
        "unit_price": 29,
        "delivery_days": 4
    }
]

DEFAULT_GUIDELINES = """
PROCUREMENT GUIDELINES

1. INVENTORY MANAGEMENT
- Maintain minimum safety stock for critical medical supplies.
- Review inventory regularly.
- Identify items below minimum stock level.
- Estimate remaining stock based on daily usage.

2. SUPPLIER EVALUATION
- Compare supplier prices and delivery times.
- Consider supplier reliability and product quality.
- Verify supplier credentials and certifications.

3. PURCHASE PLANNING
- Calculate required purchase quantities.
- Check product specifications and expiry dates.
- Confirm supplier availability and delivery timelines.

4. QUALITY AND SAFETY
- Verify product certifications.
- Check expiry dates and product condition.
- Follow approved storage and handling procedures.

5. APPROVAL AND AUDIT
- Purchase orders require authorized approval.
- Record supplier quotations and purchase decisions.
- Maintain procurement audit records.
"""


# ==========================================================
# DATA VALIDATION
# ==========================================================

def validate_columns(df, required):
    missing = required - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=400,
            detail="Missing columns: " + ", ".join(sorted(missing))
        )


def validate_inventory(df):
    required = {
        "item",
        "current_stock",
        "minimum_stock",
        "daily_usage"
    }

    validate_columns(df, required)

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Inventory CSV is empty."
        )

    df = df.copy()

    if df["item"].isnull().any():
        raise HTTPException(
            status_code=400,
            detail="Inventory item names cannot be empty."
        )

    df["item"] = df["item"].astype(str).str.strip()

    if (df["item"] == "").any():
        raise HTTPException(
            status_code=400,
            detail="Inventory item names cannot be empty."
        )

    for column in [
        "current_stock",
        "minimum_stock",
        "daily_usage"
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    if df[
        ["current_stock", "minimum_stock", "daily_usage"]
    ].isnull().any().any():

        raise HTTPException(
            status_code=400,
            detail="Inventory numeric columns contain invalid values."
        )

    if (
        (df["current_stock"] < 0).any()
        or (df["minimum_stock"] < 0).any()
        or (df["daily_usage"] < 0).any()
    ):
        raise HTTPException(
            status_code=400,
            detail="Stock and usage values cannot be negative."
        )

    return df


def validate_quotations(df):
    required = {
        "item",
        "supplier",
        "unit_price",
        "delivery_days"
    }

    validate_columns(df, required)

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Quotation CSV is empty."
        )

    df = df.copy()

    if df[["item", "supplier"]].isnull().any().any():
        raise HTTPException(
            status_code=400,
            detail="Item and supplier names cannot be empty."
        )

    df["item"] = df["item"].astype(str).str.strip()
    df["supplier"] = df["supplier"].astype(str).str.strip()

    if (
        (df["item"] == "").any()
        or (df["supplier"] == "").any()
    ):
        raise HTTPException(
            status_code=400,
            detail="Item and supplier names cannot be empty."
        )

    for column in ["unit_price", "delivery_days"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    if df[
        ["unit_price", "delivery_days"]
    ].isnull().any().any():

        raise HTTPException(
            status_code=400,
            detail="Price and delivery days must be numeric."
        )

    if (
        (df["unit_price"] < 0).any()
        or (df["delivery_days"] < 0).any()
    ):
        raise HTTPException(
            status_code=400,
            detail="Price and delivery days cannot be negative."
        )

    return df


def csv_to_df(content):
    try:
        return pd.read_csv(io.BytesIO(content))

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV file: {str(error)}"
        )


# ==========================================================
# LOAD SAVED DATA
# ==========================================================

def load_inventory():
    file_path = DATA / "inventory.csv"

    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            return validate_inventory(df)

        except Exception as error:
            print("Inventory loading error:", error)

    return pd.DataFrame(DEFAULT_INVENTORY)


def load_suppliers():
    file_path = DATA / "quotations.csv"

    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            return validate_quotations(df)

        except Exception as error:
            print("Quotation loading error:", error)

    return pd.DataFrame(DEFAULT_SUPPLIERS)


def load_guidelines():
    file_path = DATA / "guidelines.txt"

    if file_path.exists():
        return file_path.read_text(encoding="utf-8")

    return DEFAULT_GUIDELINES


inventory_df = load_inventory()
supplier_df = load_suppliers()
guideline_text = load_guidelines()


# ==========================================================
# ROOT AND HEALTH
# ==========================================================

@app.get("/")
def root():
    return {
        "message": "MedSupply AI API is running",
        "version": "5.0.0",
        "chatbot": "enabled"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "backend": "running"
    }


@app.get("/api/agents/status")
def agents_status():
    """
    Reports configured agent and model information.
    This does not independently verify live API availability.
    """

    return get_agent_status()


# ==========================================================
# DASHBOARD
# ==========================================================

@app.get("/api/dashboard")
def dashboard():

    try:
        shortages = analyze_inventory(inventory_df)

        return {
            "total_items": int(len(inventory_df)),
            "shortage_items": int(len(shortages)),
            "total_suppliers": int(
                supplier_df["supplier"].nunique()
            ),
            "shortages": shortages
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard error: {str(error)}"
        )


# ==========================================================
# INVENTORY
# ==========================================================

@app.get("/api/inventory")
def get_inventory():

    return inventory_df.fillna("").to_dict(
        orient="records"
    )


# ==========================================================
# UPLOAD INVENTORY
# ==========================================================

@app.post("/api/upload/inventory")
async def upload_inventory(file: UploadFile = File(...)):

    global inventory_df

    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    content = await file.read()
    df = csv_to_df(content)
    df = validate_inventory(df)

    inventory_df = df

    inventory_df.to_csv(
        DATA / "inventory.csv",
        index=False
    )

    return {
        "message": "Inventory uploaded successfully",
        "rows": len(df)
    }


# ==========================================================
# UPLOAD SUPPLIER QUOTATIONS
# ==========================================================

@app.post("/api/upload/quotations")
async def upload_quotations(file: UploadFile = File(...)):

    global supplier_df

    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    content = await file.read()
    df = csv_to_df(content)
    df = validate_quotations(df)

    supplier_df = df

    supplier_df.to_csv(
        DATA / "quotations.csv",
        index=False
    )

    return {
        "message": "Supplier quotations uploaded successfully",
        "rows": len(df)
    }


# ==========================================================
# UPLOAD PROCUREMENT GUIDELINES
# ==========================================================

@app.post("/api/upload/guidelines")
async def upload_guidelines(file: UploadFile = File(...)):

    global guideline_text

    if (
        not file.filename
        or not file.filename.lower().endswith((".txt", ".md"))
    ):
        raise HTTPException(
            status_code=400,
            detail="Upload a TXT or MD guideline file."
        )

    content = await file.read()

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Guideline file is empty."
        )

    guideline_text = content.decode(
        "utf-8",
        errors="ignore"
    )

    (DATA / "guidelines.txt").write_text(
        guideline_text,
        encoding="utf-8"
    )

    return {
        "message": "Guidelines uploaded successfully",
        "characters": len(guideline_text)
    }


# ==========================================================
# INTERACTIVE RAG CHATBOT
# ==========================================================

@app.post("/api/chat")
def chat_with_med_supply_ai(request: ChatRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    try:
        result = answer_guidelines_question(
            question,
            guideline_text
        )

        return {
            "success": True,
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
            "retrieval_method": result["retrieval_method"],
            "ai_generated": result["ai_generated"]
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(
            "Chatbot execution error:",
            type(error).__name__,
            str(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Chatbot failed. Please check the backend logs."
        )


# ==========================================================
# AI AGENTS + RAG ANALYSIS
# ==========================================================

@app.get("/api/analysis")
def analysis():

    try:
        # AGENT 1: INVENTORY AGENT

        shortages = analyze_inventory(
            inventory_df
        )

        # AGENT 2: SUPPLIER COMPARISON AGENT

        supplier_comparison = compare_suppliers(
            supplier_df,
            shortages
        )

        # AGENT 3: RAG GUIDELINES AGENT

        guideline_matches = retrieve_guidelines(
            guideline_text,
            (
                "hospital critical stock safety stock "
                "procurement supplier reliability delivery "
                "approval product specifications expiry "
                "certifications warranty audit records"
            )
        )

        # AGENT 4: PURCHASE PLANNING AGENT

        purchase_plan = build_purchase_plan(
            shortages,
            supplier_df,
            supplier_comparison
        )

        return {
            "shortages": shortages,
            "supplier_comparison": supplier_comparison,
            "guideline_matches": guideline_matches,
            "purchase_plan": purchase_plan
        }

    except Exception as error:

        print(
            "Analysis execution error:",
            type(error).__name__,
            str(error)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(error)}"
        )


# ==========================================================
# SERVER INFORMATION
# ==========================================================

@app.get("/api/info")
def api_info():

    return {
        "application": "MedSupply AI",
        "version": "5.0.0",
        "features": [
            "Inventory Management",
            "Inventory Shortage Analysis",
            "Supplier Comparison",
            "Procurement Guidelines Upload",
            "RAG Guideline Retrieval",
            "Interactive AI Chatbot",
            "Purchase Planning"
        ],
        "chat_endpoint": "/api/chat",
        "documentation": "/docs"
    }
