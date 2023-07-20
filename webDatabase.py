import mysql.connector
from mysql.connector import Error
from xlsxwriter.workbook import Workbook
from tqdm import tqdm
import pickle
# import database as db

class webDb(object):
    def __init__(self, server, login, password, base) -> None:
        # self.server = server
        # self.login = login
        # self.password = password
        # self.base = base
        # self.table = table

        try:
            self.con = mysql.connector.connect(
                host = server,
                user = login,
                passwd = password,
                database = base
            )
            self.cur =self.con.cursor()
        
        except Error as e:
            print(e)


    # def create_connection(self):
    #     connection = None
    #     try:
    #         connection = mysql.connector.connect(
    #             host=self.server,
    #             user=self.login,
    #             passwd=self.password,
    #             database=self.base
    #         )
    #         print('Connection to MySQL DB successful')
    #     except Error as e:
    #         print(f'The error "{e}" occurred')

    #     return (connection)

    # def main(self, param):
    #     con = webDb.create_connection(self)
    #     cur = con.cursor()
    #     cur.execute(f'SELECT * FROM {self.table} WHERE {param}')
    #     # cur.execute('''select main.id as id_old,main.groupId,main.prodaji,main.barcode,main.colorObl,main.imtId,main.ozonProductId,
    #     # main.tiraz,main.tcalc,main.sto,main.cena_calc,izdat.id as izdat_id,main.mag,main.electron,main.validDate,main.description,cena__,main.cena_str,main.nal,main.original,main.recomend,main.dop_recomend,main.nzapol,main.id_razdel,main.p_p,main.soderzan,main.pict,main.link,main.kobr,izdat.izdat,main.str,main.series,main.series2,main.isbn,main.ogl,main.bannerOgl,main.autor,year.year,main.cena,main.obl,main.tobl,main.anot,main.ves,main.skachat,main.skachatf,main.format,main.proizvodim,ost,mizdat.mizdat
    #     # from main ,year ,izdat, mizdat
    #     # where    izdat.id=main.id_izdat and year.id=main.id_year and 	mizdat.id=main.id_mizdat
    #     # and main.id in ("00003957")''')
    #     return(cur.fetchall())

    def create(self, table, items):
        self.cur.execute(f'CREATE TABLE IF NOT EXISTS {table}(id INT PRIMARY KEY, {(", ").join(items)})')
        self.con.commit()
        self.cur.execute(f'SELECT * FROM {table}')

    def add(self, table, items, order=True):
        countItems = []
        count = len(items)
        if order:
            [countItems.append('%s') for _ in range(count)]
            idObj = self.find(table, 'id', f'id != ""')
            if len(idObj) == 0:
                id_ = 0
            else:
                id_ = idObj[-1][0] + 1
        else:
            [countItems.append('%s') for _ in range(count - 1)]
        com = f'INSERT INTO {table} VALUES({(", ").join(countItems)}, %s)'
        if order:
            self.cur.execute(com, (id_, *items))
        else:
            self.cur.execute(com, items)
        self.con.commit()

    def find(self, table, param1, param2):
        self.cur.execute(f'SELECT {param1} FROM {table} WHERE {param2}')
        return(self.cur.fetchall())

    def upd(self, table, param1, param2):
        self.cur.execute(f'UPDATE {table} SET {param1} WHERE {param2}')
        self.con.commit()

    def del_(self, table, param):
        self.cur.execute(f'DELETE FROM {table} WHERE {param}')
        self.con.commit()
        self.cur.execute(f'SELECT * FROM {table}')

    def show(self, table):
        self.cur.execute(f'SELECT * FROM {table}')
        return(self.cur.fetchall())

    def sortA(self, table, param):
        self.cur.execute(f'SELECT * FROM {table} ORDER BY {param} ASC')
        self.con.commit()

    def sortZ(self, table, param):
        self.cur.execute(f'SELECT * FROM {table} ORDER BY {param} DESC')
        self.con.commit()

    def getColumns(self):
        columns = [el[0:el.rfind(' ')] for el in [els for els in self.cur.execute('SELECT * FROM sqlite_master')][0][4].split(', ')]
        columns[0] = columns[0][columns[0].find('(') + 1:columns[0].rfind('INT') - 1]
        return(columns)
    
    def disconnect(self):
        self.cur.close()

    def sql2Exel(self, table, file):
        columns = webDb.getColumns()
        workbook = Workbook(f'{file}.xlsx')
        worksheet = workbook.add_worksheet()
        while columns.count(None) != 0:
            columns.remove(None)
        for i, el in enumerate(columns):
            worksheet.write(0, i, el)
        for y, row in tqdm(enumerate(self.cur.execute(f'SELECT * FROM {table}'))):
            for x, value in enumerate(row):
                worksheet.write(y + 1, x, value)
        workbook.close()

    


# print(webDb('centrmag2.mtw.ru', 'centrmag3', '2022Fabrika', 'db_centrmag3').main())
# pages = []
# print(result[0])
# for i, row in enumerate(result):
    # if row[12] != 0:
    #     pages.append({'№': i, 'id': row[0], 'pages': row[12], 'nmId': row[-5], 'ImtId': row[-4]})



# pickle.dump(pages, open('pages', 'wb'), protocol=pickle.HIGHEST_PROTOCOL)

# db.sqlCreate('db', [])