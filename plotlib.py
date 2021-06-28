from logdb import DBManager
import datetime
import matplotlib.pyplot as plt

db = DBManager("logparse.db")


def plotsort(lastseen, maxvalue):
    sorr = sorted(lastseen, key=lambda ipaddress: lastseen[ipaddress][0], reverse=True)
    labels = []
    sizes = []
    for name in sorr:
        print("{} , {} , {}, {}, {}".format(name, lastseen[name][0], lastseen[name][1], lastseen[name][2], lastseen[name][3]))
        labels.append('{}, {}'.format(name, lastseen[name][2]))
        sizes.append(int((lastseen[name][0] / maxvalue)*100))
    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.show()


def getfromdb():
    dblastseen = {}
    alld = db.get_allblockcount()
    maxvalue = 0
    for row in alld:
        if row[1] >= 10:
            dblastseen[row[0]] = (row[1], row[2], row[3], row[4])
            maxvalue += row[1]
    plotsort(dblastseen, maxvalue)


getfromdb()
