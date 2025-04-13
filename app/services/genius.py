import os
import lyricsgenius
import re
from app.models import LyricsCache
from datetime import datetime
from app import db

def get_genius_client():
    """Get a Genius client"""
    return lyricsgenius.Genius(
        os.getenv('GENIUS_TOKEN'),
        remove_section_headers=True,
        skip_non_songs=True,
        excluded_terms=["Remix", "Live", "Demo", "Instrumental"],
        verbose=False,
        timeout=5,
        retries=1
    )

def clean_lyrics(lyrics):
    """Clean lyrics by removing metadata and formatting artifacts"""
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

def get_lyrics(title, artist):
    """Get lyrics for a song, using cache if available"""
    # Check cache first
    cached_lyrics = LyricsCache.query.filter_by(
        title=title, 
        artist=artist
    ).first()
    
    if cached_lyrics:
        return cached_lyrics.lyrics
    
    # Fetch from Genius
    try:
        genius = get_genius_client()
        result = genius.search_song(title, artist)
        lyrics = result.lyrics if result else None
        
        if lyrics:
            lyrics = clean_lyrics(lyrics)
            
            # Cache the lyrics
            cache_entry = LyricsCache(
                title=title,
                artist=artist,
                lyrics=lyrics,
                last_updated=datetime.now()
            )
            db.session.add(cache_entry)
            db.session.commit()
            
        return lyrics
    except Exception as e:
        print(f"Error fetching lyrics for {title} by {artist}: {e}")
        return None