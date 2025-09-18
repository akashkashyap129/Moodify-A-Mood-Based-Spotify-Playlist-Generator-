import os

from dotenv import load_dotenv
from flask import Flask, session, redirect, url_for, request
from flask_session import Session

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler 

load_dotenv()

client_id=os.getenv('client_id')
client_secret=os.getenv('client_secret')
redirect_uri=os.getenv('redirect_uri')
scope=os.getenv('scope')

if not all([client_id, client_secret, redirect_uri, scope]):
    raise ValueError('Missing environment variables! Check your .env file.')

app = Flask(__name__)

# Configure Flask-Session
app.config['SECRET_KEY'] = os.urandom(64)


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
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    return redirect(url_for('get_playlists'))




@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args.get('code'))
    return redirect(url_for('get_playlists'))




@app.route('/get_playlists')
def get_playlists():
    token_info = cache_handler.get_cached_token()
    
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())

    playlists = sp.current_user_playlists()
    playlists_info = [(pl['name'], pl['external_urls']['spotify']) for pl in playlists['items']]
    
    playlists_html = '<br>'.join([f'{name} : {url}' for name, url in playlists_info])
    return playlists_html




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
        