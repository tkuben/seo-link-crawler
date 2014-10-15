from contextlib import closing
from lxml import etree, html
import requests
from time import sleep

import db_adapter
import configuration



def handle_links(db_obj, db_conn, links, node):
    cur = db_conn.cursor()
    for href in links:
        valid_link = configuration.valid_link_re.match(href)
        if not valid_link:
            valid_link = configuration.relative_links_re.match(href)
            if valid_link:
                href = node['domain'] + href if valid_link.group(0) == "/" else node['domain'] + "/" + href
        elif not configuration.valid_abs_link_re.match(href):
            # this is for cases where we have foobar.htm (which falls in line with the valid_link_re
            valid_link = True
            href = node['domain'] + "/" + href

        if valid_link:
            if not configuration.link_starts_http_re.match(href):
                href = "http://" + href

            root_url = _fqdn(href)

            # if the netloc of the link is one of the disallowed, ignore it.
            if configuration.disallowed_list_re.match(root_url):
                continue

            cur.execute("select * from {} where url=%s".format(configuration.all_links_table), (href))
            row = cur.fetchone()
            if not row:
                cur.execute("insert into {} values (%s, %s, %s)".format(configuration.all_links_table),
                            (href, node['depth'] + 1, node['url']))
                db_conn.commit()
                if db_obj.check_and_get_table_lock(cur, configuration.to_be_crawled_table):
                    cur.execute("insert into {} values (%s, %s)".format(configuration.to_be_crawled_table), (href, node['depth'] + 1))
                    db_conn.commit()
                    db_obj.release_table_lock(cur)
                else:
                    _insert_into_non_working(db_conn, root_url, node['depth'] + 1, 'Unable to get DB Lock')
    cur.close()


def traverse_for_links(node):

    if node['depth'] > configuration.MAX_DEPTH:
        return

    try:
        # import ipdb; ipdb.set_trace()
        db_obj = db_adapter.DB()
        db_conn = db_obj.get_db_connection()
        cur = db_conn.cursor()
        cur.execute("select * from {} where url = %s".format(configuration.non_working_urls_table), node['domain'])
        row = cur.fetchone()
        # sleep(10)
        if not row:
            # by adding Steam=True, we only get the header details until we request response.content
            with closing(requests.get(node['url'], timeout=5, stream=True)) as response:
                if response.status_code > 400:
                    _insert_into_non_working(db_conn, node['domain'], node['depth'], response.status_code)
                if node['depth'] < configuration.MAX_DEPTH:
                    html_doc = html.fromstring(response.content)
                    links = html.iterlinks(html_doc)
                    links = [l[2] for l in links if not configuration.site_assets_re.match(l[2])]
                    handle_links(db_obj, db_conn, links, node)
        else:
            print "** Already analyzed: {}".format(node['url'])
    except Exception as e:
        # this additional try catch is needed because the exception might be caused by parsed_uri and that if the
        #exception is thrown that means that varirable was not defined.
        try:
            url = _fqdn(node['url'])
        except Exception as f:
            print "Unable to parse URI: '{}'".format(node['url'])
            url = node['url']
        _insert_into_non_working(db_conn, url, node['depth'], e.message)
        print "{} Error: {}".format(node['url'], e.message)
    cur.close()


def _insert_into_non_working(db_conn, url, depth, reason):
    try:
        with closing(requests.get(url, timeout=5, stream=True)) as response:
            if response.status_code < 300:
                print "******** TODO {} Works! shoud be added to be crawled".format(url)
                # cur.execute("insert into {} values (%s, %s, %s)".format(non_working_urls_table), (
                # url, depth, 'Works - Some page on domain probably did not work'))
                # db_conn.commit()

    except Exception as e:
        # TODO find out what type of error and do some "seo" analysis on the url
        temp_cur = db_conn.cursor()
        temp_cur.execute("insert into {} values (%s, %s, %s)".format(configuration.non_working_urls_table), (url, depth, e.message))
        db_conn.commit()
        temp_cur.close()
        print "{} Error: {}".format(url, e.message)


def _fqdn(url):
    parse_url = configuration.valid_link_re.match(url)
    if parse_url:
        scheme = "http://"
        parse_url = parse_url.groups()
        if parse_url[0]:
            scheme = parse_url[0]
        return "{}{}.{}".format(scheme, parse_url[1], parse_url[2])
    return None


