#!/usr/bin/env python
"""Generates a series of wget commands.
Requires zp_cache.txt to be in current folder, and to be populated.

$ python zp_grabber.py -g -a # populate zp_cache.txt
$ python wget_generator.py > grabber.sh # generate wget shell script
$ chmod +x grabber.sh # make executable
$ ./grabber.sh # grab all Zero Punctuation episodes into current directory

Use sanely
"""
import re

def sort_nicely( l ): 
    """
    Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    l.sort( key=alphanum_key )
    return l

fp = open("zp_cache.txt")
lines = fp.readlines()

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
        print "invalid line %s" % (current_line)
        continue # Invalid line, skip

counter = 1
for vid in sort_nicely(videos.keys()):
    cur = videos[vid]
    new_name = "Zero Punctuation - [%02d] - %s.flv" % (counter, cur['title'])
    print "wget -c %s -O \"%s\"" % (cur['flv'], new_name)
    counter += 1