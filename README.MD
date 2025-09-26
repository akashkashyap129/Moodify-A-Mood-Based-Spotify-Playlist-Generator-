# 🎵 Moodify - AI-Powered Mood-Based Spotify Playlist Generator


Moodify is an intelligent web application that creates personalized Spotify playlists based on your current mood. Using advanced sentiment analysis and Spotify's recommendation algorithm, it curates the perfect soundtrack for any moment.

## ✨ Features

### 🧠 Smart Mood Detection
- **Text Analysis**: Describe how you're feeling in natural language
- **Quick Selection**: Choose from 5 pre-defined moods (Happy, Energetic, Chill, Sad, Calm)
- **AI-Powered**: Advanced sentiment analysis to understand your emotions

### 🎶 Personalized Recommendations
- **Your Music History**: Uses your Spotify listening history for personalized suggestions
- **Popular Tracks**: Prioritizes mainstream hits and popular songs (60+ popularity score)
- **Audio Feature Matching**: Matches tracks based on musical characteristics (energy, valence, danceability)
- **Variety System**: Prevents repetitive recommendations with intelligent caching

### 🔄 Dynamic Playlist Management
- **Real-time Generation**: Instant playlist creation based on your mood
- **Refresh Function**: Get new track suggestions without losing personalization
- **Spotify Integration**: Save playlists directly to your Spotify library
- **Track Selection**: Choose specific tracks to include in saved playlists

### 🎨 Modern User Interface
- **Glassmorphism Design**: Beautiful, modern interface with backdrop blur effects
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Smooth Animations**: Engaging hover effects and transitions
- **Dark Theme**: Easy on the eyes with a sleek dark color scheme

## 📋 Prerequisites

- Python 3.8 or higher
- Spotify Premium or Free account
- Spotify Developer App credentials

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/moodify.git
cd moodify
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Note your `Client ID` and `Client Secret`
4. Add `http://localhost:5000/callback` to Redirect URIs

### 5. Environment Configuration
Create a `.env` file in the project root:
```env
client_id=your_spotify_client_id
client_secret=your_spotify_client_secret
redirect_uri=http://localhost:5000/callback
scope=user-top-read user-library-read playlist-modify-private playlist-modify-public user-read-private
```

### 6. Run the Application
```bash
python main.py
```

Visit `http://localhost:5000` in your browser!

## 📦 Dependencies

```txt
Flask==2.3.3
spotipy==2.23.0
python-dotenv==1.0.0
Flask-Session==0.5.0
```

## 🎯 How It Works

### Mood Detection Process
1. **Text Input**: User describes their mood in natural language
2. **Sentiment Analysis**: Custom algorithm analyzes emotional keywords
3. **Mood Mapping**: Text is mapped to one of 5 core moods
4. **Audio Features**: Each mood corresponds to specific musical characteristics

### Recommendation Algorithm
1. **User Personalization**: Analyzes your Spotify listening history
2. **Popular Track Filtering**: Prioritizes songs with 60+ popularity score
3. **Multi-Strategy Approach**:
   - User's top tracks (short/medium/long term)
   - Spotify recommendations based on user's music
   - Popular playlist mining
   - Targeted search with mood-specific queries
4. **Variety System**: Intelligent caching prevents repetitive suggestions

### Audio Feature Mapping

| Mood | Energy | Valence | Danceability | Special Features |
|------|---------|---------|--------------|------------------|
| **Happy** | 0.7 | 0.8 | 0.75 | High positivity |
| **Energetic** | 0.9 | 0.7 | 0.8 | Maximum energy |
| **Chill** | 0.3 | 0.5 | - | High acousticness |
| **Sad** | 0.3 | 0.25 | - | Low energy/valence |
| **Calm** | 0.25 | 0.4 | - | Slow tempo (60-110 BPM) |

## 🎵 Mood Categories

### 😊 Happy
Perfect for celebrations, good news, or when you're feeling upbeat
- **Characteristics**: Uplifting, positive, danceable
- **Example Genres**: Pop, Dance, Feel-good Rock

### ⚡ Energetic  
Ideal for workouts, motivation, or high-energy activities
- **Characteristics**: High tempo, powerful, intense
- **Example Genres**: EDM, Rock, Hip-Hop, Metal

### 😌 Chill
Great for relaxing, studying, or casual hangouts
- **Characteristics**: Laid-back, smooth, mellow
- **Example Genres**: Indie, Lo-fi, Acoustic, Jazz

### 😢 Sad
For processing emotions, rainy days, or reflective moments
- **Characteristics**: Emotional, melancholic, introspective
- **Example Genres**: Indie Folk, Sad Pop, Alternative

### 🧘 Calm
Perfect for meditation, sleep, or peaceful moments
- **Characteristics**: Gentle, peaceful, slow tempo
- **Example Genres**: Ambient, Acoustic, Classical, New Age

## 🔧 API Endpoints

### Core Routes
- `GET /` - Main application interface
- `POST /generate_playlist` - Generate mood-based playlist
- `GET /generate_playlist?mood={mood}` - Refresh playlist (AJAX)
- `POST /create_spotify_playlist` - Save playlist to Spotify
- `GET /callback` - Spotify OAuth callback
- `GET /logout` - Clear session and logout

### Authentication Flow
1. User visits `/` 
2. Redirected to Spotify for authentication
3. Spotify redirects to `/callback` with authorization code
4. App exchanges code for access token
5. User can now generate playlists

## 🛠️ Customization

### Adding New Moods
1. Update `mood_emojis` dictionary in templates
2. Add mood features in `get_mood_features()`
3. Create search strategies in `get_popular_search_strategies()`
4. Update sentiment analyzer word lists

### Adjusting Popularity Threshold
```python
# In get_enhanced_tracks_for_mood()
if track.get('popularity', 0) > 65:  # Change this value (0-100)
```

### Modifying Audio Features
```python
# In get_mood_features()
'happy': {
    'target_valence': 0.8,     # Positivity (0.0-1.0)
    'target_energy': 0.7,      # Energy level (0.0-1.0) 
    'target_danceability': 0.75 # Danceability (0.0-1.0)
}
```

## 🔒 Security Features

- **Session Management**: Secure Flask sessions for user data
- **Token Validation**: Automatic Spotify token refresh
- **Private Playlists**: Created playlists are private by default
- **No Data Storage**: User data is not permanently stored

## 📱 Mobile Support

Moodify is fully responsive and optimized for:
- **iOS Safari**: Full functionality including playlist creation
- **Android Chrome**: Complete feature support
- **Mobile Browsers**: Touch-friendly interface with optimized controls

## 🐛 Troubleshooting

### Common Issues

**"Invalid redirect URI" Error**
- Ensure `http://localhost:5000/callback` is added to your Spotify app settings
- Check that the redirect_uri in `.env` matches exactly

**"Insufficient client scope" Error**
- Verify all required scopes in `.env` file
- Re-authenticate by visiting `/logout` then `/`

**No tracks generated**
- Check your internet connection
- Ensure your Spotify account has listening history
- Try a different mood or refresh the playlist

**Template not found**
- Ensure `templates/` directory exists
- Verify `index.html` and `playlist.html` are in templates folder

### Debug Mode
Enable debug logging by adding to your `.env`:
```env
FLASK_DEBUG=1
```

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production Deployment
1. Set environment variables on your hosting platform
2. Update redirect URI to your domain
3. Use a production WSGI server like Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

## 📊 Performance

- **Average Response Time**: < 2 seconds for playlist generation
- **Concurrent Users**: Supports multiple users with session isolation
- **API Rate Limits**: Implements intelligent caching to stay within Spotify limits
- **Memory Usage**: Efficient session management with automatic cleanup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 🙏 Acknowledgments

- **Spotify Web API** for music data and recommendations
- **Flask** for the web framework
- **Spotipy** for Spotify API integration
- **Material Design** for UI inspiration

