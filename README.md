# Inventory Search Function

> **Status:** MVP – provides a blazing‑fast keyword & semantic search API over live inventory data.

`Inventory_Search` is an **Azure Functions** microservice that lets Culvana products (Recipe Costing, Menu Assistant, etc.) query inventory items by name, vendor, SKU, or embedding similarity. It returns rich JSON objects ready to power autocomplete dropdowns, analytics dashboards, or AI agents that need real‑time stock info.

---

## 🚀 Highlights

| Feature                            | Description                                                                                       |
| ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Hybrid vector / keyword search** | Combines traditional text filters with cosine‑similarity over OpenAI embeddings.                  |
| **Instant indexing**               | Webhook endpoint to push new invoices or stock updates (`/ingest`).                               |
| **Serverless scaling**             | Azure Functions Consumption plan keeps costs near zero during idle.                               |
| **Typed responses**                | Pydantic models enforce schema: `id`, `name`, `category`, `uom`, `on_hand_qty`, `last_cost`, etc. |
| **CORS**                           | Allowlist pulled from `ALLOWED_ORIGINS` env‑var.                                                  |

---

## 📁 Structure

```
Inventory_Search/
├── function_app.py    # HTTP trigger routing
├── function.json      # Bindings metadata
├── __init__.py        # So VS Code treats folder as package
├── requirements.txt   # fastapi, openai, sqlite-utils, etc.
├── host.json          # Global function settings
└── local.settings.json# Sample secrets for local runs (excluded from Git)
```

---

## 🖥️ Run Locally

```bash
git clone https://github.com/Culvana/Inventory_Search.git
cd Inventory_Search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
func start  # function on http://localhost:7071/api/search
```

### Query Examples

```bash
# Find items containing "romaine"
curl "http://localhost:7071/api/search?q=romaine&limit=5"

# Semantic match for "red delicious apple"
curl "http://localhost:7071/api/search?q=red+delicious+apple&mode=semantic"
```

Response:

```json
[
  {
    "id": "inv_123",
    "name": "Romaine Hearts (carton)",
    "uom": "ctn",
    "on_hand_qty": 4,
    "last_cost": 16.25,
    "match_score": 0.92
  }
]
```

---

## 🔐 Configuration

| Env Var           | Description                                          |
| ----------------- | ---------------------------------------------------- |
| `OPENAI_API_KEY`  | Needed only for `mode=semantic`.                     |
| `DB_PATH`         | Location of SQLite or DuckDB file storing inventory. |
| `ALLOWED_ORIGINS` | CORS origins.                                        |

---

## 🧪 Tests

```bash
pytest -v
```

---

## ☁️ Deploy to Azure

```bash
az functionapp create ...
func azure functionapp publish culvana-inventory-search
```

---

## 📝 License

MIT © Culvana 2025
