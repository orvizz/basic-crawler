from warcio import WARCWriter
import requests as http
from bs4 import BeautifulSoup
import time as t
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import random
from warcio.statusandheaders import StatusAndHeaders
from warcio.archiveiterator import ArchiveIterator
import gzip
from io import BytesIO
import os
from datetime import datetime
import time

OUT_DIR = "out"
SEEDS = "seeds.txt"
DELAY = 1
MAX_DOWNLOADS = 20
MAX_DEPTH = 5
USER_AGENT = "Mozilla/5.0"
HEADER = {"user-agent": USER_AGENT}
CHECK_ROBOTS = False
SAVE_HTML = False
RANDOMIZE_BREATH = False

METRICS_DIR = "metrics"

os.makedirs(METRICS_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def obtain_links(url, delay, archiveCounter=0):
    if CHECK_ROBOTS:
        print(f"Checking robots.txt for {url}")
        if not obtainRobotsPermission(url):
            print(f"Robots.txt does not allow crawling {url}")
            return [], False

    try:
        print(f"Crawling {url}")
    except:
        print("Crawling a url with non standard characters")

    try:
        html = http.get(url, headers=HEADER)
    except:
        try:
            print(f"An error ocurred during the get petition to {url}")
        except:
            print(
                f"An error ocurred during the get petition to an url with non standard characters"
            )
        return [], False

    content_type = html.headers.get("Content-Type", "")

    if not "text/html" in content_type.lower():
        print(f"Site {url} does not return an html")
        return [], False

    save_html(html, url, archiveCounter)

    t.sleep(delay)

    soup = BeautifulSoup(html.text, "html.parser")
    links = []
    for link in soup.find_all("a"):
        ref = link.get("href")
        if ref == "#":
            continue
        ref = normalizeLink(url, ref)
        links.append(ref)

    return links, True


def crawl_depth(
    url,
    delay,
    explored,
    depth=0,
    max_depth=MAX_DEPTH,
    archiveCounter=0,
    maxDownloads=MAX_DOWNLOADS,
):

    if archiveCounter >= maxDownloads:
        return archiveCounter

    links, success = obtain_links(url, delay, archiveCounter=archiveCounter)

    if not success:
        return archiveCounter

    print(
        f"Depth {depth}: found {len(links)} links in {url}. ArchiveCounter: {archiveCounter + 1}/{maxDownloads} downloads ({(archiveCounter + 1)/maxDownloads*100:.2f}%)"
    )
    explored.append(url)

    if depth == max_depth - 1:
        return archiveCounter + 1

    archiveCounter += 1
    for link in links:
        print(f"Depth {depth}: exploring link {link}")

        if link not in explored:
            archiveCounter = crawl_depth(
                link,
                delay,
                explored,
                depth + 1,
                max_depth,
                archiveCounter=archiveCounter,
                maxDownloads=maxDownloads,
            )
            if archiveCounter >= maxDownloads:
                return archiveCounter
        else:
            print(f"Depth {depth}: link {link} already explored")

        if archiveCounter >= maxDownloads:
            return archiveCounter

    return archiveCounter


def normalizeLink(url, link):
    if bool(urlparse(link).netloc):
        return link
    else:
        return urljoin(url, link)


def obtainRobotsPermission(url):
    try:
        rp = RobotFileParser()
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp.set_url(robots_url)
        rp.read()
        print(parsed)
        return rp.can_fetch(USER_AGENT, url)
    except:
        print(f"An error ocurred obtaining robots.txt for {url}")
        return False


def already_in_warc(warc_path, url):
    """Comprueba si la URL ya está en el WARC"""
    if not os.path.exists(warc_path):
        return False

    # Abrir el WARC comprimido en modo lectura
    with gzip.open(warc_path, "rb") as fh:
        for record in ArchiveIterator(fh):
            if record.rec_type == "response":
                if record.rec_headers.get_header("WARC-Target-URI") == url:
                    return True
    return False


def save_html(html, url, archiveCounter=0):
    # Store the HTTP response in a WARC file using warcio

    warc_path = f"{OUT_DIR}/{urlparse(url).netloc}.warc.gz"

    if already_in_warc(warc_path, url):
        print(f"-  URL already stored: {url}")
        return

    with open(f"{OUT_DIR}/{urlparse(url).netloc}.warc.gz", "ab") as fh:
        warc_writer = WARCWriter(fh, gzip=True)
        # Prepare headers
        http_headers = []
        for k, v in html.headers.items():
            http_headers.append((k, v))
        status_headers = StatusAndHeaders(
            f"{html.status_code} {html.reason}", http_headers, protocol="HTTP/1.1"
        )
        # Write WARC record
        warc_writer.write_record(
            warc_writer.create_warc_record(
                url,
                "response",
                payload=BytesIO(html.content),
                http_headers=status_headers,
            )
        )

    if SAVE_HTML:
        with open(
            f"{OUT_DIR}/html_{timestamp}/page{archiveCounter}.html",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(html.text)


def obtain_seeds(seeds_file=SEEDS):
    frontier = []
    if os.path.exists(seeds_file):
        with open(seeds_file, "r") as f:
            frontier = f.readlines()
        frontier = [line.strip() for line in frontier]
    else:
        print(f"Seeds file {seeds_file} does not exist")
        return ([],)
    return frontier, len(frontier)


def breath_first_crawl(maxDownloads=MAX_DOWNLOADS, delay=DELAY, seeds_file=SEEDS):
    start_time = time.time()
    frontier, seeds = obtain_seeds(seeds_file)
    explored = []
    down_number = maxDownloads
    archiveCounter = 0

    while frontier and maxDownloads > 0:
        line = frontier.pop(frontier.index(frontier[0]))
        result, success = obtain_links(line, DELAY, archiveCounter=archiveCounter)

        if not success:
            print("Fail")
            continue

        print(
            f"Success. ArchiveCounter: {archiveCounter + 1}/{down_number} downloads ({(archiveCounter + 1)/down_number*100:.2f}%)"
        )
        maxDownloads -= 1
        archiveCounter += 1

        explored.append(line)

        for link in result:
            if link not in explored and link not in frontier:
                frontier.append(link)
        if archiveCounter > seeds and RANDOMIZE_BREATH:
            random.shuffle(frontier)
    end_time = time.time()
    total_time = end_time - start_time
    save_metrics(
        "breath",
        explored,
        total_time,
        maxDownloads=down_number,
        delay=delay,
        seeds_file=seeds_file,
    )
    pass


def depth_first_crawl(
    maxDownloads=MAX_DOWNLOADS, maxDepth=MAX_DEPTH, delay=DELAY, seeds_file=SEEDS
):
    start_time = time.time()
    frontier, seeds = obtain_seeds(seeds_file)
    down_number = maxDownloads
    archiveCounter = 0
    explored = []

    while frontier and archiveCounter < maxDownloads:
        line = frontier.pop()
        archiveCounter += crawl_depth(
            line,
            delay,
            explored,
            0,
            max_depth=maxDepth,
            archiveCounter=archiveCounter,
            maxDownloads=maxDownloads,
        )
    end_time = time.time()
    total_time = end_time - start_time
    save_metrics(
        "depth",
        explored,
        total_time,
        maxDownloads=down_number,
        delay=delay,
        maxDepth=maxDepth,
        seeds_file=seeds_file,
    )
    print("Crawling finished")

    pass


def save_metrics(
    type,
    explored,
    time,
    maxDownloads=MAX_DOWNLOADS,
    delay=DELAY,
    maxDepth=MAX_DEPTH,
    seeds_file=SEEDS,
):

    if type not in ["depth", "breath"]:
        print("Invalid type for metrics")
        return

    metrics_instant = datetime.now().strftime("%Y%m%d_%H%M%S")

    seeds_filename = os.path.splitext(os.path.basename(seeds_file))[0]

    if type == "depth":
        os.makedirs(
            f"{METRICS_DIR}/{seeds_filename}/depth/{maxDownloads}_{maxDepth}",
            exist_ok=True,
        )
        filename = f"{METRICS_DIR}/{seeds_filename}/depth/{maxDownloads}_{maxDepth}/{metrics_instant}.txt"
    else:
        os.makedirs(
            f"{METRICS_DIR}/{seeds_filename}/breath/{maxDownloads}",
            exist_ok=True,
        )
        filename = f"{METRICS_DIR}/{seeds_filename}/breath/{maxDownloads}/{metrics_instant}.txt"

    with open(f"{filename}", "w") as f:
        f.write(f"Crawling type: {type}\n")
        f.write(f"Max downloads: {maxDownloads}\n")
        f.write(f"Delay: {delay}\n")
        if type == "depth":
            f.write(f"Max depth: {maxDepth}\n")
        f.write(f"Total time: {time:.2f} seconds\n")
        f.write(f"Total pages crawled: {len(explored)}\n")
        f.write("Crawled URLs:\n")
        for url in explored:
            f.write(f"\t-\t{url}\n")
    pass


def test_crawlers():
    max_downloads_list = [10, 30, 50, 100]
    max_depth_list = [2, 3, 5, 7]
    for max_downloads in max_downloads_list:
        print(f"\nTesting breath_first_crawl with maxDownloads={max_downloads}")
        breath_first_crawl(maxDownloads=max_downloads, delay=DELAY)
        for max_depth in max_depth_list:
            print(
                f"\nTesting depth_first_crawl with maxDownloads={max_downloads}, maxDepth={max_depth}"
            )
            depth_first_crawl(
                maxDownloads=max_downloads, maxDepth=max_depth, delay=DELAY
            )


## depth_first_crawl()
## breath_first_crawl()

# test_crawlers()


import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Crawler académico configurable (depth-first o breadth-first)"
    )

    # Tipo de búsqueda
    parser.add_argument(
        "--mode",
        choices=["depth", "breadth"],
        required=True,
        help="Tipo de búsqueda: 'depth' para búsqueda en profundidad o 'breadth' para búsqueda en anchura",
    )

    # Parámetros comunes
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=MAX_DOWNLOADS,
        help=f"Número máximo de descargas (default: {MAX_DOWNLOADS})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DELAY,
        help=f"Tiempo de espera entre peticiones en segundos (default: {DELAY})",
    )

    # Solo para depth-first
    parser.add_argument(
        "--max-depth",
        type=int,
        default=MAX_DEPTH,
        help=f"Profundidad máxima de exploración (solo para depth-first, default: {MAX_DEPTH})",
    )

    # Flags opcionales
    parser.add_argument(
        "--check-robots",
        action="store_true",
        help="Respeta las restricciones de robots.txt",
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Guarda las páginas HTML además de los WARC",
    )
    parser.add_argument(
        "--randomize-breath",
        action="store_true",
        help="Aleatoriza el frontier en breadth-first después de los seeds",
    )

    parser.add_argument(
        "--seeds",
        type=str,
        default=SEEDS,
        help="Archivo de semillas (default: seeds.txt)",
    )

    args = parser.parse_args()

    # Configurar variables globales
    global CHECK_ROBOTS, SAVE_HTML, RANDOMIZE_BREATH
    CHECK_ROBOTS = args.check_robots
    SAVE_HTML = args.save_html
    RANDOMIZE_BREATH = args.randomize_breath

    # Ejecutar el crawler
    if args.mode == "depth":
        depth_first_crawl(
            maxDownloads=args.max_downloads,
            maxDepth=args.max_depth,
            delay=args.delay,
            seeds_file=args.seeds,
        )
    else:
        breath_first_crawl(
            maxDownloads=args.max_downloads,
            delay=args.delay,
            seeds_file=args.seeds,
        )


if __name__ == "__main__":
    main()
