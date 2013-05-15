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
#    Creator of uProcess: jkaberg, https://github.com/jkaberg

import os, sys, time, shutil, logging, subprocess, ctypes, urllib, urllib2, ConfigParser

from utorrent.client import UTorrentClient
import autoProcessTV

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)

def createDestination(outputDestination):
    if os.path.exists(outputDestination):
        logger.debug(loggerHeader + "Destination directory exist: %s", outputDestination)
    else:
        try:
            logger.info(loggerHeader + "Creating destination: %s", outputDestination)
            os.makedirs(outputDestination)
        except Exception, e:
            logger.error(loggerHeader + "Failed to create destination directory: %s", outputDestination)
            logging.exception(e)
    return

def extractFile(compressedFile, outputDestination):
    try:
        logger.info(loggerHeader + "Extracting %s to %s", compressedFile, outputDestination)
        FNULL = open(os.devnull, 'w')
        subprocess.call(['7z', 'x', compressedFile, '-aos', '-o' + outputDestination], stdout=FNULL, stderr=subprocess.STDOUT)
    except Exception, e:
        logger.error(loggerHeader + "Unable to execute 7-zip, is the 7-zip directory in your system variables?")
        logging.exception(e)
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
                logger.info(loggerHeader + "Linking failed, copying file %s to %s", inputFile, outputFile)
                logging.exception(e)
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

def processMovie(inputDirectory):

    host = config.get("Couchpotato", "host")
    port = config.get("Couchpotato", "port")
    apikey = config.get("Couchpotato", "apikey")
    ssl = config.getboolean("Couchpotato", "ssl")

    try:
        baseURL = config.get("Couchpotato", "baseURL")
        logger.debug(loggerHeader + "processMovie :: URL base: %s", baseURL)
    except ConfigParser.NoOptionError:
        baseURL = None

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + "/" + baseURL + "api/" + apikey + "/renamer.scan/?movie_folder=" + inputDirectory

    try:
        urlObj = urllib2.urlopen(url)
        logger.debug(loggerHeader + "processMovie :: Opening URL: %s", url)
    except IOError, e:
        logger.error(loggerHeader + "processMovie :: Unable to open URL: ", str(e))
        sys.exit(1)

    result = urlObj.readlines()
    for line in result:
        logger.info(loggerHeader + "processMovie :: " + line)

def processEpisode(inputDirectory, torrentName=None):

    host = config.get("Sickbeard", "host")
    port = config.get("Sickbeard", "port")
    username = config.get("Sickbeard", "username")
    password = config.get("Sickbeard", "password")
    ssl = config.getboolean("Sickbeard", "ssl")

    try:
        baseURL = config.get("Sickbeard", "baseURL")
        logger.debug(loggerHeader + "processEpisode :: URL base: %s", baseURL)
    except ConfigParser.NoOptionError:
        baseURL = None

    params = {}
    params['quiet'] = 1
    params['dir'] = inputDirectory
    if torrentName != None:
        params['torrentName'] = torrentName

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    url = protocol + host + ":" + port + "/" + baseURL + "home/postprocess/processEpisode?" + urllib.urlencode(params)

    myOpener = AuthURLOpener(username, password)
    try:
        urlObj = myOpener.openit(url)
        logger.debug(loggerHeader + "processEpisode :: Opening URL: %s", url)
    except IOError, e:
        logger.error(loggerHeader + "processEpisode :: Unable to open URL: ", str(e))
        sys.exit(1)

    result = urlObj.readlines()
    for line in result:
        logger.debug(loggerHeader + "processEpisode :: " + line)

def main(inputDirectory, inputName, inputHash, inputKind, inputFileName, inputLabel):

    fileAction = config.get("uProcess", "fileAction")
    outputDestination = os.path.join(config.get("uProcess", "outputDirectory"), inputLabel, inputName)

    logger.debug(loggerHeader + "Torrent Dir: %s", inputDirectory)
    logger.debug(loggerHeader + "Torrent Name: %s", inputName)
    logger.debug(loggerHeader + "Torrent Hash: %s", inputHash)
    logger.debug(loggerHeader + "Torrent Kind: %s", inputKind)

    if inputKind == "single":
        logger.debug(loggerHeader + "Torrent Filename: %s", inputFileName)
    if inputLabel:
        logger.debug(loggerHeader + "Torrent Label: %s", inputLabel)

    # Extentions to use when searching directorys for files to process
    mediaExt = ('.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso', '.nfo', '.sub', '.srt', '.jpg', '.jpeg', '.gif')
    archiveExt = ('.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj', '.1', '.01', '.001')

    # An list of words that we dont want filenames/directorys to contain
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
                logger.debug(loggerHeader + "Stoping torrent with hash: %s", inputHash)
                uTorrent.stop(inputHash)
        except Exception, e:
            logger.error(loggerHeader + "Failed to connect with uTorrent: %s", uTorrentHost)
            logging.exception(e)
        time.sleep(2)
    else:
        uTorrent = False

    # If we received a "single" file torrent from uTorrent, then we dont need to search the directory for files as we can join directory + filename 
    if inputFileName and inputFileName.lower().endswith(mediaExt) and not any(word in inputFileName.lower() for word in ignoreWords) and not any(word in inputDirectory.lower() for word in ignoreWords):
        if os.path.isfile(inputDirectory):
            processFile(fileAction, inputDirectory, outputDestination)
        else:
            processFile(fileAction, os.path.join(inputDirectory, inputFileName), outputDestination)
    else:
        for dirpath, dirnames, filenames in os.walk(inputDirectory):
            for filename in filenames:
                inputFile = os.path.join(dirpath, filename)
                outputFile = os.path.join(outputDestination, filename)
                if filename.lower().endswith(mediaExt) and not any(word in filename.lower() for word in ignoreWords) and not any(word in inputDirectory.lower() for word in ignoreWords):
                    logger.debug(loggerHeader + "Found media file: %s", filename)
                    processFile(fileAction, inputFile, outputFile)

                elif filename.lower().endswith(archiveExt) and not any(word in filename.lower() for word in ignoreWords) and not any(word in inputDirectory.lower() for word in ignoreWords):
                    logger.debug(loggerHeader + "Found compressed file: %s", filename)
                    extractFile(inputFile, outputDestination)

    # Optionally process the outputDestination by calling Couchpotato/Sickbeard
    if inputLabel == config.get("Couchpotato", "label") and config.getboolean("Couchpotato", "active"):
        try:
            logger.info(loggerHeader + "Calling Couchpotato to process directory: %s", outputDestination)
            processMovie(outputDestination)
        except Exception, e:
            logger.error(loggerHeader + "Couchpotato post process failed for directory: %s", outputDestination)
            logging.exception(e)
        time.sleep(2)

    elif inputLabel == config.get("Sickbeard", "label") and config.getboolean("Sickbeard", "active"):
        try:
            logger.info(loggerHeader + "Calling Sickbeard to process directory: %s", outputDestination)
            processEpisode(outputDestination, inputName)
        except Exception, e:
            logger.error(loggerHeader + "Sickbeard post process failed for directory: %s", outputDestination)
            logging.exception(e)
        time.sleep(2)

    # Delete leftover files
    if config.getboolean("uProcess", "deleteLeftover"):
        try:
            logger.debug(loggerHeader + "Deleting directory and content: %s", outputDestination)
            shutil.rmtree(outputDestination)
        except Exception, e:
            logger.error(loggerHeader + "Failed to delete directory: %s", outputDestination)
            logging.exception(e)

    # Resume seeding in uTorrent
    if uTorrent:
        if fileAction == "move":
            logger.debug(loggerHeader + "Removing torrent with hash: %s", inputHash)
            uTorrent.removedata(inputHash)
        elif fileAction == "link":
            logger.debug(loggerHeader + "Starting torrent with hash: %s", inputHash)
            uTorrent.start(inputHash)
        time.sleep(2)

    logger.info(loggerHeader + "Success, all done!\n")

if __name__ == "__main__":

    logfile = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "uProcess.log"))
    loggerHeader = "uProcess :: "
    loggerFormat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S')
    logger = logging.getLogger('uProcess')
    if config.getboolean("uProcess", "debug"):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    config = ConfigParser.ConfigParser()
    configFilename = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "config.cfg"))
    config.read(configFilename)

    if not os.path.isfile(configFilename):
        logger.error(loggerHeader + "Config file not found: " + configFilename)
        sys.exit(1)
    else:
        logger.info(loggerHeader + "Config loaded: " + configFilename)

    # usage: uProcess.py "%D" "%N" "%I" "%K" "%F" "%L"
    # uTorrent 3.0+ only
    inputDirectory = os.path.normpath(sys.argv[1])  # %D - Where the files are located
    inputName = sys.argv[2]                         # %N - The name of the torrent (as seen in uTorrent)
    inputHash = sys.argv[3]                         # %I - The hash of the torrent
    inputKind = sys.argv[4]                         # %K - The torrent kind (single/multi)
    if inputKind == "single":
        inputFileName = sys.argv[5]                 # %F
    else:
        inputFileName = False
    if sys.argv[6]:
        inputLabel = sys.argv[6]                    # %L - The label of the torrent
    else:
        inputLabel = False

    try:
        main(inputDirectory, inputName, inputHash, inputKind, inputFileName, inputLabel)
    except Exception, e:
        logger.error(loggerHeader + "One or more variables are missing")
        logging.exception(e)