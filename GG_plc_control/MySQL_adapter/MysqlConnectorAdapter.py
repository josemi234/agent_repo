import sys
import mysql.connector
from functools import reduce


class MysqlConnectorAdapter():
    def __init__(self, db_name, db_user, db_pswd, db_host='localhost'):
        self.db_name = db_name
        self.db_user = db_user
        self.db_pswd = db_pswd
        self.db_host = db_host
        self.db_connection = mysql.connector.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_pswd,
            database=self.db_name
        )
        self.cursor = self.db_connection.cursor()

    def get_tables(self):
        self.cursor.execute("SHOW TABLES")
        tables_gen = self.cursor.fetchall()
        return tuple(str(t[0]) for t in tables_gen)

    def get_table_column_tuple(self, table):
        self.cursor.execute("SHOW COLUMNS FROM {}".format(table))
        columns_gen = self.cursor.fetchall()
        return tuple(str(c[0]) for c in columns_gen)

    def upload_data(self, table, values, column_tuple=None):
        column_tuple_from_db = self.get_table_column_tuple(table)
        if not column_tuple:
            column_tuple = column_tuple_from_db

        column_tuple_query = reduce(
            lambda s, c: s + "," + str(c), column_tuple)

        values_query = str(values)[1:-1]

        query = "INSERT INTO {} ({}) VALUES {};".format(
            table, column_tuple_query, values_query)
        self.cursor.execute(query)
        self.db_connection.commit()      

    def update_data(self, table, update_query):
        query = "UPDATE {} SET {}".format(table, update_query)
        self.cursor.execute(query)
        self.db_connection.commit()

    def get_data(self, table, add_query=""):
        column_tuple_from_db = self.get_table_column_tuple(table)
        self.cursor.execute("SELECT * FROM {} {}".format(table, add_query))
        values = self.cursor.fetchall()
        return column_tuple_from_db, values

    def delete_data(self, table, condition="TRUE", add_query=""):
        query = "DELETE FROM {} WHERE {} {}".format(
            table, condition, add_query)
        print(query)
        self.cursor.execute(query)
        self.db_connection.commit()

    def get_row_count(self, table):
        query = "SELECT table_rows FROM information_schema.tables " + \
            "WHERE table_schema='{}' AND table_name='{}'".format(
                    self.db_name,
                    table
                )
        print('query', query)

        self.cursor.execute(query)
        row_count = self.cursor.fetchall()[0][0]
        return row_count

    def get_tasks(self, table, condition):
        query = f"SELECT count(*) row_count FROM {table} WHERE {condition}"
        print('query', query)

        self.cursor.execute(query)
        row_count = self.cursor.fetchall()[0][0]
        return row_count
        
    def closing(self):
        self.db_connection.close()