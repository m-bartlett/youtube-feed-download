import pathlib
import datetime
import requests
import xml.dom.minidom as minidom
import re
import concurrent.futures
import yt_dlp

# date_parse_regex = re.compile(r"""^(?P<year>\d{2,4})
#                                    (?:[-/](?P<month>\d{1,2}))?
#                                    (?:[-/](?P<day>\d{1,2}))?
#                                    (?:[-/+ ](?P<hour>\d{1,2}))?
#                                    (?:[:](?P<minute>\d{1,2}))?$""", flags=re.VERBOSE)
# match = date_parse_regex.search("2024/10/11 11:00")
# match.groupdict()


class YouTubeFeed:

    channel_id_regex = re.compile(r"UC[\w-]{22}")
    external_id_regex = re.compile(r'"externalId":"([^"]+)"')

    def __init__(self, verbose: bool=False):
        self.verbose = verbose


    def normalize_channel_name(self, channel_name: str) -> str:
        if 'youtube' in channel_name:
            if '@' in channel_name:
                _, _, normalized_name = channel_name.rpartition('@')
            else:
                _, _, normalized_name = channel_name.rpartition('/')
        else:
            normalized_name = channel_name
        return normalized_name


    def get_channel_id(self, channel_name: str):
        channel_name = self.normalize_channel_name(channel_name)
        if match := self.channel_id_regex.search(channel_name):
            return match[0]
        for url_format in ["https://youtube.com/@{name}", "https://youtube.com/user/{name}"]:
            response = requests.get(url_format.format(name=channel_name))
            if not response.ok:
                continue
            if (match := self.external_id_regex.search(response.text)):
                channel_id = match.groups()[0]
                if self.verbose:
                    print(f"{channel_name} -> {channel_id}")
                return channel_id
        print(f"No ID found for {channel_name}")
        return


    def get_channel_ids_from_names(self, channel_names: list[str]) -> tuple[str]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = pool.map(self.get_channel_id, channel_names)
            channel_ids = tuple(c for c in futures if c)
        return channel_ids


    def get_channel_videos_uploaded_since_time(self,
                                               channel_ids: list[str],
                                               start_time: (datetime.datetime|
                                                            datetime.timedelta)) -> dict[str,dict]:
        if isinstance(start_time, datetime.timedelta):
            start_time = datetime.datetime.now(datetime.timezone.utc) - start_time

        videos_by_channel: dict[str,list] = {}

        for channel_id in channel_ids:
            video_results = {}
            channel_feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            rss_feed_response = requests.get(channel_feed_url)
            rss_dom = minidom.parseString(rss_feed_response.text)
            for entry in rss_dom.getElementsByTagName('entry'):
                publish_timestamp = entry.getElementsByTagName('published')[0].firstChild.wholeText
                publish_time = datetime.datetime.fromisoformat(publish_timestamp)

                if publish_time >= start_time:
                    title = entry.getElementsByTagName('title')[0].firstChild.wholeText
                    video_id = entry.getElementsByTagName('yt:videoId')[0].firstChild.wholeText
                    video_url = entry.getElementsByTagName('link')[0].getAttribute('href')
                    video_results[video_id] = {"title": title,
                                               "url": video_url,
                                               "publish_time": publish_time}
            if video_results:
                videos_by_channel[channel_id] = video_results

        return videos_by_channel


    def download_videos(self,
                        videos_by_channel: dict[str,dict],
                        output_dir: str='videos',
                        group_by_channel: bool=False,
                        filters: list[callable]=[]):

        if output_dir and not output_dir.endswith('/'):
            output_dir += '/'

        filename_template = "%(title)s.%(ext)s"
        if group_by_channel:
            output_template = f"{output_dir}%(channel)s/{filename_template}"
        else:
            output_template = f'{output_dir}{filename_template}'

        ydl_opts = {'extract_flat': 'discard_in_playlist',
                    'format': 'bestaudio/best',
                    'fragment_retries': 10,
                    'ignoreerrors': 'only_download',
                    'mark_watched': True,
                    'nocheckcertificate': True,
                    'outtmpl': {'default': output_template, 'pl_thumbnail': ''},
                    'overwrites': False,
                    'postprocessors': [{'key': 'FFmpegExtractAudio',
                                        'nopostoverwrites': False,
                                        'preferredquality': '0'},
                                       {'add_chapters': True,
                                        'add_infojson': 'if_exists',
                                        'add_metadata': True,
                                        'key': 'FFmpegMetadata'},
                                       {'already_have_thumbnail': False, 'key': 'EmbedThumbnail'},
                                       {'key': 'FFmpegConcat',
                                        'only_multi_video': True,
                                        'when': 'playlist'}],
                    'retries': 10,
                    'updatetime': False,
                    'writethumbnail': True}

        download_manifest = {}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for channel_id, videos in videos_by_channel.items():
                for video_id, video_props in videos.items():
                    video_info = ydl.extract_info(video_props['url'], download=False, process=False)
                    skip_video = False
                    try:
                        if not all(_filter(video_info) for _filter in filters):
                            skip_video = True
                    except TypeError:
                        skip_video = True
                    if skip_video:
                        print(f"Skipping {video_props['url']}")
                        continue
                    download_manifest[video_id] = video_props

            error_code = ydl.download([v['url'] for v in download_manifest.values()])

        return download_manifest