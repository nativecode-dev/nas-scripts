import datetime
import feedparser
import guessit
import os
import re
import traceback


MOVIES_CUSTOM='http://nativecode.no-ip.org:82/movies.rss'
MOVIES_XSPEEDS='http://bit.ly/1wYYP1r'

SERIES_CUSTOM='http://nativecode.no-ip.org:82/shows.rss'
SERIES_XSPEEDS='http://bit.ly/1tye55k'

REGEX_IMDB_LINK=re.compile('http://www\.imdb\.com')


def archive_feed(url):
    try:
        feed = feedparser.parse(url)

        for item in feed['items']:
            if 'description' in  item:
                description = item['description']
            link = item['link']
            title = item['title']
            # published = datetime.datetime(item['published'])

            guess = guessit.guess_movie_info(title)

            codec_audio = None if not 'audioProfile' in guess else guess['audioProfile']
            codec_video = None if not 'videoCodec' in guess else guess['videoCodec']
            dimensions = '2D' if not 'other' in guess else guess['other']
            format = None if not 'format' in guess else guess['format']
            resolution = None if not 'screenSize' in guess else guess['screenSize']
            title_cleaned = title if not 'title' in guess else guess['title']
            year = None if not 'year' in guess else guess['year']

            parts = [title_cleaned]

            if year: parts.append('(%s)' % year)
            if resolution: parts.append(resolution)
            if format: parts.append(format)
            # if dimensions: parts.append(dimensions)
            parts.append('[%s]' % link)

            print(' '.join(parts))
    except Exception as e:
        traceback.print_exc()
        print(e)


def main():
    archive_feed(MOVIES_CUSTOM)

main()
