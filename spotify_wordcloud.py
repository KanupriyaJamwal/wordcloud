import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import lyricsgenius
import json
from pathlib import Path
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Load environment variables from .env file
load_dotenv()

# Configuration
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
REDIRECT_URI = "http://localhost:8888/callback"
CACHE_FILE = "lyrics_cache.json"
TOP_SONGS_FILE = "top_songs.txt"
WORDCLOUD_FILE = "lyrics_wordcloud.png"

# Common words to exclude
STOPWORDS = {
    'the', 'and', 'to', 'of', 'a', 'i', 'you', 'it', 'in', 'me', 'my',
    'that', 'is', 'be', 'with', 'for', 'on', 'not', 'this', 'are', 'your',
    'at', 'but', 'have', 'he', 'she', 'we', 'they', 'was', 'all', 'so',
    'do', 'don', 'what', 'when', 'why', 'how', 'just', 'can', 'like', 'oh',
    'yeah', 'uh', 'gonna', 'wanna', 'gotta', 'na', 'cause', 'em', 'yo', 'll'
}

# Initialize Spotify and Genius APIs
def setup_apis():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-top-read",
        cache_path=".spotify_cache"  # Cache Spotify auth token
    ))
    
    genius = lyricsgenius.Genius(
        GENIUS_TOKEN,
        remove_section_headers=True,
        skip_non_songs=True,
        excluded_terms=["Remix", "Live", "Demo", "Instrumental"],
        verbose=False,
        timeout=5,  # Shorter timeout for faster failures
        retries=1   # Less retries for speed
    )
    
    return sp, genius

# Simple cache for lyrics
def load_cache():
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f)

# Clean lyrics by removing metadata and formatting artifacts
def clean_lyrics(lyrics):
    if not lyrics:
        return None
        
    # Remove the Genius header that appears at the beginning
    lyrics = re.sub(r'^.*?Lyrics', '', lyrics, flags=re.DOTALL, count=1)
    
    # Remove the Genius footer
    lyrics = re.sub(r'You might also like.*?$', '', lyrics, flags=re.DOTALL)
    
    # Remove section headers like [Verse], [Chorus], etc.
    lyrics = re.sub(r'\[.*?\]', '', lyrics)
    
    # Remove numbers that appear at the beginning of lines (often formatting artifacts)
    lyrics = re.sub(r'^\d+\.?\s*', '', lyrics, flags=re.MULTILINE)
    
    # Remove Embed/HTML markers
    lyrics = re.sub(r'Embed$', '', lyrics, flags=re.MULTILINE)
    lyrics = re.sub(r'<.*?>', '', lyrics)
    
    # Remove credits and contributor notes
    lyrics = re.sub(r'Lyrics\s+powered\s+by\s+.*?$', '', lyrics, flags=re.DOTALL | re.IGNORECASE)
    lyrics = re.sub(r'Contributors:.*?$', '', lyrics, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any URLs
    lyrics = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', lyrics)
    
    # Remove extra spaces and lines
    lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
    lyrics = re.sub(r' {2,}', ' ', lyrics)
    
    return lyrics.strip()

# Get lyrics for a song - for parallel fetching
def fetch_lyrics(song, genius, cache):
    title = song['title']
    artist = song['artist']
    key = f"{title.lower()}|{artist.lower()}"
    
    # Check cache first
    if key in cache:
        return song, cache[key]
    
    # Try to fetch lyrics
    try:
        result = genius.search_song(title, artist)
        lyrics = result.lyrics if result else None
        
        # Clean the lyrics before caching
        if lyrics:
            lyrics = clean_lyrics(lyrics)
            cache[key] = lyrics
            
        return song, lyrics
    except Exception:
        return song, None

# Fetch lyrics in parallel using ThreadPoolExecutor
def get_lyrics_parallel(songs, genius, cache, max_workers=10):
    all_lyrics = ""
    updated_songs = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all fetch tasks
        futures = {executor.submit(fetch_lyrics, song, genius, cache): song for song in songs}
        
        # Process results as they complete
        for future in as_completed(futures):
            song, lyrics = future.result()
            updated_songs.append(song)
            if lyrics:
                all_lyrics += lyrics + "\n"
            time.sleep(0.1)  # Small delay to prevent rate limiting
    
    return updated_songs, all_lyrics

# Process lyrics for word cloud
def process_lyrics(text):
    # Extract words, convert to lowercase
    words = re.findall(r"[a-z']+", text.lower())
    
    # Filter out stopwords and short words
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    
    return Counter(words)

# Generate word cloud with optimized settings
def create_wordcloud(word_freq):
    wc = WordCloud(
        width=1200, 
        height=800,
        background_color='white',
        colormap='viridis',
        max_words=200,
        prefer_horizontal=0.9,  # Allow some vertical words
        collocations=False,     # Avoid repeating word pairs
        random_state=42         # For reproducible results
    ).generate_from_frequencies(word_freq)
    
    # Plot without displaying (faster)
    plt.figure(figsize=(12, 8))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(WORDCLOUD_FILE, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Start timing
    start_time = time.time()
    
    # Check for API credentials
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, GENIUS_TOKEN]):
        print("Error: Please set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and GENIUS_TOKEN environment variables")
        return
    
    print("Starting Spotify wordcloud generation...")
    
    # Set up APIs
    sp, genius = setup_apis()
    cache = load_cache()
    
    # Get top songs from Spotify - use smaller limit for faster run (adjust as needed)
    top_tracks = sp.current_user_top_tracks(limit=30, time_range='medium_term')['items']
    
    # Format song data
    songs = []
    for track in top_tracks:
        artist_name = track['artists'][0]['name']
        songs.append({
            'title': track['name'],
            'artist': artist_name
        })
    
    # Fetch lyrics in parallel
    songs, all_lyrics = get_lyrics_parallel(songs, genius, cache)
    
    # Write top songs to file
    with open(TOP_SONGS_FILE, 'w', encoding='utf-8') as f:
        for i, song in enumerate(songs, 1):
            f.write(f"{i}. {song['title']} - {song['artist']}\n")
    
    # Save cache for future runs
    save_cache(cache)
    
    # Create word cloud if we have lyrics
    if all_lyrics:
        word_freq = process_lyrics(all_lyrics)
        create_wordcloud(word_freq)
        print(f"✓ Word cloud created: {WORDCLOUD_FILE}")
    
    print(f"✓ Top songs list created: {TOP_SONGS_FILE}")
    print(f"✓ Completed in {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    # Check for required packages
    try:
        import dotenv, lyricsgenius, spotipy, wordcloud
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run(['pip', 'install', 'python-dotenv', 'lyricsgenius', 'spotipy', 'wordcloud', 'matplotlib'])
    
    main()