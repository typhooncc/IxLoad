

# Description
#   A sample Python REST API script on loading a saved configuration,
#   run traffic and getting stats.
#
#   Supports both Windows and Linux gateway Server. If connecting to a 
#   Linux server, a license server running on Windows PC is still required unless it is 
#   installed in the chassis.
#   This script will configure the license server IP and license model on the Linux server.
#
#   If the saved config file is located locally, you could upload it to the gateway.
#   Otherwise, the saved config file must be already in the Windows filesystem.
#
#   This sample script also has SSH capabilities to retrieve all the statistic csv result
#   files to anywhere on your local file system and optionally, you could also delete them in the Gateway
#   server as clean up.

#   If you want to retrieve results from a Windows Gateway server, you must install and enable
#   OpenSSH so the script could connect to it. SSH is enabled by default if using a Linux Gateway server.
#   Here is a link on how to install and set up OpenSSH for Windows.
#       http://openixia.amzn.keysight.com/tutorials?subject=Windows&page=sshOnWindows.html
#
#   - Load a saved config .rxf file
#   - Run traffic
#   - Get stats
#
# Requirements
#    Python2.7 and Python3
#    IxL_RestApi.py 
#    Optional: sshAssistant.py

import os, sys, time, signal, traceback

baseDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, baseDir.replace('SampleScripts', 'Modules'))

from IxL_RestApi import *

# Choices: linux or windows 
serverOs = 'windows'
#
# It is mandatory to include the exact IxLoad version.
ixLoadVersion = '8.50.115.124'
ixLoadVersion = '8.50.115.333'

# Do you want to delete the session at the end of the test or if the test failed?
deleteSession = True

# CLI parameter input:  windows|linux
if len(sys.argv) > 1:
    serverOs = sys.argv[1]

if serverOs == 'windows':
    apiServerIp = '192.168.70.3'
    resultsDir = 'c:\\Results'
    rxfFileOnServer = 'C:\\Results\\IxL_Http_Ipv4Ftp_vm_8.20.rxf'

    # For SSH only. To copy results off of Windows to local filesystem.
    sshUsername = 'hgee'
    sshPasswordFile = '/mnt/hgfs/Utilities/vault'    
    with open (sshPasswordFile, 'r') as pwdFile:
        sshPassword = pwdFile.read().strip()

    # Do you want to upload your saved config file to the Gateway server?
    # If not, a saved config must be already in the Windows filesystem.
    upLoadFile = False

if serverOs == 'linux':
    apiServerIp = '192.168.70.169'
    sshUsername = 'ixload'  ;# Leave as default if you did not change it
    sshPassword = 'ixia123' ;# Leave as default if you did not change it
    resultsDir = '/mnt/ixload-share/Results' ;# Default

    localRxfFileToUpload = 'IxL_Http_Ipv4Ftp_vm_8.20.rxf'
    rxfFileOnServer = '/mnt/ixload-share/IxL_Http_Ipv4Ftp_vm_8.20.rxf'

apiServerIpPort = 8443 ;# http=8080.  https=8443 (https is supported starting 8.50)

licenseServerIp = '192.168.70.3'
# licenseModel choices: 'Subscription Mode' or 'Perpetual Mode'
licenseModel = 'Subscription Mode'

# To record stats to CSV file: True or False
csvStatFile = False

# Enable timestamp to not overwrite the previous csv file: True or False
csvEnableFileTimestamp = False

# To add a custom ID name to the beginning of the CSV file: string format
csvFilePrependName = None
pollStatInterval = 2

# To reassign ports, uncomment this and replace chassis and port values
# Format = (cardId,portId)
# To get the Activity names: /ixload/test/activeTest/communityList
communityPortList = {
    'chassisIp': '192.168.70.128',
    'Traffic1@Network1': [(1,1)],
    'Traffic2@Network2': [(2,1)]
}

# Stat names to display at run time:
#     https://openixia.amzn.keysight.com/tutorials?subject=ixLoad/getStatName&page=fromApiBrowserForRestApi.html
statsDict = {
    'HTTPClient': ['TCP Connections Established',
                   'HTTP Simulated Users',
                   'HTTP Concurrent Connections',
                   'HTTP Connections',
                   'HTTP Transactions',
                   'HTTP Connection Attempts'
               ],
    'HTTPServer': ['TCP Connections Established',
                   'TCP Connection Requests Failed'
               ]
}

try:
    restObj = Main(apiServerIp=apiServerIp, apiServerIpPort=apiServerIpPort, osPlatform=serverOs,
                   deleteSession=deleteSession, generateRestLogFile=True)

    restObj.connect(ixLoadVersion)
    restObj.configLicensePreferences(licenseServerIp=licenseServerIp, licenseModel=licenseModel)
    restObj.setResultDir(resultsDir, createTimestampFolder=True)

    # If connecting to Linux server, must upload the config file to the server first.
    if serverOs == 'linux':
        restObj.uploadFile(localRxfFileToUpload, rxfFileOnServer)

    if serverOs == 'windows' and upLoadFile == True:
        restObj.uploadFile(localFilePath, rxfFileOnServer)

    restObj.loadConfigFile(rxfFileOnServer)

    if 'communityPortList' in locals():
        restObj.assignChassisAndPorts(communityPortList)

    restObj.enableForceOwnership()

    # Modify the sustain time
    restObj.configTimeline(name='Timeline1', sustainTime=12)

    restObj.getStatNames()
    runTestOperationsId = restObj.runTraffic()
    restObj.pollStats(statsDict, pollStatInterval=pollStatInterval, csvFile=csvStatFile,
                      csvEnableFileTimestamp=csvEnableFileTimestamp, csvFilePrependName=csvFilePrependName)
    restObj.waitForActiveTestToUnconfigure()
    resultPath = restObj.getResultPath()

    if serverOs == 'linux':
        # SSH to the Gateway to retrieve the csv stat results and delete them in the server.
        # SSH is enabled on a Linux Gateway, but more than likely, you don't have OpenSSH enabled on your Windows.
        # You could modify this condition to include Windows if you have SSH enabled.
        restObj.sshSetCredentials(sshUsername, sshPassword, sshPasswordFile=None,  port=22)
        restObj.scpFiles(sourceFilePath=resultPath, destFilePath='.', typeOfScp='download')
        restObj.deleteFolder(filePath=resultPath)

    if deleteSession:
        restObj.deleteSessionId()

except (IxLoadRestApiException, Exception) as errMsg:
    print('\n%s' % traceback.format_exc())
    if deleteSession:
        restObj.abortActiveTest()
        restObj.deleteSessionId()
    sys.exit(errMsg)

except KeyboardInterrupt:
    print('\nCTRL-C detected.')
    if deleteSession:
        restObj.abortActiveTest()
        restObj.deleteSessionId()
 
