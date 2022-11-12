import os
import glob
import psycopg2
import pandas as pd

from sql_queries import *


def process_song_file(cur, filepath):
    """
    Description: Processes a song file. Artist data is inserted into the 'artists' table and song data
    is inserted into the 'songs' table.
    
    Args:
        cur (psycopg2.cursor): A database cursor
        filepath (str): A filepath to a song file
    """
    
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    song_data = list(
        df[['song_id', 'title', 'artist_id', 'year', 'duration']].values[0])

    cur.execute(song_table_insert, song_data)

    # insert artist record
    artist_data = list(df[['artist_id', 'artist_name', 'artist_location',
                           'artist_latitude', 'artist_longitude']].values[0])
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    Description: Processes a log file. Time data is inserted into the 'time' table and user information
    is upserted into the 'users' table. Songplay data is inserted into the 'songplays' table.
    
    Args:
        cur (psycopg2.cursor): A database cursor
        filepath (str): A filepath to a log file
    """
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df.loc[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    t = pd.to_datetime(df['ts'], unit='ms')

    # insert time data records
    time_data = [df.ts.values, t.dt.hour.values, t.dt.day.values,
                 t.dt.weekofyear.values, t.dt.month.values, t.dt.year.values,
                 t.dt.weekday.values]
    column_labels = ['start_time', 'hour', 'day',
                     'week', 'month', 'year', 'weekday']
    time_df = pd.DataFrame(dict(zip(column_labels, time_data)))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[['userId', 'firstName', 'lastName',
                  'gender', 'level']]

    # insert user records    
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        result = cur.fetchone()
        if result:
            songid, artistid = result
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = [row.ts, row.userId,
                         row.level, songid, artistid, row.sessionId,
                         row.location, row.userAgent]
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    Description: Processes JSON files located in a specified path and takes the 'process_song_file' or 'process_log_file' functions to process the data.
    
    Args:
        cur (psycopg2.cursor): A database cursor
        conn (psycopg2.connection): A database connection
        filepath (str): A filepath of the directory to process
        func (function): The function to call for each found file
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
    Used to define what will run in the script. This establishes a database connection and processes song & log information from the JSON logs and finally closes the cursor and database connection.
    """
    conn = psycopg2.connect(
        "host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()