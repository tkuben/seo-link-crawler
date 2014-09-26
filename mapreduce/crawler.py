from collections import defaultdict
from urllib2 import Request, urlopen, URLError
from HTMLParser import HTMLParser
from urlparse import urlparse
import re
import _mysql

from mrjob.job import MRJob

valid_link_re = re.compile(r"^(http|www){1}")
link_starts_http_re = re.compile(r"^(http){1}")
disallowed_list_re = re.compile(r"(google.com|facebook.com|twitter.com|instagram.com){1}")
discovered_urls = []


MAX_DEPTH = 2
WORD_RE = re.compile(r"[\w']+")

all_links_table = "all_links"
to_be_crawled_table = "to_be_crawled_links"
non_working_urls_table = "non_working_urls"


db = _mysql.connect(host="localhost", user="root", passwd="letmein", db="seo_crawler")

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    current_node = {'visited': False, 'child_nodes': defaultdict(dict)}
    def set_cur_node(self, node):
        self.current_node = node

    def get_cur_node(self):
        return self.current_node

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = [ attr for attr in attrs if 'href' in attr ]
            if href:
                href = href[0][1]
            if (isinstance(href, unicode) or isinstance(href, str)) and valid_link_re.match(href):

                if not link_starts_http_re.match(href):
                    href = "http://" + href

                parsed_url = urlparse(href)
                root_url = "http://" + parsed_url.netloc

                #if the netloc of the link is one of the disallowed, ignore it.
                if disallowed_list_re.match(parsed_url.netloc):
                    return

                db.query("select * from {} where url='{}'".format(all_links_table, href))
                result = db.use_result()
                row = result.fetch_row()
                if not row:
                    db.query("insert into {} values ('{}', '{}', '{}')".format(all_links_table, href, self.current_node['depth']+1, self.current_node['url']))
                    db.query("insert into {} values ('{}', '{}')".format(to_be_crawled_table, href, self.current_node['depth']+1))


def traverse_for_links(node):
    # print u"Traversing URL: {} Parent: {} Depth: {}".format(node['url'], node['parent'], node['depth'])

    # if isinstance(node['url'], unicode):
    #     print u"     ****UNICODE URL**** {} Parent: {} Depth: {}".format(node['url'], node['parent'], node['depth'])
    #     return defaultdict(dict)

    req = Request(node['url'])
    parser = MyHTMLParser()
    parser.set_cur_node(node)
    try:
        # import ipdb; ipdb.set_trace()
        response = urlopen(req)
    except Exception as e:
        #TODO find out what type of error and do some "seo" analysis on the url
        db.query("insert into {} values ('{}', '{}', '{}')".format(non_working_urls_table, node['url'], node['depth'], e.reason))
        return defaultdict(dict)
    else:
        #we want to only parse the html document if we want to further dive down into the
        #links of the current node.
        if(node['depth'] < MAX_DEPTH):
            try:
                encoding = response.headers.getparam('charset')
                if encoding:
                    parser.feed(response.read().decode(encoding))
                else:
                    parser.feed(response.read())
                return parser.get_cur_node()
            except Exception as e:
                #TODO handle encoding errors.
                pass
    db.query("insert into {} values ('{}', '{}', 'Unable to traverse')".format(non_working_urls_table, node['url'], node['depth']))
    return defaultdict(dict)


class SEOCrawler(MRJob):

    # INPUT_PROTOCOL = MyCustomProtocol

    def configure_options(self):
        super(SEOCrawler, self).configure_options()
        self.add_file_option('--database')

    def _read_input(self):
        input_url = self.fetch_next_available_link_if_exists()
        while input_url:
            input_url = input_url[0]
            #TODO is this the right place to do this?
            self.db.query("delete from to_be_crawled_links where url='{}'".format(input_url[0]))
            yield "{},{}".format(input_url[0], input_url[1])
            input_url = self.fetch_next_available_link_if_exists()

    def fetch_next_available_link_if_exists(self):
        #TODO make sure combiner & reducer does appropriate.
        if hasattr(self, 'db'):
            #TODO wait for X seconds and try again to see if another mapper has added in a link.
            self.db.query("select * from to_be_crawled_links")
            result = self.db.use_result()
            row = result.fetch_row()
            if row:
                return row
        return None

    def mapper_init(self):
        seed_url = "http://www.ratesupermarket.ca/"
        self.db = _mysql.connect(host="localhost", user="root", passwd="letmein", db="seo_crawler")
        self.db.query("delete from to_be_crawled_links")

        #TODO should we really delete the found non_working urls on each run of this program?
        self.db.query("delete from {}".format(to_be_crawled_table))
        self.db.query("insert into {} values('{}','0')".format(to_be_crawled_table, seed_url))

        self.db.query("delete from {}".format(all_links_table))
        self.db.query("insert into {} values('{}','0', 'root')".format(all_links_table, seed_url))

        self.db.query("delete from {}".format(non_working_urls_table))

    def mapper(self, _, line):
        url,depth = line.split(',')
        if valid_link_re.match(url):
            current_node = {'depth': int(depth), 'visited': False, 'url': url, 'child_nodes': defaultdict(dict)}
            if not current_node['visited'] and current_node['depth'] <= MAX_DEPTH:
                traverse_for_links(current_node)

if __name__ == '__main__':
    SEOCrawler.run()