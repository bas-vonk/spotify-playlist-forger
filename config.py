OAUTH_TOKEN = "OAUTH TOKEN"

# song_criteria = lambda row: row['year'] > 1989 and row['year'] < 2000
# song_criteria = lambda row: 'pop' in row['genres']
# song_criteria = lambda row: row['energy'] > 0.9
song_criteria = lambda row: row['danceability'] > 0.8

playlist_config = {
    "name": "# DANCEABILITY 0.8+",
    "description": "Danceable",
    "public": False,
}
