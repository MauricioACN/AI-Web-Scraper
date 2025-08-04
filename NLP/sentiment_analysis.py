from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import os
from textblob import TextBlob

# Load environment variables
load_dotenv()

# MongoDB connection string
uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Download required NLTK data for sentiment analysis


def ensure_nltk_data():
    """Ensure all required NLTK data is downloaded"""
    required_packages = ['punkt', 'punkt_tab', 'vader_lexicon']

    for package in required_packages:
        try:
            if package == 'vader_lexicon':
                nltk.data.find(f'vader_lexicon')
            else:
                nltk.data.find(f'tokenizers/{package}')
            print(f"✅ NLTK {package} already available")
        except LookupError:
            print(f"📥 Downloading NLTK {package}...")
            nltk.download(package, quiet=True)
            print(f"✅ NLTK {package} downloaded successfully")


# Download NLTK data
ensure_nltk_data()


class SentimentAnalyzer:
    def __init__(self):
        """Initialize with MongoDB connection and sentiment analyzer"""
        try:
            self.client = MongoClient(uri, server_api=ServerApi('1'))
            self.db = self.client.canadiantire_scraper
            self.nlp_collection = self.db.basic_nlp_processing

            # Initialize sentiment analyzers
            self.vader_analyzer = SentimentIntensityAnalyzer()

            # Test connection
            self.client.admin.command('ping')
            print("✅ Connected to MongoDB successfully")
            print("✅ Sentiment analyzers initialized")

        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise

    def analyze_sentiment(self, text):
        """Analyze sentiment using multiple methods and return consolidated result"""
        if not text or len(text.strip()) == 0:
            return {
                'sentiment': 'neutral',
                'confidence_score': 0.0,
                'vader_scores': {},
                'textblob_polarity': 0.0,
                'method': 'no_text'
            }

        try:
            # Method 1: VADER Sentiment
            vader_scores = self.vader_analyzer.polarity_scores(text)

            # Method 2: TextBlob Sentiment
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity

            # Determine overall sentiment and confidence
            # VADER compound score ranges from -1 to 1
            vader_compound = vader_scores['compound']

            # Combine both methods for better accuracy
            # Average the normalized scores
            combined_score = (vader_compound + textblob_polarity) / 2

            # Determine sentiment label
            if combined_score >= 0.1:
                sentiment = 'positive'
            elif combined_score <= -0.1:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'

            # Calculate confidence score based on agreement between methods
            # and absolute value of the combined score
            agreement_factor = 1 - abs(vader_compound - textblob_polarity) / 2
            intensity_factor = abs(combined_score)
            confidence_score = (agreement_factor * 0.6 +
                                intensity_factor * 0.4)
            # Clamp between 0 and 1
            confidence_score = min(max(confidence_score, 0.0), 1.0)

            return {
                'sentiment': sentiment,
                'confidence_score': round(confidence_score, 3),
                'combined_score': round(combined_score, 3),
                'vader_scores': {
                    'compound': round(vader_compound, 3),
                    'positive': round(vader_scores['pos'], 3),
                    'negative': round(vader_scores['neg'], 3),
                    'neutral': round(vader_scores['neu'], 3)
                },
                'textblob_polarity': round(textblob_polarity, 3),
                'method': 'vader_textblob_combined'
            }

        except Exception as e:
            print(f"❌ Error analyzing sentiment: {e}")
            return {
                'sentiment': 'neutral',
                'confidence_score': 0.0,
                'vader_scores': {},
                'textblob_polarity': 0.0,
                'method': 'error'
            }

    def add_sentiment_to_document(self, review_id):
        """Add sentiment analysis to existing NLP document"""
        try:
            # Find the existing NLP document
            document = self.nlp_collection.find_one({"review_id": review_id})

            if not document:
                print(f"❌ No NLP document found for review {review_id}")
                return False

            # Check if sentiment already exists
            if 'sentiment_analysis' in document:
                print(f"⏭️ Sentiment already exists for review {review_id}")
                return True

            # Get text to analyze
            text_to_analyze = document.get('text')

            # Perform sentiment analysis
            sentiment_result = self.analyze_sentiment(text_to_analyze)

            # Update document with sentiment analysis
            update_result = self.nlp_collection.update_one(
                {"review_id": review_id},
                {
                    "$set": {
                        "sentiment_analysis": sentiment_result,
                        "sentiment_updated_at": datetime.utcnow()
                    }
                }
            )

            if update_result.modified_count > 0:
                sentiment = sentiment_result['sentiment']
                confidence = sentiment_result['confidence_score']
                print(
                    f"✅ Added sentiment to {review_id}: {sentiment} (confidence: {confidence})")
                return True
            else:
                print(f"❌ Failed to update document for review {review_id}")
                return False

        except Exception as e:
            print(f"❌ Error processing sentiment for review {review_id}: {e}")
            return False

    def process_all_sentiments(self, limit=None):
        """Add sentiment analysis to all NLP documents that don't have it"""
        print("🎭 Starting sentiment analysis for all documents...")

        # Count documents
        total_docs = self.nlp_collection.count_documents({})
        docs_with_sentiment = self.nlp_collection.count_documents(
            {"sentiment_analysis": {"$exists": True}})
        remaining_docs = total_docs - docs_with_sentiment

        print(f"📊 Total NLP documents: {total_docs}")
        print(f"📊 Already have sentiment: {docs_with_sentiment}")
        print(f"📊 Need sentiment analysis: {remaining_docs}")

        if remaining_docs == 0:
            print("✅ All documents already have sentiment analysis!")
            return

        # Find documents without sentiment analysis
        query = {"sentiment_analysis": {"$exists": False}}
        cursor = self.nlp_collection.find(query, {"review_id": 1})

        if limit:
            cursor = cursor.limit(limit)
            print(f"🎯 Processing maximum {limit} documents...")

        processed_count = 0
        success_count = 0

        for doc in cursor:
            review_id = doc.get("review_id")
            if review_id:
                success = self.add_sentiment_to_document(review_id)
                if success:
                    success_count += 1
                processed_count += 1

                # Progress update every 50 documents
                if processed_count % 50 == 0:
                    print(
                        f"📈 Progress: {processed_count} processed, {success_count} successful...")

        print(f"\n🎉 Sentiment analysis complete!")
        print(f"   📝 Documents processed: {processed_count}")
        print(f"   ✅ Successful updates: {success_count}")
        print(f"   ❌ Failed updates: {processed_count - success_count}")

    def get_sentiment_stats(self):
        """Get sentiment analysis statistics"""
        pipeline = [
            {"$match": {"sentiment_analysis": {"$exists": True}}},
            {
                "$group": {
                    "_id": "$sentiment_analysis.sentiment",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$sentiment_analysis.confidence_score"},
                    "avg_combined_score": {"$avg": "$sentiment_analysis.combined_score"}
                }
            },
            {"$sort": {"count": -1}}
        ]

        sentiment_breakdown = list(self.nlp_collection.aggregate(pipeline))

        # Overall stats
        total_with_sentiment = self.nlp_collection.count_documents(
            {"sentiment_analysis": {"$exists": True}})
        total_docs = self.nlp_collection.count_documents({})

        return {
            "total_documents": total_docs,
            "documents_with_sentiment": total_with_sentiment,
            "coverage_percentage": round((total_with_sentiment / total_docs * 100), 2) if total_docs > 0 else 0,
            "sentiment_breakdown": sentiment_breakdown
        }

    def process_sample_sentiments(self, limit=5):
        """Process sentiment for a few sample documents"""
        print(f"🧪 Processing sentiment for {limit} sample documents...")

        # Get sample documents without sentiment
        docs = list(self.nlp_collection.find(
            {"sentiment_analysis": {"$exists": False}},
            {"review_id": 1, "original_text": 1}
        ).limit(limit))

        if not docs:
            print("❌ No documents without sentiment found")
            return

        for doc in docs:
            review_id = doc.get("review_id")
            text_preview = doc.get("original_text", "")[:100] + "..." if len(
                doc.get("original_text", "")) > 100 else doc.get("original_text", "")

            print(f"\n🔍 Processing review {review_id}")
            print(f"   Text preview: {text_preview}")

            success = self.add_sentiment_to_document(review_id)
            if not success:
                print(f"   ❌ Failed to process {review_id}")

    def close_connection(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            print("🔌 MongoDB connection closed")


# Example usage
if __name__ == "__main__":
    print("🎭 Starting Sentiment Analysis Script")

    try:
        analyzer = SentimentAnalyzer()

        # # Process sample documents first
        # analyzer.process_sample_sentiments(limit=3)

        # # Show current statistics
        # print("\n📊 Sentiment Analysis Statistics:")
        # stats = analyzer.get_sentiment_stats()

        # print(f"   Total documents: {stats['total_documents']}")
        # print(
        #     f"   Documents with sentiment: {stats['documents_with_sentiment']}")
        # print(f"   Coverage: {stats['coverage_percentage']}%")

        # if stats['sentiment_breakdown']:
        #     print("\n🎭 Sentiment Breakdown:")
        #     for sentiment_data in stats['sentiment_breakdown']:
        #         sentiment = sentiment_data['_id']
        #         count = sentiment_data['count']
        #         avg_confidence = sentiment_data.get('avg_confidence', 0)
        #         print(
        #             f"   {sentiment}: {count} reviews (avg confidence: {avg_confidence:.3f})")

        # Uncomment to process all documents
        print("\n🚀 Processing all documents...")
        analyzer.process_all_sentiments()

        analyzer.close_connection()

    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
