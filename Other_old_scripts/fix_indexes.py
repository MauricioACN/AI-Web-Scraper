from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


def fix_indexes_properly():
    """Remove bad indexes and create proper review_id unique index."""

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper

    print("🔧 Fixing MongoDB indexes to use review_id properly...")

    try:
        # Show current indexes
        print("\n📋 Current indexes in reviews collection:")
        indexes = list(db.reviews.list_indexes())
        for idx in indexes:
            name = idx.get('name')
            key = idx.get('key', {})
            unique = idx.get('unique', False)
            print(f"   - {name}: {key} (unique: {unique})")

        # Remove problematic indexes
        problematic_indexes = [
            "product_id_1_author_1",  # The main culprit
            "product_id_1_author_1_rating_1_text_1"  # Any other compound indexes
        ]

        for index_name in problematic_indexes:
            try:
                db.reviews.drop_index(index_name)
                print(f"✅ Dropped problematic index: {index_name}")
            except Exception as e:
                print(
                    f"⚠️ Index {index_name} not found or already dropped: {e}")

        # Create the CORRECT unique index on review_id
        try:
            db.reviews.create_index("review_id", unique=True)
            print("✅ Created proper unique index on review_id")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("✅ Unique index on review_id already exists")
            else:
                print(f"⚠️ Could not create review_id index: {e}")

        # Create useful performance indexes (non-unique)
        performance_indexes = [
            ("product_id", "product_id"),
            ("rating", "rating"),
            ("source", "source"),
            ("submission_time", "submission_time"),
            ("author", "author")
        ]

        for field, name in performance_indexes:
            try:
                db.reviews.create_index(field)
                print(f"✅ Created performance index on {name}")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"✅ Index on {name} already exists")
                else:
                    print(f"⚠️ Could not create {name} index: {e}")

        # Show final indexes
        print(f"\n📋 Final indexes in reviews collection:")
        final_indexes = list(db.reviews.list_indexes())
        for idx in final_indexes:
            name = idx.get('name')
            key = idx.get('key', {})
            unique = idx.get('unique', False)
            print(f"   - {name}: {key} (unique: {unique})")

        print(f"\n🎉 Index optimization complete!")
        print("   ✅ review_id is now the unique identifier")
        print("   ✅ Multiple reviews per author/product are allowed")
        print("   ✅ Performance indexes created for common queries")

    except Exception as e:
        print(f"❌ Error fixing indexes: {e}")

    client.close()


def verify_index_fix():
    """Verify that the index fix worked by testing a potential duplicate scenario."""

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper

    print("\n🧪 Testing index fix with sample data...")

    try:
        # Try to insert two reviews from same author for same product (should work now)
        test_reviews = [
            {
                'product_id': 'TEST001P',
                'review_id': 'test_review_1',
                'author': 'TestUser',
                'rating': 5,
                'title': 'First Review',
                'text': 'This is the first review',
                'source': 'test'
            },
            {
                'product_id': 'TEST001P',
                'review_id': 'test_review_2',
                'author': 'TestUser',  # Same author
                'rating': 4,
                'title': 'Second Review',
                'text': 'This is the second review',
                'source': 'test'
            }
        ]

        # Clean up any existing test data
        db.reviews.delete_many({'product_id': 'TEST001P'})

        # Insert test reviews
        for review in test_reviews:
            result = db.reviews.insert_one(review)
            print(f"✅ Successfully inserted: {review['review_id']}")

        # Verify both reviews exist
        count = db.reviews.count_documents({'product_id': 'TEST001P'})
        print(f"✅ Found {count} reviews for TEST001P (should be 2)")

        # Clean up test data
        db.reviews.delete_many({'product_id': 'TEST001P'})
        print("✅ Test data cleaned up")

        if count == 2:
            print(
                "\n🎉 Index fix successful! Multiple reviews per author are now allowed.")
        else:
            print("\n⚠️ Index fix may not be complete. Check for remaining issues.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("   There may still be index conflicts")

    client.close()


if __name__ == "__main__":
    print("🚀 MongoDB Index Optimization Tool")
    print("This will fix the problematic indexes causing duplicate key errors")

    response = input(
        "\n⚠️ Proceed with index optimization? (y/N): ").strip().lower()

    if response == 'y':
        fix_indexes_properly()
        verify_index_fix()

        print("\n🎯 Next steps:")
        print("   1. Your indexes are now optimized")
        print("   2. Run: python clear_mongodb.py (optional - to start fresh)")
        print("   3. Run: python load_data_to_mongodb.py")
        print("   4. Multiple reviews per author are now allowed!")
    else:
        print("❌ Index optimization cancelled.")
