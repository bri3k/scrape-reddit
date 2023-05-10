#!/usr/local/bin/python3

import json
import datetime
import requests
import re, os, sys
import time
import zstandard

lastSlashRE = '.*\/(.*)'
subreddit = ''
toDownload = 10
cwd = os.getcwd()

class bFormat:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

newFileCount = 0
successCount = 0
failedCount = 0
errCount = 0
alreadyDLCount = 0
itemCount = 1

opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

verbose = True if ('-v' in opts) else False
debug   = True if ('-d' in opts) else False

for a in opts:
    if a[:2] == '-n': 
        try:
            toDownload = int(a[2:])
        except Exception as e:
            print('Invalid value for download count.')
            sys.exit()

baseHeaders = {}
baseHeaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'

bearerHeaders = {}
bearerHeaders['user-agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
bearerHeaders['origin']='https://www.redgifs.com'
bearerHeaders['referer']='https://www.redgifs.com/'
bearerHeaders['accept']='application/json, text/plain, */*'
bearerHeaders['accept-encoding']='gzip, deflate, br'
bearerHeaders['accept-language']='en-US,en;q=0.9'
bearerHeaders['sec-ch-ua']='"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'
bearerHeaders['sec-ch-ua-mobile']='?0'
bearerHeaders['sec-ch-platform']='"macOS"'
bearerHeaders['sec-fetch-site']='same-site'


class MissingDownload(Exception):
	"Download not found"
	pass

class TokenDecodeError(Exception):
	"Old/Bad bearer token"
	pass

#------------------------------------------------
#   writeImageOut
#   args: filename, url, headers
#
#    returns: None
#------------------------------------------
def writeImageOut(filename, url, head=baseHeaders):
    global successCount, newFileCount, alreadyDLCount
    filename = filename.replace('/','~')
    filename = filename.replace('&amp;','&')
    filename = filename.replace('lt;','<')
    filename = filename.replace('gt;','>')
    filename = filename.replace('&quot;','~')
    if not os.path.isfile(cwd + '/' + subreddit + '/' + filename):
        media = requests.get(url, headers=head)
        if (len(media.content) in [503,1048]):
            raise MissingDownload('file not found PNG image')
        if (len(media.content) == 0):
            raise MissingDownload('Zero size file returned')
        fileHandle = open(cwd + '/' + subreddit + '/' + filename,'wb')
        fileHandle.write(media.content)
        fileHandle.close()  
        if verbose: print(bFormat.OKGREEN + '** ' + str(itemCount) + ') ' + filename + bFormat.ENDC)
        newFileCount += 1
    else:
        if verbose: print(bFormat.OKBLUE + '** ' + str(itemCount) + ') ' + ' Already downloaded ' + filename + bFormat.ENDC)
        alreadyDLCount += 1
    successCount += 1
    return 

#------------------------------------------
#   readZSTDfile
#   args: filename
#     
#   returns: list containing score, url, author, title, and create_utc
#------------------------------------------
def readZSTDfile(file_handle):
    aList = []
    buffer = ''
    reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)
    while True:
        try:
            chunk = reader.read(2**24).decode()
        except Exception as e:
            print(e)
            print(len(aList))
            sys.exit()
        if not chunk:
            break
        lines = (buffer + chunk).split("\n")

        for line in lines[:-1]:
            extractedValue = json.loads(line)
            if (isinstance(extractedValue['url'], type(None))): extractedValue['url'] == ''
            aList.append({'score':extractedValue['score'], 'url':extractedValue['url'], 'author':extractedValue['author'], 'title':extractedValue['title'], 'created_utc':extractedValue['created_utc']})
        buffer = lines[-1]

    reader.close()
    file_handle.close()
    return aList

#----------------------- Imgur Processor -----------------------
def imgurProcessor(y):
    if debug: print(str(itemCount) + ') imgur processing: ' + y['url'])
    if (y['url'][-3:] in ['gif','jpg','png','peg']):
        #No work needed, grab link as is
        writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(int(y['created_utc'])).strftime("%Y %b") + ') - ' + y['title'][:200] + ' - ' + re.search(lastSlashRE, y['url'])[1], y['url'])
    elif (y['url'][-4:] == 'gifv'):
        #Just replace gifv with mp4 and download
        writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(int(y['created_utc'])).strftime("%Y %b") + ') - ' + y['title'][:200] + ' - ' + re.search(lastSlashRE + '\.gifv', y['url'])[1] + '.mp4',y['url'].replace('gifv','mp4'))
    else:
        #Grab webpage and scrape for links
        code = requests.get(y['url']).text
        codeFound = re.findall('"(https:\/\/i\.imgur\.com.{7,40}?(?:jpg|png|mp4|jpeg|webm))"', code)
        if (codeFound):
            writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(int(y['created_utc'])).strftime("%Y %b") + ') - ' + y['title'][:200] + ' - ' + re.search(lastSlashRE, codeFound[0])[1], codeFound[0])
        else:
            raise MissingDownload('Unable to find imgur image by scraping. ') 
    return

#----------------------- Redgifs Processor -----------------------
def redgifsProcessor(y):
    if debug: print(str(itemCount) + ') redgif processing: ' + y['url'])
    #Extact unique string from address
    redgifsRE = re.findall(lastSlashRE, y['url'])
    if (redgifsRE):
        #Use redgif API to get webpage with the real links
        initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + redgifsRE[0] + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
        if ('TokenDecodeError' in initialRequest.text):
            raise TokenDecodeError(initialRequest.text)
        if ('error' in initialRequest.text):
            initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + redgifsRE[0].lower() + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
            if ('error' in initialRequest.text):
                raise MissingDownload(initialRequest.text)
        #Process final page with real links
        finalRequest = re.findall('(?i)"hd":"(.*?' + redgifsRE[0] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
        writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(y['created_utc']).strftime("%Y %b") + ') - ' + y['title'][:200] + ' - ' + redgifsRE[0] + '.' + finalRequest[1], finalRequest[0], bearerHeaders)
    return

#----------------------- Redd.it Processor -----------------------
def redditProcessor(y):
    if debug: print(str(itemCount) + ') redd.it processing: ' + y['url'])
    #No work needed, grab link as is
    writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(y['created_utc']).strftime("%Y %b") + ') - ' + y['title'][:200] + ' - ' + re.search(lastSlashRE, y['url'])[1], y['url'])
    return

#----------------------- Gfycat Processor -----------------------
def gfycatProcessor(y):
    if debug: print(str(itemCount) + ') gfycat processing: ' + y['url'])
    gfycatRE = re.findall('https:\/\/(?:gfycat)\.com((?:\/watch\/|\/)(.*)|.*)', y['url'])
    if (gfycatRE):
        initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + gfycatRE[0][1] + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
        if ('TokenDecodeError' in initialRequest.text):
            raise TokenDecodeError(initialRequest.text)
        if ('error' in initialRequest.text):
            initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + gfycatRE[0][1].lower() + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
            if ('error' in initialRequest.text):
                raise MissingDownload(initialRequest.text)
        finalRequest = re.findall('(?i)"hd":"(.*?' + gfycatRE[0][1] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
        writeImageOut(y['author'] + ' (' + datetime.datetime.utcfromtimestamp(y['created_utc']).strftime("%Y %b") + ') - ' + y['title'] + ' - ' + gfycatRE[0][1] + '.' + finalRequest[1], finalRequest[0], bearerHeaders)
    return


#------------ Grab data of posts, either locally or from the internet
subreddit = args[0]

if (os.path.isfile(args[0] + '_submissions.zst')): 
    print('Found local copy of the-eye.eu zst file, using')
    rawData = open(subreddit + '_submissions.zst','rb')
else:
    print('Downloading copy of subreddit from the-eye.eu...')
    try:
        internetData = requests.get('https://the-eye.eu/redarcs/files/' + subreddit + '_submissions.zst')
        if (internetData.status_code != 200): raise MissingDownload('Returned ' + str(internetData.status_code) + '. Please check subreddit name is correct.')
        rawData = open(args[0] + '_submissions.zst','wb+')
        rawData.write(internetData.content)
        rawData.seek(0)
        print('Saved as ' + args[0] + '_submissions.zst')
    except Exception as e:
        print('Failed to download: ' + str(e))
        sys.exit()

#------------ Make subfolder to put images in
try:
    os.mkdir(cwd + '/' + subreddit)
except FileExistsError:
    if verbose: print(bFormat.OKGREEN + "Folder exists, reusing..." + bFormat.ENDC)

#------------ Retrieve bearer token provided by user
try:
	bearerTokenFile = open('bearerToken.txt','r')
	bearerHeaders['authorization']=bearerTokenFile.read()
	bearerTokenFile.close()
except:
	print(bFormat.FAIL + "No bearerToken.txt file found. Please retrieve the bearer token from chrome and insert it into the file." + bFormat.ENDC)
	sys.exit()

#------------ Start extracting data from zst file
startProcessing = time.time()
print('Processing json...')

workingList = readZSTDfile(rawData)
workingList = sorted(workingList, key=lambda x:x['score'], reverse=True)

print('Completed processing in ' + bFormat.BOLD +  str(round(time.time() - startProcessing,1)) + bFormat.ENDC + ' seconds. Found ' + str(len(workingList)) + ' posts.')
print('Starting downloading top ' + str(toDownload) + ' images. The cutoff score is ' + str(workingList[toDownload]['score']))

#------------ Main loop to grab images
for y in workingList[:toDownload]:
    try:
        if (len(y['url']) == 0):
            raise MissingDownload('No link in post with title: ' + str(y['title']))
        elif ('imgur' in y['url']):             
            imgurProcessor(y)
        elif ('i.redd.it' in y['url']):         
            redditProcessor(y)
        elif ('redgifs' in y['url']):           
            redgifsProcessor(y)
        elif ('gfycat' in y['url']):            
            gfycatProcessor(y)
        elif ('deleted_by_user' in y['url']):   
            raise MissingDownload('deleted by user')
        elif ('removed_by_reddit' in y['url']): 
            raise MissingDownload('removed by reddit')
        else: 
            raise Exception('No known URL found: ' + y['url'])

    except MissingDownload as e:
        failedCount += 1
        if verbose: print(bFormat.WARNING + '** ' + str(itemCount) + ') ' + y['url'] + ' missing media: ' + str(e) + bFormat.ENDC)
    except KeyboardInterrupt:
        #Capture CTRL-C event and quit gracefully
        print(bFormat.FAIL +  "\r\nCTRL-C Break\r\n" + bFormat.ENDC)
        break
    except TokenDecodeError as e:
        failedCount += 1
        print(bFormat.FAIL + '** ' + bFormat.ENDC + str(itemCount) + ') ' + y['url'] + bFormat.WARNING + ' Bad/Old bearer token: ' + str(e) + bFormat.ENDC)
    except Exception as e:
        errCount += 1
        print(bFormat.FAIL + '** ' + str(itemCount) + ') Coding Error - ' + str(e) + bFormat.ENDC)
        print('      ' + bFormat.FAIL + str(y) + bFormat.ENDC)
    itemCount += 1


#------------ Cleanup and stats
print(subreddit + ' scraped. ' + bFormat.OKBLUE + str(alreadyDLCount) + bFormat.ENDC + ' already downloaded, ' + bFormat.OKGREEN + str(newFileCount) + bFormat.ENDC + ' downloaded, ' + bFormat.WARNING + str(failedCount) + bFormat.ENDC + ' missing, ' + bFormat.FAIL + str(errCount) + bFormat.ENDC + ' processing errors.')
print('Total Time ' + bFormat.BOLD +  str(round(time.time() - startProcessing,1)) + bFormat.ENDC + ' seconds')


