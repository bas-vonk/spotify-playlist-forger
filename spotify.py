from typing import List, Dict
from config import playlist_config, song_criteria, OAUTH_TOKEN
from random import shuffle
import dateutil.parser as parser
import requests
import pandas as pd
import sys

API_BASE = 'https://api.spotify.com/v1'
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer " + OAUTH_TOKEN
}


def call_api_and_return_json(uri, http_method, json=None):

    if http_method == 'GET':
        r = requests.get(uri, headers=HEADERS)
    elif http_method == 'POST':
        assert json is not None, "Json not provided for POST request."
        r = requests.post(uri, headers=HEADERS, json=json)
    else:
        raise ValueError("http_method not set or not in ['GET', 'POST'].")

    r.raise_for_status()
    return r.json()


def chunk_list(l: List, n: int) -> List[List]:
    """Get successive n-sized chunks from l."""
    # https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    return [l[i:i + n] for i in range(0, len(l), n)]


def get_all_tracks() -> List:
    """Short summary.

    Parameters
    ----------
    token : str
        Description of parameter `token`.
    headers : str
        Description of parameter `headers`.

    Returns
    -------
    List
        Description of returned object.

    """

    # Initialize tracks
    tracks = []

    offset = 0
    body = call_api_and_return_json(API_BASE + '/me/tracks?limit=50&offset=' + str(offset),
                                    'GET')
    tracks = body['items']

    while len(body['items']) is 50:

        offset += 50
        body = call_api_and_return_json(API_BASE + '/me/tracks?limit=50&offset=' + str(offset),
                                        'GET')
        tracks += body['items']

    return tracks


def get_audio_features_dictionary(tracks: List) -> Dict:
    """Short summary.

    Parameters
    ----------
    tracks : List
        Description of parameter `tracks`.

    Returns
    -------
    Dict
        Description of returned object.

    """

    LIMIT = 100

    track_ids = [d['track']['id'] for d in tracks]
    track_ids_chunked = chunk_list(track_ids, LIMIT)

    audio_features_dictionary = {}
    for track_ids in track_ids_chunked:
        body = call_api_and_return_json(API_BASE + '/audio-features?ids=' + ','.join(track_ids), 'GET')
        for track in body['audio_features']:
            audio_features_dictionary[track['id']] = track

    return audio_features_dictionary


def get_artists_dictionary(tracks: List) -> Dict:
    """Short summary.

    Parameters
    ----------
    tracks : List
        Description of parameter `tracks`.

    Returns
    -------
    Dict
        Description of returned object.

    """

    LIMIT = 50

    artists = [d['track']['artists'] for d in tracks]
    artist_ids = []
    for all_artists in artists:
        for artist in all_artists:
            artist_ids.append(artist['id'])
    artist_ids = list(set(artist_ids))
    artist_ids_chunked = chunk_list(artist_ids, LIMIT)

    artists_dictionary = {}
    for artist_ids in artist_ids_chunked:
        body = call_api_and_return_json(API_BASE + '/artists?ids=' + ','.join(artist_ids), 'GET')
        for artist in body['artists']:
            artists_dictionary[artist['id']] = artist

    return artists_dictionary


def get_genres_for_artist_ids(genres_by_artist_id: Dict, artist_ids: List) -> List:
    """Short summary.

    Parameters
    ----------
    genres_by_artist_id : Dict
        Description of parameter `genres_by_artist_id`.
    artist_ids : List
        Description of parameter `artist_ids`.

    Returns
    -------
    List
        Description of returned object.

    """

    genres = []
    for artist_id in artist_ids:
        genres = genres + genres_by_artist_id[artist_id]

    return list(set(genres))


def get_df_songs():
    """Short summary.

    Returns
    -------
    type
        Description of returned object.

    """

    tracks = get_all_tracks()

    audio_features_by_track_id = get_audio_features_dictionary(tracks=tracks)

    artists_by_id = get_artists_dictionary(tracks=tracks)

    genres_by_artist_id = get_genres_dictionary(artists_by_id=artists_by_id)

    songs = []
    for track in tracks:

        audio_features = audio_features_by_track_id.get(track['track']['id'])

        song = {
            "id": track['track']['id'],
            "uri": track['track']['uri'],
            "title": track['track']['name'],
            "artists": [d['name'] for d in track['track']['artists']],
            "genres": get_genres_for_artist_ids(genres_by_artist_id,
                                                [d['id'] for d in track['track']['artists']]),
            "year": parser.parse(track['track']['album']['release_date']).year,
            "popularity": track['track']['popularity'],
            "bpm": audio_features['tempo'],
            "acousticness": audio_features['acousticness'],
            "danceability": audio_features['danceability'],
            "energy": audio_features['energy']
        }

        songs.append(song)

    # Create songs dataframe
    df_songs = pd.DataFrame(songs)
    df_songs.set_index('id', inplace=True)

    return df_songs


def get_genres_dictionary(artists_by_id):
    """Short summary.

    Parameters
    ----------
    artists_by_id : type
        Description of parameter `artists_by_id`.

    Returns
    -------
    type
        Description of returned object.

    """

    return {key: val['genres'] for key, val in artists_by_id.items()}


def create_playlist_and_add_songs(playlist_data, spotify_uris):
    """Short summary.

    Parameters
    ----------
    playlist_data : type
        Description of parameter `playlist_data`.
    spotify_uris : type
        Description of parameter `spotify_uris`.

    Returns
    -------
    type
        Description of returned object.

    """

    LIMIT = 100

    body = call_api_and_return_json(API_BASE + '/users/bas_vonk/playlists', 'POST',
                                    json=playlist_data)

    playlist_id = body['id']

    spotify_uris_chunked = chunk_list(spotify_uris, LIMIT)

    for spotify_uris in spotify_uris_chunked:
        call_api_and_return_json(API_BASE + '/playlists/' + playlist_id + '/tracks', 'POST',
                                 json={"uris": spotify_uris})


def main():
    """Short summary.

    Returns
    -------
    type
        Description of returned object.

    """

    # Get dataframe with all songs available for the user
    df_songs = get_df_songs()

    # Apply the criteria to create an additional 'select column'
    df_songs['select'] = df_songs.apply(lambda row: song_criteria(row), axis=1)

    # Select the spotify URIs
    spotify_uris = df_songs['uri'].loc[df_songs['select']].tolist()
    shuffle(spotify_uris)
    create_playlist_and_add_songs(playlist_data=playlist_config,
                                  spotify_uris=spotify_uris)

    return df_songs.loc[df_songs['select']]


if __name__ == '__main__':

    try:

        songs = main()
        print(songs[['title', 'artists', 'year']].to_string())
        print(songs.describe())
        print("Playlist succesfully created!")

    except requests.exceptions.HTTPError as error:
        print(error)
