"""
This basically parses the zp_cache.txt file into a prettier looking HTML page
"""

import os, sys, re, random
import PyRSS2Gen

def sort_nicely( l ): 
    """
    Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    l.sort( key=alphanum_key )
    return l

def anon_url(url):
    """
    Takes a URL, returns the anonym.to'ified version of it.
    """
    return "http://anonym.to/?%s" % (url)


# Config
data = {}
data['title'] = "Zero Punctation FLV feed"

# Parse cache file
data['thelist'] = ""

cache_file = os.path.join(
    sys.path[0],
    "zp_cache.txt"
)
lines = open(cache_file).readlines()

videos = {}
for current_line in lines:
    try:
        c_vid, c_flv_url, c_web_url, c_title = [x.strip() for x in current_line.split("|")]
        videos[c_vid] = {
            'flv':c_flv_url,
            'web':c_web_url,
            'vid':c_vid,
            'title':c_title
        }
    except ValueError:
        continue # Invalid line, skip

items = []

for vid in sort_nicely(videos.keys()):
    cur = videos[vid]
    
    title = cur['title']
    link = anon_url(cur['flv'])
    orig = anon_url(cur['web'])
    
    items.append(
        PyRSS2Gen.RSSItem(
                title = title,
                link = link,
                description = """FLV Link: <a href="%s">%s</a>Original link: <a href="%s">%s</a> """ % (link, link, orig, orig),
                guid = link
        )
    )

rss = PyRSS2Gen.RSS2(
    title = data['title'],
    link = "http://zp.dbrweb.co.uk",
    description = "FLV links to Zero Punctuation files. Generated by code available at http://github.com/dbr/zp_grabber/tree/master",
    items = items
)

print rss.to_xml()