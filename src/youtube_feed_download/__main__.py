#!/usr/bin/env python3
import argparse
import json
import datetime
import pathlib
import yt_dlp
from .youtube_feed import YouTubeFeed
from .util import parse_iso8601_duration


def main():

    parser = argparse.ArgumentParser()

    start_time_arg_group = parser.add_mutually_exclusive_group()
    start_time_arg_group.required = True

    start_time_arg_group.add_argument('--start-time', '-T', type=datetime.datetime.fromisoformat,
                                      help="""Only process video uploaded on or after the given
                                           date and time. Argument must be an ISO format datetime
                                           (i.e. YYY-mm-ddTHH:MM:SS)""")
    start_time_arg_group.add_argument('--since', '-S', type=parse_iso8601_duration,
                                      help="""Only process videos uploaded at or after the given
                                           time interval into the past. Argument can be hh:mm:ss
                                           format or a number followed by the first letter of the
                                           unit of time (e.g. 5m for 5 minutes, 1h for 1 hour, 3d
                                           for 3 days, etc.). Cannot be used with --start-time""")

    parser.add_argument('--min-duration', type=str,
                        metavar='<hh:mm:ss or total seconds>',
                        help="Only process videos at least this long")

    parser.add_argument('--max-duration', type=str,
                        metavar='<hh:mm:ss or total seconds>',
                        help="Do not process videos longer than this")

    parser.add_argument('--channels',
                        metavar="<file path or list of channels>",
                        required=True,
                        nargs='+',
                        help="""A path to a file with newline delimited list of channels, or
                                provide a space-separated list of channels inline.""")

    parser.add_argument('--output', '-o', default='videos', help="Path to output downloaded files")

    parser.add_argument('--receipt',
                        metavar="/path/to/receipt.json",
                        help="Output data of the videos that were downloaded to the given path.")

    parser.add_argument('--group-by-channel',
                        action="store_true",
                        help="""Downloaded files will be placed in subdirectories named after their
                                respective channel""")

    parser.add_argument('--verbose', action="store_true")

    args = parser.parse_args()

    start_time = args.since or args.start_time

    download_filters = []

    if args.min_duration:
        try:
            hours, minutes, seconds = args.min_duration.split(':')
            duration_seconds = hours*3600 + minutes*60 + seconds
        except ValueError:
            try:
                duration_seconds = float(args.min_duration)
            except ValueError:
                raise ValueError("Invalid value provided for minimum duration")
        download_filters.append(lambda v, s=duration_seconds: v['duration'] >= s)

    if args.max_duration:
        try:
            hours, minutes, seconds = args.max_duration.split(':')
            duration_seconds = hours*3600 + minutes*60 + seconds
        except ValueError:
            try:
                duration_seconds = float(args.max_duration)
            except ValueError:
                raise ValueError("Invalid value provided for maximum duration")
        download_filters.append(lambda v, s=duration_seconds: v['duration'] <= s)

    channels = []
    for channel in args.channels:
        if (channels_file := pathlib.Path(channel)).exists():
            channels += channels_file.read_text().splitlines()
        else:
            channels.append(channel)

    ytf = YouTubeFeed(verbose=args.verbose)
    channel_ids = ytf.get_channel_ids_from_names(channels)

    videos_by_channel = ytf.get_channel_videos_uploaded_since_time(channel_ids,
                                                                   start_time)

    if args.verbose:
        print(f"{start_time=}")
        print(f"{channels=}")
        print(f"{channel_ids=}")
        print(json.dumps(videos_by_channel, indent=4, default=str))

    download_receipt = ytf.download_videos(videos_by_channel,
                                           output_dir=args.output,
                                           group_by_channel=args.group_by_channel,
                                           filters=download_filters)

    download_receipt_body = json.dumps(download_receipt, indent=4, default=str)
    if args.receipt:
        if (receipt_path := pathlib.Path(args.receipt)).is_dir():
            receipt_path /= 'youtube_feed_download_receipt.json'
        receipt_path.write_text(download_receipt_body)
    else:
        print(download_receipt_body)


if __name__ == '__main__':
    main()