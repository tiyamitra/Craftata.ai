"""
AI service layer for Craftata.ai.

These functions provide working fallback logic without requiring
an external AI API. They can later be replaced with OpenAI,
Gemini, Claude, or another AI provider.
"""

from typing import Optional


def extract_product_info(
    image_bytes: Optional[bytes] = None,
    voice_text: Optional[str] = None,
    hint_category: Optional[str] = None,
):
    text = (voice_text or "").strip()

    category = hint_category or _guess_category(text)

    name = _guess_name(text, category)

    description = (
        text
        if text
        else f"A handcrafted {category.lower()} product created by an artisan."
    )

    tags = _build_tags(name, category, text)

    return {
        "name": name,
        "category": category,
        "description": description,
        "tags": tags,
    }


def translate_text(text: str, target_languages: list[str]):
    """
    Fallback translation response.

    Replace this function with a real AI translation provider
    when an API key is configured.
    """
    return {
        language: text
        for language in target_languages
    }


def recommend_price(
    cost_price: float,
    category: Optional[str] = None,
    material_quality: str = "standard",
):
    quality_multipliers = {
        "basic": 1.5,
        "standard": 2.0,
        "premium": 2.75,
        "luxury": 3.5,
    }

    multiplier = quality_multipliers.get(
        material_quality.lower(),
        2.0,
    )

    suggested_price = round(cost_price * multiplier, 2)

    category_text = category or "product"

    return {
        "suggested_price": suggested_price,
        "reasoning": (
            f"Recommended price uses a {multiplier}x markup "
            f"for a {material_quality.lower()} quality {category_text}."
        ),
    }


def match_markets(
    category: Optional[str],
    suggested_price: Optional[float],
):
    category_text = (category or "").lower()

    markets = ["local_market", "online_craft_store"]

    if any(
        keyword in category_text
        for keyword in ["jewelry", "textile", "handicraft", "art", "decor"]
    ):
        markets.append("export_market")

    if suggested_price is not None and suggested_price >= 5000:
        markets.append("premium_buyer")

    return {
        "suitable_markets": list(dict.fromkeys(markets)),
        "reasoning": (
            "Market recommendations are based on product category "
            "and suggested price."
        ),
    }


def _guess_category(text: str) -> str:
    text = text.lower()

    categories = {
        "jewelry": ["necklace", "ring", "earring", "bracelet"],
        "textile": ["saree", "fabric", "scarf", "cloth"],
        "pottery": ["pot", "vase", "ceramic"],
        "woodwork": ["wood", "wooden", "carving"],
        "home decor": ["decor", "decoration", "wall art"],
    }

    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "Handicraft"


def _guess_name(text: str, category: str) -> str:
    if text:
        words = text.split()
        return " ".join(words[:6]).strip().title()

    return f"Handcrafted {category.title()}"


def _build_tags(name: str, category: str, text: str):
    tags = {
        "handmade",
        "artisan",
        category.lower(),
    }

    for word in (name + " " + text).lower().split():
        clean = "".join(
            character
            for character in word
            if character.isalnum()
        )

        if len(clean) >= 4:
            tags.add(clean)

    return sorted(tags)[:10]
