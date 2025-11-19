"""
Database Schemas

Define MongoDB collection schemas for the BBQ price finder app.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- Cut -> "cut"
- Price -> "price"
- Recipe -> "recipe"
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class Cut(BaseModel):
    """
    Meat cuts available in Chilean supermarkets
    Collection: "cut"
    """
    name: str = Field(..., description="Cut name, e.g., 'Lomo Vetado'")
    description: Optional[str] = Field(None, description="Short description of the cut")
    country: str = Field("Chile", description="Country context for this cut")
    image: Optional[str] = Field(None, description="Optional image URL")
    tags: Optional[List[str]] = Field(default=None, description="Search tags")

class Price(BaseModel):
    """
    Price per supermarket for a given cut
    Collection: "price"
    """
    cut_id: str = Field(..., description="Related cut id (stringified ObjectId)")
    supermarket: str = Field(..., description="Lider | Jumbo | Tottus | Unimarc | Santa Isabel | Otros")
    price_per_kg: float = Field(..., ge=0, description="Price per kg in CLP")
    source_url: Optional[str] = Field(None, description="Where the price was fetched from (optional)")

class Recipe(BaseModel):
    """
    Basic grill recipes associated to a cut
    Collection: "recipe"
    """
    cut_id: str = Field(..., description="Related cut id (stringified ObjectId)")
    title: str = Field(..., description="Recipe title")
    prep: Optional[str] = Field(None, description="Preparation / trimming notes")
    cook_time_min: Optional[int] = Field(None, ge=0, description="Estimated total cooking time in minutes")
    grill_temp: Optional[str] = Field(None, description="Fire/grill guidance")
    steps: Optional[List[str]] = Field(default=None, description="Simple step list")
