#################################
##### Name: Shujie Li       #####
##### Uniqname: lishujie    #####
#################################

from bs4 import BeautifulSoup
import requests
import json
import secrets
import sqlite3
import pandas as pd
import plotly
import plotly.express as px
from time import time



CACHE_FILENAME = "final_proj_cache.json"
CACHE_DICT = {}

class Chart:

    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.rank_dic = None


class Item:

    def __init__(self, name, info, rank):
        self.name = name
        self.info = info
        self.rank = rank
        self.youtube_info = None

    def content(self):
        return f"rank{self.rank}: {self.name} ({self.info})"

class Video:

    def __init__(self, name, videoid, views, likes, dislikes):
        self.name = name
        self.videoid = videoid
        self.views = views
        self.likes = likes
        self.dislikes = dislikes


def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_file.close()
        prev_dic = json.loads(cache_contents)
    except:
        prev_dic = {}

    prev_dic.update(cache_dict)
    dumped_json_cache = json.dumps(prev_dic)
    fw = open(CACHE_FILENAME, 'w')
    fw.write(dumped_json_cache)
    fw.close()

def construct_unique_key(baseurl, params):
    ''' constructs a key that is guaranteed to uniquely and 
    repeatably identify an API request by its baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs
    
    Returns
    -------
    string
        the unique key as a string
    '''
    items = [baseurl]
    for item in params.items():
        items.extend([str(item[0]), str(item[1])])

    return '_'.join(items)


def make_request_with_cache(url, params=None):
    '''Check the cache for a saved result for this baseurl+params:values
    combo. If the result is found, return it. Otherwise send a new 
    request, save it, then return it.

    Parameters
    ----------
    url: string
        The URL for the API endpoint
    
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
    if params:
        unique_key = construct_unique_key(url, params)
    else:
        unique_key = url

    cache_dic = open_cache()
    if unique_key in cache_dic.keys():
        print('Using Cache')
        result = cache_dic[unique_key]
    else:
        print('Fetching')
        result = requests.get(url, params).text
        save_cache({unique_key: result})

    return result


def get_popular_charts():
    
    '''get popular charts from the billboard website.

    Parameters
    ----------
    None
    
    Returns
    -------
    dic
        dictionary with popular charts and it‘s serial number
    '''
    
    baseurl = 'https://www.billboard.com'
    chart_url = 'https://www.billboard.com/charts'
    response = make_request_with_cache(chart_url)
    # response = requests.get(chart_url).text
    soup = BeautifulSoup(response, 'html.parser')
    top_charts = soup.find(id='topchartsChartPanel')
    charts = top_charts.find_all(class_='chart-panel__link')
    chart_dic = {}

    for i,c in enumerate(charts):
        sub_url = c['href']
        url = baseurl + sub_url
        name = c.find(class_='chart-panel__text').text.strip()
        chart_dic[i+1] = Chart(name, url)
        print(f"[{i+1}]: {name}")

    return chart_dic

def get_chart_rank(url):
    
    '''get chart ranking from the url.

    Parameters
    ----------
    string
        url of the specific chart
    
    Returns
    -------
    dic
        dictionary with ranking of the chart
    '''
    
    response = make_request_with_cache(url)
    # response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    rank_list = soup.find(class_='chart-list__elements').find_all('li', recursive=False)[0:20]
    rank_dic = {}

    for i,item in enumerate(rank_list):
        rank = item.find(class_='chart-element__rank__number').text.strip()
        name = item.find(class_='chart-element__information__song').text.strip()
        info = item.find(class_='chart-element__information__artist').text.strip()
        rank_item = Item(name, info, rank)
        rank_dic[i+1] = rank_item
        print(rank_item.content())

    return rank_dic

def get_youtube_info(name):

    '''get the youtube video information about the term

    Parameters
    ----------
    string
        name of the specific term
    
    Returns
    -------
    list
        list of video instances related to the search term
    '''
    
    baseurl = 'https://www.googleapis.com/youtube/v3/search'
    params = {'key': secrets.API_KEY, 'part': 'snippet', 'q': name, 'maxResults': 20, 'type': 'video', 'order': 'viewCount'}
    response = make_request_with_cache(baseurl, params)
    # response = requests.get(baseurl, params).text
    result = json.loads(response)
    videos = []

    for item in result['items']:
        name = item['snippet']['title']
        videoid = item['id']['videoId']
        views, likes, dislikes = get_video_statistics(videoid)
        video_instance = Video(name, videoid, views, likes, dislikes)
        videos.append(video_instance)

    return videos



def get_video_statistics(id):

    '''get the youtube video statistics (viwcounts, likes, dilikes) about the video

    Parameters
    ----------
    string
       id of the video
    
    Returns
    -------
    int
        3 numbers: viewCount, likeCount, dislikeCount
    '''
    
    baseurl = 'https://www.googleapis.com/youtube/v3/videos'
    params = {'key': secrets.API_KEY, 'part': 'statistics', 'id': id}
    response = make_request_with_cache(baseurl, params)
    # response = requests.get(baseurl, params).text
    result = json.loads(response)
    video_info = result['items'][0]['statistics']
    views = int(video_info['viewCount']) if 'viewCount' in video_info.keys() else 0
    likes = int(video_info['likeCount']) if 'likeCount' in video_info.keys() else 0
    dislikes = int(video_info['dislikeCount']) if 'dislikeCount' in video_info.keys() else 0

    return views, likes, dislikes

def create_db_table(name, videos):
    
    '''plot the graphs for the video list,
    including views vs likes and views vs dislikes,

    Parameters
    ----------
    string
        name of the search term
    
    list
        list of video instances

    
    Returns
    -------
    plots
        two plots views vs likes and views vs dislikes
    '''

    conn = sqlite3.connect("videos.sqlite")
    cur = conn.cursor()

    check_query = f'''
        SELECT CASE WHEN EXISTS 
        (SELECT * FROM sqlite_master WHERE type="table" AND name="{name}") 
        THEN 1 ELSE 0 END AS table_exist
    '''

    if cur.execute(check_query).fetchone()[0] == 0:

        create_table = f'''

            CREATE TABLE IF NOT EXISTS "{name}" (
                "Id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                "VideoName" TEXT NOT NULL,
                "VideoId" TEXT NOT NULL,
                "Views" INTEGER NOT NULL,
                "Likes" INTEGER NOT NULL,
                "Dislikes" INTEGER NOT NULL
            )

        '''
        cur.execute(create_table)

        for video in videos:
            videoname = video.name
            videoid = video.videoid
            views = video.views
            likes = video.likes
            dislikes = video.dislikes

            insert_data = f'''

                INSERT INTO "{name}" (VideoName, VideoId, Views, Likes, Dislikes)
                VALUES ("{videoname}", "{videoid}", {views}, {likes}, {dislikes});

            '''
            cur.execute(insert_data)


        conn.commit()

def fetch_data_from_table(name):
    
    '''fetch the reqired data from database

    Parameters
    ----------
    string
        name of the search term


    Returns
    -------
    database
        database of required data
    '''

    conn = sqlite3.connect("videos.sqlite")

    query = f"""
        SELECT VideoName, Likes, Dislikes FROM "{name}"
    """
    df = pd.read_sql(query, conn)

    return df

def plot_video_info(df):

    '''plot the graphs for the video list,
    including views vs likes and views vs dislikes,

    Parameters
    ----------
    database
        database of required video data (views, likes, dislikes)

    
    Returns
    -------
    plots
        two plots views vs likes and views vs dislikes
    '''
    fig = px.bar(df, x=df['VideoName'], y=['Likes', 'Dislikes'])
    fig.show()




if __name__ == '__main__':

    tic = time()

    chart_dic = get_popular_charts()
    rank_dic = get_chart_rank(chart_dic[1].url)
    videos = get_youtube_info(rank_dic[1].name)
    get_video_statistics('adLGHcj_fmA')
    create_db_table(rank_dic[1].name, videos)
    df = fetch_data_from_table(rank_dic[1].name)
    plot_video_info(df)

    toc = time()
    print(f'{toc-tic: .2f}s')
