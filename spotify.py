# import necessary modules
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, render_template
import os


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
    print(sp.me())
    current_playlists =  sp.current_user_playlists()['items']


    # find the and user's playlists 
    user_pl = {}
    for i in current_playlists:
        plname = i['name']
        plid = i['id']
        user_pl[plname] = plid
        
    return render_template('spotifypage.html', pl=user_pl )


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
        if pl['id'] == id:
            name = pl['name']
            id = pl['id']
            playlist = sp.playlist_tracks(id)
            for song in playlist['items']:
                songs.append(song)
            while playlist['next']:
                playlist = sp.next(playlist)
                songs.extend(playlist['items'])
            return render_template('playlist.html', pname = name, psongs = songs)

        
    return render_template('error.html', error_text = "playlist not found")
            
            
    
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
    return SpotifyOAuth(
        client_id = '6584944ee0d9495480193d9997a9efb7',
        client_secret = 'ac4205f012b64179acd46c0fbdb33f36',
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private'
    )
    
app.run(debug=True)

#session problem - need to get rid of the access token!