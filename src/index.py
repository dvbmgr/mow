#!/usr/bin/python
# -*- coding: utf-8 -*-

'''A simple music sharer'''

from __future__ import unicode_literals

import re
import glob
import os.path
import mimetypes
import urllib
from flask import Flask, \
    render_template, abort, \
    make_response, redirect, \
    url_for, request, abort
from xml.dom.minidom import parse

# Path to analyze
MUSIC_PATH = "/home/dab/Musique"

# Initaling Flask application
app = Flask("MusicPlayer")

def joinurl(path1, path2):
    '''Join two url parts'''
    p1e = path1.endswith("/")
    p2e = path2.startswith("/")
    if p1e and p2e:
        return path1[0:-1] + path2
    elif p1e or p2e:
        return path1 + path2
    else:
        return path1 + "/" + path2


def extended_glob(path,extensions):
    '''A prettier syntax to glob files'''
    retr_datas = []
    for extension in extensions:
        retr_datas += glob.glob(joinurl(path,"*."+extension))
    return retr_datas

def generate_list(path="*"):
    """Generate the list of directories from the ``path'''"""
    def clear_name(itemnane):
        return {
            'URL':joinurl("/explore/",unicode(item)[len(MUSIC_PATH):]),
            'TITLE':unicode(os.path.basename(item))
        }
    items = glob.glob(os.path.join(MUSIC_PATH,path))
    return [clear_name(item) for item in items]

def generate_music_list(path="*/*"):
    """List all mp3 files in ``path'''"""
    def clear_name(itemnane):
        return {
            'URL':joinurl("/explore/",re.sub(r'(.+/)[0-9]* ?(.+)', r'\1\2',
                        unicode(os.path.splitext(item)[0])[len(MUSIC_PATH):]
                    ).split('-')[-1]),
            'TITLE':re.sub(r'[0-9]* ?(.+)', r'\1', 
                    unicode(os.path.splitext(os.path.basename(item))[0])),
        }
    items = extended_glob(os.path.join(MUSIC_PATH,path),["mp3","flac"])
    return [clear_name(item) for item in items]
        
def find_file(path, track):
    """Localize the file from the name and the path. (For track number)"""
    def is_valid(item,track,extensions):
        is_validated = False
        for extension in extensions:
            is_validated = is_validated | item.endswith(track+"."+extension)
        return is_validated
    items = extended_glob(os.path.join(MUSIC_PATH,path),["mp3","flac"])
    try:
        item = [item for item in items if is_valid(item,track,["mp3","flac"])][0]
        return item
    except IndexError:
        abort(404)

@app.route("/")
def main():
    """Main view (lists artists)"""
    return render_template("template.html",pagetitle="Music",items=generate_list())
    
@app.route("/explore")
def explore():
    """Default view => main"""
    return redirect(url_for('main'))
        
@app.route("/explore/<artist>")
def get_by_artist(artist=None):
    """Lists albums"""
    if artist != None:
        return render_template("template.html",pagetitle=artist,items=generate_list(artist+"/*"),pageparent="/explore/")
    else:
        abort(404)
        
@app.route("/explore/<artist>/<album>")
def get_by_album(artist=None, album=None):
    """Lists tracks"""
    if artist != None and album != None:
        try:
            content = parse(urllib.urlopen("http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=5b178049274207a42b2f9476652bb6dc&artist="+urllib.quote_plus(artist)+"&album="+urllib.quote_plus(album)))
            imageurl = content.getElementsByTagName("image")[3].firstChild.nodeValue
        except:
            imageurl = "http://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
        return render_template("album.html",pagetitle=artist,subtitle=album,items=generate_music_list(artist+"/"+album),imageurl=imageurl,pageparent="/explore/"+artist)
    else:
        abort(404)
        
@app.route("/explore/<artist>/<album>/<track>")
def get_by_track(artist=None, album=None, track=None):
    """Play track and show lyrics"""
    if artist != None and album != None and track != None:
        song_infos = None
        while song_infos == None:
            try:
                song_infos = parse(urllib.urlopen("http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist="+urllib.quote_plus(artist).lower()+"&song="+urllib.quote_plus(track).lower()))
            except IOError:
                pass
        try:
            lyrics = song_infos.getElementsByTagName("Lyric")[0].firstChild.nodeValue
        except AttributeError:
            lyrics = "Aucune parole trouvée !"
        try:
            content = parse(urllib.urlopen("http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=5b178049274207a42b2f9476652bb6dc&artist="+urllib.quote_plus(artist)+"&album="+urllib.quote_plus(album)))
            imageurl = content.getElementsByTagName("image")[3].firstChild.nodeValue
        except Exception as e:
            imageurl = "http://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
        return render_template("track.html",pagetitle=artist,subtitle=album+" - "+track,items=generate_music_list(artist+"/"+album),pageparent="/explore/"+artist,subparent="/explore/"+artist+"/"+album,rawurl="/assets/"+artist+"/"+album+"/"+track+".mp3",imageurl=imageurl,lyrics=lyrics)
    else:
        abort(404)

       
@app.route("/assets/<artist>/<album>/<track>.mp3")
def get_raw_sound(artist=None, album=None, track=None): 
    """Serve track"""
    if artist != None and album != None and track != None:
        filename = find_file(artist+"/"+album, track)
        with open(filename) as song:
            datas = song.read()
            response=make_response(datas)
            response.headers['Content-Type'] = mimetypes.guess_type(filename)[0]
            return response
    else:
        abort(404)

@app.route("/assets/<file>")
def asset(file=None):
    """Serve assets"""
    if file != None:
        try:
            datas = open(os.path.join('assets',file)).read()
            response = make_response(datas)
            response.headers['Content-type'] = mimetypes.guess_type(file)[0]
            return response
        except:
            abort(404)
    else:
        abort(404)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404
    
@app.before_request
def before_request():
    if request.path != '/' and request.path.endswith('/'):
        return redirect(request.path[:-1])
    
if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0",debug=True)
