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
        top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
        
        if top_tracks and len(top_tracks['items']) > 0:
            # Use top tracks as seeds instead of genres
            seed_track_ids = [track['id'] for track in top_tracks['items'][:3]]  # Use first 3 tracks
            
            print(f"Using seed tracks: {seed_track_ids}")
            
            # Define mood-based audio features with more refined parameters
            mood_features = {
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
            
            features = mood_features[user_mood]
            
            # Make recommendation call with seed tracks instead of genres
            recommendations = sp.recommendations(
                seed_tracks=seed_track_ids,
                limit=25,  # Get more tracks for better variety
                market='US',
                **features
            )
            
            # Filter out explicit content if desired (optional)
            filtered_tracks = []
            for track in recommendations['tracks']:
                # You can add filters here, e.g., skip explicit content:
                # if not track.get('explicit', False):
                filtered_tracks.append(track)
            
            recommendations['tracks'] = filtered_tracks[:20]  # Limit to 20 tracks
            
        else:
            # Fallback: Try with popular tracks from search with better queries
            print("No top tracks found, trying enhanced search-based approach...")
            
            # Enhanced search queries with multiple terms
            search_queries = {
                'happy': 'genre:pop mood happy upbeat positive dance',
                'energetic': 'genre:rock genre:electronic energetic workout pump up',
                'chill': 'genre:indie genre:alternative chill relax mellow downtempo',
                'sad': 'genre:indie genre:alternative sad melancholy emotional heartbreak',
                'calm': 'genre:ambient genre:folk calm peaceful meditation relaxing'
            }
            
            # Try multiple search queries and combine results
            all_tracks = []
            query_terms = search_queries[user_mood].split()
            
            # Split into multiple searches for better variety
            for i in range(0, len(query_terms), 3):
                search_term = ' '.join(query_terms[i:i+3])
                try:
                    search_results = sp.search(
                        q=search_term,
                        type='track',
                        limit=10,
                        market='US'
                    )
                    all_tracks.extend(search_results['tracks']['items'])
                except Exception as search_err:
                    print(f"Search failed for term '{search_term}': {search_err}")
                    continue
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_tracks = []
            for track in all_tracks:
                if track['id'] not in seen_ids:
                    seen_ids.add(track['id'])
                    unique_tracks.append(track)
                    if len(unique_tracks) >= 20:
                        break
            
            recommendations = {'tracks': unique_tracks}
        
        print(f"Got {len(recommendations['tracks'])} tracks")
        
        # Enhanced track processing with better data
        tracks = []
        for track in recommendations['tracks']:
            # Get additional track info
            duration_ms = track.get('duration_ms', 0)
            duration_min = duration_ms // 60000
            duration_sec = (duration_ms % 60000) // 1000
            
            track_data = {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'preview_url': track['preview_url'],
                'url': track['external_urls']['spotify'],
                'mood': user_mood,
                'duration': f"{duration_min}:{duration_sec:02d}",
                'popularity': track.get('popularity', 0),
                'explicit': track.get('explicit', False),
                'release_date': track['album'].get('release_date', 'Unknown'),
                # Get album artwork if available
                'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None
            }
            tracks.append(track_data)
        
        # Sort tracks by popularity for better ordering
        tracks.sort(key=lambda x: x['popularity'], reverse=True)
            
        return render_template('playlist.html', mood=user_mood, tracks=tracks)

    except Exception as e:
        print(f"Main approach failed: {e}")
        
        # Final fallback: Use basic search with simpler terms
        try:
            print("Trying basic search fallback...")
            
            mood_search_terms = {
                'happy': 'happy pop dance',
                'energetic': 'rock electronic workout',
                'chill': 'indie acoustic chill',
                'sad': 'sad indie emotional',
                'calm': 'ambient peaceful calm'
            }
            
            search_results = sp.search(
                q=mood_search_terms[user_mood],
                type='track',
                limit=20,
                market='US'
            )
            
            tracks = []
            for track in search_results['tracks']['items']:
                duration_ms = track.get('duration_ms', 0)
                duration_min = duration_ms // 60000
                duration_sec = (duration_ms % 60000) // 1000
                
                track_data = {
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'preview_url': track['preview_url'],
                    'url': track['external_urls']['spotify'],
                    'mood': user_mood,
                    'duration': f"{duration_min}:{duration_sec:02d}",
                    'popularity': track.get('popularity', 0),
                    'explicit': track.get('explicit', False),
                    'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None
                }
                tracks.append(track_data)
                
            return render_template('playlist.html', mood=user_mood, tracks=tracks)
            
        except Exception as search_error:
            print(f"Search fallback failed: {search_error}")
            return f"All methods failed. Main error: {e}<br>Search error: {search_error}"


@app.route('/create_spotify_playlist', methods=['POST'])
def create_spotify_playlist():
    """
    Create an actual Spotify playlist from the generated tracks
    """
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
        from datetime import datetime
        timestamp = datetime.now().strftime("%B %d, %Y")
        playlist_name = f"Moodify - {mood.title()} Mood ({timestamp})"
        playlist_description = f"A {mood} mood playlist curated by Moodify based on your listening preferences."
        
        # Create the playlist
        playlist = sp.user_playlist_create(
            user_id,
            playlist_name,
            public=False,  # Make it private by default
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


@app.route('/get_track_features/<track_id>')
def get_track_features(track_id):
    """
    Get audio features for a specific track (for debugging/info)
    """
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        features = sp.audio_features(track_id)[0]
        return jsonify(features)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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