import MySQLdb as mysql
import configuration
import seed_urls

db_conn = mysql.connect(host="162.244.12.150", user="tkuben", passwd="letmein", db=configuration.database_name)
cur = db_conn.cursor()
cur.execute("delete from {}".format(configuration.to_be_crawled_table))
cur.execute("delete from {}".format(configuration.all_links_table))
cur.execute("delete from {}".format(configuration.non_working_urls_table))

for url in seed_urls.urls:
    cur.execute("insert into {} values (%s, %s)".format(configuration.to_be_crawled_table), (url, 0))
    db_conn.commit()
cur.close()
