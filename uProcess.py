#!/usr/bin/env python

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#    
#    Author: jkaberg, https://github.com/jkaberg

import os
import sys
import time
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
logger.setLevel(logging.INFO)
loggerFormat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S')

loggerStd = logging.StreamHandler()
loggerStd.setFormatter(loggerFormat)
loggerStd.setLevel(logging.INFO)

loggerHdlr = logging.FileHandler(logfile)
loggerHdlr.setFormatter(loggerFormat)
loggerHdlr.setLevel(logging.INFO)

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
    except Exception, e:
        logger.error(loggerHeader + "Failed to find 7-zip in your system variables")
        sys.exit(1)
    return

def processFile(fileAction, inputFile, outputFile):
    if not os.path.isfile(outputFile):
        if fileAction == "move":
            try:
                logger.info(loggerHeader + "Moving file %s to %s", inputFile, outputFile)
                shutil.move(inputFile, outputFile)
            except Exception, e:
                logger.error(loggerHeader + "Failed to move file %s to %s", inputFile, outputFile)
                logging.exception(e)

        elif fileAction == "link":
            try:
                logger.info(loggerHeader + "Linking file %s to %s", inputFile, outputFile)
                # Link workaround for Windows systems
                if os.name == 'nt':
                    ctypes.windll.kernel32.CreateHardLinkA(outputFile, inputFile, 0)
                else:
                    os.link(inputFile, outputFile)
            except Exception, e:
                logger.error(loggerHeader + "Failed to link file %s to %s", inputFile, outputFile)
                logging.exception(e)
                logger.info(loggerHeader + "Copying file %s to %s", inputFile, outputFile)
                shutil.copy(inputFile, outputFile)

        else:
            try:
                logger.info(loggerHeader + "Copying file %s to %s", inputFile, outputFile)
                shutil.copy(inputFile, outputFile)
            except Exception, e:
                logger.error(loggerHeader + "Failed to copy file %s to %s", inputFile, outputFile)
                logging.exception(e)
    else:
        logger.error(loggerHeader + "File already exists at destination: %s", outputFile)

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

        # Extentions to use when searching directorys for files to process
        mediaExt = ('.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso', '.nfo', '.sub', '.srt', '.jpg', '.jpeg', '.gif')
        archiveExt = ('.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj', '.1', '.01', '.001')
        ignoreWords = ['sample', 'subs', 'proof']

        # Create output directory
        try:
            createDestination(outputDestination)
        except Exception, e:
            logger.error(loggerHeader + "Failed to create destination directory: %s", outputDestination)
            logging.exception(e)

        # Connect to uTorrent and stop the seeding if we need too
        if fileAction == "move" or fileAction == "link":
            uTorrentHost = "http://" + config.get("uTorrent", "host") + ":" + config.get("uTorrent", "port") + "/gui/"
            try:
                uTorrent = UTorrentClient(uTorrentHost, config.get("uTorrent", "user"), config.get("uTorrent", "password"))
                if uTorrent:
                    logger.debug(loggerHeader + "Stoping torrent with hash: " + inputHash)
                    uTorrent.stop(inputHash)
                    time.sleep(2)
            except Exception, e:
                logger.error(loggerHeader + "Failed to connect with uTorrent: %s", uTorrentHost)
                logging.exception(e)
        else:
            uTorrent = False

        # If we received a "single" file torrent from uTorrent, then we dont need to search the directory for files as we can join directory + filename 
        if inputFileName: 
            if inputFileName.lower().endswith(mediaExt) and not any(word in inputFileName.lower() for word in ignoreWords):
                if os.path.isfile(inputDirectory):
                    try:
                        processFile(fileAction, inputDirectory, outputDestination)
                    except Exception, e:
                        logging.error(loggerHeader + "There was an error when trying to process file: %s", os.path.join(inputDirectory, inputFileName))
                        logging.exception(e)
                else:
                    try:
                        processFile(fileAction, os.path.join(inputDirectory, inputFileName), outputDestination)
                    except Exception, e:
                        logging.error(loggerHeader + "There was an error when trying to process file: %s", os.path.join(inputDirectory, inputFileName))
                        logging.exception(e)
        else:
            for dirpath, dirnames, filenames in os.walk(inputDirectory):
                for filename in filenames:
                    inputFile = os.path.join(dirpath, filename)
                    if filename.lower().endswith(mediaExt) and not any(word in filename.lower() for word in ignoreWords):
                        logger.debug(loggerHeader + "Found media file: %s", filename)
                        outputFile = os.path.join(outputDestination, filename)
                        try:
                            processFile(fileAction, inputFile, outputFile)
                        except Exception, e:
                            logging.error(loggerHeader + "There was an error when trying to process file: %s", inputFile)
                            logging.exception(e)

                    elif filename.lower().endswith(archiveExt) and not any(word in filename.lower() for word in ignoreWords):
                        logger.debug(loggerHeader + "Found compressed file: %s", filename)
                        try:
                            extractFile(inputFile, outputDestination)
                        except Exception, e:
                            logging.error(loggerHeader + "There was an error when trying to extract file: %s", inputFile)
                            logging.exception(e)

        # Optionally process the outputDestination by calling Couchpotato/Sickbeard
        if inputLabel == config.get("Couchpotato", "label") and config.get("Couchpotato", "active") == True:
            try:
                logger.info(loggerHeader + "Calling Couchpotato to process directory: %s", outputDestination)
                if config.get("Couchpotato", "ssl") == True:
                    sslBase = "https://"
                else:
                    sslBase = "http://"
                urllib2.urlopen(sslBase + config.get("Couchpotato", "host") + ":" + config.get("Couchpotato", "port") + "/" + config.get("Couchpotato", "web_root") + "api/" + config.get("Couchpotato", "apikey") + "/renamer.scan/?movie_folder=" + outputDestination)
                time.sleep(2)
            except Exception, e:
                logger.error(loggerHeader + "Couchpotato post process failed for directory: %s ", outputDestination)
                logging.exception(e)

        elif inputLabel == config.get("Sickbeard", "label") and config.get("Sickbeard", "active") == True:
            try:
                logger.info(loggerHeader + "Calling Sickbeard to process directory: %s", outputDestination)
                autoProcessTV.processEpisode(outputDestination)
                time.sleep(2)
            except Exception, e:
                logger.error(loggerHeader + "Sickbeard post process failed for directory: %s ", outputDestination)
                logging.exception(e)

        # Delete leftover files
        if config.get("uProcess", "deleteLeftover") == True:
            try:
                logger.debug(loggerHeader + "Deleting directory and content: %s", outputDestination)
                shutil.rmtree(outputDestination)
            except Exception, e:
                logger.error(loggerHeader + "Failed to delete directory: %s", outputDestination)
                logging.exception(e)

        # Resume seeding in uTorrent
        if uTorrent:
            if fileAction == "move":
                logger.debug(loggerHeader + "Removing torrent with hash: " + inputHash)
                uTorrent.removedata(inputHash)
                time.sleep(2)
            elif fileAction == "link":
                logger.debug(loggerHeader + "Starting torrent with hash: " + inputHash)
                uTorrent.start(inputHash)
                time.sleep(2)

        logger.info(loggerHeader + "Success, all done!\n")

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

    try:
        main(inputDirectory, inputName, inputHash, inputKind, inputFileName, inputLabel)
    except Exception, e:
        logger.error(loggerHeader + "One or more variables are missing")
        logging.exception(e)