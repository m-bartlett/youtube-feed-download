import datetime
import re

isop8601_duration_regex = re.compile(r'P?'
                                     r'((?P<years>\d+)Y)?'
                                     r'((?P<months>\d+)M)?'
                                     r'((?P<weeks>\d+)W)?'
                                     r'((?P<days>\d+)D)?'
                                     r'T?'
                                     r'((?P<hours>\d+)H)?'
                                     r'((?P<minutes>\d+)M)?'
                                     r'((?P<seconds>\d+)S)?')


def parse_iso8601_duration(duration_str: str) -> datetime.timedelta:
    match = isop8601_duration_regex.fullmatch(duration_str)

    if not match:
        raise ValueError(f"Invalid ISO 8601 duration format: {duration_str}")

    time_delta_props = {k:int(v) for k,v in match.groupdict().items() if v}
    days = 0
    if parsed_days := time_delta_props.pop('days', None):
        days += parsed_days
    if parsed_weeks := time_delta_props.pop('weeks', None):
        days += parsed_weeks*7
    if parsed_months := time_delta_props.pop('months', None):
        days += parsed_months*30
    if parsed_years := time_delta_props.pop('years', None):
        days += parsed_years*365

    return datetime.timedelta(days=days, **time_delta_props)