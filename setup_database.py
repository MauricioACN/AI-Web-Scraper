from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


def create_collections_with_validation():
    """Create MongoDB collections with schema validation."""

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper

    print("🏗️ Creating collections with schema validation...")

    # 1. Products collection with validation
    try:
        db.create_collection("products", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["product_id", "name"],
                "properties": {
                    "product_id": {"bsonType": "string"},
                    "name": {"bsonType": "string"},
                    "category": {"bsonType": "string"},
                    "url": {"bsonType": "string"},
                    "brand": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
        print("✅ Products collection created with validation")
    except Exception as e:
        print(f"   Products collection already exists or error: {e}")

    # 2. Reviews collection with validation
    try:
        db.create_collection("reviews", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["product_id", "author", "rating"],
                "properties": {
                    "product_id": {"bsonType": "string"},
                    "review_id": {"bsonType": "string"},
                    "author": {"bsonType": "string"},
                    "rating": {"bsonType": "int", "minimum": 1, "maximum": 5},
                    "title": {"bsonType": "string"},
                    "text": {"bsonType": "string"},
                    "date": {"bsonType": "string"},
                    "source": {"enum": ["api", "selenium"]},
                    "verified_purchase": {"bsonType": "bool"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
        print("✅ Reviews collection created with validation")
    except Exception as e:
        print(f"   Reviews collection already exists or error: {e}")

    # 3. Prices collection with validation
    try:
        db.create_collection("prices", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["product_id", "current_price", "timestamp"],
                "properties": {
                    "product_id": {"bsonType": "string"},
                    "current_price": {"bsonType": "number"},
                    "currency": {"bsonType": "string"},
                    "stock_status": {"bsonType": "string"},
                    "availability": {"bsonType": "number"},
                    "store_pickup": {"bsonType": "bool"},
                    "online_available": {"bsonType": "bool"},
                    "store_id": {"bsonType": "string"},
                    "timestamp": {"bsonType": "date"}
                }
            }
        })
        print("✅ Prices collection created with validation")
    except Exception as e:
        print(f"   Prices collection already exists or error: {e}")

    # 4. Create indexes
    print("\n🔍 Creating performance indexes...")

    # Products indexes
    db.products.create_index("product_id", unique=True)
    db.products.create_index("category")
    db.products.create_index("brand")

    # Reviews indexes
    db.reviews.create_index("product_id")
    db.reviews.create_index("rating")
    db.reviews.create_index("source")
    db.reviews.create_index([("product_id", 1), ("author", 1)], unique=True)

    # Prices indexes
    db.prices.create_index("product_id")
    db.prices.create_index([("product_id", 1), ("timestamp", -1)])
    db.prices.create_index("timestamp")

    print("✅ All indexes created")

    # 5. Show collections
    print(f"\n📋 Collections created:")
    for collection_name in db.list_collection_names():
        indexes = list(db[collection_name].list_indexes())
        print(f"   - {collection_name}: {len(indexes)} indexes")

    client.close()
    print("\n🎉 Database structure ready!")


if __name__ == "__main__":
    create_collections_with_validation()
