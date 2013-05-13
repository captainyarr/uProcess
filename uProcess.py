#!/usr/bin/env python

# Written by jkaberg, https://github.com/jkaberg
import os
import sys
import shutil
import logging
import subprocess
import ctypes
import urllib2
import ConfigParser

from utorrent.client import UTorrentClient
import autoProcessTV

logfile = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "uProcess.log"))
configFilename = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "config.cfg"))

loggerHeader = "uProcess :: "
logger = logging.getLogger('uProcess')
logger.setLevel(logging.DEBUG)
loggerFormat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S')

loggerStd = logging.StreamHandler()
loggerStd.setFormatter(loggerFormat)
loggerStd.setLevel(logging.DEBUG)

loggerHdlr = logging.FileHandler(logfile)
loggerHdlr.setFormatter(loggerFormat)
loggerHdlr.setLevel(logging.DEBUG)

logger.addHandler(loggerStd)
logger.addHandler(loggerHdlr)

def createDestination(outputDestination):
    if not os.path.exists(outputDestination):
        logger.info(loggerHeader + "Creating destination: " + outputDestination)
        os.makedirs(outputDestination)
    return

def extractFile(compressedFile, outputDestination):
    try:
        logger.info(loggerHeader + "Unpacking %s to %s", compressedFile, outputDestination)
        FNULL = open(os.devnull, 'w')
        subprocess.call(['7z', 'x', compressedFile, '-aos', '-o' + outputDestination], stdout=FNULL, stderr=subprocess.STDOUT)
    except:
        logger.error(loggerHeader + "Couldnt find 7zip in your system variables")
    return

def processFile(fileAction, inputFile, outputFile):
    if fileAction == "move":
        logger.info(loggerHeader + "Moving file %s to %s", inputFile, outputFile)
        shutil.move(inputFile, outputFile)

    elif fileAction == "link":
        try:
            logger.info(loggerHeader + "Linking file %s to %s", inputFile, outputFile)
            if os.name == 'nt':
                if ctypes.windll.kernel32.CreateHardLinkW(unicode(outputFile), unicode(inputFile), 0) == 0:
                    raise ctypes.WinError()
            else:
                os.link(inputFile, outputFile)
        except:
            logger.error(loggerHeader + "Couldnt link file, copying %s to %s", inputFile, outputFile)
            shutil.copy(inputFile, outputFile)

    else:
        logger.info(loggerHeader + "Copying file %s to %s", inputFile, outputFile)
        shutil.copy(inputFile, outputFile)

    return

def main(inputDirectory, inputName, inputHash, inputKind, inputFileName, inputLabel):

    if not os.path.isfile(configFilename):
        logger.error(loggerHeader + "Config file not found: " + configFilename)
        sys.exit(1)
    else:
        logger.info(loggerHeader + "Config loaded: " + configFilename)

        config = ConfigParser.ConfigParser()
        config.read(configFilename)

        logger.debug(loggerHeader + "Torrent Dir: " + inputDirectory)
        logger.debug(loggerHeader + "Torrent Name: " + inputName)
        logger.debug(loggerHeader + "Torrent Hash: " + inputHash)
        logger.debug(loggerHeader + "Torrent Kind: " + inputKind)

        if inputKind == "single":
            logger.debug(loggerHeader + "Torrent Filename: " + inputFileName)
        if inputLabel:
            logger.debug(loggerHeader + "Torrent Label: " + inputLabel)

        fileAction = config.get("uProcess", "fileAction")
        outputDestination = os.path.join(config.get("uProcess", "outputDirectory"), inputLabel, inputName)
        mediaExt = ('.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso', '.nfo', '.sub', '.srt', '.jpg', '.jpeg', '.gif')
        archiveExt = ('.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj', '.1', '.01', '.001')

        # Create output destination
        try:
            createDestination(outputDestination)
        except IOError:
            raise

        # Connect to uTorrent and stop the seeding if we need too
        if fileAction == "move" or fileAction == "link":
            try:
                uTorrent = UTorrentClient(config.get("uTorrent", "host"), config.get("uTorrent", "user"), config.get("uTorrent", "password"))
                if uTorrent:
                    logger.debug(loggerHeader + "Stoping torrent with hash: " + inputHash)
                    uTorrent.stop(inputHash)
            except:
                raise
        else:
            uTorrent = False

        if inputFileName: # Single type torrent, no need for loop (we can assume this dosnt need extraction)
            if inputFileName.lower().endswith(mediaExt) and 'sample' not in inputFileName.lower() and '/subs' not in inputFileName.lower():
                processFile(fileAction, os.path.join(inputDirectory, inputFileName), outputDestination)
        else: # Multi type torrent, here we need to loop the inputDirectory and copy/move/link or extract accordingly
            for dirpath, dirnames, filenames in os.walk(inputDirectory):
                for filename in filenames:
                    inputFile = os.path.join(dirpath, filename)
                    if filename.lower().endswith(mediaExt) and 'sample' not in filename.lower() and '/subs' not in filename.lower():
                        logger.debug(loggerHeader + "Found media file: %s", filename)
                        outputFile = os.path.join(outputDestination, filename)
                        try:
                            processFile(fileAction, inputFile, outputFile)
                        except IOError:
                            raise
                    elif filename.lower().endswith(archiveExt) and 'sample' not in filename.lower() and '/subs' not in filename.lower():
                        logger.debug(loggerHeader + "Found compressed file: %s", filename)
                        try:
                            extractFile(inputFile, outputDestination)
                        except IOError:
                            raise

        # Couchpotato and Sickbeard processing
        if inputLabel == config.get("Couchpotato", "label") and config.get("Couchpotato", "active"):
            try:
                logger.info(loggerHeader + "Calling Couchpotato to process directory: %s", outputDestination)
                if config.get("Couchpotato", "ssl"):
                    sslBase = "https://"
                else:
                    sslBase = "http://"
                urllib2.urlopen(sslBase + config.get("Couchpotato", "host") + ":" + config.get("Couchpotato", "port") + "/" + config.get("Couchpotato", "web_root") + "api/" + config.get("Couchpotato", "apikey") + "/renamer.scan/?movie_folder=" + outputDestination)
            except:
                logger.error(loggerHeader + "Couchpotato post process for directory %s failed", outputDestination)
        elif inputLabel == config.get("Sickbeard", "label") and config.get("Sickbeard", "active"):
            try:
                logger.info(loggerHeader + "Calling Sickbeard to process directory: %s", outputDestination)
                autoProcessTV.processEpisode(outputDestination)
            except:
                logger.error(loggerHeader + "Sickbeard post process for directory %s failed", outputDestination)

        # Resume seeding in uTorrent
        if uTorrent:
            if fileAction == "move":
                logger.debug(loggerHeader + "Removing torrent with hash: " + inputHash)
                uTorrent.removedata(inputHash)
            elif fileAction == "link":
                logger.debug(loggerHeader + "Starting torrent with hash: " + inputHash)
                uTorrent.start(inputHash)

        logger.info(loggerHeader + "Success, all done!")

if __name__ == "__main__":

    # usage: uProcess.py "%D" "%N" "%I" "%K" "%F" "%L"
    # uTorrent 3.0+ only
    inputDirectory = os.path.normpath(sys.argv[1])  # %D - Where the files are located
    inputName = sys.argv[2]                         # %N - The name of the torrent (as seen in uTorrent)
    inputHash = sys.argv[3]                         # %I - The hash of the torrent
    inputKind = sys.argv[4]                         # %K - The torrent kind (single/multi)
    if inputKind == "single":
        inputFileName = sys.argv[5]                 # %F
    else:
        inputFileName = None
    if sys.argv[6]:
        inputLabel = sys.argv[6]                    # %L - The label of the torrent
    else:
        inputLabel = None

    main(inputDirectory, inputName, inputHash, inputKind, inputFileName, inputLabel)