import re

valid_link_re = re.compile(r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6}).*")
valid_abs_link_re = re.compile(r"^(http|www){1}")
link_starts_http_re = re.compile(r"^(http){1}")
relative_links_re = re.compile(r"^(\/|.*(\.htm|\.asp|\.jsp|\.php|\.py|\/){1})")
disallowed_list_re = re.compile(r".*(google.com|facebook.com|twitter.com|instagram.com|.pinterest.com|tumblr.com|yahoo.com|bing.com){1}")

MAX_DEPTH = 3
MAX_DB_LOCK_ATTEMPTS = 10
MAX_THREAD = 30
WORD_RE = re.compile(r"[\w']+")
site_assets_re = re.compile(r".*(\.css|\.js|\.png|\.jpg|\.gif|\.jpeg|\.zip|\.swf|\.ico)", re.I)

all_links_table = "all_links"
to_be_crawled_table = "to_be_crawled_links"
non_working_urls_table = "non_working_urls"

database_name = "seo_crawler"
seed_url = "http://www.topcanada.info/"
