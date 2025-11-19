import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="BBQ Chile - Price & Grill Helper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
@app.get("/")
def read_root():
    return {"message": "BBQ Chile API Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Schemas (light response models)
class CutOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    country: str
    image: Optional[str] = None
    tags: Optional[List[str]] = None

class PriceOut(BaseModel):
    supermarket: str
    price_per_kg: float
    source_url: Optional[str] = None

class RecipeOut(BaseModel):
    title: str
    prep: Optional[str] = None
    cook_time_min: Optional[int] = None
    grill_temp: Optional[str] = None
    steps: Optional[List[str]] = None

# Helpers

def oid_str(oid: Any) -> str:
    try:
        return str(oid)
    except Exception:
        return oid


def to_cut_out(doc: Dict[str, Any]) -> CutOut:
    return CutOut(
        id=oid_str(doc.get("_id")),
        name=doc.get("name"),
        description=doc.get("description"),
        country=doc.get("country", "Chile"),
        image=doc.get("image"),
        tags=doc.get("tags"),
    )


# Seed initial cuts/recipes/prices if empty (light demo data)
SEED_CUTS = [
    {
        "name": "Lomo Vetado",
        "description": "Corte marmoleado, ideal para asar a fuego medio-alto",
        "tags": ["asado", "vetado", "lomo"],
        "image": None,
    },
    {
        "name": "Asado de Tira",
        "description": "Tiras de costilla, perfectas para cocción lenta",
        "tags": ["costilla", "tira", "lento"],
        "image": None,
    },
    {
        "name": "Punta Picana",
        "description": "Corte con capa de grasa, jugoso y sabroso",
        "tags": ["picana", "punta", "jugoso"],
        "image": None,
    },
]

SEED_RECIPES: Dict[str, List[Dict[str, Any]]] = {
    "Lomo Vetado": [
        {
            "title": "Lomo vetado a la parrilla",
            "prep": "Secar bien y salar 40 min antes."
                    "Marcar por todos los lados.",
            "cook_time_min": 18,
            "grill_temp": "Fuego medio-alto",
            "steps": [
                "Sacar del refrigerador 40 min antes",
                "Sellar 3-4 min por lado",
                "Llevar a zona media hasta llegar a punto",
                "Reposar 5-8 min y cortar contra la fibra",
            ],
        }
    ],
    "Asado de Tira": [
        {
            "title": "Tira de asado lenta",
            "prep": "Retirar exceso de membranas; sal gruesa",
            "cook_time_min": 120,
            "grill_temp": "Fuego medio-bajo, con tapa",
            "steps": [
                "Dorar a fuego alto",
                "Cocinar indirecto 1.5-2 h a 140-160°C",
                "Pincelar con mezcla de ajo y aceite",
            ],
        }
    ],
    "Punta Picana": [
        {
            "title": "Picana clásica",
            "prep": "Marcar la grasa en rombos, sal y pimienta",
            "cook_time_min": 60,
            "grill_temp": "Iniciar grasa hacia abajo, luego medio",
            "steps": [
                "Dorar del lado de la grasa",
                "Voltear y cocinar hasta 52-55°C internos",
                "Reposar 10 min",
            ],
        }
    ],
}

SEED_PRICES: Dict[str, List[Dict[str, Any]]] = {
    "Lomo Vetado": [
        {"supermarket": "Lider", "price_per_kg": 10490.0},
        {"supermarket": "Jumbo", "price_per_kg": 10990.0},
        {"supermarket": "Tottus", "price_per_kg": 9990.0},
    ],
    "Asado de Tira": [
        {"supermarket": "Lider", "price_per_kg": 8990.0},
        {"supermarket": "Unimarc", "price_per_kg": 9490.0},
    ],
    "Punta Picana": [
        {"supermarket": "Jumbo", "price_per_kg": 11990.0},
        {"supermarket": "Lider", "price_per_kg": 11490.0},
    ],
}


def seed_if_needed():
    try:
        if db is None:
            return
        if db["cut"].count_documents({}) == 0:
            # Insert cuts
            name_to_id: Dict[str, ObjectId] = {}
            for cut in SEED_CUTS:
                new_id = db["cut"].insert_one({**cut}).inserted_id
                name_to_id[cut["name"]] = new_id
            # Insert recipes
            for name, recs in SEED_RECIPES.items():
                cid = name_to_id.get(name)
                if not cid:
                    continue
                for r in recs:
                    db["recipe"].insert_one({"cut_id": str(cid), **r})
            # Insert prices
            for name, prices in SEED_PRICES.items():
                cid = name_to_id.get(name)
                if not cid:
                    continue
                for p in prices:
                    db["price"].insert_one({"cut_id": str(cid), **p})
    except Exception:
        # Silent fail if seeding not possible
        pass

seed_if_needed()

# Endpoints
@app.get("/api/cuts", response_model=List[CutOut])
def list_cuts(q: Optional[str] = Query(default=None, description="Search query")):
    """Search or list cuts"""
    if db is None:
        # Return seed data without DB
        items = SEED_CUTS
        if q:
            ql = q.lower()
            items = [c for c in items if ql in c["name"].lower() or any(ql in t for t in (c.get("tags") or []))]
        return [
            CutOut(id=str(i), name=c["name"], description=c.get("description"), country="Chile", image=c.get("image"), tags=c.get("tags"))
            for i, c in enumerate(items)
        ]
    # With DB
    filter_q = {}
    if q:
        filter_q["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}},
        ]
    docs = list(db["cut"].find(filter_q))
    return [to_cut_out(d) for d in docs]


@app.get("/api/cuts/{cut_id}/prices", response_model=List[PriceOut])
def get_prices(cut_id: str):
    """Get prices for a cut, sorted asc"""
    if db is None:
        # Map from seed
        name = None
        # Find name by pseudo id
        try:
            idx = int(cut_id)
            name = (SEED_CUTS[idx]["name"]) if 0 <= idx < len(SEED_CUTS) else None
        except Exception:
            name = None
        prices = SEED_PRICES.get(name, [])
        return sorted([PriceOut(**p) for p in prices], key=lambda x: x.price_per_kg)
    prices = list(db["price"].find({"cut_id": cut_id}))
    prices_out = [PriceOut(supermarket=p.get("supermarket"), price_per_kg=p.get("price_per_kg", 0.0), source_url=p.get("source_url")) for p in prices]
    prices_out.sort(key=lambda x: x.price_per_kg)
    return prices_out


@app.get("/api/cuts/{cut_id}/recipes", response_model=List[RecipeOut])
def get_recipes(cut_id: str):
    if db is None:
        # Fallback to seed by name
        try:
            idx = int(cut_id)
            name = (SEED_CUTS[idx]["name"]) if 0 <= idx < len(SEED_CUTS) else None
        except Exception:
            name = None
        recs = SEED_RECIPES.get(name, [])
        return [RecipeOut(**r) for r in recs]
    recs = list(db["recipe"].find({"cut_id": cut_id}))
    return [RecipeOut(title=r.get("title"), prep=r.get("prep"), cook_time_min=r.get("cook_time_min"), grill_temp=r.get("grill_temp"), steps=r.get("steps")) for r in recs]


# Calculators
class CalcInput(BaseModel):
    people: int
    adults_ratio: Optional[float] = 1.0  # 1.0 means all adults
    meat_per_adult_g: Optional[int] = 400  # grams
    meat_per_kid_g: Optional[int] = 200    # grams
    drinks_l_per_person: Optional[float] = 1.0
    charcoal_kg_per_kg_meat: Optional[float] = 0.8

class CalcResult(BaseModel):
    total_meat_kg: float
    suggested_charcoal_kg: float
    suggested_drinks_l: float

@app.post("/api/calc/quantities", response_model=CalcResult)
def calc_quantities(payload: CalcInput):
    if payload.people <= 0:
        raise HTTPException(status_code=400, detail="people must be > 0")
    adults = int(round(payload.people * (payload.adults_ratio or 1.0)))
    kids = payload.people - adults
    meat_total_g = adults * (payload.meat_per_adult_g or 400) + kids * (payload.meat_per_kid_g or 200)
    meat_total_kg = round(meat_total_g / 1000.0, 2)
    charcoal = round(meat_total_kg * (payload.charcoal_kg_per_kg_meat or 0.8), 2)
    drinks = round(payload.people * (payload.drinks_l_per_person or 1.0), 2)
    return CalcResult(total_meat_kg=meat_total_kg, suggested_charcoal_kg=charcoal, suggested_drinks_l=drinks)

class SplitInput(BaseModel):
    people: int
    amounts: List[float]
    rounding: Optional[int] = 0

class SplitResult(BaseModel):
    total: float
    per_person: float
    shares: List[float]

@app.post("/api/calc/split", response_model=SplitResult)
def calc_split(payload: SplitInput):
    if payload.people <= 0:
        raise HTTPException(status_code=400, detail="people must be > 0")
    if not payload.amounts or any(a < 0 for a in payload.amounts):
        raise HTTPException(status_code=400, detail="amounts must be non-empty and non-negative")
    total = sum(payload.amounts)
    per = total / payload.people
    r = payload.rounding or 0
    if r > 0:
        per = round(per, r)
    shares = [per for _ in range(payload.people)]
    return SplitResult(total=round(total, 2), per_person=per, shares=shares)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
