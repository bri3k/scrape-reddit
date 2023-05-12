
##Overview

This python program goes to a reddit subreddit, grabs the top posts and downloads the media to the local drive.

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Compatibility

Scrape Redditis supported on Windows, Linux & OSX. The minimum python version required is: 
* Python >= 3.7

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/bri3k/scrape-reddit.git
   ```
2. Navigate to the src folder containing the script
    ```sh
    cd scrape-reddit
    ```
3. Install required modules
   ```sh
   pip install -r requirements.txt 
   ```

### Usage

scrape-reddit_api.py subreddit
or
scrape-reddit_theeye.py subreddit

### Options
 -nX  Download X images from subreddit. Default to 100.
 -v   Verbose output on console
 -d   Debug output on console

