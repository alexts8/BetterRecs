# import necessary modules
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, render_template
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


# initialize Flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# set a random secret key to sign the cookie
app.secret_key = 'wefkhejif37r72'

# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

# route to handle logging in
@app.route('/')
def login():
    session.clear()
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)

@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect("/")

# route to handle the redirect URI after authorization
@app.route('/redirect')
def redirect_page():
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the homepage
    return render_template('home.html')

@app.route('/viewPlaylists')
def view_playlists():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    # get the user's playlists
    current_playlists =  sp.current_user_playlists()['items']


    # find the and user's playlists 
    user_pl = {}
    for i in current_playlists:
        plname = i['name']
        plid = i['id']
        user_pl[plname] = plid
        
    return render_template('spotifypage.html', pl=user_pl )


def get_recommendations(id, slider_values):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
       # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks_data = []
    playlist = sp.playlist_tracks(id)
    
    for track in playlist['items']:
        track_data = {
                'danceability': None,
                'energy': None,
                'loudness': None,
                'speechiness': None,
                'acousticness': None,
                'instrumentalness': None,
                'liveness': None,
                'valence': None,
                'tempo': None,
                'id': track['track']['id']
            }
        
        audio_features = sp.audio_features([track['track']['uri']])[0]
        if audio_features:
            track_data['danceability'] = audio_features['danceability']
            track_data['energy'] = audio_features['energy']
            track_data['loudness'] = audio_features['loudness']
            track_data['speechiness'] = audio_features['speechiness']
            track_data['acousticness'] = audio_features['acousticness']
            track_data['instrumentalness'] = audio_features['instrumentalness']
            track_data['liveness'] = audio_features['liveness']
            track_data['valence'] = audio_features['valence']
            track_data['tempo'] = audio_features['tempo']
            
        tracks_data.append(track_data)

        playlist_features = pd.DataFrame(tracks_data)
        playlist_features.drop_duplicates('id')
        all_songs_df = pd.read_csv(r'C:\Users\alext\OneDrive\Desktop\ml_data\tracksgenres.csv')

        #rearrange columns to match the user dataframe
        all_songs_df_order = ['artists','genres', 'id', 'track_pop','danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo']
        all_songs_features_order = ['danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo','id']
        all_songs_df = all_songs_df[all_songs_df_order]
        all_songs_features = all_songs_df[all_songs_features_order] 
        
        # Find all non-playlist song features
        playlistfeatures = playlist_features.drop(columns = "id")
        playlistfeatures = playlistfeatures.sum(axis=0)
        
        print("before adding sliders:", playlistfeatures)
  
        for index in playlistfeatures.index:
            if index in slider_values:
                playlistfeatures[index] += slider_values[index]

        print("after adding sliders: ", playlistfeatures)
        
        non_playlist_df = all_songs_df[all_songs_df['id'].isin(all_songs_features['id'].values)]
        
        # Find cosine similarity between the playlist and the complete song set
        non_playlist_df['sim'] = cosine_similarity(all_songs_features.drop('id', axis = 1).values, playlistfeatures.values.reshape(1, -1))[:,0]
        recommendations = non_playlist_df.sort_values('sim',ascending = False).head(40)
        
        #convert to dict
        recommendations_dict = recommendations.set_index('artists')['id'].to_dict()
        
        #func to find song title
        def get_song_title(track_id):
            track_info = sp.track(track_id)
            return track_info['name']

        #get the song title for the id
        recommendations_dict = {artist: get_song_title(track_id) for artist, track_id in recommendations_dict.items()}
            
        return(recommendations_dict)


@app.route('/playlist/<string:id>')
def playlist_page(id):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    # get the user's playlists
    songs = []
    current_playlists =  sp.current_user_playlists()['items']
   
    for pl in current_playlists:
        # find the requested playlist using id
        if pl['id'] == id:
            name = pl['name']
            id = pl['id']
            #get the playlist tracks
            playlist = sp.playlist_tracks(id)
            for song in playlist['items']:
                songs.append(song)
            # getting around the 100 song limit - extend the array when items remain in the playlist
            while playlist['next']:
                playlist = sp.next(playlist)
                songs.extend(playlist['items'])
            # display the html page 
            return render_template('playlist.html', pname = name, psongs = songs, id = id )
        
    # return error page if no playlist found or other errors occur     
    return render_template('error.html', error_text = "playlist not found")


@app.route('/getRecommendations/<string:id>',  methods=['GET', 'POST'])
def recommendations_page(id):
    slider_values = {
        'valence' : float(request.form.get('slider1')),
        'danceability': float(request.form.get('slider2')),
        'energy' : float(request.form.get('slider3')),
        'loudness' : float(request.form.get('slider4')),
        'tempo' : float(request.form.get('slider5'))
    }
    
    recommendations_dict = get_recommendations(id, slider_values)
    return render_template('recommendations.html', recommendations_dict = recommendations_dict)
            
# function to get the token info from the session
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))
    
    # check if the token is expired and refresh it if necessary
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info

def create_spotify_oauth():
    #create the client id, secret, redirect uri and scope for login
    return SpotifyOAuth(
        client_id = '6584944ee0d9495480193d9997a9efb7',
        client_secret = 'ac4205f012b64179acd46c0fbdb33f36',
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private'
    )
    
app.run(debug=True)

