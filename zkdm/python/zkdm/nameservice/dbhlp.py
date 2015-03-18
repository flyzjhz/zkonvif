# coding: utf-8

import sqlite3, Queue
import time, sys, threading


DBNAME = r'ns.db'
DBNAME_MEM = ':memory:'
TABLENAME = 'log'
TAB_HOSTS = 'hosts'
TAB_SERVICES = 'services'
TAB_STATES = 'states'

INTERVAL = 3 # 备份间隔时间

S0 = r'create table log (id integer primary key, project varchar(64), level integer, stamp integer, content text)' 
S1 = r'create table hosts (name varchar(128), type varchar(128))'
S2 = r'create table services (host varchar(128), name varchar(128), type varchar(128), url varchar(255))'
S3 = r'create table states (host varchar(128), name varchar(128), type varchar(128), stamp integer)'

TABS = [ { "name": TAB_HOSTS, "create": S1 },
         { "name": TAB_SERVICES, "create": S2 },
         { "name": TAB_STATES, "create": S3 }
       ]



class DBThread(threading.Thread):
    ''' 单线程访问内存数据库 
        通过 fifo，每个任务的数据结构为：
            { 
                "sql": "....",  sql语句
                "commit": False,  是否立即提交
                "query": False,  是否需要等待返回
                "complete": notify object，用于通知执行完成
                "result": { }
            }
    '''
    def __init__(self, fifo):
        threading.Thread.__init__(self)
        self.daemon = True
        self.__fifo = fifo
        self.__quit = False
        self.start()


    def run(self):
        conn = sqlite3.connect(DBNAME_MEM)
        cursor = conn.cursor()

        g__chk_db(conn, cursor)
        
        while not self.__quit:
            req = self.__fifo.get() # 得到下一个命令
			print req
            if req['query']:
                self.__query(cursor, req)
            else:
                # 无返回值
                s = req['sql']
                try:
                    print 'to exec:', s
                    cursor.execute(s)
                except Exception as e:
                    print 'ERR: exception for "%s",' % s, e
                else:
                    if req['commit']:
                        conn.commit()

            
    def __query(self, cursor, req):
        ''' 执行查询 '''
        s = req['sql']
        try:
            r = cursor.execute(s)
        except Exception as e:
            print 'ERR: exception for "%s",' % s, e
        else:
            rc = []
            for rec in r:
                rc.append(rec)
            req['result']['result'] = rc
            req['complete'].set()


class DBHlp:
    queue_ = Queue.Queue()  # 用于序列化
    th_ = DBThread(queue_)

    def execute(self, sent, commit = False):
        ''' 直接执行 sql 语句，没有返回 '''
        t = { 'query': False, 'commit': commit, 'sql': sent }
        DBHlp.queue_.put(t)


    def query(self, sent):
        ''' 执行查询，返回 [] '''
        result = { 'result': None }
        complete = threading.Event()
        t = {
            'query': True, 'sql': sent,
            'complete': complete,
            'result': result
        }
        DBHlp.queue_.put(t)
        complete.wait()
        return result['result']



def g__chk_db(conn, cursor):
    for chk in TABS:
        s0 = 'select COUNT(*) from sqlite_master where name="{}"'.format(chk['name'])
        n = cursor.execute(s0)
        found = False
        for x in n:
            if int(x[0]) == 1:
                found = True
                break

        if not found:
            print 'INFO: dbhlp: init:', chk['name']
            cursor.execute(chk['create'])
        else:
            print 'INFO: dbhlp: exist:', chk['name']
    conn.commit()



if __name__ == '__main__':
    db1 = DBHlp()
    db2 = DBHlp()
    db3 = DBHlp()

    db1.execute('insert into hosts values("aabbccddeeff", "x86")', commit = True)
    db2.execute('insert into hosts values("112233445566", "arm")', commit = True)

    r = db3.execute('select * from hosts')
    print r
    

    time.sleep(30.0)

