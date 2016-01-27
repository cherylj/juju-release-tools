#!/usr/bin/python
import sys
import os
import csv
import re
import HTML
import time
import collections

from optparse import OptionParser
from argparse import ArgumentParser
from launchpadlib.launchpad import Launchpad
from pprint import pprint
from datetime import datetime

csv_fields = [
    'Number',
    'Title',
    'Stakeholder',
    'Notes']


def makeMainHeader():
    row = []
    for field in csv_fields:
        row.append(HTML.TableCell("<b><center>%s</center></b>" % field, bgcolor="DarkGray"))

    return row

def processBug(row, lp):
    print("parsing bug: %s" % row[0])
    bug = lp.bugs[int(row[0])]
    html_row = []
    html_row.append(HTML.TableCell("<center><a href=\"%s\">%s</a></center>" % (bug.web_link, bug.id)))
    html_row.append(HTML.TableCell("<a href=\"%s\">%s</a>" % (bug.web_link, bug.title)))
    html_row.append("<center>%s</center>" % row[1])
    notes, table = getNotes(bug, row)
    html_row.append(notes)
    return table, html_row

def isJujuTask(s):
    matchObj = re.match(r'juju-core.*', s)
    if matchObj:
        return True
    return False

def getNotes(bug, row):
    notes = row[2]
    lines = []
    isReleased = True
    table = "new"
    tasks = bug.bug_tasks
    for t in tasks:
        print("looking at task: %s" % t.bug_target_name)
        if isJujuTask(t.bug_target_name):
            # Get assignee
            if t.assignee_link != None:
                table = "assigned"
                split = t.assignee_link.split("~")
                lines.append("<b>%s</b><ul><li><b>Assignee:\t</b>%s</li><li><b>Status:\t</b>%s</li></ul>" % (t.bug_target_name, split[1], t.status))

    if len(lines) > 0:
        string = "<ul>"
        for l in lines:
            string = string + "<li>%s</li>" % l
        string = string + "</ul>"
        notes = notes + string
    return notes, table


def main(args):
    parser = ArgumentParser('Generate TopTen bug page')
    parser.add_argument('file_name')
    args = parser.parse_args()

    try:
        lp = Launchpad.login_with("pypypy", "production", version="devel")
    except:
        print "** ERROR: Could not open LP "
        sys.exit(-1)

    new = HTML.Table(header_row = makeMainHeader(), col_width=["80", "500", "150", "500"])
    in_progress = HTML.Table(header_row = makeMainHeader(), col_width=["80", "500", "150", "500"])
    with open(args.file_name, 'rb') as csvfile:
        bugreader = csv.reader(csvfile, delimiter=':')
        for row in bugreader:
            table, html_row = processBug(row, lp)
            if table == "new":
                new.rows.append(html_row)
            else:
                in_progress.rows.append(html_row)

    htmlFile = 'juju-bugs.html'
    print("Writing html file: %s" % htmlFile)
    f = open(htmlFile, 'w')

    f.write("<title>Juju Top Bugs Report</title>")
    f.write("<h1>Juju Top Bugs Report</h1>")
    f.write("<h2><a href=\"http://reports.vapour.ws/releases/top-issues?_charset_=UTF-8&__formid__=deform&previous_days=7&issue_count=20&update=update\">Top CI Issues</a><h2>")
    f.write("<h2>Stakeholder bugs which need attention</h2>")
    htmlCode = str(new)
    f.write(htmlCode)
    f.write("<p>")
    f.write("<h2>Assigned stakeholder bugs</h2>")
    htmlCode = str(in_progress)
    f.write(htmlCode)
    f.write("<p>")
    f.write("<p>")
    f.write("<hr>")
    timeNow = datetime.now()
    f.write("<i>Last updated: %s</i>" % timeNow)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
