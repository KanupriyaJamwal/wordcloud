import io
import re
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import boto3
import os
import uuid
from botocore.exceptions import NoCredentialsError

# Common words to exclude
STOPWORDS = {
    'the', 'and', 'to', 'of', 'a', 'i', 'you', 'it', 'in', 'me', 'my',
    'that', 'is', 'be', 'with', 'for', 'on', 'not', 'this', 'are', 'your',
    'at', 'but', 'have', 'he', 'she', 'we', 'they', 'was', 'all', 'so',
    'do', 'don', 'what', 'when', 'why', 'how', 'just', 'can', 'like', 'oh',
    'yeah', 'uh', 'gonna', 'wanna', 'gotta', 'na', 'cause', 'em', 'yo', 'll'
}

def process_lyrics(text):
    """Process lyrics for word cloud"""
    # Extract words, convert to lowercase
    words = re.findall(r"[a-z']+", text.lower())
    
    # Filter out stopwords and short words
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    
    return Counter(words)

def create_wordcloud_image(word_freq):
    """Generate word cloud image"""
    wc = WordCloud(
        width=1200, 
        height=800,
        background_color='white',
        colormap='viridis',
        max_words=200,
        prefer_horizontal=0.9,
        collocations=False,
        random_state=42
    ).generate_from_frequencies(word_freq)
    
    # Save to a BytesIO object
    img_data = io.BytesIO()
    plt.figure(figsize=(12, 8))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(img_data, format='png', dpi=300, bbox_inches='tight')
    plt.close()
    img_data.seek(0)
    
    return img_data

def upload_to_s3(img_data, filename):
    """Upload an image to S3"""
    # Configure S3
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    S3_BUCKET = os.getenv('S3_BUCKET')
    
    try:
        s3.upload_fileobj(
            img_data, 
            S3_BUCKET, 
            filename, 
            ExtraArgs={'ContentType': 'image/png'}
        )
        return f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
    except NoCredentialsError:
        print("AWS credentials not available")
        return None

def generate_wordcloud(user_id, lyrics, time_range):
    """Generate and save a word cloud from lyrics"""
    # Process lyrics
    word_freq = process_lyrics(lyrics)
    
    # Generate word cloud image
    img_data = create_wordcloud_image(word_freq)
    
    # Generate a unique filename
    filename = f"wordcloud/{user_id}/{time_range}/{uuid.uuid4()}.png"
    
    # Upload to S3
    image_url = upload_to_s3(img_data, filename)
    
    return image_url, dict(word_freq)