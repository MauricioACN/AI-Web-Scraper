"""
Data models for Canadian Tire Scraper

Contains data classes for products, reviews, and pricing information.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Review:
    """Represents a product review."""

    review_id: str
    author: str
    rating: int
    title: str
    text: str
    date: str
    source: str = "api"  # "api" or "selenium"
    verified_purchase: bool = False
    recommendation: Optional[bool] = None
    submission_time: Optional[str] = None
    comments: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert review to dictionary format."""
        return {
            "review_id": self.review_id,
            "author": self.author,
            "rating": self.rating,
            "title": self.title,
            "text": self.text,
            "date": self.date,
            "source": self.source,
            "verified_purchase": self.verified_purchase,
            "recommendation": self.recommendation,
            "submission_time": self.submission_time,
            "comments": self.comments
        }


@dataclass
class PriceInfo:
    """Represents product pricing information."""

    product_id: str
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    sale_price: Optional[float] = None
    currency: str = "CAD"
    in_stock: bool = False
    inventory_count: Optional[int] = None
    store_availability: Dict[str, bool] = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert price info to dictionary format."""
        return {
            "product_id": self.product_id,
            "current_price": self.current_price,
            "original_price": self.original_price,
            "sale_price": self.sale_price,
            "currency": self.currency,
            "in_stock": self.in_stock,
            "inventory_count": self.inventory_count,
            "store_availability": self.store_availability,
            "scraped_at": self.scraped_at
        }


@dataclass
class Product:
    """Represents a Canadian Tire product."""

    product_id: str
    name: str
    category: str = "Unknown"
    brand: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    ratings_count: Optional[int] = None
    price_info: Optional[PriceInfo] = None
    reviews: List[Review] = field(default_factory=list)
    highlights: Dict[str, Any] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_review(self, review: Review) -> None:
        """Add a review to the product."""
        self.reviews.append(review)

    def get_review_count(self) -> int:
        """Get the number of reviews."""
        return len(self.reviews)

    def get_average_rating(self) -> Optional[float]:
        """Calculate average rating from reviews."""
        if not self.reviews:
            return self.rating

        ratings = [r.rating for r in self.reviews if r.rating > 0]
        return sum(ratings) / len(ratings) if ratings else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary format."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "url": self.url,
            "image_url": self.image_url,
            "rating": self.rating,
            "ratings_count": self.ratings_count,
            "price_info": self.price_info.to_dict() if self.price_info else None,
            "reviews": [review.to_dict() for review in self.reviews],
            "highlights": self.highlights,
            "features": self.features,
            "review_count": self.get_review_count(),
            "calculated_average_rating": self.get_average_rating(),
            "scraped_at": self.scraped_at
        }
