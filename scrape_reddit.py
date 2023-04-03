#!/usr/local/bin/python3

import requests
import re
import pprint
import time
import random
import os 
import sys

itemCount = 0
successCount = 0
missedCount = 0
errCount = 0
sleepy = 0
subreddit = ''
cwd = os.getcwd()

opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

if (len(args) == 1):
	subreddit = args[0]
else:
	print("Too many args. Use one subreddit at a time.")
	sys.exit()


url = 'https://www.reddit.com/r/' + subreddit + '/top/.rss?t=all&limit=100'

baseHeaders = {}
baseHeaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'

gifheaders = {}
gifheaders['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
gifheaders['authorization']='Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJodHRwczovL3d3dy5yZWRnaWZzLmNvbS8iLCJpYXQiOjE2ODA0NjA4NTMsImV4cCI6MTY4MDU0NzI1Mywic3ViIjoiY2xpZW50LzE4MjNjMzFmN2QzLTc0NWEtNjU4OS0wMDA1LWQ4ZThmZTBhNDRjMiIsInNjb3BlcyI6InJlYWQiLCJ2YWxpZF9hZGRyIjoiOTguMTY1LjMyLjIzMyIsInZhbGlkX2FnZW50IjoiTW96aWxsYS81LjAgKE1hY2ludG9zaDsgSW50ZWwgTWFjIE9TIFggMTBfMTVfNykgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExMS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwicmF0ZSI6LTF9.kAmzH47Lor2MIZvtmZ07WxLgjVWbu45nxkJJ5zAy0d3KdEjtXIoNVV_OvWNSNqlFGG-dInsN1e2i84z2EH-kFj1ZBSyv7pC9UO9wjAl1b_1FYPwP7PCXu9hK44Fzmg7W_ZcUrUCF_5ngi1wOdfsmyaD04Qjt5LinqKje4eVODT0Jzm2By_ckHVXxEFt7oQ_VRlSWr2YsVVObOu6FLgfI3ft-4lXgtqQCpm4Knpd3MNSCslXfcGFrLTJ7mc6xgyJo4dAszuDYvwWR9MkzIIhlAe5l-of7S2LzBtu8Z0rMB7UWZge985NRSuKG7Tj_V6PavRpBPjtqiyAJURU6nVFRvg'

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
		print("Already have image, skipping")
		sleepy = 0
	successCount += 1
	return



try:
	os.mkdir(cwd + '/' + subreddit)
except FileExistsError:
	print("Folder exists, reusing...")



page = requests.get(url, headers=baseHeaders)

filter_re =  '<name>\/u\/(.*?)<\/name>.*?title=&quot;(.*?)&quot.*?('
filter_re += 'https:\/\/gfycat.com\/.*?(?=&)|'
filter_re += 'https:\/\/(?:www\.)*redgifs.com\/watch\/.*?(?=&)|'
filter_re += 'https:\/\/i\.redd\.it\/(.*?)\.(jpg|png|gif)|'
filter_re += 'https:\/\/i.imgur.com\/(.*?)\.(gifv|gif|png|jpg|jpeg))'

links = re.findall(filter_re, page.text)
#print('Webpage Size: ' + str(len(page.text)))
#print(page.text)

newHandle = open(cwd + '/' + subreddit + '/' + 'rawWeb.txt', 'w')
newHandle.write(page.text)
newHandle.close()

missedImg = open(cwd + '/' + subreddit + '/' + '001-MissedImg.txt','w')
missedImg.write("Missing Image Downloads from r/" + subreddit + "\r\n")

#print(links)
#print('\r\n')

for x in links:
	itemCount += 1
	# print('Sleeping ' + str(sleepy) + ' seconds. Working on: ' + str(itemCount))
	time.sleep(sleepy)
	sleepy = random.randint(0,30) / 10

	try:
		if ('gfycat' in x[2]):
			print('gfycat processing: ' + str(x))
			gfycatRE = re.findall('https:\/\/(?:gfycat)\.com((?:\/watch\/|\/)(.*)|.*)',x[2])
			if (gfycatRE):
				initialRequest = requests.get('https://api.gfycat.com/v1/gfycats/' + gfycatRE[0][1] + '?views=yes&users=yes&niches=yes', headers=gifheaders)
				if ('error' in initialRequest.text):
					raise Exception(initialRequest.text)
				finalRequest = re.findall('(?i)"hd":"(.*?' + gfycatRE[0][1] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
				writeImageOut(x[0] + ' - ' + x[1] + ' - ' + gfycatRE[0][1] + '.' + finalRequest[1], finalRequest[0], gifheaders)
		elif ('redgifs' in x[2]):
			print('redgif processing: ' + str(x))
			redgifsRE = re.findall('.*\/(.*)',x[2])
			if (redgifsRE):
				initialRequest = requests.get('https://api.redgifs.com/v2/gifs/' + redgifsRE[0] + '?views=yes&users=yes&niches=yes', headers=gifheaders)
				if ('error' in initialRequest.text):
					raise Exception(initialRequest.text)
				finalRequest = re.findall('(?i)"hd":"(.*?' + redgifsRE[0] + '\.(.*?)\?.*?)"', initialRequest.text)[0]
				writeImageOut(x[0] + ' - ' + x[1] + ' - ' + redgifsRE[0] + '.' + finalRequest[1], finalRequest[0], gifheaders)
		elif ('imgur' in x[2]):
			print('imgur processing: ' + str(x))
			if(x[6] in ['gif','jpg','png']):
				writeImageOut(x[0] + ' - ' + x[1] + ' - ' + x[3] + x[5] + '.' + x[4] + x[6], x[2])
			else:
				imgurRE = re.findall('contentURL.*?content="(.*\/)(.*?)"', requests.get(x[2]).text)
				if (imgurRE):
					writeImageOut(x[0] + ' - ' + x[1] + ' - ' + imgurRE[0][1], imgurRE[0][0] + imgurRE[0][1])
				else:
					raise Exception("Unable to find imgur image. Likely gone forever. Returned " + requests.get(x[2]).text[0:5])
		elif ('i.redd.it' in x[2]):
			print('redd.it processing: ' + str(x))
			writeImageOut(x[0] + ' - ' + x[1] + ' - ' + x[3] + x[5] + '.' + x[4] + x[6], x[2])
		else:
			print("Unknown site, skipping")
			missedImg.write(x[2] + "\r\n")
	except Exception as e:
		print("*Failed writing   " + str(e))
		errCount += 1
		missedImg.write("*Failed writing " + x[2] + "\r\n")
		missedImg.write("    " + str(e) + "\r\n")
	print(' ')

results = "\r\n" + str(successCount) + " successful captures out of " + str(itemCount) + ". " + str(errCount) + " errors.\r\n\r\n"
print(results)
missedImg.write(results)
missedImg.close()


