# import necessary modules
import ast
import json
import time
import geohash2
import pymysql
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
app.secret_key = '######'

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

# route to handle logging out
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
    # render the homepage
    return render_template('home.html')

# route to show the user profile page and gather all data needed for it
@app.route('/profile')
def profile():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    # find what time range data has been requested for
    time_range = request.args.get('time_range', "short_term")
      
    #retrieve username , list of tracks, and list of artists for the given time range
    username = get_profile_info(token_info)
    tracks_lt = get_top_tracks(time_range, token_info)
    artists_lt = get_top_artists(time_range, token_info)
    audio_analysis = get_audio_analysis(time_range, token_info)
    
    #this time variable is used in the html template to show the suer which time period they're viewing
    if time_range == "short_term":
        time = "Last 4 Weeks"
    elif time_range == "medium_term":
        time = "Last 6 Months"
    elif time_range == "long_term":
        time = "Last Year"
    else:
        time = "Unknown"
        
    # render the profile page
    return render_template('profile.html', username = username, artists_lt = artists_lt,
                           tracks_lt = tracks_lt, time=time, audio_analysis = audio_analysis)

#function to retrieve user's username from their profile info
def get_profile_info(token_info):
    #create the spotipy object and make the call
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_info = sp.current_user()
    #return the display name
    username = None
    if 'display_name' in user_info:
        username = user_info['display_name']
    return (username)

#function to retrieve user's top artists for a given time range
def get_top_artists(time_range, token_info):
    #create the spotipy object and make the call for 20 top artists
    sp = spotipy.Spotify(auth=token_info['access_token'])
    artists_lt = sp.current_user_top_artists(limit=20, offset=0, time_range=time_range)
    artists_dict = {}
    #store artist name and images in a dictionary and return
    for artist in artists_lt['items']:
        name = artist['name']
        image_url = artist['images'][0]['url'] if artist['images'] else None
        artists_dict[name] = image_url
        
    return (artists_dict)

#function to retrieve user's top tracks for a given time range
def get_top_tracks(time_range, token_info):
    #create the spotipy object and make the call for 20 top tracks
    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks_lt = sp.current_user_top_tracks(limit=20, offset=0, time_range=time_range)
    tracks_info_list = []
    #store artist name, track name, album image list and return
    for track in tracks_lt['items']:
        name = track['album']['artists'][0]['name']
        track_id = track['id']
        track_info = sp.track(track_id)
        track_name = track_info['name']
        image_url = track['album']['images'][0]['url'] if track['album']['images'] else ''  
        tracks_info_list.append((name, track_name, image_url))
    return tracks_info_list

#function to retrieve user's auidio analysis for a given time range
def get_audio_analysis(time_range, token_info):
    #create the spotipy object and make the call for 20 top tracks
    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks_lt = sp.current_user_top_tracks(limit=20, offset=0, time_range=time_range)

    # get track IDs from the top tracks
    track_ids = [track['id'] for track in tracks_lt['items']]
    # use track ids to get audio features
    audio_features = sp.audio_features(track_ids)

    # initialize vars to store total values
    total_danceability = 0
    total_energy = 0
    total_loudness = 0
    total_instrumentalness = 0
    total_valence = 0
    total_tempo = 0

    # iterate through audio features and add values
    for track_features in audio_features:
        total_danceability += track_features['danceability']
        total_energy += track_features['energy']
        total_loudness += track_features['loudness']
        total_instrumentalness += track_features['instrumentalness']
        total_valence += track_features['valence']
        total_tempo += track_features['tempo']

        # get the averages
        num_tracks = len(audio_features)
        avg_danceability = total_danceability / num_tracks
        avg_energy = total_energy / num_tracks
        avg_loudness = total_loudness / num_tracks
        avg_instrumentalness = total_instrumentalness / num_tracks
        avg_valence = total_valence / num_tracks
        avg_tempo = total_tempo / num_tracks

    # set mins and maxes for normalizing features
    min_loudness = -20
    max_loudness = 0
    min_tempo = 0
    max_tempo = 200

    # function to handle normalization =
    def normalize_value(value, min_val, max_val):
        return (value - min_val) / (max_val - min_val)

    # normalize the irregualr values (loudness and tempo)
    normalized_loudness = normalize_value(avg_loudness, min_loudness, max_loudness)
    normalized_tempo = normalize_value(avg_tempo, min_tempo, max_tempo)

    # construct a dictionary of normalized values
    audio_analysis_dict = {
    'Danceability': avg_danceability,
    'Energy': avg_energy,
    'Loudness': avg_loudness,
    'Instrumentalness': avg_instrumentalness,
    'Happiness': avg_valence,
    'Loudness': normalized_loudness,
    'Tempo': normalized_tempo
    }
    
    return(audio_analysis_dict)
    
    
# application route for viewing playlists
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
        # store playlist names, ids, and imagesto be rendered to the html page
        plname = playlist['name']
        plid = playlist['id']
        user_pl[plname] = plid
        
        pl_details = sp.playlist(playlist['id'])
        pl_image = pl_details['images'][0]['url'] if pl_details['images'] else None
        images.append(pl_image)
        
    # render tht html template
    return render_template('playlist_list.html', pl=user_pl, images=images)

# main function for generating song recommendations - this function encapsulates the entire machine learning model
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
    
    # initialize variables to store tracks and genres
    tracks_data = []
    genres_list = []
    
    # get the playlist
    playlist = sp.playlist_tracks(id)
    
    # get track ids from playlist
    track_ids = [track['track']['id'] for track in playlist['items']]
    if song_ids:
        for id in song_ids:
            track_ids.append(id)
    
    # function to get genres from track ids
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
    
    # loop through tracks
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
            # grab the genres for this track
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
        
    # if the database hasnt been queried yet for this session, function to get the all songs df must be run
    if 'all_songs_df' not in globals():
        create_all_songs_df()
        
    #rearrange columns to match the user dataframe
    all_songs_df_order = ['artists','genres', 'id', 'track_pop','danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo']
    all_songs_features_order = ['danceability','energy','loudness','speechiness','acousticness','instrumentalness','liveness','valence','tempo', 'track_pop', 'id']
    all_songs_df_new = all_songs_df.copy()
    all_songs_df_new = all_songs_df[all_songs_df_order]
    all_songs_features = all_songs_df_new[all_songs_features_order] 
        
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
            
    # convert string representation of genre list into actual list, using ast.literal_eval
    all_songs_df_new['genres'] = all_songs_df_new['genres'].apply(ast.literal_eval)
    # Find cosine similarity between the playlist and the complete song set
    all_songs_df_new['sim'] = cosine_similarity(all_songs_features.drop('id', axis = 1).values, playlistfeatures.values.reshape(1, -1))[:,0]
    non_playlist_df = all_songs_df_new[all_songs_df_new['genres'].apply(lambda x: any(genre in genres_list for genre in x))]
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
    
    # return the recommendations, song ids, and genres
    return recommendations_dict, song_ids_list, genres_list


# function to get the all_songs_df from the database
def create_all_songs_df():
    # database connection details
    host = 'fyp-db.cpc2i6c84e9b.eu-west-1.rds.amazonaws.com'  
    port = 3306
    database = 'fypdatabase'
    username = 'admin'
    password = 'fypdatabase'

    # Establish a connection
    conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)
    cursor = conn.cursor()
    print("getting df from database...")
    # run a query to get all songs
    cursor.execute("SELECT danceability, energy, loudness, speechiness, acousticness, instrumentalness, liveness, valence, tempo, track_pop, artists, genres, id FROM Music WHERE genres != '[]'")
    rows = cursor.fetchall()
    cursor.close()
    print("done")
    # assign all songs to a dataframe, stored globally
    global all_songs_df
    all_songs_df = pd.DataFrame(rows, columns=['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'track_pop', 'artists', 'genres','id'])



# route for displaying a selected playlist
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

# route for generating recommendations
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

# function for handling creation of genres list for use in concert API calls
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
    # get track ids from playlist 
    track_ids = [track['track']['id'] for track in playlist['items']]
    
    # function to get genres from playlist track ids
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
    
    # get a list of genres from playlist, for use in generating recommendations
    for track in track_ids:
        genres = get_genres(track)
        for genre in genres:
            genres_list.append(genre)
        genres_list = list(set(genres_list))
    #return list of genres
    return genres_list

# application route for generating geohash
@app.route('/geohash', methods=['POST'])
def generate_geohash():
    # extract latitude and longitude from json request
    data = request.json
    latitude = data['latitude']
    longitude = data['longitude']
    # set the precision to 9
    precision = 9
    # use geohash2 to generate a geohash using the coordinates, and retun it in json
    geohash = geohash2.encode(latitude, longitude, precision)
    return {'geohash': geohash}
            
# application route for generating concert recommendations
@app.route('/getConcerts/<string:id>',  methods=['GET', 'POST'])
def get_concerts_pg(id):
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    
    # get the list of genres for the playlist
    genres_list = get_concerts(id)
    # render the html template
    return render_template("concerts.html", genres_list = genres_list)


# application route for creating a playlist of selected songs OR regenerating recommendations
@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")
    #create spotipy object
    sp = spotipy.Spotify(auth=token_info['access_token'])
    #get tge song ids from the HTML form
    song_ids = request.form.getlist('song_ids[]')
    # assure some songs were selected
    if len(song_ids) == 0:
        return "Select at least one song to add!"
    
    # if user selected to create a playlist
    if 'add-to-playlist-btn' in request.form:
        try:
            # get the current user
            username = sp.current_user()['id']
            # make a new playlist in user's library
            playlist = sp.user_playlist_create(user=username, name="BetterRecs. Playlist", public=True)
            # add the selected songs to that library
            sp.playlist_add_items(playlist['id'], song_ids)
            # return success message
            return "Playlist created successfully!"

        except SpotifyException as e:
            # Handle Spotify API exception
            return f"Error Creating Playlist: {e}"
        
    # if user selected to create a playlist
    elif 'regenerate-btn' in request.form:
        # get playlist id
        id = request.form.get('id')
        # rerun the machine learning model, this time sending the extra selected songs
        recommendations, song_ids_list, genres = get_recommendations(id, None, song_ids)
        #convert to lst of tuples to maintain order
        recommendations_dict = list(recommendations.items())
        # make the json response and return it
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

# function for makng the Spotify OAuth object
def create_spotify_oauth():
    #create the client id, secret, redirect uri and scope for login
    return SpotifyOAuth(
        client_id = 'ac6f1f1226104632a114669a4b2fc962',
        client_secret = 'b942dbcd77234e9f809564415f95c7e6',
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private user-top-read'
    )

# run the app
if __name__ == '__main__':
    app.debug = True
    app.run()
