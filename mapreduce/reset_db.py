import MySQLdb as mysql

all_links_table = "all_links"
to_be_crawled_table = "to_be_crawled_links"
non_working_urls_table = "non_working_urls"

seed_url = "http://www.01webdirectory.com/"


db_conn = mysql.connect(host="localhost", user="root", passwd="letmein", db="seo_crawler")
cur = db_conn.cursor()
cur.execute("delete from {}".format(to_be_crawled_table))
cur.execute("delete from {}".format(all_links_table))
cur.execute("delete from {}".format(non_working_urls_table))
cur.execute("insert into {} values (%s, %s)".format(to_be_crawled_table), (seed_url, 0))
db_conn.commit()
cur.close()
