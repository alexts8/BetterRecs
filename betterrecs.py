# import necessary modules
import ast
import json
import time
import geohash2
from sklearn.preprocessing import MinMaxScaler
import spotipy
import os
from spotipy.oauth2 import SpotifyOAuth
from spotipy.client import SpotifyException
from flask import Flask, jsonify, request, url_for, session, redirect, render_template
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
    file_path = ".cache"
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect("https://accounts.spotify.com/en/logout")


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
    images = []
    for playlist in current_playlists:
        plname = playlist['name']
        plid = playlist['id']
        user_pl[plname] = plid
        
        pl_details = sp.playlist(playlist['id'])
        pl_image = pl_details['images'][0]['url'] if pl_details['images'] else None
        images.append(pl_image)
        
    return render_template('playlist_list.html', pl=user_pl, images=images)


def get_recommendations(id, slider_values=None, song_ids=None):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
       # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    # generate the access token to make an instance of the spotipy object
    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks_data = []

    genres_list = []
    
    # get the playlist
    playlist = sp.playlist_tracks(id)
    
    track_ids = [track['track']['id'] for track in playlist['items']]
    if song_ids:
        for id in song_ids:
            track_ids.append(id)
    print(track_ids)
    
    def get_genres(track_id):
        # Get track information
        track_info = sp.track(track_id)
        
        # Get the list of genres for the first artist of the track
        if 'artists' in track_info and track_info['artists']:
            artist_id = track_info['artists'][0]['id']
            artist_info = sp.artist(artist_id)
                        
            if 'genres' in artist_info:
                return artist_info['genres']
                    
        return None
    
    for track in track_ids:
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
                'genres': None,
                'track_pop': None,
                'id': track
            }
        

        # populate the array with audio features of each track
        audio_features = sp.audio_features(track)[0]
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
            genres = get_genres(track)
            for genre in genres:
                genres_list.append(genre)
            genres_list = list(set(genres_list))
            track_info = sp.track(track)
            popularity = track_info['popularity']
            track_data['track_pop'] = popularity
            
        tracks_data.append(track_data)
        
    # create a track_data array
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
                'genres': None,
                'track_pop': None,
                'id': track['track']['id']
            }
        
    # turn array into a pandas dataframe
    playlist_features = pd.DataFrame(tracks_data)
        
    # get rid of duplicate songs
    playlist_features.drop_duplicates('id')
        
    # get the current directory and the relative path to find the csv file
    # this is a workaround before the database is implemented
    current_dir = os.getcwd()
    relative_path = 'data/tracksgenres.csv'
    file_path = os.path.join(current_dir, relative_path)

    # Read the CSV file using pandas read_csv
    all_songs_df = pd.read_csv(file_path)

    #rearrange columns to match the user dataframe
    all_songs_df_order = ['artists','genres', 'id', 'track_pop','danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo']
    all_songs_features_order = ['danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo', 'track_pop', 'id']
    all_songs_df = all_songs_df[all_songs_df_order]
    all_songs_features = all_songs_df[all_songs_features_order] 
        
    # Find all non-playlist song features
    playlistfeatures = playlist_features.drop(columns = "id")
    playlistfeatures.pop('genres')
    playlistfeatures = playlistfeatures.sum(axis=0)
    
    # add each slider value to the corresponding playlist feature
    if slider_values:
        # print the playlist to the terminal before and after sliders are added, to assure they were applied
        print("before adding sliders:", playlistfeatures)
        for index in playlistfeatures.index:
            if index in slider_values:
                playlistfeatures[index] += slider_values[index]
        print("after adding sliders: ", playlistfeatures)
                
    all_songs_df['genres'] = all_songs_df['genres'].apply(ast.literal_eval)
    # Find cosine similarity between the playlist and the complete song set
    all_songs_df['sim'] = cosine_similarity(all_songs_features.drop('id', axis = 1).values, playlistfeatures.values.reshape(1, -1))[:,0]
    non_playlist_df = all_songs_df[all_songs_df['genres'].apply(lambda x: any(genre in genres_list for genre in x))]
    recommendations = non_playlist_df.sort_values('sim',ascending = False).head(40)
        
    # maintain a list of song ids for later use
    song_ids_list = recommendations['id'].tolist()
        
    recommendations_dict= {}
    for song_id in song_ids_list:
        # Get track information
        track_info = sp.track(song_id)

        # Extract track name
        track_name = track_info['name']

        # Extract first artist name
        artist_name = track_info['artists'][0]['name']

        # Store track name and artist in the dictionary
        recommendations_dict[track_name] = artist_name
            
    return recommendations_dict, song_ids_list, genres_list



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
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    # get the slider values from the form using a GET request
    slider_values = {
        'valence' : float(request.form.get('slider1')),
        'danceability': float(request.form.get('slider2')),
        'energy' : float(request.form.get('slider3')),
        'loudness' : float(request.form.get('slider4')),
        'tempo' : float(request.form.get('slider5'))
    }
    
    # getting recommendations and returning them to the recommendations.html page
    recommendations_dict, song_ids_list, genres = get_recommendations(id, slider_values)
    return render_template('recommendations.html', id = id, recommendations_dict = recommendations_dict, song_ids_list = song_ids_list, genres=genres )


def get_concerts(id):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
       # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    # generate the access token to make an instance of the spotipy object
    sp = spotipy.Spotify(auth=token_info['access_token'])
    genres_list = []
    
    # get the playlist
    playlist = sp.playlist_tracks(id)
    
    track_ids = [track['track']['id'] for track in playlist['items']]
    
    def get_genres(track_id):
        # Get track information
        track_info = sp.track(track_id)
        
        # Get the list of genres for the first artist of the track
        if 'artists' in track_info and track_info['artists']:
            artist_id = track_info['artists'][0]['id']
            artist_info = sp.artist(artist_id)
                        
            if 'genres' in artist_info:
                return artist_info['genres']
                    
        return None
    
    for track in track_ids:
        genres = get_genres(track)
        for genre in genres:
            genres_list.append(genre)
        genres_list = list(set(genres_list))
    
    return genres_list

@app.route('/geohash', methods=['POST'])
def generate_geohash():
    data = request.json
    latitude = data['latitude']
    longitude = data['longitude']
    precision = 9

    geohash = geohash2.encode(latitude, longitude, precision)
    return {'geohash': geohash}
            

@app.route('/getConcerts/<string:id>',  methods=['GET', 'POST'])
def get_concerts_pg(id):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    genres_list = get_concerts(id)

    return render_template("concerts.html", genres_list = genres_list)



@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    song_ids = request.form.getlist('song_ids[]')
    print('Song IDs:', song_ids)
    
    if len(song_ids) == 0:
        return "Select at least one song to add!"
        
    if 'add-to-playlist-btn' in request.form:
        try:
            username = sp.current_user()['id']

            playlist = sp.user_playlist_create(user=username, name="BetterRecs. Playlist", public=True)
            
            sp.playlist_add_items(playlist['id'], song_ids)
            
            return "Playlist created successfully!"

        except SpotifyException as e:
            # Handle Spotify API exception
            return f"Error Creating Playlist: {e}"
        
    elif 'regenerate-btn' in request.form:
        
        id = request.form.get('id')
        recommendations_dict, song_ids_list, genres = get_recommendations(id, None, song_ids)
        
        response_data = {
        'id': id,
        'recommendations_dict': recommendations_dict,
        'song_ids_list': song_ids_list
        }

        return jsonify(response_data)

    return "ERROR: Unknown Action"

            
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
        client_id = 'ac6f1f1226104632a114669a4b2fc962',
        client_secret = 'b942dbcd77234e9f809564415f95c7e6',
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private'
    )

app.run(debug=True)