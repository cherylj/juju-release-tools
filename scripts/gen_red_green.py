#!/usr/bin/python
import sys
import os
import csv
import re
import HTML
import datetime

from optparse import OptionParser
from launchpadlib.launchpad import Launchpad
from pprint import pprint

milestone126 = "1.26.0"
reportedSeries = ["1.26", "2.0"]
expectedWorkItems = [
    'feature one-pager approved',
    'design spec',
    'implementation',
    'demo',
    'ci tests',
    'release notes',
    'stakeholder signoff',
    'documentation draft',
    'documentation complete']

color_dict = {
    'done': 'DarkGreen',
    'inprogress' : 'LightGreen',
    'postponed' : 'Maroon',
    'todo': 'LightGray',
    'near deadline': 'DarkOrange',
    'overdue': 'Red',
    'n/a': 'Black'}

csv_fields = [
    'Feature',
    'Owner',
    'One Pager',
    'Design Spec',
    'Code Complete',
    'Demo',
    'CI Tests',
    'Release Notes',
    'Stakeholder Signoff',
    'Documentation Submitted',
    'Documentation Published']

validStatuses = [
    'inprogress',
    'todo',
    'postponed',
    'done']

def makeMainHeader():
    row = []
    for field in csv_fields:
        row.append(HTML.TableCell("<b><center>%s</center></b>" % field, bgcolor="DarkGray"))

    return row

def isNATask(string):
    matchObj = re.match(r'.*\(n\/a\)', string)
    if matchObj:
        return True
    return False

def correctTask(string, index):
    if index >= len(expectedWorkItems):
        return "", False

    task = string.strip()
    split = task.split("(")
    if len(split) != 2:
        return "", False

    task = split[0]
    task = task.strip()
    return task, task == expectedWorkItems[index]

def validStatus(status):
    for stat in validStatuses:
        if status == stat:
            return True
    return False

def isDateTask(string):
    return False

def addFeature(spec, t):
    html_row = []
    html_row.append(HTML.TableCell("<a href=\"%s\">%s</a>" % (spec.web_link, spec.title)))
    if spec.assignee:
        html_row.append(HTML.TableCell("<center>%s</center>" % spec.assignee.display_name))
    else:
        html_row.append(HTML.TableCell(""))

    work_items = spec.workitems_text
    items = work_items.split("\n")
    #skip first header
    items = items[1:]
    i = 0
    for item in items:
        strings = item.lower().split(":")
        if len(strings) != 2:
            print("ERROR formatting feature: %s" % spec.title)
            return

        task, ok = correctTask(strings[0], i)
        if not ok:
            print("ERROR formatting feature: %s" % spec.title)
            return
        if isNATask(strings[0]):
            status = 'n/a'
        elif isDateTask(strings[0]):
            status = getDateStatus(strings[0])
        else:
            status = strings[1].strip()
            if not validStatus(status):
                print("Error reading status for task: %s, for %s" % (expectedWorkItems[i], spec.title))

        #print("TASK: %s ---- STATUS: %s" % (expectedWorkItems[i], strings[1]))
        html_row.append(HTML.TableCell("", bgcolor=color_dict[status]))
        i = i + 1
    t.rows.append(html_row)

def genKey():
    rows = [
        [
            HTML.TableCell('TODO', bgcolor=color_dict["todo"]),
            HTML.TableCell('IN PROGRESS', bgcolor=color_dict["inprogress"]),
            HTML.TableCell('<font color="White">DONE</font>', bgcolor=color_dict["done"]),
            HTML.TableCell('NEAR DEADLINE', bgcolor=color_dict["near deadline"]),
            HTML.TableCell('<font color="White">OVERDUE</font>', bgcolor=color_dict["overdue"]),
            HTML.TableCell('<font color="White">POSTPONED</font>', bgcolor=color_dict["postponed"]),
            HTML.TableCell('<font color="White">N/A</font>', bgcolor=color_dict["n/a"]),
        ]
    ]

    t = HTML.Table(rows, 
        col_width=['150', '150', '150', '150', '150', '150', '150'], 
        col_align=['center', 'center', 'center', 'center', 'center', 'center', 'center'])

    return str(t)

def writeTop(f):
    release_table = [
        ["3-Nov-2015", "Alpha 1"],
        ["17-Nov-2015", "Alpha 2"],
        ["1-Dec-2015", 'Beta 1\
<list>\
<li>Feature Freeze</li>\
<li>All release notes complete</li>\
</list>'],
        ["8-Dec-2015", "Beta 2"],
        ["15-Dec-2015", 'Beta 3\
<list>\
<li>Code freeze</li>\
<li>Feature buddy signoff complete</li>\
</list>'],
        ["18-Dec-2015", "Documentation Complete"],
        ["<i>22-Dec-2015</i>", "<i>Holiday Break</i>"],
        ["<i>29-Dec-2015</i>", "<i>Holiday Break</i>"],
        ["5-Jan-2016", "Beta 4"],
        ["12-Jan-2016", "1.26 Released"],
    ]

    htmlcode = HTML.table(release_table, header_row=[HTML.TableCell("<b><center>Date</center</b>", bgcolor="DarkGray"), HTML.TableCell("<b><center>Milestone</center</b>", bgcolor="DarkGray")], 
        col_width=['200', '600'], col_align=['center', 'left'])
    f.write(htmlcode)
    f.write("<p>")
        

def main(args):

    try:
        lp = Launchpad.login_with("pypypy", "production", version="devel")
    except:
        print "** ERROR: Could not open LP "
        sys.exit(-1)



    try:
        project = lp.projects["juju-core"]
    except KeyError:
        print "** ERROR: Project name does not exist: juju-core"
        quit()

    for series in reportedSeries:
        lpSeries = project.series
        for ls in lpSeries:
            if ls.name == series:
                writeSeriesFile(series, ls)


def writeSeriesFile(seriesName, series):
    htmlFile = 'juju-release-%s.html' % seriesName
    print("Writing html file: %s" % htmlFile)
    f = open(htmlFile, 'w')
    t = HTML.Table(header_row = makeMainHeader(), col_width=["300", "200", "90", "90", "90", "90", "90", "90", "90", "90", "90"])

    specs = series.all_specifications
    for spec in specs:
        addFeature(spec, t)

    f.write("<h1>Juju %s Feature Tracker</h1>" % seriesName)
    htmlCode = str(t)
    f.write("<title>Juju %s Feature Tracker</title>" % seriesName)
    f.write(htmlCode)
    f.write("<p>")
    f.write(genKey())
    f.write("<p>")
    f.write("<h2>Juju %s Release Schedule</h2>" % seriesName)
    writeTop(f)
    f.write("<hr>")
    timeNow = datetime.datetime.now()
    f.write("<i>Last updated: %s</i>" % timeNow)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
