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
import platform
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

def makeValidFilename(value, normalize_unicode = False, windows_safe = False, custom_blacklist = None, replace_with = "_"):
    """
    Takes a string and makes it into a valid filename.

    normalize_unicode replaces accented characters with ASCII equivalent, and
    removes characters that cannot be converted sensibly to ASCII.

    windows_safe forces Windows-safe filenames, regardless of current platform

    custom_blacklist specifies additional characters that will removed. This
    will not touch the extension separator:

        >>> makeValidFilename("T.est.avi", custom_blacklist=".")
        'T_est.avi'
    """

    if windows_safe:
        # Allow user to make Windows-safe filenames, if they so choose
        sysname = "Windows"
    else:
        sysname = platform.system()

    # If the filename starts with a . prepend it with an underscore, so it
    # doesn't become hidden.

    # This is done before calling splitext to handle filename of ".", as
    # splitext acts differently in python 2.5 and 2.6 - 2.5 returns ('', '.')
    # and 2.6 returns ('.', ''), so rather than special case '.', this
    # special-cases all files starting with "." equally (since dotfiles have
    # no extension)
    if value.startswith("."):
        value = "_" + value

    # Treat extension seperatly
    value, extension = os.path.splitext(value)

    # Remove any null bytes
    value = value.replace("\0", "")

    # Blacklist of characters
    if sysname == 'Darwin':
        # : is technically allowed, but Finder will treat it as / and will
        # generally cause weird behaviour, so treat it as invalid.
        blacklist = r"/:"
    elif sysname in ['Linux', 'FreeBSD']:
        blacklist = r"/"
    else:
        # platform.system docs say it could also return "Windows" or "Java".
        # Failsafe and use Windows sanitisation for Java, as it could be any
        # operating system.
        blacklist = r"\/:*?\"<>|"

    # Append custom blacklisted characters
    if custom_blacklist is not None:
        blacklist += custom_blacklist

    # Replace every blacklisted character with a underscore
    value = re.sub("[%s]" % re.escape(blacklist), replace_with, value)

    # Remove any trailing whitespace
    value = value.strip()

    # There are a bunch of filenames that are not allowed on Windows.
    # As with character blacklist, treat non Darwin/Linux platforms as Windows
    if sysname not in ['Darwin', 'Linux']:
        invalid_filenames = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2",
        "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1",
        "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        if value in invalid_filenames:
            value = "_" + value

    # Replace accented characters with ASCII equivalent
    if normalize_unicode:
        import unicodedata
        value = unicode(value) # cast data to unicode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

    # Truncate filenames to valid/sane length.
    # NTFS is limited to 255 characters, HFS+ and EXT3 don't seem to have
    # limits, FAT32 is 254. I doubt anyone will take issue with losing that
    # one possible character, and files over 254 are pointlessly unweidly
    max_len = 254

    if len(value + extension) > max_len:
        if len(extension) > len(value):
            # Truncate extension instead of filename, no extension should be
            # this long..
            new_length = max_len - len(value)
            extension = extension[:new_length]
        else:
            # File name is longer than extension, truncate filename.
            new_length = max_len - len(extension)
            value = value[:new_length]

    return value + extension


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

        transcoded_name = transcoded_name.replace(": ", " - ")

        transcoded_name = makeValidFilename(transcoded_name)


        print "Transcoding:"
        t = Transcoder(urlfilename)
        transcode_cmd = t.getcommand(transcoded_name)
        tproc = subprocess.Popen(transcode_cmd)
        tproc.communicate()
        if tproc.returncode != 0:
            print "Non-zero exit code: %s" % tproc.returncode
            continue
        print

        print "Tagging:"
        tag_command = ["AtomicParsley", transcoded_name, "--TVShowName", "Zero Punctuation", "--TVSeasonNum", "1", "--TVEpisodeNum", str(counter), "--stik", "TV Show", "--overWrite"]
        print tag_command
        try:
            tagproc = subprocess.Popen(tag_command)
        except OSError, e:
            print "Error while launching AtomicParsley, may not be installed?"
            print e
        else:
            tagproc.communicate()
            if tagproc.returncode != 0:
                print "Non-zero exit code while tagging: %s" % tagproc.returncode
                print
        
        # Mark as done, as save
        state.add_done(vid)
        state.save_state()

if __name__ == '__main__':
    main()
