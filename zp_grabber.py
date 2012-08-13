#!/usr/bin/env python
import os, sys, urllib, urllib2, tempfile, re
from cache import CacheHandler
from optparse import OptionParser
from BeautifulSoup import BeautifulSoup

def get_cache_dir(suffix):
    tmp = tempfile.gettempdir()
    tmppath = os.path.join(tmp, suffix)
    if not os.path.isdir(tmppath):
        os.mkdir(tmppath)
    print "Temp directory:", tmppath
    return tmppath

headers = {
    'user_agent': "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
    'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    'accept_language': "en-gb,en;q=0.5",
    # Strict Firefox headers would use "gzip,deflate" and would need decoding.
    #'accept_encoding': "gzip,deflate",
    'accept_encoding': "identity",
    'accept_charset': "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
    'keep_alive': "300",
    'connection': "keep-alive",
    'if_modified_since': "Mon, 25 Jan 2000 20:32:57 GMT",
    'cache_control': "max-age=0",
}
cached_opener = urllib2.build_opener(CacheHandler(get_cache_dir("zp_grabber")))
cached_opener.addheaders = headers.items()

####################
# Helper functions #
####################

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
        for vid,values in sorted(self.cache.items(), key=lambda x: int(x[0])):
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
    Takes an EscapistMagazine /video/view/... URL, retrieves the URL for the .flv file
    
    # Initialise
    t = EscapistMagazine("http://www.escapistmagazine.com/videos/view/zero-punctuation/175-Ninja-Gaiden-2")
    # Get the URL
    t.get_flv_url() 
    # Get the video ID
    t.get_vid()
    
    Working as of Dec 10, 2009 (rtmp URL for mp4 file)
    """
    def __init__(self, url):
        self.url = url
        
    def _parse_escapist_url(self):
        vid_check = re.match("http[s]?://(?:www.)?escapistmagazine.com/videos/view/.+?/([\d]+)-.*?", self.url)
        if vid_check:
            vid = vid_check.groups()[0]
            return vid
        else:
            raise error_invalidurl("%s" % self.url)
    
    def _get_flv_link(self, url, postdata):
        src = cached_opener.open(url, postdata).read()
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
        # Check URL
        self._parse_escapist_url()

        webp = cached_opener.open(self.url)
        src = webp.read()
        soup = BeautifulSoup(src)
        
        # Extract player from the soup
        vid_player = soup.find('object', id="player_api")
        config = vid_player.find("param", {'name': "flashvars"})['value']
        config_url = config.split("config=")[1]
        
        # Got flashvars config path, load it
        config = cached_opener.open(config_url).read()
        
        # Ew. The contents doesn't parse as JSON, so this is necessary
        flv_teller_url = config.split("{'url':'")[2].split("'")[0]

        # Skip rtmp nonsense
        return flv_teller_url


#end EscapistVideo

def parse_page_for_videos(zpc, soup):
    """
    Takes a BeautifulSoup instance of an escapistmagazine page,
    grabs all filmstrip_video div's from the gallery_display div.
    
    From each filmstrip_video div, it grabs the title, and URL.
    Using the URL, it grabs the video-ID, checks if the ZpCacher
    knows the FLV already, if not, finds the flv url.
    
    Working as of Sep 3, 2009. May break due to page layout changes.
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

        # Crudely remove "<i>HTML stuff</i>" from title
        title = re.sub("</?[a-z]+>", "", title)

        if cv.a['href'].startswith("http://"):
            web_url = cv.a['href']
        else:
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
    
    Working as of April 6, 2009. Getting all pages 
    could break due to layout changes.
    """
    zpc = ZpCacher()
    
    # Load the newest ZP page, into BeautifulSoup
    url="http://www.escapistmagazine.com/videos/view/zero-punctuation"
    webp = cached_opener.open(url)
    src = webp.read()
    src = cached_opener.open(url).read()
    soup = BeautifulSoup(src)
    
    # Always parse first page
    flv_requests, cache_hits = parse_page_for_videos(zpc, soup)
    if get_all:
        for page in soup.findAll('div',{'class':'pagination_pages'})[0].findAll('a'):
            if page.contents[0].isdigit() and int(page.contents[0]) > 1:
                url="http://www.escapistmagazine.com/videos/view/zero-punctuation?page=%d" % (int(page.contents[0]))
                src = cached_opener.open(url).read()
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
                      help="retrieves and caches flv-links from escapistmagazine.com's ZP page (overrides)")
    parser.add_option("-a", "--all", dest="all", action="store_true",
                      help="retrieves videos from all Zero-Punctuation-list pages")

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
