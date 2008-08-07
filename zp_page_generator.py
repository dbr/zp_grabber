"""
This basically parses the zp_cache.txt file into a prettier looking HTML page
"""

import re, random

def sort_nicely( l ): 
    """
    Sort the given list in the way that humans expect. 
    """ 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    l.sort( key=alphanum_key )
    return l

def toggle(i):
    """
    Reverse an list.
    Use with a two index list, call in each loop iteration,
    i = ['one','two']
    i = toggle(i)
    i[0]
    ..to alternate between 'one' and 'two'
    """
    return i[::-1]

def anon_url(url):
    """
    Takes a URL, returns the anonym.to'ified version of it.
    """
    return "http://anonym.to/?%s" % (url)


# Config
data = {}
data['title'] = random.choice([
    "Theft of the Punctuationless",
])

# Parse cache file
data['thelist'] = ""

file = "zp_cache.txt"
lines = open(file).readlines()

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

# Sort videos using the video-id, generate data['thelist]
oddeven = ["odd", "even"] #for alternating line colours

for vid in sort_nicely(videos.keys()):
    cur = videos[vid]
    
    item = "<li class=\"%s\"><a href=\"%s\">%s</a> <span class=\"flv-link\"><a href=\"%s\">#</a></span></li>\n" % (
        oddeven[0], anon_url(cur['flv']), cur['title'], anon_url(cur['web'])
    )
    data['thelist'] += item
    oddeven=toggle(oddeven)


template = """<html>
    <head>
        <title>%(title)s</title>
        <style type="text/css" media="screen">
            body{
                background-color:#fede00;
                color:#000000;
                font-family:"Arial";
                font-size:18px;
            }
            #holder{
                width:600px;
                margin-right:auto;
                margin-left:auto;
            }
            #content ul li{
                list-style:none;
                padding:2px;
            }
            .even{
                background:#7F7F7F;
            }
            .odd{
                background:#B3B3B3;
            }
            #footer{
                padding:5px;
                
                width:auto;
                text-align:right;
                font-size:9px;
            }
            .footer-text, .footer-text a{
                color:#808000;
            }
            .flv-link{
                text-align:right;
            }
        </style>
    </head>
    <body>
        <div id="holder">
            <div id="title">
                <img src="commonTheif.png" width="150" height="148" alt="A common theif (like you, but with a better hat)">
            </div>
            <div id="content">
                <ul>
                    %(thelist)s
                </ul>
            </div>
        </div>
        <div id="footer" class="footer-text">
            This page simply links to the .flv files that <a href="http://www.escapistmagazine.com">The Escapist's</a> video-player displays.<br>
            All links use <a href="http://anonym.to">anonym.to</a> to remove the HTTP referer<br>
            The code this was generated this page is available on <a href="http://github.com/dbr/zp_grabber/tree/master">GitHub</a>.
            And the current list of episodes can be found <a href="#">here</a>. Share and enjoy.<br>
            Remember and visit <a href="http://www.escapistmagazine.com">escapistmagazine.com</a> you filthy thief.
        </div>
    </body>
</html>""" % data

print str(template)