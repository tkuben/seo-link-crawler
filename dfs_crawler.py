from collections import defaultdict
from urllib2 import Request, urlopen, URLError
from HTMLParser import HTMLParser
from urlparse import urlparse
import re
import time

#REQUIREMENTS
# pip install memory_profiler

#Run
# python -m memory_profiler crawler.py

valid_link_re = re.compile(r"^(http|www){1}")
link_starts_http_re = re.compile(r"^(http){1}")
disallowed_list_re = re.compile(r"(google.com|facebook.com|twitter.com|instagram.com){1}")
discovered_urls = []


MAX_DEPTH = 1

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
            # import ipdb; ipdb.set_trace()
            if (isinstance(href, unicode) or isinstance(href, str)) and valid_link_re.match(href):

                if not link_starts_http_re.match(href):
                    href = "http://" + href

                parsed_url = urlparse(href)
                root_url = "http://" + parsed_url.netloc

                #if the netloc of the link is one of the disallowed, ignore it.
                if disallowed_list_re.match(parsed_url.netloc):
                    return
                if not self.current_node['child_nodes']:
                    self.current_node['child_nodes'] = defaultdict(dict)

                if href not in discovered_urls and href not in self.current_node['child_nodes'].keys():
                    self.current_node['child_nodes'][href] = {'depth': self.current_node['depth']+1,
                                                              'url': href,
                                                              'child_nodes': defaultdict(dict),
                                                              'visited': False,
                                                              'parent': self.current_node['url']}
                    discovered_urls.append(href)

def traverse_for_links(node):
    print u"Traversing URL: {} Parent: {} Depth: {}".format(node['url'], node['parent'], node['depth'])
    
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
        print u"     FAILED URL: {} - Error: {}".format(node['url'], e.reason)
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
                print u"     URL: {} - Error: {}".format(node['url'], e.reason)
    return defaultdict(dict)

def DFS(seed_url):
    S = []
    # import ipdb; ipdb.set_trace()
    S.append({'depth': 0, 'visited': False, 'url': seed_url, 'child_nodes': defaultdict(dict), 'parent': 'Root'})
    while S:
        current_node = S.pop()
        if not current_node['visited'] and current_node['depth'] <= MAX_DEPTH:
            current_node = traverse_for_links(current_node)
            # import ipdb; ipdb.set_trace()
            current_node['visited'] = True
            for child_key, child_node in current_node['child_nodes'].iteritems():
                S.append(child_node)


start = time.time()
seed_url = "http://www.realtyforsale.ca/";
DFS(seed_url)
end = time.time()
print "Script took: {}s".format(end - start)

