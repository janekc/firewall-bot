#!/usr/bin/python
import time
import re
import os 
import sys
import getopt
from logdb import DBManager
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
from ip2geotools.databases.noncommercial import DbIpCity

db = DBManager('logparse.db')


def main(argv):
    path = '.'
    try:
        opts, args = getopt.getopt(argv,"hd:",["dir="])
    except getopt.GetoptError:
        print('__init__.py -d <watched directory>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('__init__.py -d <watched directory>')
            sys.exit()
        elif opt in ("-d", "--dir"):
            path = arg

    syslogfile = find("syslog", path)

    event_handler = MyHandler(syslogfile)
    observer = Observer()
    observer.schedule(event_handler, path=syslogfile, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(40)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            print("found log file: {}".format(os.path.join(root, name)))
            return os.path.join(root, name)
        else:
            print("no log file found")
            sys.exit()


def parse(file, bytecursor, lastseen):
    with open(file, "r") as logfile:
        logfile.seek(bytecursor)
        print("at byte in file: {}".format(bytecursor))
        for line in logfile.readlines():
            matchMail = re.search(r'\[UFW BLOCK\] \w*=\w*( \w*=){2}[a-fA-F0-9]{2}(:[a-fA-F0-9]{2}){13} SRC=(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}', line)
            if matchMail:
                counter = 0
                ipaddress = matchMail.group()[80:]
                timestampstring = re.search(r'\[\d*.\d*\]', line)
                if timestampstring:
                    timestamp = int(timestampstring.group()[1:-8])
                if lastseen.get(ipaddress) is not None:
                    counter, timestamp_old = lastseen.get(ipaddress)
                    if timestamp - timestamp_old <= timedelta(hours=1).total_seconds():
                        timestamp = timestamp_old
                    else:
                        counter = 0
                counter = counter + 1
                lastseen.update({ipaddress: (counter, timestamp)})
        bytecursor = logfile.tell()
    return bytecursor, lastseen


def storetodb(lastseen):
    for ipaddress in lastseen:
        counter, timestamp = lastseen.get(ipaddress)
        if counter >= 2:
            try:
                response = DbIpCity.get(ipaddress, api_key='free')
            except Exception:
                response.country = "NA"
                response.city = "NA"
            db.store_blockcount(ipaddress, counter, timestamp, response.country, response.city)
            print("\t{}\t\t{}\t\t{}\t\t{}\t\t{}".format(ipaddress, counter, timestamp, response.country, response.city))
    print("\n")


class MyHandler(FileSystemEventHandler):
    def __init__(self, logfile):
        self.last_modified = datetime.now()
        self.last_bytecursor = 0
        self.lastseen = {}
        self.logfile = logfile
        print("---------------------------------------------------------------------------------")
        print("|\tipaddress\t\tblocksinlasthour\t\ttimestamp       |")
        print("---------------------------------------------------------------------------------")


    def on_modified(self, event):
        if datetime.now() - self.last_modified < timedelta(seconds=40):
            return
        else:
            self.last_modified = datetime.now()
            self.last_bytecursor, self.lastseen = parse(self.logfile, self.last_bytecursor, self.lastseen)
            storetodb(self.lastseen)


if __name__ == "__main__":
    main(sys.argv[1:])