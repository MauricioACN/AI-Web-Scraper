import nltk
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MongoDB connection string
uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


# Download required NLTK data (updated for newer NLTK versions)
def ensure_nltk_data():
    """Ensure all required NLTK data is downloaded"""
    required_packages = ['punkt', 'punkt_tab']

    for package in required_packages:
        try:
            nltk.data.find(f'tokenizers/{package}')
            print(f"✅ NLTK {package} already available")
        except LookupError:
            print(f"📥 Downloading NLTK {package}...")
            nltk.download(package, quiet=True)
            print(f"✅ NLTK {package} downloaded successfully")


# Download NLTK data
ensure_nltk_data()


class SimpleNLP:
    def __init__(self):
        """Initialize with MongoDB connection"""
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client.canadiantire_scraper
        self.nlp_collection = self.db.basic_nlp_processing
        self.review_collection = self.db.reviews

    def process_text(self, text, review_id, product_id, title, concatenate_text=False):
        """Process text with sentence segmentation and word tokenization"""

        if concatenate_text:
            # Concatenate text and title in a single string
            text = f"{title} {text}" if title else text

        # Sentence segmentation
        sentences = nltk.sent_tokenize(text)

        # Word tokenization
        words = nltk.word_tokenize(text)

        # Create document to store
        document = {
            "product_id": product_id,
            "review_id": review_id,
            "title": title,
            "text": text,
            "sentences": sentences,
            "words": words,
            "created_at": datetime.now()
        }

        # Store in database
        result = self.nlp_collection.insert_one(document)

        print(f"Text processed and stored with ID: {result.inserted_id}")
        print(f"Found {len(sentences)} sentences and {len(words)} words")

        return document

    def get_all_data(self):
        """Retrieve all processed data"""
        return list(self.nlp_collection.find())


# Example usage
if __name__ == "__main__":
    nlp = SimpleNLP()

    reviews = nlp.review_collection.find()
    review_count = 0

    for review in reviews:
        review_id = review.get("review_id", "unknown")
        product_id = review.get("product_id", "unknown")
        title = review.get("title", "")
        text = review.get("text", "")

        # Process and store each review
        nlp.process_text(text, review_id, product_id,
                         title, concatenate_text=True)
        review_count += 1

    if review_count == 0:
        print("No reviews found in the database.")
    else:
        print(f"\nProcessed {review_count} reviews")

        # Show all stored data
        data = nlp.get_all_data()
        print(f"Total documents in database: {len(data)}")
