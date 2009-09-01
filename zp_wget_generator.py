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
from zp_grabber import ZpCacher

def sort_nicely(l): 
    """
    Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    l.sort(key=alphanum_key)
    return l

zpc = ZpCacher()
videos = zpc.cache

for counter, vid in enumerate(sort_nicely(videos.keys())):
    cur = videos[vid]
    new_name = "Zero Punctuation - [%02d] - %s.flv" % (counter, cur['title'])
    print "wget -c %s -O \"%s\"" % (cur['flv'], new_name)
