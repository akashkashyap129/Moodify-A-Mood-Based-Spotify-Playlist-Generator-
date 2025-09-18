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

    # Using ONLY valid Spotify genre seeds from the official list
    mood_mappings = {
        'happy': {
            'seed_genres': ['pop', 'dance'],
            'target_valence': 0.9,
            'target_danceability': 0.8,
            'target_energy': 0.7
        },
        'energetic': {
            'seed_genres': ['rock', 'electronic'],
            'target_valence': 0.8,
            'target_energy': 0.9,
            'target_danceability': 0.7
        },
        'chill': {
            'seed_genres': ['chill', 'acoustic'],
            'target_valence': 0.6,
            'target_acousticness': 0.7,
            'target_energy': 0.3
        },
        'sad': {
            'seed_genres': ['indie', 'blues'],
            'target_valence': 0.2,
            'target_energy': 0.3,
            'target_acousticness': 0.5
        },
        'calm': {
            'seed_genres': ['ambient', 'jazz'],
            'target_valence': 0.5,
            'target_energy': 0.2,
            'min_tempo': 60,
            'max_tempo': 100
        },
    }

    if user_mood not in mood_mappings:
        return f"Sorry, '{user_mood}' is not a recognized mood."
    
    # Make a deep copy to avoid modifying the original
    import copy
    audio_features = copy.deepcopy(mood_mappings[user_mood])
    
    try:
        # Extract and validate the seed genres
        seed_genres_list = audio_features.pop('seed_genres')
        
        print(f"Original mood mapping: {mood_mappings[user_mood]}")  # Debug print
        print(f"Seed genres extracted: {seed_genres_list}")  # Debug print
        print(f"Type of seed_genres_list: {type(seed_genres_list)}")  # Debug print
        
        # Ensure we have a proper list
        if not isinstance(seed_genres_list, list):
            print(f"ERROR: seed_genres is not a list! It's: {type(seed_genres_list)}")
            return f"Internal error: seed_genres should be a list, got {type(seed_genres_list)}"
        
        # Join the genres properly
        seed_genres_str = ','.join(seed_genres_list)
        
        print(f"Final seed_genres string: '{seed_genres_str}'")  # Debug print
        print(f"Remaining audio features: {audio_features}")  # Debug print
        print(f"Audio features: {audio_features}")  # Debug print
        
        # Make the API call with proper parameter structure
        recommendations = sp.recommendations(
            limit=20,
            market='US',
            seed_genres=seed_genres_str,
            **audio_features
        )
        
        print(f"API call successful! Got {len(recommendations['tracks'])} tracks")  # Debug print
        
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
        print(f"Full error details: {e}")  # Debug print
        print(f"Error type: {type(e)}")  # Debug print
        
        # Let's try to get available genres for debugging
        try:
            available_genres = sp.recommendation_genre_seeds()
            print(f"Available genres: {available_genres}")
        except Exception as genre_error:
            print(f"Could not fetch available genres: {genre_error}")
        
        return f"An error occurred: {e}"


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