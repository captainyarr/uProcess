uProcess
========

a tiny python post processer for uTorrent

Features:
---------
- Extract downloaded content
- Move/copy or (hard)link downloaded content (that dosnt need extraction)
- Optionally calls Couchpotato and Sickbbeard when done (additional post-processing)

Requirements:
---------
- uTorrent 2.2.1 Build 25302 (confirmed), might work on earlier versions
- 7-zip
- Python 2.7+

Usage:
---------
- Install uTorrent, 7-zip and Python
- Setup uTorrent to use Web UI (Options-Preferences->Advanced->Web UI), note down user/password and listening port
- Extract this script to any location, in this example C:\Downloaders\uProcess
- Edit the config.cfg file in C:\Downloaders\uProcess to your preferences
- Goto uTorrent again, in Options-Preferences->Advanced->Run Program, where it says "run this program when torrent finishes" add: C:\Python27\pythonw.exe C:\Downloaders\uProcess\uProcess.py "%D" "%N" "%I" "%L"
- Add 7zip to your system environment variables in Windows

Done :-)


Note: this script might work on Linux and OSX as all 3 requirements exists there, not tested though
