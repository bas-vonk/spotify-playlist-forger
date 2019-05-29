from typing import List, Dict
import dateutil.parser as parser
import requests
import pandas as pd
import sys


token = 'BQDBllyp3bktpOe5UCpAkBBiTz_dRE3ACqpnRuBEBKdnVIw6CBH8PDDTBPPwoL0REQj2C3z_HKZti_591JftMd1D2Sz6G1M0poppk8cyUfjgq5KwHDtlwzcCR8IebitQsrU1vVboe4gxP1oKf9qIF7EqFhT1nkucma6dOFbt0WcaoBWxOSIeTri1qZJSyf3KV_VCCBg8K4M-udc7uyHvAOgZk8nr4h8UP64YiE4bAy4neMFdHxzFzPnkruRDVtO2ZxoyN-S7v7RNHP4R'

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer " + token
}


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

    tracks = []
    offset = 0

    body = requests.get('https://api.spotify.com/v1/me/tracks?limit=50&offset=' + str(offset), headers=headers).json()
    tracks = body['items']

    while len(body['items']) is 50:

        offset += 50
        body = requests.get('https://api.spotify.com/v1/me/tracks?limit=50&offset=' + str(offset), headers=headers).json()
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
        result = requests.get('https://api.spotify.com/v1/audio-features?ids=' + ','.join(track_ids), headers=headers).json()
        for track in result['audio_features']:
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
        result = requests.get('https://api.spotify.com/v1/artists?ids=' + ','.join(artist_ids), headers=headers).json()
        for artist in result['artists']:
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
    df_songs.set_index('id', inplace = True)

    print(df_songs.describe())

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

    return {key : val['genres'] for key, val in artists_by_id.items()}


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

    r = requests.post('https://api.spotify.com/v1/users/bas_vonk/playlists',
                      json=playlist_data,
                      headers=headers)
    playlist_id = r.json()['id']

    spotify_uris_chunked = chunk_list(spotify_uris, LIMIT)

    for spotify_uris in spotify_uris_chunked:

        data = {
            "uris": spotify_uris
        }

        r = requests.post('https://api.spotify.com/v1/playlists/' + playlist_id + '/tracks',
                          json=data,
                          headers=headers)


def print_selection(df_songs):
    """Print selection.

    Parameters
    ----------
    df_songs : type
        Description of parameter `df_songs`.

    """

    print(df_songs[['title', 'artists', 'year']].loc[df_songs['select']])


def main():
    """Short summary.

    Returns
    -------
    type
        Description of returned object.

    """

    # Get dataframe with all songs
    df_songs = get_df_songs()

    # Define playlist data
    playlist_data = {
        "name": "Pop",
        "description": "Test",
        "public": False
    }

    # Define the lambda function
    #criteria = lambda row: row['year'] > 1989 and row['year'] < 2000
    #criteria = lambda row: row['bpm'] > 120 and row['danceability'] > 0.8
    criteria = lambda row: 'pop' in row['genres']

    # Add dummy column with a selection boolean
    df_songs['select'] = df_songs.apply(lambda row: criteria(row), axis=1)

    # Print selection
    print_selection(df_songs)

    spotify_uris = df_songs['uri'].loc[df_songs['select']].tolist()

    create_playlist_and_add_songs(playlist_data=playlist_data,
                                  spotify_uris=spotify_uris)


if __name__ == '__main__':

    main()
