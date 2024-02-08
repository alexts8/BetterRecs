import os
import pymysql
import csv

# Update these values with your MySQL RDS connection details
host = 'fyp-db.cpc2i6c84e9b.eu-west-1.rds.amazonaws.com'  # Replace with your RDS endpoint
port = 3306
database = 'fypdatabase'
username = 'admin'
password = 'fypdatabase'

current_dir = os.getcwd()
relative_path = 'data/tracksgenres.csv'
csv_file_path = os.path.join(current_dir, relative_path)

# Establish a connection
conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)


# Create a cursor from the connection
cursor = conn.cursor()

cursor.close()
conn.close()