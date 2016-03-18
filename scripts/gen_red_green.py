#!/usr/bin/python
import sys
import os
import csv
import re
import HTML
import time
import collections

from optparse import OptionParser
from launchpadlib.launchpad import Launchpad
from pprint import pprint
from datetime import datetime

reportedSeries = ["2.0"]
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
    'Milestone',
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

milestoneDates = {
    "2.0": [
        "16/2/2016",
        "16/2/2016",
        "16/2/2016",
        "16/2/2016",
        "21/3/2016",
        "16/2/2016",
        "21/3/2016",
        "25/3/2016",
        "14/4/2016"]}

developmentDates = {
    "1.26-alpha2": "1/12/2015",
    "1.26-alpha3": "16/12/2015",
    "2.0-alpha1": "12/1/2016",
    "2.0-alpha2": "9/2/2016",
    "2.0-beta1": "16/2/2016",
    "2.0-beta2": "10/3/2016",
    "2.0-beta3": "21/3/2016",
    "2.0-beta4": "7/4/2016"}

releaseTablesDict = {
    "2.0": [
        ["15-Dec-2015", "<b>1.26 Alpha 3 code cut off</b>\
<p><i>This release is called 1.26-alpha3, as the command and rename changes that characterize the 2.0 release will not be ready in time, but \
additional stakeholder requested features are ready for testing.</i>"],
        ["<i>22-Dec-2015</i>", "<i>Holiday Break</i>"],
        ["<i>29-Dec-2015</i>", "<i>Holiday Break</i>"],
        ["12-Jan-2016", "<b>Alpha 1 code cut off</b>"],
        ["9-Feb-2016", "<b>Alpha 2 code cut off</b>"],
        ["16-Feb-2016", '<b>Beta 1 code cut off</b>\
<list>\
<li>Feature Freeze (Except <a href="https://bugs.launchpad.net/ubuntu/+source/juju-core/+bug/1545913">FFe items</a>)</li>\
<li>All release notes complete</li>\
</list>'],
        ["10-Mar-2016", "<b>Beta 2 code cut off</b>"],
        ["21-Mar-2016", '<b>Beta 3 code cut off</b>\
<list>\
<li>Target release date:  24-Mar-2016</li>\
<li>Feature freeze for <a href="https://bugs.launchpad.net/ubuntu/+source/juju-core/+bug/1545913">FFe items</a></li>\
<li>Feature buddy signoff complete</li>\
<li>CI tests complete</li>\
</list>'],
        ["25-Mar-2016", "<b>Documentation Complete</b>"],
        ["4-Apr-2016", "<b>Beta 4 code cut off</b>\
<list>\
<li>Target release date:  7-Apr-2016</li>\
<li>Bugfix only</li>\
</list>"],
        ["11-Apr-2016", "<b>2.0.0 Release code cut off</b>\
<list>\
<li>Target release date:  14-Apr-2016 (for inclusion in Xenial)</li>\
<li>Critical Bugfix only</li>\
</list>"],
        ["21-Apr-2016", "<b>Xenial Xerus released(with Juju 2.0.0)</b>"], ] }


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

def getDate(string):
    strings = string.split("(")
    if len(strings) != 2:
        raise Exception("invalid format")
    strings = strings[1].split(")")
    if len(strings) != 2:
        raise Exception("invalid format")
    return strings[0]

def getDateStatus(date, status):
    today = datetime.now()
    if today > date:
        return color_dict['overdue']

    delta = date - today
    if delta.days < 5:
        return color_dict['near deadline']

    return color_dict[status]

def getStatusColor(strings, seriesName, itemIndex, milestone):
    # Is this done or NA?
    if isNATask(strings[0]):
        return color_dict['n/a']

    status = strings[1].strip()
    if not validStatus(status):
        print("Not a valid status: %s" % status)
        raise Exception("Invalid status: %s" %status)
    if status == 'done' or status == 'postponed':
        return color_dict[status]

    dateStr = getDate(strings[0])
    if dateStr == "":
        #If this is a development task, use the milestone
        if itemIndex < 4 or itemIndex == 5:
            dateStr = developmentDates[milestone]
        else:
            dateStr = milestoneDates[seriesName][itemIndex]

    try:
        targetDate = datetime.strptime(dateStr, "%d/%m/%Y")
    except Exception as e:
        print("Getting target date threw exception: %s" % e)
    return getDateStatus(targetDate, status)
        

def addFeature(spec, row_map, seriesName):
    html_row = []
    html_row.append(HTML.TableCell("<a href=\"%s\">%s</a>" % (spec.web_link, spec.title)))
    if spec.assignee:
        html_row.append(HTML.TableCell("<center>%s</center>" % spec.assignee.display_name))
    else:
        html_row.append(HTML.TableCell(""))

    milestone = "2.0-beta1"
    if spec.milestone:
        milestone = spec.milestone.name
    html_row.append(HTML.TableCell("<center>%s</center>" % milestone))

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
        try:
            color = getStatusColor(strings, seriesName, i, milestone)
        except:
            print("Error reading status for task: %s, for %s" % (expectedWorkItems[i], spec.title))
            print("string was: %s" % strings[0])
            return

        #print("TASK: %s ---- STATUS: %s" % (expectedWorkItems[i], strings[1]))
        html_row.append(HTML.TableCell("", bgcolor=color))
        i = i + 1
    row_map[milestone].append(html_row)

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

def writeSchedule(f, seriesName):
    release_table = releaseTablesDict[seriesName]
    htmlcode = HTML.table(release_table, header_row=[HTML.TableCell("<b><center>Date</center</b>", bgcolor="DarkGray"), HTML.TableCell("<b><center>Milestone</center</b>", bgcolor="DarkGray")], 
        col_width=['200', '600'], col_align=['center', 'left'])
    f.write(htmlcode)
    f.write("<p>")

def writeSeriesFile(seriesName, series):
    htmlFile = 'juju-features-20.html'
    print("Writing html file: %s" % htmlFile)
    f = open(htmlFile, 'w')
    t = HTML.Table(header_row = makeMainHeader(), col_width=["300", "200", "100", "90", "90", "90", "90", "90", "90", "90", "90", "90"])

    release_map20 = collections.OrderedDict()
    release_map20["1.26-alpha2"] = []
    release_map20["1.26-alpha3"] = []
    release_map20["2.0-alpha1"] = []
    release_map20["2.0-alpha2"] = []
    release_map20["2.0-beta1"] = []
    release_map20["2.0-beta2"] = []
    release_map20["2.0-beta3"] = []
    release_map20["2.0-beta4"] = []
    release_map20["2.0-beta5"] = []

    specs = series.all_specifications
    for spec in specs:
        addFeature(spec, release_map20, seriesName)

    for rows in release_map20.values():
        for html_row in rows:
            t.rows.append(html_row)

    htmlCode = str(t)
    f.write("<title>Juju %s Feature Tracker</title>" % seriesName)
    f.write("<h1>Juju %s Feature Tracker</h1>" % seriesName)
    f.write("<h2>All dates and features are subject to change and do not represent a committment from the Juju Core team.</h2>")
    f.write("<a href=\"https://docs.google.com/document/d/1D4hOenHkJN5HG-bnjJOJjjjuW1xMQfPmWhNtq76m4H4/edit#heading=h.2o2sucn297cp\">Information on how to track features</a><p>")
    f.write(htmlCode)
    f.write("<p>")
    f.write(genKey())
    f.write("<p>")
    f.write("<h2>Juju %s Release Schedule</h2>" % seriesName)
    f.write("<i>All dates are code cut-off dates.  Releases will appear in streams a few days after the cutoff.</i><p>")
    writeSchedule(f, seriesName)
    f.write("<hr>")
    timeNow = datetime.now()
    f.write("<i>Last updated: %s</i>" % timeNow)

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

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
