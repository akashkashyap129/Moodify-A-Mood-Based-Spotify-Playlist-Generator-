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


@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    """
    This route takes a user's mood from the form, maps it to Spotify audio features,
    and generates a new playlist of recommended tracks.
    """
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())
    
    # Get mood from the form submission
    user_mood = request.form.get('mood')

    # Mapping moods to Spotify audio features for recommendations
    # Values are between 0.0 and 1.0
    mood_mappings = {
        'happy': {'target_valence': 0.9, 'target_danceability': 0.8},
        'energetic': {'target_valence': 0.8, 'target_danceability': 0.9},
        'chill': {'target_valence': 0.6, 'target_acousticness': 0.7},
        'sad': {'target_valence': 0.2, 'target_energy': 0.3},
        'calm': {'target_valence': 0.5, 'target_tempo': 90},
    }

    # Get the audio feature parameters for the selected mood
    audio_features = mood_mappings.get(user_mood, {})

    if not audio_features:
        return f"Sorry, '{user_mood}' is not a recognized mood."
    
    try:
        # Get recommendations based on the mood features
        # The limit is set to 20 songs, but you can change this
        recommendations = sp.recommendations(limit=20, **audio_features)
        
        # Prepare a list of tracks to display
        tracks = []
        for track in recommendations['tracks']:
            tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'preview_url': track['preview_url'],
                'url': track['external_urls']['spotify']
            })
            
        return render_template('playlist.html', mood=user_mood, tracks=tracks)

    except Exception as e:
        return f"An error occurred: {e}"


@app.route('/logout')
def logout():
    """
    Clears the session and logs the user out.
    """
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
