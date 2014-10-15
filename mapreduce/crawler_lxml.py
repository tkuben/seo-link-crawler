from collections import defaultdict
from contextlib import closing
from lxml import etree, html
import MySQLdb as mysql
import re
import requests
from rfc3987 import parse
from time import sleep
from urlparse import urlparse

from mrjob.job import MRJob

valid_link_re = re.compile(r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6}).*")
valid_abs_link_re = re.compile(r"^(http|www){1}")
link_starts_http_re = re.compile(r"^(http){1}")
relative_links_re = re.compile(r"^(\/|.*(\.htm|\.asp|\.jsp|\.php|\.py|\/){1})")
disallowed_list_re = re.compile(r".*(google.com|facebook.com|twitter.com|instagram.com|.pinterest.com|tumblr.com|yahoo.com|bing.com){1}")

MAX_DEPTH = 3
WORD_RE = re.compile(r"[\w']+")
site_assets_re = re.compile(r".*(\.css|\.js|\.png|\.jpg|\.gif|\.jpeg|\.zip|\.swf|\.ico)", re.I)

all_links_table = "all_links"
to_be_crawled_table = "to_be_crawled_links"
non_working_urls_table = "non_working_urls"

db_conn = mysql.connect(host="localhost", user="root", passwd="letmein", db="seo_crawler")


def check_and_get_table_lock(cursor, table):
    num_attempts = 1
    cursor.execute("SHOW OPEN TABLES WHERE `Table` =%s", (table))
    row = cursor.fetchone()
    # sleep for 1 second and try to check the table lock again if "in_use" is > 0
    while num_attempts >= 0 and row and row[2]:
        sleep(.5)
        num_attempts -= 1
        cursor.execute("SHOW OPEN TABLES WHERE `Table` =%s", (table))
        row = cursor.fetchone()

    #only obtain the write lock if the "in_use" column is set to 0
    if row and not row[2]:
        cursor.execute("LOCK TABLE {} WRITE".format(table))
        return True
    return False


def release_table_lock(cursor):
    cursor.execute("UNLOCK TABLES")


def handle_links(links, node):
    cur = db_conn.cursor()
    for href in links:
        valid_link = valid_link_re.match(href)
        if not valid_link:
            valid_link = relative_links_re.match(href)
            if valid_link:
                href = node['domain'] + href if valid_link.group(0) == "/" else node['domain'] + "/" + href
        elif not valid_abs_link_re.match(href):
            # this is for cases where we have foobar.htm (which falls in line with the valid_link_re
            valid_link = True
            href = node['domain'] + "/" + href

        if valid_link:
            if not link_starts_http_re.match(href):
                href = "http://" + href

            parsed_url = urlparse(href)
            root_url = "http://" + parsed_url.netloc

            # if the netloc of the link is one of the disallowed, ignore it.
            if disallowed_list_re.match(parsed_url.netloc):
                continue

            cur.execute("select * from {} where url=%s".format(all_links_table), (href))
            row = cur.fetchone()
            if not row:
                cur.execute("insert into {} values (%s, %s, %s)".format(all_links_table),
                            (href, node['depth'] + 1, node['url']))
                db_conn.commit()
                if check_and_get_table_lock(cur, to_be_crawled_table):
                    cur.execute("insert into {} values (%s, %s)".format(to_be_crawled_table), (href, node['depth'] + 1))
                    db_conn.commit()
                    release_table_lock(cur)
                else:
                    _insert_into_non_working(cur, root_url, node['depth'] + 1, 'Unable to get DB Lock')

    cur.close()


def _insert_into_non_working(cur, url, depth, reason):
    try:
        with closing(requests.get(url, timeout=5, stream=True)) as response:
            if response.status_code < 300:
                print "******** TODO {} Works! shoud be added to be crawled".format(url)
                # cur.execute("insert into {} values (%s, %s, %s)".format(non_working_urls_table), (
                # url, depth, 'Works - Some page on domain probably did not work'))
                # db_conn.commit()

    except Exception as e:
        # TODO find out what type of error and do some "seo" analysis on the url
        cur.execute("insert into {} values (%s, %s, %s)".format(non_working_urls_table), (url, depth, e.message))
        db_conn.commit()
        print "{} Error: {}".format(url, e.message)


def traverse_for_links(node):
    if node['depth'] > MAX_DEPTH:
        return

    try:
        # import ipdb; ipdb.set_trace()
        cur = db_conn.cursor()
        parsed_uri = parse(node['url'], rule='URI')
        if parsed_uri:
            node['domain'] = parsed_uri['authority']
            cur.execute("select * from {} where url = %s".format(non_working_urls_table),
                        (parsed_uri['scheme'] + "://" + node['domain']))
            row = cur.fetchone()
            if not row:
                # by adding Steam=True, we only get the header details until we request response.content
                with closing(requests.get(node['url'], timeout=5, stream=True)) as response:
                    if response.status_code > 300:
                        _insert_into_non_working(cur, parsed_uri['scheme'] + "://" + node['domain'], node['depth'],
                                                 response.status_code)
                    if node['depth'] < MAX_DEPTH:
                        html_doc = html.fromstring(response.content)
                        links = html.iterlinks(html_doc)
                        links = [l[2] for l in links if not site_assets_re.match(l[2])]
                        handle_links(links, node)
            else:
                print "** Already analyzed: {}".format(node['url'])
        else:
            raise Exception("NODE NOT URI!! This should not have happened")
    except Exception as e:
        # this additional try catch is needed because the exception might be caused by parsed_uri and that if the
        #exception is thrown that means that varirable was not defined.
        try:
            parsed_uri = parse(node['url'], rule='URI')
            url = parsed_uri['scheme'] + "://" + node['domain']
        except Exception as f:
            print "Unable to parse URI: '{}'".format(node['url'])
            url = node['url']
        _insert_into_non_working(cur, url, node['depth'], e.message)
        print "{} Error: {}".format(node['url'], e.message)
    cur.close()


class SEOCrawler(MRJob):
    # INPUT_PROTOCOL = MyCustomProtocol

    def configure_options(self):
        super(SEOCrawler, self).configure_options()
        self.add_file_option('--database')

    def _read_input(self):
        input_url = self.fetch_next_available_link_if_exists()
        while input_url:
            # input_url = input_url[0]
            yield "{}:::{}".format(input_url[0], input_url[1])
            input_url = self.fetch_next_available_link_if_exists()

    def fetch_next_available_link_if_exists(self):
        cur = db_conn.cursor()
        if check_and_get_table_lock(cur, to_be_crawled_table):
            cur.execute("select * from {} limit 1".format(to_be_crawled_table))
            row = cur.fetchone()
            if row:
                cur.execute("delete from {} where url=%s".format(to_be_crawled_table), (row[0]))
                release_table_lock(cur)
                return row
        cur.close()
        return None

    def mapper(self, _, line):
        try:
            url, depth = line.split(':::')
            depth = re.sub('[^0-9]+', '', depth)
            if not depth or not url:
                return None
        except Exception as e:
            import ipdb;

            ipdb.set_trace()
        if valid_link_re.match(url):
            current_node = {'depth': int(depth), 'visited': False, 'url': url, 'child_nodes': defaultdict(dict)}
            if not current_node['visited'] and current_node['depth'] <= MAX_DEPTH:
                # TODO implement threading here and monitor thread to make sure as speed deteriorts don't thread.
                traverse_for_links(current_node)


if __name__ == '__main__':
    SEOCrawler.run()
