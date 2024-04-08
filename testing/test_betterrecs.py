import pytest
from betterrecs import *
from flask import session

# simulate an access token
TOKEN_INFO = {"access_token":
    "BQB-RAzKcTjP8kcT8-rfw4kbL0f8UgMmzx-Ds-YwhvS7ZydMxPAEbIc7d3ReLyODaGhj-Ll7B2eC3TEHKtwM50NxwmhNtvx0hXVvt6GO8AVFSVI6WyUW6WknCa1POMNOWbV3HbfgPmfkbH3R9fpvx3yczQsl1GsHzWE2ql4NMkivufCzbBL9HjEZzMrI8_cp7f-zEOhgCdBuyZeqCoBX97i_I4dMwKMJOzbTzfA8-OlcAf8ot9pYJQlFO6sQ",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "user-library-read playlist-modify-public playlist-modify-private user-top-read",
    "expires_at": 1710793219,
    "refresh_token": "AQCIsxkgAw_zlB2F8ZEiiAPMOaFczmUrG-LBOFhXdt9DpTidaZ18EVsvXVl9Bki91EuaeH1haFQjEpS890SV-mHSc9T_b6Mg_gWasHWfCjFmP3tkzZK3J7MLwIsAxhAx7xc"
    }
username = "alextsiogas"

@pytest.fixture
# set up testing client
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# test profile app route w valid token
def test_profile_route_with_valid_token(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    response = client.get('/profile?time_range=short_term')
    assert response.status_code == 200


# test profile app route w invalid token
def test_profile_route_with_invalid_token(client):
    response = client.get('/profile')
    assert response.status_code == 302
  
    
# test get profile info with a valid token - should be logged in as my account
def test_get_profile_info(client):
    result = get_profile_info(TOKEN_INFO)
    assert result == 'alextsiogas'


# test get top artists function
def test_get_top_artists_integration():
    result = get_top_artists('long_term', TOKEN_INFO)
    # assert that the result is a dictionary (indicating a successful call)
    assert isinstance(result, dict)


def test_get_top_artists_no_token():
    with pytest.raises(KeyError):
        # simulate no access token by passing an empty dictionary
        get_top_artists('long_term', {})


# test get top songs function
def test_get_top_tracks_integration():
    result = get_top_tracks('long_term', TOKEN_INFO)
    # assert that the result is a list of tracks as tuples (indicating a successful call)
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) for item in result)
    
    
def test_get_top_tracks_no_token():
    with pytest.raises(KeyError):
        # simulate no access token by passing an empty dictionary
        get_top_tracks('long_term', {})
        
        
# test view_playlists app route w valid token
def test_view_playlists_with_valid_token(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    response = client.get('/viewPlaylists')
    assert response.status_code == 200


# test view_playlists app route w invalid access token
def test_view_playlists_with_invalid_token(client):
    response = client.get('/viewPlaylists')
    assert response.status_code == 302
    
    
# test playlist route with a valid playlist id and valid access token
def test_playlist_page_with_valid_id(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    # make a GET request to the playlist page route with a valid playlist ID
    response = client.get('/playlist/7p1c7RCxxR9JDdLsRb6fRE')
    assert response.status_code == 200


# test playlist route with an invalid playlist id and valid access token
def test_playlist_page_with_invalid_id(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    # make a GET request to the playlist page route with an invalid playlist ID
    response = client.get('/playlist/invalid_playlist_id')
    assert response.status_code == 302
    assert b'playlist not found' in response.data.lower()
    
    
# test playlist route with a valid playlist id and invalid access token
def test_playlist_page_with_invalid_token(client):
    response = client.get('/playlist/7p1c7RCxxR9JDdLsRb6fRE')
    assert response.status_code == 302

# test recommendations page route with valid playlst id 
def test_recommendations_page_with_valid_id(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
        # Make a GET request to the recommendations page route with a valid playlist ID and slider values
        response = client.get('/getRecommendations/7p1c7RCxxR9JDdLsRb6fRE', query_string={'slider1': '0.5', 'slider2': '0.7', 'slider3': '0.8', 'slider4': '0.6', 'slider5': '0'})
        assert response.status_code == 302  


# test get concerts function w valid playlist
def test_get_concerts_page(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    
    response = client.get('/getConcerts/7p1c7RCxxR9JDdLsRb6fRE')
    # check response code and that a known genre from genres list was returned
    assert response.status_code == 200  
    assert b'alternative rock' in response.data  
    
    
# test get concerts function w invalid token
def test_get_concerts_page(client):
    response = client.get('/getConcerts/7p1c7RCxxR9JDdLsRb6fRE')
    assert response.status_code == 302  


#test generate geohash function with valid coordinates
def test_generate_geohash_valid(client):
    data = {'latitude': 37.7749, 'longitude': -122.4194}
    response = client.post('/geohash', json=data)
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert 'geohash' in response_data

#test generate geohash function with no coordinates
def test_generate_geohash_invalid_token(client):
    response = client.post('/geohash')
    # expecting a 415 response (unexpected payload)
    assert response.status_code == 415


def test_add_to_playlist_valid(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    form_data = {'song_ids[]': '4iVV7MR404y1QRJlWBt2eH', 'add-to-playlist-btn': '1', 'id': '6YhYiQh5lceGuWG14ioxEj'}
    response = client.post('create_playlist',  data=form_data)
    assert b'Playlist created successfully!' in response.data
    

def test_add_to_playlist_invalid(client):
    form_data = {'add-to-playlist-btn': '1', 'id': '6YhYiQh5lceGuWG14ioxEj'}
    response = client.post('create_playlist',  data=form_data)
    assert response.status_code == 302  

def test_regenerate_valid(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    form_data = {'song_ids[]': '4iVV7MR404y1QRJlWBt2eH', 'regenerate-btn': '1', 'id': '6YhYiQh5lceGuWG14ioxEj'}
    response = client.post('create_playlist',  data=form_data)
    assert response.status_code == 200
    
    assert b'id' in response.data
    assert b'recommendations_dict' in response.data
    assert b'song_ids_list' in response.data

def test_regenerate_invalid(client):
    with client.session_transaction() as sess:
        sess['token_info'] = TOKEN_INFO
    form_data = {'regenerate-btn': '1', 'id': '6YhYiQh5lceGuWG14ioxEj'}
    response = client.post('create_playlist',  data=form_data)
    assert response.status_code == 200  
    
    
if __name__ == '__main__':
    pytest.main()
