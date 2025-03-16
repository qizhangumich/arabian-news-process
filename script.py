import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import json
import dateutil.parser
import os
import pytz
from openai import OpenAI  # Updated import for newer OpenAI client

# Constants
FIREBASE_COLLECTION = 'arabian_news_articles'  # Updated to correct collection name
PROCESSED_COLLECTION = 'processed_arabian_news_articles'  # Collection for processed articles
UAE_TIMEZONE = pytz.timezone('Asia/Dubai')  # UAE timezone

# Initialize the OpenAI client with the API key from environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_yesterday_date_range():
    """Get the date range for yesterday in UAE timezone."""
    # Get current date in UAE timezone
    now = datetime.now(UAE_TIMEZONE)
    
    # Calculate yesterday's start and end (in UAE timezone)
    yesterday = now - timedelta(days=1)
    yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=UAE_TIMEZONE)
    yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, tzinfo=UAE_TIMEZONE)
    
    return yesterday_start, yesterday_end

def initialize_firebase():
    """Initialize Firebase with service account credentials."""
    # Path to service account key file
    cred_path = "./firebase_key.json"
    
    # Initialize Firebase
    try:
        # Try to read from file first
        if os.path.exists(cred_path):
            try:
                # Check if file is valid JSON first
                with open(cred_path, 'r', encoding='utf-8-sig') as f:
                    try:
                        json_content = json.load(f)
                        print(f"✅ Firebase key file is valid JSON")
                    except json.JSONDecodeError as json_err:
                        print(f"⚠️ Firebase key file contains invalid JSON: {json_err}")
                        # Try to diagnose the issue by printing part of the file (without sensitive info)
                        with open(cred_path, 'r', encoding='utf-8-sig') as debug_f:
                            first_lines = debug_f.readlines()[:5]  # Just read the first few lines
                            print(f"First few lines of the file structure (sanitized):")
                            for i, line in enumerate(first_lines):
                                if i == 0:  # First line is usually just the opening brace
                                    print(line.strip())
                                else:
                                    # Print structure without actual values
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        print(f"{parts[0]}: [...]")
                                    else:
                                        print(line.strip())
                        raise
                
                # Now proceed with the credential
                cred = credentials.Certificate(cred_path)
            except Exception as e:
                print(f"Error reading Firebase key file: {e}")
                raise
        # If file doesn't exist, try to use environment variable
        else:
            # Check if the environment variable exists (for GitHub Actions)
            firebase_key_base64 = os.environ.get("FIREBASE_KEY_JSON")
            if firebase_key_base64:
                # Write the key to a temporary file
                with open(cred_path, 'w', encoding='utf-8-sig') as f:
                    f.write(firebase_key_base64)
                
                # Verify the file is valid JSON before proceeding
                try:
                    with open(cred_path, 'r', encoding='utf-8-sig') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error: Firebase key from environment variable is not valid JSON: {e}")
                    raise
                
                cred = credentials.Certificate(cred_path)
            else:
                raise ValueError("Firebase credentials not found. Please provide a credentials file or set the FIREBASE_KEY_JSON environment variable.")
                
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise

def fetch_yesterday_news(db):
    """Fetch news articles published yesterday."""
    yesterday_start, yesterday_end = get_yesterday_date_range()
    
    # Convert to timestamp format Firebase uses (ISO 8601 string)
    yesterday_start_str = yesterday_start.isoformat()
    yesterday_end_str = yesterday_end.isoformat()
    
    print(f"Querying for news between {yesterday_start_str} and {yesterday_end_str}")
    
    # Query Firestore for news published yesterday
    news_ref = db.collection(FIREBASE_COLLECTION)
    # Using where() method for compatibility
    query = news_ref.where('date_published', '>=', yesterday_start_str).where('date_published', '<=', yesterday_end_str)
    
    # Execute query and get results
    news_docs = query.stream()
    
    # Convert to list of dictionaries
    news_items = []
    for doc in news_docs:
        news_data = doc.to_dict()
        news_data['id'] = doc.id
        news_items.append(news_data)
    
    # Sort news items by date_published
    news_items.sort(key=lambda x: x.get('date_published', ''), reverse=True)
    
    return news_items

def rate_news(news_article):
    """Rate a news article for business importance using OpenAI (1 is most important)."""
    try:
        # Using the newer OpenAI client API format
        print("Sending request to OpenAI for business importance rating...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a business analyst rating news articles for business importance. Rank articles from 1 to 10, where 1 is MOST important and 10 is LEAST important. The most impactful news that business leaders must see should be ranked 1."},
                {"role": "user", "content": f"Rate the following news article for business importance on a scale of 1 to 10 (where 1 is MOST important and 10 is LEAST important):\n\n{news_article}"}
            ],
            max_tokens=10
        )
        rating = response.choices[0].message.content.strip()
        print(f"Received importance rating from OpenAI: {rating}")
        return rating
    except Exception as e:
        print(f"Error rating news: {str(e)}")
        # Try a simpler approach as fallback
        try:
            print("Trying fallback approach for rating...")
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=f"Rate the following news article for business importance on a scale of 1 to 10 (where 1 is MOST important and 10 is LEAST important):\n\n{news_article}",
                max_tokens=10
            )
            rating = response.choices[0].text.strip()
            print(f"Received importance rating from fallback approach: {rating}")
            return rating
        except Exception as fallback_e:
            print(f"Fallback rating also failed: {str(fallback_e)}")
            return "Error: Could not rate article"

def summarize_news(news_article):
    """Summarize a news article using OpenAI."""
    try:
        # Using the newer OpenAI client API format
        print("Sending request to OpenAI for summary...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert summarizer who creates concise, informative summaries."},
                {"role": "user", "content": f"Summarize the following news article in about 3 sentences:\n\n{news_article}"}
            ],
            max_tokens=150
        )
        summary = response.choices[0].message.content.strip()
        print(f"Received summary from OpenAI (length: {len(summary)} chars)")
        return summary
    except Exception as e:
        print(f"Error summarizing news: {str(e)}")
        # Try a simpler approach as fallback
        try:
            print("Trying fallback approach for summarization...")
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=f"Summarize the following news article in about 3 sentences:\n\n{news_article}",
                max_tokens=150
            )
            summary = response.choices[0].text.strip()
            print(f"Received summary from fallback approach (length: {len(summary)} chars)")
            return summary
        except Exception as fallback_e:
            print(f"Fallback summarization also failed: {str(fallback_e)}")
            return "Error: Could not summarize article"

def translate_to_chinese(text):
    """Translate text to Chinese using OpenAI."""
    if not text or text.startswith("Error:"):
        return "Error: No text to translate"
    
    try:
        print("Sending request to OpenAI for Chinese translation...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following text to Simplified Chinese (Mandarin)."},
                {"role": "user", "content": f"Please translate this text to Chinese:\n\n{text}"}
            ],
            max_tokens=300
        )
        translation = response.choices[0].message.content.strip()
        print(f"Received Chinese translation (length: {len(translation)} chars)")
        return translation
    except Exception as e:
        print(f"Error translating to Chinese: {str(e)}")
        # Try a simpler approach as fallback
        try:
            print("Trying fallback approach for translation...")
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=f"Translate this text to Chinese:\n\n{text}",
                max_tokens=300
            )
            translation = response.choices[0].text.strip()
            print(f"Received translation from fallback approach (length: {len(translation)} chars)")
            return translation
        except Exception as fallback_e:
            print(f"Fallback translation also failed: {str(fallback_e)}")
            return "Error: Could not translate to Chinese"

def get_content_field(news_item):
    """Extract content from a news item, handling different field names."""
    if 'content' in news_item:
        return news_item['content']
    
    # Try to find alternative content fields
    content_candidates = ['text', 'body', 'article', 'description']
    for field in content_candidates:
        if field in news_item:
            print(f"Using '{field}' instead of 'content'")
            return news_item[field]
    
    print(f"No suitable content field found. Available fields: {list(news_item.keys())}")
    return None

def process_news_articles(news_items):
    """Process news articles by rating, summarizing, and translating them."""
    processed_news = []
    
    for i, news in enumerate(news_items):
        print(f"\n--- Processing article {i+1}/{len(news_items)}: {news.get('title', 'No title')} ---")
        
        # Get the content to process
        content = get_content_field(news)
        if not content:
            print(f"Skipping article {i+1} due to missing content")
            continue
        
        # Check if the content is too short
        if len(content) < 50:
            print(f"Warning: Content seems very short ({len(content)} chars). This might not be a full article.")
        
        # Create a copy and add our analysis
        article_copy = news.copy()
        
        # Truncate content if it's too long (to avoid API limits)
        processed_content = content[:3000] if content and len(content) > 3000 else content
        
        # Add a note if content was truncated
        if content and len(content) > 3000:
            print(f"Content was truncated from {len(content)} characters to 3000 characters")
        
        # Process the article
        try:
            # Get business importance rating (1 is most important)
            article_copy['business_importance'] = rate_news(processed_content)
            
            # Get English summary
            english_summary = summarize_news(processed_content)
            article_copy['summary'] = english_summary
            
            # Translate the summary to Chinese
            print("Translating summary to Chinese...")
            chinese_summary = translate_to_chinese(english_summary)
            article_copy['summary_chinese'] = chinese_summary
            
            # Also translate the title if available
            if 'title' in article_copy and article_copy['title'] and article_copy['title'] != 'No title':
                print("Translating title to Chinese...")
                article_copy['title_chinese'] = translate_to_chinese(article_copy['title'])
            
            processed_news.append(article_copy)
        except Exception as e:
            print(f"Failed to process article: {e}")
            continue
    
    return processed_news

def delete_historical_data(db):
    """Delete all existing data in the processed news collection."""
    print(f"\nDeleting all historical data from '{PROCESSED_COLLECTION}'...")
    
    processed_ref = db.collection(PROCESSED_COLLECTION)
    
    # Get all documents in the collection
    docs = processed_ref.stream()
    
    # Delete each document
    delete_count = 0
    for doc in docs:
        doc.reference.delete()
        delete_count += 1
    
    print(f"✅ Successfully deleted {delete_count} historical news articles.")
    return delete_count

def save_processed_news_to_firebase(db, processed_news):
    """Save processed news articles with ratings, summaries and translations to Firebase."""
    if not processed_news:
        print("No processed news to save to Firebase.")
        return
    
    # Get reference to the processed news collection
    processed_ref = db.collection(PROCESSED_COLLECTION)
    
    # Current timestamp in UAE timezone
    now = datetime.now(UAE_TIMEZONE)
    timestamp = now.isoformat()
    
    print(f"\nSaving {len(processed_news)} processed articles to Firebase collection: '{PROCESSED_COLLECTION}'")
    
    success_count = 0
    for rank, article in enumerate(processed_news, start=1):
        try:
            # Create a document with the same ID as the original article
            original_id = article.get('id', '')
            doc_id = f"{original_id}_{timestamp}" if original_id else None
            
            # Prepare the data to save
            save_data = {
                'original_article_id': original_id,
                'title': article.get('title', 'No title'),
                'date_published': article.get('date_published', ''),
                'business_importance': article.get('business_importance', 'N/A'),
                'summary': article.get('summary', 'N/A'),
                'processed_at': timestamp,
                'source': article.get('article_url', article.get('url', 'Unknown')),
                'rank': rank  # Added rank field based on sorted order
            }
            
            # Add Chinese translations
            if 'summary_chinese' in article:
                save_data['summary_chinese'] = article['summary_chinese']
            
            if 'title_chinese' in article:
                save_data['title_chinese'] = article['title_chinese']
            
            # Add optional fields if they exist in the original article
            for field in ['author', 'category', 'tags']:
                if field in article:
                    save_data[field] = article[field]
            
            # Save to Firebase
            if doc_id:
                processed_ref.document(doc_id).set(save_data)
            else:
                processed_ref.add(save_data)
                
            success_count += 1
            print(f"✅ Saved article: {article.get('title', 'No title')[:50]}...")
            
        except Exception as e:
            print(f"❌ Failed to save article to Firebase: {e}")
    
    print(f"Successfully saved {success_count} out of {len(processed_news)} articles to Firebase.")
    return success_count

def main():
    # Initialize Firebase using the robust method
    db = initialize_firebase()
    
    # Check available collections
    collections = db.collections()
    print("Available collections in Firestore:")
    for collection in collections:
        print(f"- {collection.id}")
    
    # Fetch yesterday's news
    news_items = fetch_yesterday_news(db)
    print(f"\nFound {len(news_items)} news articles from yesterday")
    
    # If no yesterday's news, try getting some recent articles as fallback
    if not news_items:
        print("No articles from yesterday found. Fetching most recent articles as fallback...")
        news_ref = db.collection(FIREBASE_COLLECTION)
        
        # Try to get any articles without date filtering
        try:
            recent_docs = news_ref.order_by('date_published', direction=firestore.Query.DESCENDING).limit(10).stream()
            
            for doc in recent_docs:
                news_data = doc.to_dict()
                news_data['id'] = doc.id
                # Print some diagnostic info about the article
                print(f"\nFound article:")
                print(f"ID: {doc.id}")
                print(f"Fields: {list(news_data.keys())}")
                if 'date_published' in news_data:
                    print(f"Date: {news_data['date_published']}")
                news_items.append(news_data)
            
            print(f"Found {len(news_items)} recent articles to use instead")
        except Exception as e:
            print(f"Error retrieving recent articles: {e}")
    
    # Process the news articles
    if news_items:
        processed_news = process_news_articles(news_items)
        
        # Sort by importance (prioritize lower numbers)
        processed_news.sort(key=lambda x: float(x.get('business_importance', '10')) if x.get('business_importance', '10').replace('.', '', 1).isdigit() else 10)
        
        # Display the results
        print("\nRated and summarized news:")
        for article in processed_news:
            print("\n" + "="*50)
            print(f"Title: {article.get('title', 'No title')}")
            if 'title_chinese' in article:
                print(f"中文标题 (Chinese Title): {article.get('title_chinese')}")
            if 'date_published' in article:
                print(f"Date: {article.get('date_published')}")
            print(f"Business Importance: {article.get('business_importance', 'N/A')} (1=most important, 10=least important)")
            print(f"Summary: {article.get('summary', 'N/A')}")
            if 'summary_chinese' in article:
                print(f"中文摘要 (Chinese Summary): {article.get('summary_chinese')}")
            print("="*50)
        
        # Delete all historical data before saving new data
        delete_historical_data(db)
        
        # Save the processed news to Firebase
        save_processed_news_to_firebase(db, processed_news)
    else:
        print("\nNo news articles found to process. Please check your Firestore database structure.")

if __name__ == "__main__":
    main() 