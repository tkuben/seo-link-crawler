from time import sleep

import MySQLdb as mysql
import configuration

class DB(object):

    def __init__(self):
        self.db_connection = self._init_db_connection()

    def _init_db_connection(self):
        return mysql.connect(host="162.244.12.150", user="tkuben", passwd="letmein", db=configuration.database_name)

    def get_db_connection(self):
        return self.db_connection

    def check_and_get_table_lock(self, cursor, table):
        num_attempts = configuration.MAX_DB_LOCK_ATTEMPTS
        cursor.execute("SHOW OPEN TABLES WHERE `Table` =%s", table)
        row = cursor.fetchone()
        # sleep for 1 second and try to check the table lock again if "in_use" is > 0
        while num_attempts >= 0 and row and row[2]:
            sleep(.5)
            num_attempts -= 1
            cursor.execute("SHOW OPEN TABLES WHERE `Table` =%s", table)
            row = cursor.fetchone()

        #only obtain the write lock if the "in_use" column is set to 0
        if row and not row[2]:
            cursor.execute("LOCK TABLE {} WRITE".format(table))
            return True
        print "Failed to get lock for {}:".format(table)
        return False

    def release_table_lock(self, cursor):
        cursor = self.db_connection.cursor()
        cursor.execute("UNLOCK TABLES")
