import os
import json
import random
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, session, redirect, url_for, request, render_template, jsonify
from flask_session import Session

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

# Simple sentiment analysis without external dependencies
class SimpleSentimentAnalyzer:
    def __init__(self):
        self.positive_words = {
            'happy', 'joy', 'excited', 'amazing', 'great', 'fantastic', 'wonderful', 'awesome',
            'energetic', 'pumped', 'motivated', 'upbeat', 'cheerful', 'elated', 'euphoric',
            'thrilled', 'ecstatic', 'delighted', 'content', 'optimistic', 'confident',
            'energized', 'vibrant', 'lively', 'dynamic', 'enthusiastic', 'passionate'
        }
        
        self.negative_words = {
            'sad', 'depressed', 'down', 'upset', 'disappointed', 'hurt', 'broken', 'lonely',
            'melancholy', 'blue', 'gloomy', 'miserable', 'heartbroken', 'sorrowful',
            'dejected', 'despondent', 'mournful', 'grief', 'anguish', 'despair'
        }
        
        self.calm_words = {
            'calm', 'peaceful', 'relaxed', 'serene', 'tranquil', 'zen', 'meditative',
            'quiet', 'still', 'gentle', 'soft', 'mellow', 'soothing', 'restful',
            'centered', 'balanced', 'harmonious', 'composed', 'placid'
        }
        
        self.energetic_words = {
            'energetic', 'pumped', 'hyped', 'intense', 'powerful', 'strong', 'fierce',
            'aggressive', 'wild', 'crazy', 'insane', 'hardcore', 'extreme', 'explosive',
            'electric', 'charged', 'amped', 'turbo', 'high-energy', 'adrenaline'
        }
        
        self.chill_words = {
            'chill', 'relaxed', 'laid-back', 'easy', 'casual', 'cool', 'smooth',
            'mellow', 'flowing', 'cruising', 'cozy', 'comfortable', 'easygoing',
            'lowkey', 'ambient', 'dreamy', 'floating', 'drifting'
        }
    
    def analyze_sentiment(self, text):
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        scores = {
            'happy': 0,
            'sad': 0,
            'calm': 0,
            'energetic': 0,
            'chill': 0
        }
        
        for word in words:
            if word in self.positive_words:
                scores['happy'] += 2
            if word in self.negative_words:
                scores['sad'] += 2
            if word in self.calm_words:
                scores['calm'] += 2
            if word in self.energetic_words:
                scores['energetic'] += 2
            if word in self.chill_words:
                scores['chill'] += 2
        
        # Add context-based scoring
        if 'feel good' in text or 'feeling good' in text:
            scores['happy'] += 1
        if 'feel bad' in text or 'feeling bad' in text:
            scores['sad'] += 1
        if 'need energy' in text or 'want energy' in text:
            scores['energetic'] += 1
        if 'want to relax' in text or 'need to chill' in text:
            scores['chill'] += 1
        
        # Return the mood with highest score, default to 'happy' if tie
        max_score = max(scores.values())
        if max_score == 0:
            return 'happy'  # Default mood if no keywords found
        
        for mood, score in scores.items():
            if score == max_score:
                return mood
        
        return 'happy'

load_dotenv()

client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')
redirect_uri = os.getenv('redirect_uri')
scope = os.getenv('scope')

if not all([client_id, client_secret, redirect_uri, scope]):
    raise ValueError('Missing environment variables! Check your .env file.')

app = Flask(__name__)

# Configure Flask-Session
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize sentiment analyzer
sentiment_analyzer = SimpleSentimentAnalyzer()

# Spotipy Cache Handler
cache_handler = FlaskSessionCacheHandler(session)

# Spotify OAuth setup
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True,
)

sp = Spotify(auth_manager=sp_oauth)

# Store previously generated tracks to avoid repetition
def get_user_cache_key():
    """Generate a unique cache key for the current user"""
    token_info = cache_handler.get_cached_token()
    if token_info and 'access_token' in token_info:
        # Use a hash of the access token for user identification
        return f"user_{abs(hash(token_info['access_token']))}"
    return "anonymous"

def get_cached_tracks(mood):
    """Get previously generated tracks for this user and mood"""
    cache_key = get_user_cache_key()
    user_cache = session.get(f'track_cache_{cache_key}', {})
    return user_cache.get(mood, [])

def cache_tracks(mood, track_ids):
    """Cache generated tracks for this user and mood"""
    cache_key = get_user_cache_key()
    user_cache = session.get(f'track_cache_{cache_key}', {})
    
    # Keep only last 100 tracks per mood to prevent session bloat
    if mood not in user_cache:
        user_cache[mood] = []
    
    user_cache[mood].extend(track_ids)
    user_cache[mood] = list(set(user_cache[mood]))[-100:]  # Remove duplicates and limit
    
    session[f'track_cache_{cache_key}`'] = user_cache

@app.route('/')
def home():
    """Main route that checks for a valid Spotify token."""
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    return render_template('index.html')

@app.route('/callback')
def callback():
    """Callback route after Spotify authentication."""
    sp_oauth.get_access_token(request.args.get('code'))
    return redirect(url_for('home'))

@app.route('/generate_playlist', methods=['GET', 'POST'])
def generate_playlist():
    """Generate playlist from mood selection or text description."""
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())
    
    if request.method == 'POST':
        # Check if it's a mood selection or text description
        user_mood = request.form.get('mood')
        mood_text = request.form.get('mood_text', '').strip()
        
        if mood_text:
            # Use sentiment analysis on the text
            user_mood = sentiment_analyzer.analyze_sentiment(mood_text)
            print(f"Analyzed mood text: '{mood_text}' -> {user_mood}")
        elif not user_mood:
            return "Please select a mood or describe your mood.", 400
            
    else:  # GET request (refresh)
        user_mood = request.args.get('mood')
        if not user_mood:
            return "Mood parameter missing.", 400
    
    if user_mood not in ['happy', 'energetic', 'chill', 'sad', 'calm']:
        return f"Invalid mood: {user_mood}", 400
    
    # Get tracks for the mood
    tracks = get_enhanced_tracks_for_mood(user_mood)
    
    if not tracks:
        return "Sorry, couldn't generate a playlist at this time. Please try again.", 500
    
    # Check if this is an AJAX request (refresh)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('playlist.html', mood=user_mood, tracks=tracks)
    else:
        return render_template('playlist.html', mood=user_mood, tracks=tracks)

# Add these modifications to your main.py file

def get_enhanced_tracks_for_mood(user_mood, avoid_recent=True):
    """Enhanced track generation with better variety and POPULAR tracks focus."""
    try:
        print(f"Generating enhanced {user_mood} playlist with popular tracks...")
        
        cached_tracks = get_cached_tracks(user_mood) if avoid_recent else []
        print(f"Found {len(cached_tracks)} cached tracks to avoid")
        
        all_tracks = []
        
        # Strategy 1: Popular tracks from user's top tracks
        time_ranges = ['short_term', 'medium_term', 'long_term']
        user_top_tracks = []
        
        for time_range in time_ranges:
            try:
                # Get more tracks and filter by popularity
                top_tracks = sp.current_user_top_tracks(limit=25, time_range=time_range)
                if top_tracks and top_tracks['items']:
                    # Filter for popular tracks (popularity > 60)
                    popular_tracks = [track['id'] for track in top_tracks['items'] 
                                    if track.get('popularity', 0) > 60]
                    user_top_tracks.extend(popular_tracks)
            except Exception as e:
                print(f"Error getting {time_range} top tracks: {e}")
        
        user_top_tracks = list(set(user_top_tracks))
        user_top_tracks = [tid for tid in user_top_tracks if tid not in cached_tracks]
        
        # Strategy 2: Enhanced search with popular tracks focus
        search_strategies = get_popular_search_strategies(user_mood)
        
        for search_query in search_strategies:
            try:
                # Search with popularity filters
                search_results = sp.search(
                    q=search_query,
                    type='track',
                    limit=20,  # Get more results
                    market='US',
                    offset=0  # Start from top results (most popular)
                )
                
                if search_results and search_results['tracks']['items']:
                    # Filter for high popularity tracks
                    popular_tracks = [track for track in search_results['tracks']['items'] 
                                    if track.get('popularity', 0) > 40 and track['id'] not in cached_tracks]
                    all_tracks.extend(popular_tracks)
                    
            except Exception as e:
                print(f"Error with search query '{search_query}': {e}")
        
        # Strategy 3: Get recommendations from popular seed tracks
        if user_top_tracks:
            seed_combinations = [
                user_top_tracks[:3],
                user_top_tracks[3:6] if len(user_top_tracks) > 3 else user_top_tracks[:3],
            ]
            
            mood_features = get_mood_features(user_mood)
            
            for seed_tracks in seed_combinations:
                if len(seed_tracks) >= 1:
                    try:
                        # Add popularity constraint to features
                        popular_features = add_popularity_constraint(mood_features)
                        
                        recommendations = sp.recommendations(
                            seed_tracks=seed_tracks[:3],
                            limit=20,
                            market='US',
                            **popular_features
                        )
                        
                        # Filter for popular recommendations
                        popular_recs = [track for track in recommendations['tracks'] 
                                      if track.get('popularity', 0) > 60 and track['id'] not in cached_tracks]
                        all_tracks.extend(popular_recs)
                        
                    except Exception as e:
                        print(f"Error with recommendation API: {e}")
        
        # Strategy 4: Popular playlists search
        try:
            playlist_queries = get_popular_playlist_queries(user_mood)
            for query in playlist_queries:
                playlist_results = sp.search(q=query, type='playlist', limit=3)
                if playlist_results and playlist_results['playlists']['items']:
                    for playlist in playlist_results['playlists']['items']:
                        if playlist['tracks']['total'] > 0:
                            playlist_tracks = sp.playlist_tracks(playlist['id'], limit=10)
                            if playlist_tracks and playlist_tracks['items']:
                                for item in playlist_tracks['items']:
                                    if item['track'] and item['track'].get('popularity', 0) > 40:
                                        if item['track']['id'] not in cached_tracks:
                                            all_tracks.append(item['track'])
        except Exception as e:
            print(f"Error getting popular playlists: {e}")
        
        # Remove duplicates and sort by popularity
        seen_ids = set()
        unique_tracks = []
        
        for track in all_tracks:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_tracks.append(track)
        
        # Sort by popularity (highest first) with some randomness
        unique_tracks.sort(key=lambda x: x.get('popularity', 0) + random.randint(-10, 10), reverse=True)
        
        # Take top tracks
        selected_tracks = unique_tracks[:30]
        
        # Process tracks for display
        processed_tracks = []
        for track in selected_tracks:
            try:
                duration_ms = track.get('duration_ms', 0)
                duration_min = duration_ms // 60000
                duration_sec = (duration_ms % 60000) // 1000
                
                track_data = {
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'url': track['external_urls']['spotify'],
                    'mood': user_mood,
                    'duration': f"{duration_min}:{duration_sec:02d}",
                    'duration_ms': duration_ms,  # Fixed the error
                    'popularity': track.get('popularity', 0),
                    'explicit': track.get('explicit', False),
                    'release_date': track['album'].get('release_date', 'Unknown'),
                    'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None
                }
                processed_tracks.append(track_data)
            except Exception as e:
                print(f"Error processing track: {e}")
                continue
        
        # Cache the track IDs
        track_ids = [track['id'] for track in processed_tracks]
        cache_tracks(user_mood, track_ids)
        
        return processed_tracks[:20]
        
    except Exception as e:
        print(f"Error in enhanced track generation: {e}")
        return []

def add_popularity_constraint(features):
    """Add popularity constraints to mood features."""
    popular_features = features.copy()
    # Add minimum popularity constraint
    popular_features['min_popularity'] = 40
    return popular_features

def get_popular_search_strategies(mood):
    """Get search strategies focused on popular tracks."""
    strategies = {
        'happy': [
            'happy pop hits top charts dance party',
            'feel good music billboard hot 100',
            'uplifting pop rock mainstream hits',
            'celebration party top songs 2024',
            'sunny pop hits radio friendly'
        ],
        'energetic': [
            'high energy workout hits gym music',
            'pump up songs top charts rock metal',
            'intense workout playlist billboard',
            'adrenaline rush top hits electronic',
            'motivation music popular tracks'
        ],
        'chill': [
            'chill pop indie hits relaxing vibes',
            'laid back hits mainstream chill',
            'coffee shop music popular acoustic',
            'sunday morning hits indie pop',
            'chill vibes top tracks ambient'
        ],
        'sad': [
            'sad pop hits emotional ballads',
            'heartbreak songs top charts',
            'emotional pop rock mainstream',
            'melancholy hits indie sad songs',
            'breakup songs popular emotional'
        ],
        'calm': [
            'peaceful pop acoustic hits calm',
            'meditation music popular relaxing',
            'soft pop hits gentle acoustic',
            'calming music mainstream peaceful',
            'zen music popular ambient tracks'
        ]
    }
    
    return strategies.get(mood, strategies['happy'])

def get_popular_playlist_queries(mood):
    """Get popular playlist search queries for each mood."""
    queries = {
        'happy': [
            'Today\'s Top Hits happy',
            'Pop Rising feel good',
            'Mood Booster'
        ],
        'energetic': [
            'Beast Mode workout',
            'Power Hour gym',
            'Adrenaline Workout'
        ],
        'chill': [
            'Chill Hits',
            'Indie Pop chill',
            'Coffee House'
        ],
        'sad': [
            'Sad Songs emotional',
            'Heartbreak Pop',
            'Life Sucks indie'
        ],
        'calm': [
            'Peaceful Piano',
            'Calm meditation',
            'Acoustic Chill'
        ]
    }
    
    return queries.get(mood, queries['happy'])

def get_mood_features(mood):
    """Get audio features for mood with some base randomization."""
    base_features = {
        'happy': {
            'target_valence': 0.8, 
            'target_energy': 0.7, 
            'target_danceability': 0.75,
            'min_valence': 0.6,
            'min_energy': 0.5
        },
        'energetic': {
            'target_valence': 0.7, 
            'target_energy': 0.9, 
            'target_danceability': 0.8,
            'min_energy': 0.7,
            'min_danceability': 0.6
        },
        'chill': {
            'target_valence': 0.5, 
            'target_energy': 0.3, 
            'target_acousticness': 0.6,
            'max_energy': 0.5,
            'min_acousticness': 0.3
        },
        'sad': {
            'target_valence': 0.25, 
            'target_energy': 0.3, 
            'target_acousticness': 0.5,
            'max_valence': 0.4,
            'max_energy': 0.5
        },
        'calm': {
            'target_valence': 0.4, 
            'target_energy': 0.25, 
            'min_tempo': 60, 
            'max_tempo': 110,
            'max_energy': 0.4,
            'target_acousticness': 0.5
        }
    }
    
    return base_features.get(mood, base_features['happy'])

def add_feature_variation(features):
    """Add slight randomization to features for variety."""
    varied = features.copy()
    
    for key, value in varied.items():
        if isinstance(value, (int, float)) and 'tempo' not in key:
            # Add ±10% variation
            variation = value * 0.1 * (random.random() - 0.5) * 2
            varied[key] = max(0, min(1, value + variation))
    
    return varied

def get_search_strategies(mood):
    """Get diverse search strategies for each mood."""
    strategies = {
        'happy': [
            'happy pop upbeat dance party',
            'feel good music positive vibes',
            'uplifting songs cheerful',
            'celebration joy music',
            'sunny day driving songs'
        ],
        'energetic': [
            'high energy workout music',
            'rock metal electronic pump up',
            'intense powerful songs',
            'gym motivation music',
            'adrenaline rush tracks'
        ],
        'chill': [
            'indie alternative chill vibes',
            'relaxed downtempo ambient',
            'laid back acoustic mellow',
            'sunday morning coffee music',
            'dreamy atmospheric sounds'
        ],
        'sad': [
            'sad emotional heartbreak songs',
            'melancholy indie folk ballads',
            'rainy day depression music',
            'lonely contemplative tracks',
            'slow emotional piano'
        ],
        'calm': [
            'peaceful meditation ambient',
            'soft acoustic folk gentle',
            'nature sounds relaxation',
            'spa yoga calming music',
            'quiet evening piano instrumental'
        ]
    }
    
    return strategies.get(mood, strategies['happy'])

@app.route('/create_spotify_playlist', methods=['POST'])
def create_spotify_playlist():
    """Create an actual Spotify playlist from the generated tracks."""
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        mood = data.get('mood')
        track_ids = data.get('track_ids', [])
        
        if not mood or not track_ids:
            return jsonify({'error': 'Missing mood or track_ids'}), 400
        
        # Get current user info
        user = sp.current_user()
        user_id = user['id']
        
        # Create playlist name with timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        playlist_name = f"Moodify - {mood.title()} Mood ({timestamp})"
        playlist_description = f"A personalized {mood} mood playlist curated by Moodify based on your listening preferences and history."
        
        # Create the playlist
        playlist = sp.user_playlist_create(
            user_id,
            playlist_name,
            public=False,
            description=playlist_description
        )
        
        # Add tracks to the playlist
        track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
        sp.playlist_add_items(playlist['id'], track_uris)
        
        return jsonify({
            'success': True,
            'playlist_url': playlist['external_urls']['spotify'],
            'playlist_name': playlist_name
        })
        
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """Clears the session and logs the user out."""
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)