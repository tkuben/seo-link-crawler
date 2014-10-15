import MySQLdb as mysql
import configuration

db_conn = mysql.connect(host="localhost", user="root", passwd="letmein", db=configuration.database_name)
cur = db_conn.cursor()
cur.execute("delete from {}".format(configuration.to_be_crawled_table))
cur.execute("delete from {}".format(configuration.all_links_table))
cur.execute("delete from {}".format(configuration.non_working_urls_table))
cur.execute("insert into {} values (%s, %s)".format(configuration.to_be_crawled_table), (configuration.seed_url, 0))
db_conn.commit()
cur.close()
