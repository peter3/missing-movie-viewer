import sys, os
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import unicodedata
import urllib
import re

import datetime

##import rpdb2 
##rpdb2.start_embedded_debugger('pw')

# plugin modes
MODE_FIRST = 10
MODE_SECOND = 20
MODE_HELP = 30

# clear output file settings
NEVER = "0"
BEFORE_MOVIES = "1"
BEFORE_TVSERIES = "2"
ASK = "3"
ALWAYS = "4"

# parameter keys
PARAMETER_KEY_MODE = "mode"

__addon__ = xbmcaddon.Addon(id='plugin.video.missingmovies')
__addonid__ = __addon__.getAddonInfo('id')
__scriptdebug__ = __addon__.getSetting("debug") == "true"
##__fileextensions__ = ['mpg', 'mpeg', 'avi', 'flv', 'wmv', 'mkv', '264', '3g2', '3gp', 'ifo', 'mp4', 'mov', 'iso', 'divx', 'ogm']
__fileextensions__ = __addon__.getSetting("custom_file_extensions").split(";")
__skip_content__ = __addon__.getSetting("skip_content").split(";")
__strip_path__ = __addon__.getSetting("strip_path") == "true"
__handle__ = int(sys.argv[1])
__language__ = __addon__.getLocalizedString
__clear_output_file__ = __addon__.getSetting("clear_output_file")

__outputfile__ = os.path.join(__addon__.getSetting("output_dir"), __addon__.getSetting("output_file"));
__dircount__ = 0
__filecount__ = 0

def log(txt, severity=xbmc.LOGDEBUG):
    if __scriptdebug__ and severity == xbmc.LOGINFO:
        severity = xbmc.LOGNOTICE
    try:
        message = (u"MMV: %s" % txt)
        xbmc.log(msg=message, level=severity)
    except UnicodeEncodeError:
        message = ("UnicodeEncodeError")
        xbmc.log(msg=message, level=xbmc.LOGWARNING) 

def clear_output(action):
    log("action is %s and __clear_output_file__ is %s" % (action,__clear_output_file__), xbmc.LOGINFO)
    clearoutput = False;
    if __clear_output_file__ == ALWAYS:
        log("Clearing output because __clear_output_file__ is ALWAYS", xbmc.LOGINFO)
        clearoutput = True
    elif __clear_output_file__ == ASK:
        if xbmcgui.Dialog().yesno("Missing Movies", "Clear output file?"):
            log("Clearing output because __clear_output_file__ is ASK", xbmc.LOGINFO)
            clearoutput = True
    elif __clear_output_file__ == action:
        log("Clearing output because __clear_output_file__ is same as action", xbmc.LOGINFO)
        clearoutput = True
    if clearoutput:
        f = open(__outputfile__, 'w')
        f.close()

def string_startswith_case_insensitive(stringA, stringB):
    return stringA.lower().startswith( stringB.lower() )

def ends_on_sep(path):
    if path[-1] == '/' or path[-1] == os.sep:
        return True
    return False

def clean_path(s):
    s = urllib.unquote(s)
    s = strip_username_password(s)
    s = unicode(s, 'utf-8')
    return s

def remove_duplicates(files):
    # converting it to a set and back drops all duplicates
    return list(set(files))

def strip_username_password(s):
    if s.find('@') != -1:
        startpos = s.find("://") + 3
        if s.startswith("rar://") or s.startswith("zip://"):
            startpos = s.find("://", startpos) + 3
        s = s[0:startpos] + s[s.find('@') + 1:]
    return s

def output_to_file(list):
    f = open(__outputfile__, 'a')
    for item in list:
        file = item + '\n'
        f.write(file.encode('utf-8'))
    f.close()

def get_sources():
    results = []
    result = eval(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media": "video"}, "id": 1}'))
    if 'sources' not in result['result']:
        return results

    sources = result['result']['sources']
    sources = [ xbmc.validatePath(s['file']) for s in sources ]

    for s in sources:
        log("FOUND SOURCE: %s" % s, xbmc.LOGINFO)
        if s.startswith('addons://'):
            s = clean_path(s)
            log("%s is an addon source, ignoring..." % s, xbmc.LOGINFO)
        elif s.startswith('multipath://'):
            log("%s is a multipath source, splitting and adding individuals..." % s, xbmc.LOGINFO)
            s = s.replace('multipath://', '')
            parts = s.split('/')
            parts = [ f for f in parts ]

            for b in parts:
                if b:
                    b = clean_path(b)
                    log("%s is a straight forward source, adding.." % b, xbmc.LOGINFO)
                    results.append(b)
        else:
            s = clean_path(s)
            log("%s is a straight forward source, adding..." % s, xbmc.LOGINFO)
            results.append(s)

    return results
    
def get_movie_sources():
    result = eval(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params":{"properties": ["file"]},  "id": 1}'))
    if 'movies' not in result['result']:
        return []
      
    files = []
    for item in result['result']['movies']:
        files.extend( decode_stacked( item['file'] ) )  #handle possibly stacked movies here
        
    files = [ clean_path(os.path.dirname(f)) for f in files ]
    files = remove_duplicates(files)
    log(files, xbmc.LOGINFO)

    sources = remove_duplicates(get_sources())

    results = []
    for f in files:
       for s in sources:
            if f[-1] != '/' and f.find('/') != -1:
                f += '/'
            elif f[-1] != os.sep and f.find(os.sep) != -1:
                f += os.sep
            
            if string_startswith_case_insensitive(f,s):
                log("%s was confirmed as a movie source using %s" % (s, f), xbmc.LOGINFO)
                results.append(f[:len(s)])
                sources.remove(s)
                            
    return results

def get_tv_files(called_from_tv_menu, progress, done):
    result = eval(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "id": 1}'))
    if 'tvshows' not in result['result']:
        return []
        
    tv_shows = result['result']['tvshows']
    files = []

    for tv_show in tv_shows:
        show_id = tv_show['tvshowid']
        show_name = clean_path(tv_show['label'])
        log("%s" % show_name, xbmc.LOGINFO)
        displaystring = __language__(30209) + show_name
        log("%s" % displaystring, xbmc.LOGINFO)
        progress.update(done, displaystring.encode('utf-8')) 

        episode_result = eval(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": ["file"]}, "id": 1}' % show_id))

        try:
            episodes = episode_result['result']['episodes']
            files.extend([ clean_path(e['file']) for e in episodes ])
        except KeyError as e:
            if called_from_tv_menu and __scriptdebug__:
                displaystring = __language__(30209) + show_name
                xbmcgui.Dialog().ok(__language__(30203), displaystring.encode('utf-8'), __language__(30204))
            
            log("get_tv_files exception %s" % str(e), xbmc.LOGINFO)

    return files

def get_tv_sources(progress, done):
    files = get_tv_files(False, progress, done)
    files = [ os.path.dirname(f) for f in files ]
    files = remove_duplicates(files)

    sources = remove_duplicates(get_sources())

    results = []
    for f in files:
        for s in sources:
            if f[-1] != '/' and f.find('/') != -1:
                f += '/'
            elif f[-1] != os.sep and f.find(os.sep) != -1:
                f += os.sep
                
            if string_startswith_case_insensitive(f,s):
                log("%s was confirmed as a TV source using %s" % (s, f), xbmc.LOGINFO)
                results.append(f[:len(s)])
                sources.remove(s)

    return results

def skip_content(filename, content):
    for part in content:
        if part.strip() != "" and part.lower() in filename.lower():
            return True
    return False
    
def file_has_extensions(filename, extensions):
    # get the file extension, without a leading colon.
    name, extension = os.path.splitext(os.path.basename(filename))
    name = name.lower()
    extension = extension[1:].lower()
    extensions = [ f.lower() for f in extensions ]

    if extension == '' or (extension == 'ifo' and name != 'video_ts'):
        return False

    return extension in extensions

def get_files(path, progress, done):
    global __dircount__
    global __filecount__
    __dircount__ += 1
    path = path.replace("\\", "/")
    results = []
    #log("get_files called for %s" % path, xbmc.LOGNOTICE)
    displaypath = __language__(30213) + path
    progress.update(done, __language__(30210) + str(__dircount__) + __language__(30211) + str(__filecount__) + __language__(30212), displaypath.encode('utf-8'))

    #for some reason xbmc throws an exception when doing GetDirectory on an empty source directory. it works when one file is in there. so catch that
    try:
        json = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params":{"directory": "' + path + '"},  "id": 1}'
        result = eval(xbmc.executeJSONRPC(json.encode('utf-8')))
    except NameError:
        return results
    if 'files' not in result['result']:
        return results

    #log("Files.GetDirectory %s" % result, xbmc.LOGNOTICE)

    for item in result['result']['files']:
            f = clean_path(item['file'])
            
            if skip_content(f, __skip_content__):
                log("SKIPPED %s" % f, xbmc.LOGNOTICE)
            elif ends_on_sep(f) and not f.startswith("zip://") and not f.startswith("rar://"):
                #log("EXTEND TO %s" % f, xbmc.LOGNOTICE)
                results.extend(get_files(f, progress, done))
            elif file_has_extensions(f, __fileextensions__):
                __filecount__ += 1
                results.append(os.path.basename(f) if __strip_path__ else f)
                #log("ADDED %s" % f, xbmc.LOGNOTICE)
            progress.update(done, __language__(30210) + str(__dircount__) + __language__(30211) + str(__filecount__) + __language__(30212), displaypath.encode('utf-8'))
    return results

# utility functions
def parameters_string_to_dict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

def addDirectoryItem(name, isFolder=True, parameters={}, totalItems=1):
    ''' Add a list item to the XBMC UI. '''
    li = xbmcgui.ListItem(name)

    url = sys.argv[0] + '?' + urllib.urlencode(parameters)

    if not isFolder:
        url  = name
    return xbmcplugin.addDirectoryItem(handle=__handle__, url=url, listitem=li, isFolder=isFolder,totalItems=totalItems)

# UI builder functions
def show_root_menu():
    ''' Show the plugin root menu. '''
    addDirectoryItem(name=__language__(30200), parameters={ PARAMETER_KEY_MODE: MODE_FIRST }, isFolder=True)
    addDirectoryItem(name=__language__(30201), parameters={ PARAMETER_KEY_MODE: MODE_SECOND }, isFolder=True)
    addDirectoryItem(name=__language__(30202), parameters={ PARAMETER_KEY_MODE: MODE_HELP }, isFolder=True)
    xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

def decode_stacked(s):
    parts = [ s ]
    if s.startswith('stack://'):
        s = s.replace('stack://', '')
        parts = s.split(' , ')
    return parts
     
def show_movie_submenu():
    ''' Show movies missing from the library. '''

    xbmc.executebuiltin("Dialog.Close(busydialog)")
    progress = xbmcgui.DialogProgress()
    progress.create(__language__(30214), __language__(30215))

    done = 0
    progress.update(done, __language__(30216))
    movie_sources = remove_duplicates(get_movie_sources())
    if len(movie_sources) == 0 or len(movie_sources[0]) == 0:
        xbmcgui.Dialog().ok(__language__(30203), __language__(30205), __language__(30204))
        log("No movie sources!", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle=__handle__, succeeded=False)
        return

    result = eval(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params":{"properties": ["file"]},  "id": 1}'))
    movies = result['result']['movies']

    library_files = []
    missing = []

    done = 10
    progress.update(done, __language__(30217))
    log("SEARCHING MOVIES", xbmc.LOGNOTICE)
    # this magic section adds the files from sets!
    for m in movies:
        f = clean_path(m['file'])

        if f.startswith("videodb://"):
            json = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "' + f + '"}, "id": 1}'
            set_files = eval(xbmc.executeJSONRPC(json.encode('utf-8')))

            sub_files = []

            for item in set_files['result']['files']:
                sub_files.append(clean_path(item['file']))
            library_files.extend(sub_files)
        elif f.startswith('stack://'):
            stack = decode_stacked(f)
            library_files.extend(stack)
        else:
            library_files.append(f)
    library_files = set(library_files)
    
    done = 50
    progress.update(done, __language__(30218))
    #log("library_files %s" % library_files, xbmc.LOGNOTICE)
    #log("movie_sources %s" % movie_sources, xbmc.LOGNOTICE)
    for movie_source in movie_sources:
        #log("Getting files from movie source %s" % movie_source, xbmc.LOGNOTICE)
        movie_files = set(get_files(movie_source, progress, done))

        if not library_files.issuperset(movie_files):
            log("%s contains missing movies!" % movie_source, xbmc.LOGNOTICE)
            l = list(movie_files.difference(library_files))
            l.sort()
            missing.extend(l)

    done = 90
    progress.update(done, __language__(30219))
    #log("movie_file -> missing %s" % missing, xbmc.LOGNOTICE)
    for movie_file in missing:
        # get the end of the filename without the extension
        addDirectoryItem(movie_file, isFolder=False, totalItems=len(missing))

    if __outputfile__:
        clear_output(BEFORE_MOVIES)
        output_to_file(missing);

    xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

def show_tvshow_submenu():
    ''' Show TV shows missing from the library. '''

    xbmc.executebuiltin("Dialog.Close(busydialog)")
    progress = xbmcgui.DialogProgress()
    progress.create(__language__(30214), __language__(30215))

    done = 0
    progress.update(0, __language__(30220))
    tv_sources = remove_duplicates(get_tv_sources(progress, done))
    if len(tv_sources) == 0 or len(tv_sources[0]) == 0:
        xbmcgui.Dialog().ok(__language__(30203), __language__(30206), __language__(30204))
        log("No TV sources!", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle=__handle__, succeeded=False)
        return

    done = 10
    progress.update(done, __language__(30221))
    library_files = set(get_tv_files(True, progress, done))
    missing = []

    done = 50
    progress.update(done, __language__(30222))
    log("SEARCHING TV SHOWS", xbmc.LOGNOTICE);
    for tv_source in tv_sources:
        #log("Getting files from tv source %s" % tv_source, xbmc.LOGNOTICE)
        tv_files = set(get_files(tv_source, progress, done))
        if not library_files.issuperset(tv_files):
            log("%s contains missing TV shows!" % tv_source, xbmc.LOGNOTICE)
            l = list(tv_files.difference(library_files))
            l.sort()
            missing.extend(l)

    done = 90    
    progress.update(done, __language__(30219))
    for tv_file in missing:
        addDirectoryItem(tv_file, isFolder=False)

    #log("library files: %s" % library_files, xbmc.LOGINFO)
    #log("missing episodes: %s" % missing, xbmc.LOGNOTICE)

    if __outputfile__:
        clear_output(BEFORE_TVSERIES)
        output_to_file(missing)

    xbmcplugin.endOfDirectory(handle=__handle__, succeeded=True)

def show_help():
    xbmcgui.Dialog().ok(__language__(30202), __language__(30208))

# parameter values
params = parameters_string_to_dict(sys.argv[2])
mode = int(params.get(PARAMETER_KEY_MODE, "0"))

# Depending on the mode, call the appropriate function to build the UI.
if not sys.argv[2]:
    # new start
    log("MISSING MOVIE VIEWER STARTED.", xbmc.LOGNOTICE);
    ok = show_root_menu()
elif mode == MODE_FIRST:
    ok = show_movie_submenu()
elif mode == MODE_SECOND:
    ok = show_tvshow_submenu()
elif mode == MODE_HELP:
    ok = show_help()
