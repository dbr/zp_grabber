#!/usr/bin/env python
import os, sys, urllib, re
from hashlib import md5
from optparse import OptionParser
from BeautifulSoup import BeautifulSoup

class Cache:
    """
    Simple caching URL opener. Acts like:
    import urllib
    return urllib.urlopen("http://example.com").read()
    
    Caches complete files to temp directory, 
    
    >>> ca = Cache()
    >>> ca.loadUrl("http://example.com") #doctest: +ELLIPSIS
    '<HTML>...'
    """
    import os
    import time
    import tempfile
    import urllib
    try:
        import sha1 as hasher
    except ImportError:
        import md5 as hasher
    
    def __init__(self, max_age=21600, prefix="zp_grabber", useragent = "Mozilla-compatible 5.0 etc"):
        class AppURLopener(urllib.FancyURLopener):
            version = useragent
        self.urllib._urlopener = AppURLopener()
        
        self.prefix = prefix
        self.max_age = max_age
        
        tmp = self.tempfile.gettempdir()
        tmppath = self.os.path.join(tmp, prefix)
        if not self.os.path.isdir(tmppath):
            self.os.mkdir(tmppath)
        self.tmp = tmppath
    #end __init__
    
    def getCachePath(self, url):
        """
        Calculates the cache path (/temp_directory/hash_of_URL)
        """
        cache_name = self.hasher.new(url).hexdigest()
        cache_path = self.os.path.join(self.tmp, cache_name)
        return cache_path
    #end getUrl
    
    def checkCache(self, url):
        """
        Takes a URL, checks if a cache exists for it.
        If so, returns path, if not, returns False
        """
        path = self.getCachePath(url)
        if self.os.path.isfile(path):
            cache_modified_time = self.os.stat(path).st_mtime
            time_now = self.time.time()
            if cache_modified_time < time_now - self.max_age:
                # Cache is old
                return False
            else:
                return path
        else:
            return False
    #end checkCache

    def loadUrl(self, url, postdata = None):
        """
        Takes a URL, returns the contents of the URL, and does the caching.
        """
        if postdata is None:
            postdata = ""
        else:
            postdata = urllib.urlencode(postdata)
        
        cacheExists = self.checkCache(url)
        if cacheExists:
            cache_file = open(cacheExists)
            dat = cache_file.read()
            cache_file.close()
            return dat
        else:
            path = self.getCachePath(url)
            dat = self.urllib.urlopen(url, postdata).read()
            target_socket = open(path, "w+")
            target_socket.write(dat)
            target_socket.close()
            return dat
        #end if cacheExists
    #end loadUrl
#end Cache

####################
# Helper functions #
####################

def is_int(inp):
    """
    Checks if supplied variable is an integer.
    Returns True if it is an integer, or False if not.
    """
    try:
        return True
    except ValueError:
        return False

class ZpCacher:
    """
    Stores a list of episodes we have FLV URLs for in a text file.
    It is used in the following way:
    - Load ZP index page
    - Grab a list of all video addresses, and grab the video-ID from the URL
    - Check if ZpCacher knows about video ID 123
    - If it does *NOT* have ID 123, we have to get 
    the FLV for that ID.
    
    Cache file format is
    video_id|flv_url|web_url|title
    """
    def __init__(self):
        self.cache_file = os.path.join(sys.path[0], "zp_cache.txt")
        
        self.cache = {}
        self.load_cache()
    def load_cache(self):
        try:
            cur_cache = open(self.cache_file)
            
            for current_line in cur_cache.readlines():
                try:
                    c_vid, c_flv_url, c_web_url, c_title = [x.strip() for x in current_line.split("|")]
                except ValueError:
                    continue # Invalid line, skip
                self.cache[c_vid] = {
                    'flv':c_flv_url,
                    'web':c_web_url,
                    'vid':c_vid,
                    'title':c_title
                }
            
        except IOError:
            pass
        else:
            cur_cache.close()
    
    def add(self,vid,flv_url, web_url, title):
        self.cache[vid] = {
            'flv':flv_url,
            'web':web_url,
            'vid':vid,
            'title':title
        }
        self.save()
    def save(self):
        out = ""
        for vid,values in self.cache.items():
            out += "%s|%s|%s|%s\n" % (vid, values['flv'], values['web'], values['title'])
        f = open(self.cache_file, "w+")
        f.write(out)
        f.close()
# end ZpCacher


class error_sitechange(Exception):pass
class error_invalidurl(Exception):pass
class error_connection(Exception):pass

class EscapistVideo:
    """
    Takes an EscapistMagazine /video/view/... URL, retrives the URL for the .flv file
    
    # Initalise
    t = EscapistMagazine("http://www.escapistmagazine.com/videos/view/zero-punctuation/175-Ninja-Gaiden-2")
    # Get the URL
    t.get_flv_url() 
    # Get the video ID
    t.get_vid()
    
    Working as of Nov 16, 2008 (still using CastFire CDN for video files, with format= hash "protection" added)
    """
    def __init__(self, url):
        self.url = url
        
    def _parse_escapist_url(self):
        vid_check = re.match("http[s]?://(?:www.)?escapistmagazine.com/videos/view/.+?/([\d]+)-.*?", self.url)
        if vid_check:
            vid = vid_check.groups()[0]
            return vid
        else:
            raise error_invalidurl
    
    def _format_teller_url(self, vid):
        base_url = "http://www.themis-group.com/global/castfire/m4v/%s" % (vid)
        postdata = {'version': 'ThemisMedia1.2',
        'format': md5("Video %s Hash" % (vid)).hexdigest(),
        }
        return (base_url, postdata)
    
    def _get_flv_link(self, url, postdata):
        x = Cache(useragent="User-Agent: Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-GB; rv:1.9.0.4) Gecko/2008102920 Firefox/3.0.4")
        src = x.loadUrl(url, postdata)
        if src.find("url=") > -1:
            return urllib.unquote(str( # url decode..
                src.split("url=")[1] # ..the segment after the url=
            ))
        else:
            raise error_sitechange("Couldn't find the FLV url on %s, check it is a valid URL you supplied. If so, the FLV retrival system may have changed!" % (url))
    
    def get_vid(self):
        vid = self._parse_escapist_url()
        return vid
    
    def get_flv_url(self):
        vid = self._parse_escapist_url()
        flv_teller_url, flv_teller_postdata = self._format_teller_url(vid)
        flv_url = self._get_flv_link(flv_teller_url, flv_teller_postdata)
        return flv_url
#end EscapistVideo

def parse_page_for_videos(zpc, soup):
    """
    Takes a BeautifulSoup instance of an escapistmagazine page,
    grabs all filmstrip_video div's from the gallery_display div.
    
    From each filmstrip_video div, it grabs the title, and URL.
    Using the URL, it grabs the video-ID, checks if the ZpCacher
    knows the FLV already, if not, finds the flv url.
    
    Working as of Nov 16, 2008. May break due to page layout changes.
    """
    # counters
    cache_hits = 0
    flv_requests = 0
    
    # Find all div class='filmstrip_video', loop over each one
    video_column = soup.find('div',{'id':'gallery_display'})
    av = video_column.findAll('div', {'class':'filmstrip_video'})
    for cv in av:
        # Get title and the URL
        title = cv.findAll('div',{'class':'title'})[0].contents[0]
        web_url = "http://www.escapistmagazine.com" + cv.a['href']
        
        z = EscapistVideo(web_url)
        vid = z.get_vid()
        
        if zpc.cache.has_key(vid):
            cache_hits += 1
        else:
            # Get the flv URL!
            flv_url = z.get_flv_url()
            flv_requests += 1
            
            zpc.add(vid,flv_url, web_url, title)
    
    return flv_requests, cache_hits
    
def get_recent_zp_videos(get_all = False):
    """
    This is the main ZP-grabber function.
    It parses the first page of videos (and the rest, if requested)
    It gets the page count using the pagination_pages div.
    
    Working as of Nov 16, 2008. Getting all pages 
    could break due to layout changes.
    """
    zpc = ZpCacher()
    
    # Load the newest ZP page, into BeautifulSoup
    x = Cache(useragent="Googlebot/2.1 (+http://www.googlebot.com/bot.html)")
    url="http://www.escapistmagazine.com/videos/view/zero-punctuation"
    src = x.loadUrl(url)
    soup = BeautifulSoup(src)
    
    # Always parse first page
    flv_requests, cache_hits = parse_page_for_videos(zpc, soup)
    if get_all:
        for page in soup.findAll('div',{'class':'pagination_pages'})[0].findAll('a'):
            if is_int(page.contents[0]) and int(page.contents[0]) > 1:
                url="http://www.escapistmagazine.com/videos/view/zero-punctuation?page=%d" % (int(page.contents[0]))
                src = x.loadUrl(url)
                soup = BeautifulSoup(src)
                fr, ch = parse_page_for_videos(zpc, soup)
                flv_requests += fr
                cache_hits += ch
    
    if flv_requests > 0:
        # FLV's have been requested, display how many (this means new videos were grabbed!)
        print "Parsed %d videos (%d requests, %d cache hits)" % (flv_requests + cache_hits, flv_requests, cache_hits)
    else:
        # If we don't request any new FLV files, stay quiet
        pass

def main():
    """
    Either parses escapistmagazine.com for ZP episodes, and grabs their flv URL
    or
    Takes one (or more) ZP episode URLs, returns the flv URL
    """
    parser = OptionParser()
    parser.add_option("-g", "--grab", dest="grab", action="store_true", default="true",
                      help="retrives and caches flv-links from escapistmagazine.com's ZP page (overrides)")
    parser.add_option("-a", "--all", dest="all", action="store_true",
                      help="retrives videos from all Zero-Punctuation-list pages")

    (options, args) = parser.parse_args()
    
    if options.grab:
        get_recent_zp_videos(options.all)
    else:
        for cur_url in args:
            zpc = ZpCacher()
            
            try:
                z = EscapistVideo(cur_url)
                vid = z.get_vid()
                
                if zpc.cache.has_key(vid):
                    print zpc.cache[vid]['flv']
                else:
                    print z.get_flv_url()
            except error_invalidurl:
                print "Invalid URL?"
                sys.exit(1)

if __name__ == '__main__':
    main()