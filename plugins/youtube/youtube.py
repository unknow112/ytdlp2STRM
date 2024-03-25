from flask import stream_with_context, Response, send_file, redirect
from sanitize_filename import sanitize
import os
import time
import platform
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n

## -- YOUTUBE CLASS
class Youtube:
    def __init__(self, channel=False, channel_url=False):
        if channel:
            
            self.channel = channel
            self.channel_url = channel_url
            self.channel_id = ""
            if  'keyword-' in channel:
                print("Searching {}...".format(channel))
                self.videos = self.get_search()
            else:
                print("Working channel URL: {}".format(channel_url))
                print('Getting channel ID...')
                self.channel_id = self.get_id()
                print('Generating name folder...')
                self.channel_name_folder = self.get_name_folder()
                print('Getting name...')
                self.channel_name = self.get_name()
                print('Getting description...')
                self.channel_description = self.get_description()
                print('Getting thumbnails...')
                self.thumbs = self.get_thumbs()
                self.channel_poster = self.thumbs['poster']
                self.channel_landscape = self.thumbs['landscape']

                if 'novideo' in channel_url:
                    print('novideo flag, only channel info...')
                    self.videos = []
                else:
                    print('Getting videos...')
                    self.videos = self.get_videos()

    def get_id(self):
        command = [
            'yt-dlp', 
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--restrict-filenames',
            '--ignore-errors',
            '--no-warnings',
            '--playlist-start', '1', 
            '--playlist-end', '1', 
            '--print', 'channel_url', 
            self.channel_url
        ]

        print(' '.join(command))

        self.set_proxy(command)

        output = (
            w.worker(
                command
            ).output()
            .split('\n')
        )

        for line in output:
            if 'channel' in line:
                self.channel_id = (
                    line
                    .rstrip()
                    .split('/')[-1]
                )
        
        if not self.channel_id:
            youtube_channel_url = "https://www.youtube.com/{}".format(
                self.channel.lstrip('/')
            )
            self.channel_url = youtube_channel_url
            self.get_id()
        
        return self.channel_id

    def get_name(self):
        #get channel or playlist name
        if 'list-' in self.channel_name_folder:
            command = ['yt-dlp', 
                    'https://www.youtube.com/playlist?list={}'.format(self.channel.split('list-')[1]), 
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--print', '"%(playlist_title)s"', 
                    '--playlist-items', '1',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--no-warnings']
        else:
            command = ['yt-dlp', 
                        'https://www.youtube.com/{}'.format(self.channel),
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--print', '"%(channel)s"',
                        '--restrict-filenames',
                        '--ignore-errors',
                        '--no-warnings',
                        '--playlist-items', '1',
                        '--compat-options', 'no-youtube-channel-redirect']
        self.set_proxy(command)

        print("Command {}".format(' '.join(command)))
        #self.channel_name = subprocess.getoutput(' '.join(command))
        self.channel_name = w.worker(command).output()
        return sanitize(
            self.channel_name
        )

    def get_name_folder(self):
        self.channel_name_folder = (
            self.channel
            .replace('/user/','@')
            .replace('/streams','')
        )

        return self.channel_name_folder

    def get_description(self):
        #get description
        if platform.system() == "Linux":
            command = [
                'yt-dlp', 
                'https://www.youtube.com/{}'.format(
                    self.channel
                ), 
                '--write-description', 
                '--playlist-items', '0',
                '--output', '"{}/{}.description"'.format(
                    media_folder, 
                    sanitize(self.channel_name)
                )
            ]
            self.set_proxy(command)

            command = (
                command 
                + [
                    '>', 
                    '/dev/null', 
                    '2>&1',
                    '&&', 
                    'cat', 
                    '"{}/{}.description"'.format(
                        media_folder, 
                        sanitize(
                            self.channel_name
                        )
                    )
                ]
            )
            
            #print("Command \n {}".format(' '.join(command)))
            #self.channel_description = subprocess.getoutput(' '.join(command))
            self.channel_description = w.worker(command).output()
            #print("Output \n {}".format(description))
            try:
                os.remove("{}/{}.description".format(media_folder,sanitize(self.channel_name)))
            except:
                pass

        else:
            command = [
                'yt-dlp', 
                'https://www.youtube.com/{}'.format(
                    self.channel
                ), 
                '--write-description', 
                '--playlist-items', '0',
                '--output', '"{}/{}.description"'.format(
                    media_folder, 
                    sanitize(
                        self.channel_name
                    )
                )
            ]
            self.set_proxy(command)

            command = (
                command 
                + [
                    '>', 
                    'nul', 
                    '2>&1', 
                    '&&', 
                    'more', 
                    '"{}/{}.description"'.format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    )
                ]
            )
            
            #print("Command \n {}".format(' '.join(command)))
            try:
                self.channel_description = w.worker(command).output()
            except:
                d_file = open(
                    "{}/{}.description".format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    ),
                    'r',
                    encoding='utf-8'
                )

                self.channel_description = d_file.read()
                d_file.close()


            #print("Output \n {}".format(self.channel_description))
            try:
                os.remove(
                    "{}/{}.description".format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    )
                )
            except:
                pass

        return self.channel_description

    def get_thumbs(self):
        c = 0
        command = ['yt-dlp', 
                    'https://www.youtube.com/{}'.format(self.channel),
                    '--list-thumbnails',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '0']
        self.set_proxy(command)

        #The madness begins... 
        #No comments between lines, smoke a joint if you want understand it
        lines = (
            w.worker(
                command
            ).output()
            .split('\n')
        )

        headers = []
        thumbnails = []
        for line in lines:
            line = ' '.join(line.split())
            if not '[' in line:
                data = line.split(' ')
                if c == 0:
                    headers = data
                else:
                    if not 'ID' in data[0]:
                        row = {}
                        for i, d in enumerate(data):
                            row[headers[i]] = d
                        thumbnails.append(row)
                c += 1
        #finally...

        #get images
        poster = ""
        try:
            url_avatar_uncropped_index = next(
                (index for (index, d) in enumerate(thumbnails) if d["ID"] == "avatar_uncropped"), 
                None
            )
            poster = thumbnails[url_avatar_uncropped_index]['URL']
            #print("Poster found")
        except:
            print("No poster detected")

        landscape = ""
        try:
            url_max_landscape_index = next(
                (index for (index, d) in enumerate(thumbnails) if d["ID"] == "banner_uncropped"), 
                None
            )

            landscape = thumbnails[url_max_landscape_index-1]['URL']
            #print("Landscape found")
        except:
            print("No landscape detected")

        return {
            "landscape" : landscape,
            "poster" : poster
        }

    def get_videos(self):
        #print("Processing videos in channel")
        command = ['yt-dlp', 
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--print', '"%(id)s;%(title)s;%(upload_date)s;%(thumbnail)s;%(description)s;@#"', 
                    '--dateafter', "today-{}days".format(days_dateafter), 
                    '--playlist-start', '1', 
                    '--playlist-end', videos_limit, 
                    '--ignore-errors',
                    '--no-warnings',
                    '{}'.format(self.channel_url)]
        if config['days_dateafter'] == "0":
            command.pop(7)
            command.pop(7)

        self.videos = (
            w.worker(
                command
            ).output()
            .split(';@#')
        )

        return self.videos

    def get_search(self):
        keyword = self.channel.split('-')[1]
        command = ['yt-dlp', 
                        '-f', 'best', 'ytsearch10:["{}"]'.format(keyword),
                        '--compat-options', 'no-youtube-channel-redirect',
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--dateafter', "today-{}days".format(days_dateafter), 
                        '--playlist-start', '1', 
                        '--playlist-end', videos_limit, 
                        '--no-warning',
                        '--print', '"%(id)s;%(channel_id)s;%(uploader_id)s;%(title)s"']
                    

        if config['days_dateafter'] == "0":
            command.pop(8)
            command.pop(8)

        self.videos = (
            w.worker(
                command
            ).output()
            .split('\n')
        )

        return self.videos
    
    def set_proxy(self, command):
        if proxy:
            if proxy_url != "":
                command.append('--proxy')
                command.append(proxy_url)

## -- END

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/youtube/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

media_folder = config["strm_output_folder"]
days_dateafter = config["days_dateafter"]
videos_limit = config["videos_limit"]
source_platform = "youtube"
host = ytdlp2strm_config['ytdlp2strm_host']
port = ytdlp2strm_config['ytdlp2strm_port']

SECRET_KEY = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
DOCKER_PORT = os.environ.get('DOCKER_PORT', False)
if SECRET_KEY:
    port = DOCKER_PORT

if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""

## -- END

## -- AUXILIARS STRM (CHANNEL AND SEARCH KEYWORD)
def channel_strm(youtube_channel, youtube_channel_url, method):
    extract_audio = False
    if 'extractaudio-' in youtube_channel:
        extract_audio = True
        youtube_channel = youtube_channel.replace('extractaudio-','')

    yt = Youtube(
        youtube_channel,
        youtube_channel_url
    )

    # -- MAKES CHANNEL DIR (AND SUBDIRS) IF NOT EXIST, REMOVE ALL STRM IF KEEP_OLDER_STRM IS SETTED TO FALSE IN GENERAL CONFIG
    f.folders().make_clean_folder(
        "{}/{}".format(
            media_folder,  
            sanitize(
                "{}".format(
                    yt.channel_name_folder
                )
            )
        ),
        False,
        config
    )
    ## -- END

    ## -- BUILD CHANNEL NFO FILE
    n.nfo(
        "tvshow",
        "{}/{}".format(
            media_folder, 
            "{} [{}]".format(
                yt.channel_name_folder,
                yt.channel_id
            )
        ),
        {
            "title" : yt.channel_name,
            "plot" : yt.channel_description,
            "season" : "",
            "episode" : "",
            "landscape" : yt.channel_landscape,
            "poster" : yt.channel_poster,
            "studio" : "Youtube"
        }
    ).make_nfo()
    ## -- END 

    ## -- BUILD STRM
    for line in yt.videos:
        if line != "" and not 'ERROR:' in line:
            video_id = str(line).rstrip().split(';')[0]
            video_upload_name = str(line).rstrip().split(';')[1]
            video_upload_date = str(line).rstrip().split(';')[2]
            video_thumbnail = str(line).rstrip().split(';')[3]
            video_description = str(line).rstrip().split(';')[4]

            video_name = "{} - {} [{}]".format(
                video_upload_date,
                video_upload_name, 
                video_id
            )

            if extract_audio:
                video_id += '-audio'

            file_content = "http://{}:{}/{}/{}/{}".format(
                host, 
                port, 
                source_platform, 
                method, 
                video_id
            )

            file_path = "{}/{}/{}.{}".format(
                media_folder,  
                sanitize(
                    "{} [{}]".format(
                        yt.channel_name_folder,
                        yt.channel_id
                    )
                ),  
                sanitize(video_name), 
                "strm"
            )

            ## -- BUILD VIDEO NFO FILE
            n.nfo(
                "episode",
                "{}/{}".format(
                    media_folder, 
                    "{} [{}]".format(
                        yt.channel_name_folder,
                        yt.channel_id
                    )
                ),
                {
                    "item_name" : sanitize(video_name),
                    "title" : sanitize(video_name),
                    "plot" : video_description,
                    "season" : "",
                    "episode" : "",
                    "preview" : video_thumbnail
                }
            ).make_nfo()
            ## -- END 

            if not os.path.isfile(file_path):
                f.folders().write_file(
                    file_path, 
                    file_content
                )
    ## -- END 

def keyword_strm(keyword, method):
    extract_audio = False
    if 'extractaudio-' in keyword:
        extract_audio = True
        keyword = keyword.replace('extractaudio-','')

    yt = Youtube(
        keyword
    )

    for line in yt.videos:
        if line != "" and not 'ERROR' in line:
            video_id = str(line).rstrip().split(';')[0]
            channel_id = str(line).rstrip().split(';')[1]
            video_name = str(line).rstrip().split(';')[3]
            youtube_channel = str(line).rstrip().split(';')[2]
            youtube_channel_folder = youtube_channel.replace('/user/','@').replace('/streams','')

            if extract_audio:
                video_id += '-audio'

            file_content = "http://{}:{}/{}/{}/{}".format(
                host, 
                port, 
                source_platform, 
                method, 
                video_id
            )


            file_path = "{}/{}/{}.{}".format(
                media_folder, 
                sanitize(
                    "{} [{}]".format(
                        youtube_channel_folder,
                        channel_id
                    )
                ),  
                sanitize(video_name), 
                "strm"
            )

            f.folders().make_clean_folder(
                "{}/{}".format(
                    media_folder,  
                    sanitize(
                        "{} [{}]".format(
                            youtube_channel_folder,
                            channel_id
                        )
                    )
                ),
                False,
                config
            )

            channel = Youtube(
                youtube_channel_folder, 
                "https://www.youtube.com/channel/{}?novideo".format(
                    channel_id
                )
            )

            n.nfo(
                "tvshow",
                "{}/{}".format(
                    media_folder, 
                    "{} [{}]".format(
                        channel.channel_name_folder,
                        channel_id
                    )
                ),
                {
                    "title" : channel.channel_name,
                    "plot" : channel.channel_description,
                    "season" : "1",
                    "episode" : "-1",
                    "landscape" : channel.channel_landscape,
                    "poster" : channel.channel_poster,
                    "studio" : "Youtube"
                }
            ).make_nfo()

            if not os.path.isfile(file_path):
                f.folders().write_file(
                    file_path, 
                    file_content
                )

## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for youtube_channel in channels:
        print("Preparing channel {}".format(youtube_channel))

        youtube_channel = (
            youtube_channel.replace('https://www.youtube.com/', '') if not '/user/' in youtube_channel 
            else youtube_channel.replace('https://www.youtube.com', '')
        )
        print(youtube_channel)
        

 
        #formating youtube URL and init channel_id
        youtube_channel_url = "https://www.youtube.com/{}/videos".format(
            youtube_channel
        )
        #Cases like /user/xbox
        if not "@" in youtube_channel:
            youtube_channel_url = "https://www.youtube.com{}".format(
                youtube_channel
            )

        if 'list-' in youtube_channel:
            youtube_channel_url = "https://www.youtube.com/playlist?list={}".format(
                youtube_channel.split('list-')[1]    
            )

        if '/streams' in youtube_channel:
            method = 'direct'

        if 'extractaudio-' in youtube_channel:
            youtube_channel_url = youtube_channel_url.replace('extractaudio-','')

        if 'keyword-' in youtube_channel:
            keyword_strm(
                youtube_channel, 
                method
            )
        else:
            channel_strm(
                youtube_channel, 
                youtube_channel_url, 
                method
            )


    return True 

## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 
def direct(youtube_id): #Sponsorblock doesn't work in this mode
    s_youtube_id = youtube_id.split('-audio')[0]

    command = [
        'yt-dlp', 
        '-f', 'best',
        '--no-warnings',
        '--get-url', 
        s_youtube_id
    ]
    Youtube().set_proxy(command)
    if '-audio' in youtube_id:
        command[2] = 'bestaudio'

    print(' '.join(command))
    youtube_url = w.worker(command).output()
    return redirect(
        youtube_url, 
        code=302
    )

def bridge(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]

    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False
        if config["sponsorblock"]:
            command = ['yt-dlp', '-o', '-', '-f', 'best', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', s_youtube_id]
        else:
            command = ['yt-dlp', '-o', '-', '-f', 'best', '--restrict-filenames', s_youtube_id]
        Youtube().set_proxy(command)
        if '-audio' in youtube_id:
            command[4] = 'bestaudio'

        process = w.worker(command).pipe()
        try:
            while True:
                # Get some data from ffmpeg
                line = process.stdout.read(1024)

                # We buffer everything before outputting it
                buffer.append(line)

                # Minimum buffer time, 3 seconds
                if sentBurst is False and time.time() > startTime + 3 and len(buffer) > 0:
                    sentBurst = True

                    for i in range(0, len(buffer) - 2):
                        print("Send initial burst #", i)
                        yield buffer.pop(0)

                elif time.time() > startTime + 3 and len(buffer) > 0:
                    yield buffer.pop(0)

                process.poll()
                if isinstance(process.returncode, int):
                    if process.returncode > 0:
                        print('yt-dlp Error', process.returncode)
                    break
        finally:
            process.kill()

    return Response(
        stream_with_context(generate()), 
        mimetype = "video/mp4"
    ) 

def download(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]

    if config["sponsorblock"]:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', s_youtube_id]
    else:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '--restrict-filenames', s_youtube_id]
    Youtube().set_proxy(command)
    if '-audio' in youtube_id:
        command[2] = 'bestaudio'

    w.worker(command).call()
    filename = w.worker(
        ['yt-dlp', '--print', 'filename', '--restrict-filenames', "{}".format(youtube_id)]
    ).output()
    return send_file(
        filename
    )

## -- END