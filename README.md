uProcess
========

a tiny python post process for uTorrent


Usage:
---------
- Install uTorrent 3.0+, 7zip and Python 2.7.4
- Setup uTorrent to use Web UI (Options-Preferences->Advanced->Web UI), note down user/password and listening port
- Extract this script to any location, in this example C:\Downloaders\uProcess
- Edit the config.cfg file in C:\Downloaders\uProcess to your preferences
- Goto uTorrent again, in Options-Preferences->Advanced->Run Program, where it says "run this program when torrent finishes" add: C:\Python27\pythonw.exe C:\Downloaders\uProcess\uProcess.py "%D" "%N" "%I" "%K" "%F" "%L"
- Add 7zip to your system environment variables in Windows

Done :-)

Note: this script might work on Linux and OSX as all 3 requirements exists there, not tested though
