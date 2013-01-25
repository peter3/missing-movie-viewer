missing-movie-viewer
====================

MMV is an XBMC plugin for searching your source folders for videos and TV shows in your path(s) but not in the library.

Currently it defaults to the following file types (can be changed in settings):
mpg, mpeg, avi, flv, wmv, mkv, 264, 3g2, 3gp, vob, mp4, mov, iso and ogm.

This is a fork of Nathan Hoads plugin with a few new and fixed options:
* You can now strip the path from the filename
* You can clear the output file before the scan
* File extensions are not hard-coded, instead they have a default
* You can skip files with specific filename parts (like 'sample' or 'extra')
