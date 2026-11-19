import json
import math
import re
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values
from openai import OpenAI


# ==========================================================
# NEXUS CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
CONFIG = dotenv_values(BASE_DIR / ".env")

API_KEY = CONFIG.get("NEXUS_API_KEY")
BASE_URL = CONFIG.get("NEXUS_API_BASE_URL")
MODEL = CONFIG.get("NEXUS_MODEL", "nova-micro")
EMBEDDING_MODEL = CONFIG.get(
    "NEXUS_EMBEDDING_MODEL",
    "text-embedding-3-small"
)

_client = None


def get_nexus_client():
    global _client

    if _client is None:
        if not API_KEY or not BASE_URL:
            raise ValueError(
                "NEXUS_API_KEY or NEXUS_API_BASE_URL missing in backend/.env"
            )

        _client = OpenAI(
            api_key=API_KEY.strip(),
            base_url=BASE_URL.strip(),
            timeout=30.0,
            max_retries=1
        )

    return _client


def ask_nexus(prompt, max_tokens=400):
    try:
        client = get_nexus_client()

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are MedSupply AI, an intelligent hospital "
                        "procurement assistant. Use only provided data. "
                        "Never invent suppliers, prices, stock or policies. "
                        "Give safe and explainable recommendations."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as error:
        print("Nexus AI error:", type(error).__name__, str(error))
        return None


def parse_json_response(response_text):
    if not response_text:
        return None

    try:
        cleaned = response_text.strip()
        cleaned = re.sub(
            r"^```(?:json)?\s*", "", cleaned,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()

            for index, char in enumerate(cleaned):
                if char in "[{":
                    try:
                        result, _ = decoder.raw_decode(cleaned[index:])
                        return result
                    except json.JSONDecodeError:
                        continue

        return None

    except Exception as error:
        print("JSON parsing error:", str(error))
        return None


# ==========================================================
# AGENT 1 - INVENTORY AGENT
# ==========================================================

def analyze_inventory(df):
    results = []

    required_columns = {
        "item", "current_stock", "minimum_stock", "daily_usage"
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"Inventory must contain columns: {required_columns}"
        )

    for _, row in df.iterrows():
        stock = float(row["current_stock"])
        minimum = float(row["minimum_stock"])
        usage = max(float(row["daily_usage"]), 0.01)

        if stock < minimum:
            days = round(stock / usage, 1)
            shortage = max(minimum - stock, 0)

            results.append({
                "item": str(row["item"]),
                "current_stock": stock,
                "minimum_stock": minimum,
                "shortage_quantity": shortage,
                "daily_usage": usage,
                "estimated_days_remaining": days,
                "status": "Critical" if days <= 3 else "Low"
            })

    if not results:
        return results

    prompt = f"""
You are the Inventory Agent of MedSupply AI.

Analyse these calculated inventory shortages:
{json.dumps(results)}

For every item return:
- item
- priority (Critical, High, Medium or Low)
- reason
- recommendation

Use only provided data. Never change stock or shortage quantities.
Return a valid JSON array only.
"""

    ai_data = parse_json_response(ask_nexus(prompt, 500))
    insights = {}

    if isinstance(ai_data, list):
        insights = {
            str(item.get("item", "")).strip().lower(): item
            for item in ai_data
            if isinstance(item, dict)
        }

    for result in results:
        insight = insights.get(result["item"].strip().lower())

        if insight:
            result["ai_priority"] = str(
                insight.get("priority", result["status"])
            )
            result["ai_reason"] = str(insight.get("reason", ""))
            result["ai_recommendation"] = str(
                insight.get("recommendation", "")
            )
        else:
            result["ai_priority"] = result["status"]
            result["ai_reason"] = (
                f"Stock is below minimum level. Approximately "
                f"{result['estimated_days_remaining']} days remain."
            )
            result["ai_recommendation"] = (
                "Review stock and prepare a replenishment order."
            )

    return results


# ==========================================================
# AGENT 2 - SUPPLIER COMPARISON AGENT
# ==========================================================

def compare_suppliers(suppliers, shortages):
    required_columns = {
        "item", "supplier", "unit_price", "delivery_days"
    }

    if not required_columns.issubset(suppliers.columns):
        raise ValueError(
            f"Supplier quotations must contain: {required_columns}"
        )

    items = list(dict.fromkeys(
        str(shortage["item"]) for shortage in shortages
    ))

    output = []

    for item in items:
        options = suppliers[
            suppliers["item"].astype(str).str.strip().str.lower()
            == item.strip().lower()
        ].copy()

        if not options.empty:
            options["unit_price"] = pd.to_numeric(
                options["unit_price"], errors="coerce"
            )
            options["delivery_days"] = pd.to_numeric(
                options["delivery_days"], errors="coerce"
            )
            options = options.dropna(
                subset=["unit_price", "delivery_days", "supplier"]
            )
            options = options[
                (options["unit_price"] >= 0)
                & (options["delivery_days"] >= 0)
            ]

        ranked = options.sort_values(
            ["unit_price", "delivery_days"]
        ).to_dict(orient="records")

        candidates = [
            {
                "supplier": str(row["supplier"]),
                "unit_price": float(row["unit_price"]),
                "delivery_days": int(row["delivery_days"])
            }
            for row in ranked
        ]

        recommended = "Quotation required"
        ai_reason = "No supplier quotation is available."

        if candidates:
            recommended = candidates[0]["supplier"]
            ai_reason = (
                "Fallback recommendation based on lowest price "
                "and delivery time."
            )

            prompt = f"""
You are the Supplier Comparison Agent of MedSupply AI.

Item: {item}
Available supplier quotations:
{json.dumps(candidates)}

Choose one supplier considering unit price and delivery days.
Select an exact supplier name from the supplied list.
Do not invent suppliers or modify prices.

Return JSON only:
{{
  "recommended_supplier": "exact supplier name",
  "reason": "short explanation"
}}
"""

            ai_result = parse_json_response(ask_nexus(prompt, 250))

            if isinstance(ai_result, dict):
                proposed = str(
                    ai_result.get("recommended_supplier", "")
                ).strip()

                valid_names = [
                    candidate["supplier"] for candidate in candidates
                ]

                if proposed in valid_names:
                    recommended = proposed
                    ai_reason = str(
                        ai_result.get("reason", ai_reason)
                    )

        output.append({
            "item": item,
            "suppliers": candidates,
            "recommended_supplier": recommended,
            "ai_reason": ai_reason
        })

    return output


# ==========================================================
# AGENT 3 - RAG GUIDELINES AGENT
# ==========================================================

def split_into_chunks(text, max_length=500):
    if not text:
        return []

    words = text.split()
    chunks = []
    current = []
    current_length = 0

    for word in words:
        current.append(word)
        current_length += len(word) + 1

        if current_length >= max_length:
            chunks.append(" ".join(current))
            current = []
            current_length = 0

    if current:
        chunks.append(" ".join(current))

    return chunks


def cosine_similarity(vector_a, vector_b):
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def retrieve_guidelines(text, query):
    if not text or not text.strip():
        return []

    chunks = split_into_chunks(text)

    if not chunks:
        return []

    ranked = []
    retrieval_method = "keyword_fallback"

    try:
        client = get_nexus_client()

        embedding_response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query] + chunks
        )

        vectors = [
            item.embedding
            for item in sorted(
                embedding_response.data,
                key=lambda item: item.index
            )
        ]

        query_vector = vectors[0]

        for index, chunk in enumerate(chunks):
            score = cosine_similarity(
                query_vector, vectors[index + 1]
            )

            ranked.append({
                "content": chunk,
                "similarity": round(score, 4),
                "matched_terms": 0
            })

        ranked.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        retrieval_method = "nexus_embeddings"

    except Exception as error:
        print(
            "Nexus embedding error:",
            type(error).__name__,
            str(error)
        )

        terms = [
            word.lower()
            for word in query.split()
            if len(word) > 3
        ]

        for chunk in chunks:
            matches = sum(
                term in chunk.lower() for term in terms
            )

            ranked.append({
                "content": chunk,
                "similarity": 0.0,
                "matched_terms": matches
            })

        ranked.sort(
            key=lambda item: item["matched_terms"],
            reverse=True
        )

    selected = ranked[:4]

    context = "\n\n".join(
        item["content"] for item in selected
    )

    prompt = f"""
You are the Guidelines RAG Agent of MedSupply AI.

Answer using ONLY the retrieved hospital procurement guideline
content.

Retrieved guideline context:
{context}

User question:
{query}

Rules:
1. Do not invent hospital policies.
2. Do not add unsupported facts.
3. If the guidelines do not contain the answer, clearly state that.
4. Give a concise and understandable answer.
"""

    answer = ask_nexus(prompt, 400)

    if answer:
        selected.append({
            "content": answer,
            "matched_terms": 0,
            "similarity": 0.0,
            "type": "ai_generated_answer",
            "retrieval_method": retrieval_method
        })

    return selected


# ==========================================================
# INTERACTIVE RAG CHATBOT
# ==========================================================

def answer_guidelines_question(question, guideline_text):
    question = str(question or "").strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if not guideline_text or not guideline_text.strip():
        return {
            "answer": (
                "No procurement guidelines have been uploaded yet. "
                "Please upload a TXT or MD guideline file first."
            ),
            "sources": [],
            "retrieval_method": "none",
            "ai_generated": False
        }

    retrieved = retrieve_guidelines(guideline_text, question)

    answer_entry = next(
        (
            item for item in retrieved
            if isinstance(item, dict)
            and item.get("type") == "ai_generated_answer"
        ),
        None
    )

    sources = [
        {
            "content": item.get("content", ""),
            "similarity": item.get("similarity", 0),
            "matched_terms": item.get("matched_terms", 0)
        }
        for item in retrieved
        if isinstance(item, dict)
        and item.get("type") != "ai_generated_answer"
    ]

    if answer_entry:
        answer = answer_entry.get("content", "")
        retrieval_method = answer_entry.get(
            "retrieval_method", "unknown"
        )
        ai_generated = True
    else:
        answer = (
            "I couldn't generate an AI answer. "
            "Please check the Nexus API connection and try again."
        )
        retrieval_method = "unknown"
        ai_generated = False

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_method": retrieval_method,
        "ai_generated": ai_generated
    }


# ==========================================================
# AGENT 4 - PURCHASE PLANNING AGENT
# ==========================================================

def build_purchase_plan(
    shortages,
    suppliers,
    supplier_comparison=None
):
    plan = []
    supplier_recommendations = {}

    if supplier_comparison:
        for comparison in supplier_comparison:
            supplier_recommendations[
                str(comparison["item"]).strip().lower()
            ] = comparison.get("recommended_supplier")

    for shortage in shortages:
        item = str(shortage["item"])

        options = suppliers[
            suppliers["item"].astype(str).str.strip().str.lower()
            == item.strip().lower()
        ].copy()

        if options.empty:
            plan.append({
                "item": item,
                "suggested_quantity": int(
                    shortage["shortage_quantity"]
                ),
                "supplier": "Not available",
                "unit_price": None,
                "estimated_cost": None,
                "note": "Upload a quotation for this item.",
                "approval_required": True
            })
            continue

        recommended_name = supplier_recommendations.get(
            item.strip().lower()
        )

        chosen_options = options[
            options["supplier"].astype(str).str.strip()
            == str(recommended_name).strip()
        ]

        if not chosen_options.empty:
            chosen = chosen_options.iloc[0]
        else:
            chosen = options.sort_values(
                ["unit_price", "delivery_days"]
            ).iloc[0]

        quantity = int(shortage["shortage_quantity"])
        price = float(chosen["unit_price"])
        estimated_cost = round(quantity * price, 2)

        plan.append({
            "item": item,
            "suggested_quantity": quantity,
            "supplier": str(chosen["supplier"]),
            "unit_price": price,
            "estimated_cost": estimated_cost,
            "note": "Draft recommendation. Authorized approval required.",
            "approval_required": True
        })

    if not plan:
        return plan

    prompt = f"""
You are the Purchase Planning Agent of MedSupply AI.

Review this draft purchase plan:
{json.dumps(plan)}

For each item provide:
- item
- recommendation_reason

Do not change quantities, suppliers, prices or costs.
Do not create purchase orders.
Human approval is mandatory.
Use only provided information.

Return a valid JSON array only.
"""

    ai_data = parse_json_response(ask_nexus(prompt, 400))

    if isinstance(ai_data, list):
        reasons = {
            str(entry.get("item", "")).strip().lower():
            str(entry.get("recommendation_reason", ""))
            for entry in ai_data
            if isinstance(entry, dict)
        }

        for entry in plan:
            reason = reasons.get(entry["item"].strip().lower())

            if reason:
                entry["ai_recommendation"] = reason

    for entry in plan:
        if "ai_recommendation" not in entry:
            entry["ai_recommendation"] = (
                "Review the suggested quantity and supplier "
                "quotation before obtaining approval."
            )

    return plan


# ==========================================================
# AGENT STATUS
# ==========================================================

def get_agent_status():
    return {
        "inventory_agent": "configured",
        "supplier_agent": "configured",
        "rag_agent": "configured",
        "purchase_agent": "configured",
        "nexus_model": MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "nexus_api_configured": bool(API_KEY and BASE_URL)
    }