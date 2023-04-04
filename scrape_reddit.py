#!/usr/local/bin/python3

import requests
import re
import sys
import time
import os

numToScrape = 100
verbose = False

itemCount = 0
successCount = 0
failedCount = 0
errCount = 0

cwd = os.getcwd()

baseHeaders = {}
baseHeaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'

bearerHeaders = {}
bearerHeaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'

specificRE = '(?i)<name>\/u\/(?P<name>.*?)<\/name>.*?title=&quot;(?P<title>.*?)&quot;.*?a href=&quot;(?P<address>https{0,1}:\/\/(?P<site>(?:www\.){0,1}redgifs.com|(?:i\.){0,1}imgur.com|(?:i\.)redd.it|(?:i\.)reddituploads.com|(?:giant\.){0,1}gfycat.com).*?)&quot;&gt;'
generalRE  = '(?i)a href=&quot;(.*?)&quot;&gt;'
missingNameRE = '(?i)title=&quot;(?P<title>.*?)&quot;.*?a href=&quot;(?P<address>https{0,1}:\/\/(?P<site>(?:www\.){0,1}redgifs.com|(?:i\.){0,1}imgur.com|(?:i\.)redd.it|(?:i\.)reddituploads.com|(?:giant\.){0,1}gfycat.com).*?)&quot;&gt;'
lastSlashRE = '.*\/(.*)'

opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

def writeImageOut(filename, url, head=baseHeaders):
	global sleepy, successCount
	filename = filename.replace('/','~')
	filename = filename.replace('&amp;','&')
	filename = filename.replace('lt;','<')
	filename = filename.replace('gt;','>')
	filename = filename.replace('&quot;','~')
	if not os.path.isfile(cwd + '/' + subreddit + '/' + filename):
		fileHandle = open(cwd + '/' + subreddit + '/' + filename,'wb')
		fileHandle.write(requests.get(url, headers=head).content)
		fileHandle.close()
	else:
		#print("Already have image, skipping")
		sleepy = 0
	successCount += 1
	return



#----------------- Start Main ------------------------
if (len(args) == 1):
	subreddit = args[0]
	url = 'https://www.reddit.com/r/' + subreddit + '/top/.rss?t=all&limit=' + str(numToScrape)
else:
	print("Too many args. Use one subreddit at a time.")
	sys.exit()

try:
	os.mkdir(cwd + '/' + subreddit)
except FileExistsError:
	if verbose: print("Folder exists, reusing...")

try:
	bearerTokenFile = open('bearerToken.txt','r')
	bearerHeaders['authorization']=bearerTokenFile.read()
	bearerTokenFile.close()
except:
	print("No bearerToken.txt file found. Please retrieve the bearer token from chrome and insert it into the file.")
	sys.exit()

#Grab RSS feed from reddit
rawRSS = requests.get(url, headers=baseHeaders)

#Seperate each entry into a list
groupRSS = re.findall('<entry>.*?</entry>',rawRSS.text)


#Run though each entry and extract the link. 
#Specific regex for known link hosts
#General regex for a hail mary capture
for entry in groupRSS:
	itemCount += 1
	specificImg = re.search(specificRE, entry)
	missingNameImg = re.search(missingNameRE, entry)
	try:

		if (specificImg) or (missingNameImg):
			if (specificImg): 
				name = specificImg.group('name')
			else:
				name = 'Deleted'
			title = missingNameImg.group('title')
			address = missingNameImg.group('address')
			site = missingNameImg.group('site')

			#----------------------- Imgur Processor -----------------------
			if ('imgur' in site):
				if verbose: print(str(itemCount) + ') imgur processing: ' + address)
				if (address[-3:] in ['gif','jpg','png']):
					#No work needed, grab link as is
					writeImageOut(name + ' - ' + title + ' - ' + re.search(lastSlashRE, address)[1], address)
				elif (address[-4:] == 'gifv'):
					#Just replace gifv with mp4 and download
					writeImageOut(name + ' - ' + title + ' - ' + re.search(lastSlashRE + '\.gifv', address)[1] + '.mp4', address.replace('gifv','mp4'))
				else:
					#Grab webpage and scrape for links
					code = requests.get(address).text
					codeFound = re.findall('"(https:\/\/i\.imgur\.com.{7,40}?(?:jpg|png|mp4|jpeg|webm))"', code)
					if (codeFound):
						writeImageOut(name + ' - ' + title + ' - ' + re.search(lastSlashRE, codeFound[0])[1], codeFound[0])
					else:
						raise Exception('Unable to find imgur image by scraping. ')
			
			#----------------------- Redd.it Processor -----------------------
			elif ('i.redd.it' in site):
				if verbose: print(str(itemCount) + ') redd.it processing: ' + address)
				#No work needed, grab link as is
				writeImageOut(name + ' - ' + title + ' - ' + re.search(lastSlashRE, address)[1], address)

			#----------------------- Redgifs Processor -----------------------
			elif ('redgifs' in site):
				if verbose: print(str(itemCount) + ') redgif processing: ' + address)
				#Extact unique string from address
				redgifsRE = re.findall(lastSlashRE, address)
				if (redgifsRE):
					#Use redgif API to get webpage with the real links
					initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + redgifsRE[0] + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
					if ('error' in initialRequest.text):
						raise Exception(initialRequest.text)
					#Process final page with real links
					finalRequest = re.findall('(?i)"hd":"(.*?' + redgifsRE[0] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
					writeImageOut(name + ' - ' + title + ' - ' + redgifsRE[0] + '.' + finalRequest[1], finalRequest[0], bearerHeaders)

			#----------------------- Gfycat Processor -----------------------
			elif ('gfycat' in site):
				if verbose: print(str(itemCount) + ') gfycat processing: ' + address)
				gfycatRE = re.findall('https:\/\/(?:gfycat)\.com((?:\/watch\/|\/)(.*)|.*)', address)
				if (gfycatRE):
					initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + gfycatRE[0][1] + '?views=yes&users=yes&niches=yes', headers=bearerHeaders)
					if ('error' in initialRequest.text):
						raise Exception(initialRequest.text)
					finalRequest = re.findall('(?i)"hd":"(.*?' + gfycatRE[0][1] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
					writeImageOut(name + ' - ' + title + ' - ' + gfycatRE[0][1] + '.' + finalRequest[1], finalRequest[0], bearerHeaders)

			# ------------------- Catchall for no specific processor --------------------
			else:
				failedCount += 1
				print('** ' + str(itemCount) + ') Skipping site:' + site + ' ' + address)

		# ------------------- Unable to parse, grabbing all links --------------------
		else:
			failedCount += 1
			#print(entry)
			print('** ' + str(itemCount) + ') No match, showing all links:')
			for allLinks in re.findall(generalRE, entry):
				print('       ' + allLinks)

	except Exception as e:
		print('** ' + str(itemCount) + ') ' + address + ' failed writing:  ' + str(e))
		errCount += 1



print("Good " + str(successCount) + ". Failed " + str(failedCount) + ". Error " + str(errCount))
print('Total entry found ' + str(itemCount) + '. done.')


