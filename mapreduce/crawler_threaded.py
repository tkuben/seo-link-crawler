import os
import threading
import re

import db_adapter
import configuration
from mrjob.job import MRJob
import url_traversal


class SEOCrawler(MRJob):
    # INPUT_PROTOCOL = MyCustomProtocol

    def configure_options(self):
        super(SEOCrawler, self).configure_options()
        self.add_file_option('--database')

    def _read_input(self):
        # import ipdb; ipdb.set_trace()
        input_url = self.fetch_next_available_link_if_exists()
        num_threads = threading.activeCount()
        while input_url or num_threads > 1:
            if input_url:
                yield "{}:::{}".format(input_url[0], input_url[1])
            input_url = self.fetch_next_available_link_if_exists()
            num_threads = threading.activeCount()

    def fetch_next_available_link_if_exists(self):
        cur = self.db_conn.cursor()
        if self.db_obj.check_and_get_table_lock(cur, configuration.to_be_crawled_table):
            cur.execute("select * from {} limit 1".format(configuration.to_be_crawled_table))
            row = cur.fetchone()
            if row:
                cur.execute("delete from {} where url=%s".format(configuration.to_be_crawled_table), (row[0]))
                self.db_obj.release_table_lock(cur)
                return row
            self.db_obj.release_table_lock(cur)
        cur.close()
        return None

    def mapper_init(self):
        self.db_obj = db_adapter.DB()
        self.db_conn = self.db_obj.get_db_connection()


    def mapper(self, _, line):
        try:
            url, depth = line.split(':::')
            depth = re.sub('[^0-9]+', '', depth)
            if not depth or not url:
                return None
        except Exception as e:
            print "***ERROR*** on getting url/depth {}".format(e.message)

        if configuration.valid_link_re.match(url):
            current_node = {'depth': int(depth), 'visited': False, 'url': url}
            current_node['domain'] = url_traversal._fqdn(current_node['url'])
            # import ipdb; ipdb.set_trace()
            if not current_node['visited'] and current_node['depth'] <= configuration.MAX_DEPTH:
                # TODO implement threading here and monitor thread to make sure as speed deteriorts don't thread.
                # import ipdb; ipdb.set_trace()
                if threading.active_count() < configuration.MAX_THREAD:
                    # print "Starting Thread. Cur Num Threads: {} URL: {}".format(threading.active_count(), current_node['url'])
                    thread = threading.Thread(target=url_traversal.traverse_for_links, args=(current_node,), kwargs=None)
                    thread.daemon = True
                    thread.start()
                else:
                    url_traversal.traverse_for_links(current_node)



if __name__ == '__main__':
    import time
    db_obj = db_adapter.DB()
    db_conn = db_obj.get_db_connection()
    cur = db_conn.cursor()   
    
    cwd = os.getcwd()
    SEOCrawler.run()
    file_name = 'resumed_{}'.format(time.time())
    cur.execute("SELECT distinct url,error INTO OUTFILE '{}/crawl_data/{}_non_working.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\n' FROM {}".format(cwd, file_name,configuration.non_working_urls_table))
    cur.execute("SELECT * INTO OUTFILE '{}/crawl_data/{}_all_links.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\n' FROM {}".format(cwd, file_name,configuration.all_links_table))
    cur.execute("select * from {} where crawled=0 limit 1".format(configuration.queue_table))
    row = cur.fetchone()
    while row:
        seed_url = row[1]
        parse_url = configuration.valid_link_re.match(seed_url)
        file_name = re.sub('[^0-9a-zA-Z\-]+', '', seed_url)
        if parse_url:
            file_name = parse_url.groups()[1]
        cur.execute("update {} set crawled=1 where url='{}'".format(configuration.queue_table, seed_url))
        cur.execute("delete from {}".format(configuration.to_be_crawled_table))
        cur.execute("delete from {}".format(configuration.all_links_table))
        cur.execute("delete from {}".format(configuration.non_working_urls_table))
        cur.execute("insert into {} values ('{}',0)".format(configuration.to_be_crawled_table, seed_url)) 
        db_conn.commit()
        SEOCrawler.run()
        print "****----------------Outputting results for {}".format(seed_url)
        cur.execute("SELECT distinct url,error INTO OUTFILE '{}/crawl_data/{}_non_working.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\n' FROM {}".format(cwd, file_name,configuration.non_working_urls_table))
        cur.execute("SELECT * INTO OUTFILE '{}/crawl_data/{}_all_links.csv' FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\n' FROM {}".format(cwd, file_name,configuration.all_links_table))
        cur.execute("delete from {}".format(configuration.to_be_crawled_table))
        cur.execute("delete from {}".format(configuration.all_links_table))
        cur.execute("delete from {}".format(configuration.non_working_urls_table))
        cur.execute("select * from {} where crawled=0 limit 1".format(configuration.queue_table))
        row = cur.fetchone()
