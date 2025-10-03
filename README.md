<div class="cover">
	<h1>Development of a Crawler</h1>
	<p>Mario Orviz Viesca - UO295180</p>
</div>

- [Introduction](#introduction)
- [General Concepts](#general-concepts)
  - [Parameterization](#parameterization)
  - [Execution](#execution)
- [Functionality](#functionality)
  - [Obtaining Links](#obtaining-links)
  - [Obtaining Permissions from `robots.txt`](#obtaining-permissions-from-robotstxt)
  - [Normalize Links](#normalize-links)
  - [Save Records](#save-records)
- [Search Algorithms](#search-algorithms)
  - [Depth-First Search](#depth-first-search)
  - [Breadth-First Search](#breadth-first-search)
- [Evaluation](#evaluation)
  - [Results Verification](#results-verification)
- [Submission](#submission)

## Introduction

The proposed exercise is the development of a crawler. The technology used is `python` with the help of the following libraries:
- `requests`: Used to make HTTP requests
- `warcio`: Used to store the retrieved documents
- `bs4`: Used to extract all the links from an HTML document
- `urllib`: Used to work with URLs, and its `RobotFileParser` module to read and check websites’ `robots.txt` files

For this project, I implemented two different search algorithms: a depth-first search and a breadth-first search.
The main idea is to start from a file of seed URLs, make a request to each of them, extract all the URLs found, and repeat the process with these according to the chosen algorithm.

## General Concepts

The project is based on a single file `crawler.py` that implements the crawler’s logic.  
Additionally, there is a `seeds.txt` file containing the “seed” URLs that serve as the starting point for the crawler.

The program exports the results in `.warc.gz` format inside the `/out` directory.  
These files are named after the domain of the website, storing all the results from that domain.  
Before saving a page in `warc` format, the algorithm checks that the page has not already been indexed.

### Parameterization

The program can be configured with 8 different variables found in the `.py` file:

```python
OUT_DIR = "out"
SEEDS = "seeds.txt"
DELAY = 2
MAX_DOWNLOADS = 50
MAX_DEPTH = 5
USER_AGENT = 'Mozilla/5.0'
CHECK_ROBOTS = False
SAVE_HTML = False
RANDOMIZE_BREATH = False
```

- `OUT_DIR`: Output directory where results are stored
- `SEEDS`: File containing the seed URLs
- `DELAY`: Time (in seconds) the program waits between downloads
- `MAX_DOWNLOADS`: Maximum number of downloads the program will perform
- `MAX_DEPTH`: (only for depth-first search) Maximum depth the algorithm will reach
- `USER_AGENT`: User-agent string used by the program for HTTP requests
- `CHECK_ROBOTS`: Boolean indicating whether to check `robots.txt` before downloading a URL
- `SAVE_HTML`: Boolean indicating whether to save `.html` files directly
- `RANDOMIZE_BREATH`: Boolean indicating whether to randomize the breadth-first search (explained later)

### Execution

The script is intended to be executed from the command line.  
The default parameter values can be overridden using the following command-line arguments:
- `--mode`: Selects the algorithm to use (`depth` or `breath`)
- `--max-downloads`: Sets the maximum number of downloads
- `--delay`: Sets the wait time between downloads
- `--max-depth`: For depth-first search, sets the maximum depth
- `--check-robots`: If provided, the program checks `robots.txt` (disabled by default)
- `--save-html`: If provided, the program saves `.html` files (disabled by default)
- `--randomize-breath`: If provided, randomizes breadth-first exploration after seeds are consumed (disabled by default)
- `--seeds`: Sets the relative path to the seed file

Example execution:

```cmd
python crawler.py --mode depth --max-downloads 100 --delay 1 --max-depth 5 --seeds seeds.txt --check-robots --save-html --randomize-breath
```

## Functionality

This section describes the main functions the crawler uses to perform its task.

### Obtaining Links

This is the crawler’s core function, used by both algorithms to download and extract links from a website.  
It receives a URL as a parameter, makes a request to it, and extracts its links.  
It returns a list of extracted links and a boolean indicating success. If unsuccessful, the returned list is empty.

First, if `CHECK_ROBOTS` is `True`, it calls `obtainRobotsPermission` to read the site’s `robots.txt` and check permissions.  
Next, it uses `requests` to perform a `GET` request and verifies that the `Content-Type` is `text/html`.  
It then calls `save_html` to record the website and waits for the time specified by the `delay` variable.

Using `BeautifulSoup`, it extracts all `a` elements from the HTML, retrieves their `href` values, and normalizes them using `normalizeLink` to avoid relative links.  
Finally, it returns the list of normalized links.

### Obtaining Permissions from `robots.txt`

The `obtainRobotsPermission` function reads `robots.txt` files (if they exist) and determines whether the crawler is allowed to access a given domain.  
It uses the `RobotFileParser` module and `urlparse`.  
The `robots.txt` URL is obtained as follows:

```python
robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
```

Then, on a `RobotFileParser` instance:

```python
rp.set_url(robots_url)
rp.read()
rp.can_fetch(USER_AGENT, url)
```

### Normalize Links

This simple function takes the original URL and a link.  
If the parsed link has no `netloc`, it joins it with the original URL using `urljoin`, as it is a relative link.

### Save Records

Two functions handle this functionality: `save_html` and `already_in_warc`.  
The latter prevents duplicate entries in `warc` files.  
`save_html` creates a `warc` file named after the URL’s `netloc` if it doesn’t exist; otherwise, it checks for duplicates before appending the new record.

## Search Algorithms

### Depth-First Search

The depth-first search algorithm is recursive.  
It starts in `depth_first_crawl` and is executed by the recursive function `crawl_depth`.  
The first function reads the seed URLs and calls `crawl_depth` for each in order.  
`crawl_depth` calls `obtain_links` for the given URL and then recursively processes each returned URL.

### Breadth-First Search

The breadth-first search algorithm is implemented in `breath_first_crawl`.  
It uses a `frontier` list to store unexplored URLs and an `explored` list to track visited URLs.  

The function loops while `frontier` has elements and the download limit is not exceeded.  
In each iteration, it pops an element from `frontier` and calls `obtain_links`.  
If successful, it increments the download counter and appends the returned links to `frontier` in order.

If `RANDOMIZE_BREATH` is `True`, once the seeds are consumed, the `frontier` list is shuffled to randomize exploration, leading to unpredictable results.

## Evaluation

To evaluate the algorithm, I implemented a function that automatically saves the output of each run to a text file.  
These files are named with the date of execution and stored under the `/metrics` directory in the following structure:

```
/metrics/{seed_file_name}/{type}/{configuration}/{date}.txt
```

The configuration folder name varies by search type:
- For breadth-first search (`breath`), it represents the number of downloaded files.
- For depth-first search (`depth`), it includes the number of downloaded files and search depth in the format:  
  `/{downloads}_{depth}`.

### Results Verification

Manually comparing two text files for differences in URLs can be tedious, especially as the list grows.  
Therefore, I include a script `comparar_metricas.py` that compares the text files in a directory to find differences in URLs.  

The script is run as follows:

```
python comparar_metricas.py --dir /directory
```

Example usage:

## Submission

The submission includes:

- The `crawler.py` file
- The `comparar_metricas.py` file
- Two seed files: `seeds.txt` and `seeds_2.txt`
- The `/metrics` directory with at least one crawler run for different algorithms and configurations.  
  This directory contains all the URLs that should be retrieved by the crawler (at least when `RANDOMIZE_BREATH` is `False`).
