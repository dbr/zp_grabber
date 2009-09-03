#!/usr/bin/env python
"""Downloads and transcodes any new ZP episodes.

Gets URL's from the zp_cache.txt file, which is updated using running..

    python zp_grabber.py -g

A list of previously transcoded episodes are stored in transcoded_state.txt

Requires wget, and HandbrakeCLI to be somewhere in $PATH

You can download this from http://handbrake.fr/

It transcodes to iPod an compatible format, there is no quality
difference loss from the original .flv file and this, and it should
play back on most devices (including iPhone, Xbox 360 etc)
"""
import os
import re
import subprocess
from urlparse import urlparse

from zp_grabber import ZpCacher

def sort_nicely(l): 
    """
    Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    l.sort(key=alphanum_key)
    return l

class DoneState:
    def __init__(self):
        zpc = ZpCacher()
        zpc.load_cache()
        
        self.cache = zpc.cache
        self.load_state()
    
    def add_done(self, id):
        self.cache[id]['done'] = True

    def not_done(self):
        return [x for x, v in self.cache.items() if 'done' in v and not v['done']]

    def done(self):
        return [x for x, v in self.cache.items() if 'done' in v and v['done']]

    def open_statefile(self, write = False):
        cfile = os.path.abspath(__file__)
        cpath, cfile = os.path.split(cfile)
        fname = os.path.join(cpath, "transcoded_state.txt")
        if not write:
            return open(fname)
        else:
            return open(fname, "w")

    def load_state(self):
        f = self.open_statefile()
        raw = f.read()
        raw = raw.strip().split(",")
        f.close()
        
        if raw[0] == '':
            del raw[0]
        
        if len(raw) > 0:
            done = [int(x.strip()) for x in raw]
        else:
            done = []
        
        for k, v in self.cache.items():
            if int(k) in done:
                self.cache[k]['done'] = True
            else:
                self.cache[k]['done'] = False

    def save_state(self):
        done = ",".join(self.done())
        f = self.open_statefile(write = True)
        f.write(done)
        f.close()


class Transcoder:
    CMD_NAME = "HandbrakeCLI"
    ARGS = [
        "-e", "x264",
        "-b", "700",
        "-a", "1",
        "-E", "faac",
        "-B", "160",
        "-R", "48",
        "-6", "dpl2",
        "-f", "mp4",
        "-I", "-X",
        "320", "-m",
        "-x", "level=30:bframes=0:cabac=0:ref=1:vbv-maxrate=768:vbv-bufsize=2000:analyse=all:me=umh:no-fast-pskip=1"
    ]
    
    def __init__(self, fname):
        self.fname = fname
    
    def getcommand(self, outname):
        cmd = [self.CMD_NAME] + self.ARGS
        cmd += ["-i", self.fname, "-o", outname]
        return cmd

def main():
    zpc = ZpCacher()
    zpc.load_cache()

    state = DoneState()
    done = state.done()

    for counter, vid in enumerate(sort_nicely(zpc.cache.keys())):
        if vid in done:
            # Skip, already done
            continue
    
        cur = zpc.cache[vid]
        
        # Get filename part of URL, as we need it for transcoding,
        # Explicitly extracting and downloading to this should prevent
        # any unexpected weirdness.
        urlpath = urlparse(cur['flv']).path
        _, urlfilename = os.path.split(urlpath)
        
        # Generate wget command
        grab_command = ["curl", "-L", "-A", "\"Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)\"", "-C", "-", cur['flv'], "-o", urlfilename]
        print "Getting FLV file:"
        print grab_command
        gproc = subprocess.Popen(grab_command)
        gproc.communicate()
        if gproc.returncode != 0:
            print "Non-zero exit code: %s" % gproc.returncode
            continue
        print

        if not os.path.isfile(urlfilename):
            print "Downloaded file \"%s\" not found, not transcoding" % urlfilename
            continue

        transcoded_name = "Zero Punctuation - [%02d] - %s.mp4" % (counter, cur['title'])

        print "Transcoding:"
        t = Transcoder(urlfilename)
        transcode_cmd = t.getcommand(transcoded_name)
        tproc = subprocess.Popen(transcode_cmd)
        tproc.communicate()
        if gproc.returncode != 0:
            print "Non-zero exit code: %s" % gproc.returncode
            continue
        print
        
        # Mark as done, as save
        state.add_done(vid)
        state.save_state()

if __name__ == '__main__':
    main()