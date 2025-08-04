from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


def clear_all_data():
    """Clear all data from MongoDB collections."""

    print("🗑️ MongoDB Data Cleanup Tool")
    print("This will DELETE ALL data from your MongoDB collections!")

    # Connect to MongoDB
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.canadiantire_scraper

        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")

    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

    # Show current data counts
    print("\n📊 Current data in database:")
    try:
        products_count = db.products.count_documents({})
        reviews_count = db.reviews.count_documents({})
        prices_count = db.prices.count_documents({})

        print(f"   📦 Products: {products_count}")
        print(f"   💬 Reviews: {reviews_count}")
        print(f"   💰 Prices: {prices_count}")

        total_docs = products_count + reviews_count + prices_count
        print(f"   🎯 Total documents: {total_docs}")

        if total_docs == 0:
            print("✅ Database is already empty!")
            client.close()
            return True

    except Exception as e:
        print(f"❌ Error checking data counts: {e}")
        client.close()
        return False

    # Confirm deletion
    print(
        f"\n⚠️ WARNING: This will permanently delete {total_docs} documents!")
    response = input(
        "Are you sure you want to continue? Type 'DELETE' to confirm: ").strip()

    if response != 'DELETE':
        print("❌ Operation cancelled. Data preserved.")
        client.close()
        return False

    # Delete all data
    print("\n🗑️ Clearing collections...")

    try:
        # Clear products collection
        result = db.products.delete_many({})
        print(f"   📦 Products deleted: {result.deleted_count}")

        # Clear reviews collection
        result = db.reviews.delete_many({})
        print(f"   💬 Reviews deleted: {result.deleted_count}")

        # Clear prices collection
        result = db.prices.delete_many({})
        print(f"   💰 Prices deleted: {result.deleted_count}")

        print("✅ All data cleared successfully!")

    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        client.close()
        return False

    # Verify cleanup
    print("\n🔍 Verifying cleanup...")
    try:
        products_count = db.products.count_documents({})
        reviews_count = db.reviews.count_documents({})
        prices_count = db.prices.count_documents({})

        print(f"   📦 Products remaining: {products_count}")
        print(f"   💬 Reviews remaining: {reviews_count}")
        print(f"   💰 Prices remaining: {prices_count}")

        if products_count == 0 and reviews_count == 0 and prices_count == 0:
            print("✅ Database successfully cleared!")
            success = True
        else:
            print("⚠️ Some data may still remain")
            success = False

    except Exception as e:
        print(f"❌ Error verifying cleanup: {e}")
        success = False

    client.close()
    return success


def reset_collections():
    """Optionally recreate collections with indexes."""

    print("\n🔧 Do you want to recreate collections with indexes?")
    response = input(
        "This will ensure optimal performance (y/N): ").strip().lower()

    if response != 'y':
        return

    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.canadiantire_scraper

        print("🏗️ Recreating collections with indexes...")

        # Products indexes
        db.products.create_index("product_id", unique=True)
        db.products.create_index("category")
        db.products.create_index("brand")
        db.products.create_index("average_rating")
        print("   📦 Products indexes created")

        # Reviews indexes
        db.reviews.create_index("product_id")
        db.reviews.create_index("rating")
        db.reviews.create_index("source")
        db.reviews.create_index("submission_time")
        db.reviews.create_index(
            [("product_id", 1), ("review_id", 1)], unique=True)
        print("   💬 Reviews indexes created")

        # Prices indexes
        db.prices.create_index("product_id")
        db.prices.create_index([("product_id", 1), ("timestamp", -1)])
        db.prices.create_index("timestamp")
        db.prices.create_index("current_price")
        print("   💰 Prices indexes created")

        print("✅ Collections and indexes ready for optimal performance!")

        client.close()

    except Exception as e:
        print(f"❌ Error creating indexes: {e}")


if __name__ == "__main__":
    print("🚀 Starting MongoDB cleanup process...")

    success = clear_all_data()

    if success:
        reset_collections()

        print("\n🎉 MongoDB cleanup completed!")
        print("You can now run the migration script to reload your data:")
        print("   python load_data_to_mongodb.py")
    else:
        print("\n❌ Cleanup failed or was cancelled.")
