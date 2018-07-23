from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode
import config

DB_NAME = "UpdatesAssistant"

TABLES = {}
TABLES['submissions'] = (
    "CREATE TABLE `submissions` ("
    "   `submission_id` varchar(10) NOT NULL,"  #I believe comment id's are 10 characters and submission id's are 9. 
    "   `uid` int NOT NULL AUTO_INCREMENT,"
    "   `type` tinyint(1),"
    "   `url` varchar(108) NOT NULL," #90 + len("https://reddit.com") according to https://www.reddit.com/r/redditdev/comments/dcd39/maximum_string_lengths_in_reddit/
    "   `hash` varchar(32) NOT NULL,"
    "   `poster` varchar(22),"  #Username max length: 20 + len("u/")
    "   `requester` varchar(22) NOT NULL,"
    "   `expiration_date` date NOT NULL,"
    "   `num_upvotes` int(32) NOT NULL,"
    "   `num_comments` int(32) NOT NULL,"
    "   PRIMARY KEY (`uid`)"
    ") ENGINE=InnoDB")


def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

cnx = mysql.connector.connect(user=config.sql_user, password=config.sql_pass)
cursor = cnx.cursor()

try:
    cnx.database = DB_NAME  
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        create_database(cursor)
        cnx.database = DB_NAME
    else:
        print(err)
        exit(1)
        

for name, ddl in TABLES.items():
    try:
        print("Creating table {}: ".format(name), end='')
        cursor.execute(ddl)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")


# add_user = ("INSERT ignore INTO posts"
#                "(username,local,title,body,date,months,seeking,offering,pid)"
#                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
#                #"WHERE NOT EXISTS (SELECT uid FROM users u)"
#                )

# get_users = ("SELECT username,pid FROM posts")
