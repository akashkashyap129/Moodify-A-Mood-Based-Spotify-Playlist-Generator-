import os
import json
from dotenv import load_dotenv
from flask import Flask, session, redirect, url_for, request, render_template, jsonify
from flask_session import Session

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler 

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


@app.route('/')
def home():
    """
    Main route that checks for a valid Spotify token.
    If no token exists, it redirects to the Spotify authentication page.
    If a token exists, it renders the index.html page to get mood input.
    """
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    return render_template('index.html')


@app.route('/callback')
def callback():
    """
    Callback route after Spotify authentication.
    It handles the token exchange and redirects back to the home page.
    """
    sp_oauth.get_access_token(request.args.get('code'))
    return redirect(url_for('home'))


@app.route('/generate_playlist', methods=['GET', 'POST'])
def generate_playlist():
    """
    This route now handles both POST requests from the form and GET requests
    from the refresh button.
    """
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())
    
    if request.method == 'POST':
        user_mood = request.form.get('mood')
    elif request.method == 'GET':
        user_mood = request.args.get('mood')

    if user_mood not in ['happy', 'energetic', 'chill', 'sad', 'calm']:
        return f"Sorry, '{user_mood}' is not a recognized mood."
    
    try:
        # First, let's try to get user's top tracks as seed tracks instead of genres
        print("Trying to get user's top tracks as seed...")
        top_tracks = sp.current_user_top_tracks(limit=5, time_range='medium_term')
        
        if top_tracks and len(top_tracks['items']) > 0:
            # Use top tracks as seeds instead of genres
            seed_track_ids = [track['id'] for track in top_tracks['items'][:2]]  # Use first 2 tracks
            
            print(f"Using seed tracks: {seed_track_ids}")
            
            # Define mood-based audio features
            mood_features = {
                'happy': {'target_valence': 0.9, 'target_energy': 0.7, 'target_danceability': 0.8},
                'energetic': {'target_valence': 0.8, 'target_energy': 0.9, 'target_danceability': 0.7},
                'chill': {'target_valence': 0.5, 'target_energy': 0.3, 'target_acousticness': 0.7},
                'sad': {'target_valence': 0.2, 'target_energy': 0.3, 'target_acousticness': 0.5},
                'calm': {'target_valence': 0.4, 'target_energy': 0.2, 'min_tempo': 60, 'max_tempo': 100}
            }
            
            features = mood_features[user_mood]
            
            # Make recommendation call with seed tracks instead of genres
            recommendations = sp.recommendations(
                seed_tracks=seed_track_ids,
                limit=20,
                **features
            )
            
        else:
            # Fallback: Try with popular tracks from search
            print("No top tracks found, trying search-based approach...")
            
            # Search for popular tracks by mood
            search_queries = {
                'happy': 'genre:pop happy upbeat',
                'energetic': 'genre:rock energetic workout',
                'chill': 'genre:indie chill relax',
                'sad': 'genre:indie sad melancholy',
                'calm': 'genre:ambient calm peaceful'
            }
            
            search_results = sp.search(
                q=search_queries[user_mood],
                type='track',
                limit=20,
                market='US'
            )
            
            recommendations = {'tracks': search_results['tracks']['items']}
        
        print(f"Got {len(recommendations['tracks'])} tracks")
        
        tracks = []
        for track in recommendations['tracks']:
            tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'preview_url': track['preview_url'],
                'url': track['external_urls']['spotify'],
                'mood': user_mood
            })
            
        return render_template('playlist.html', mood=user_mood, tracks=tracks)

    except Exception as e:
        print(f"Main approach failed: {e}")
        
        # Final fallback: Use basic search
        try:
            print("Trying basic search fallback...")
            
            mood_search_terms = {
                'happy': 'happy upbeat pop',
                'energetic': 'energetic rock workout',
                'chill': 'chill indie acoustic',
                'sad': 'sad indie emotional',
                'calm': 'calm ambient peaceful'
            }
            
            search_results = sp.search(
                q=mood_search_terms[user_mood],
                type='track',
                limit=20
            )
            
            tracks = []
            for track in search_results['tracks']['items']:
                tracks.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track['preview_url'],
                    'url': track['external_urls']['spotify'],
                    'mood': user_mood
                })
                
            return render_template('playlist.html', mood=user_mood, tracks=tracks)
            
        except Exception as search_error:
            print(f"Search fallback failed: {search_error}")
            return f"All methods failed. Main error: {e}<br>Search error: {search_error}"


@app.route('/available-genres')
def available_genres():
    """
    Debug route to check available genre seeds
    """
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())
    
    try:
        genres = sp.recommendation_genre_seeds()
        return jsonify(genres)
    except Exception as e:
        return f"Error fetching genres: {e}"


@app.route('/logout')
def logout():
    """
    Clears the session and logs the user out.
    """
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)