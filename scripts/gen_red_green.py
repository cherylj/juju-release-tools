#!/usr/bin/python
import sys
import os
import csv
import re
import HTML
import time
import collections
import yaml

from optparse import OptionParser
from argparse import ArgumentParser
from launchpadlib.launchpad import Launchpad
from pprint import pprint
from datetime import datetime, timedelta
from natsort import natsorted

# workItemsDelta is the number of days past the target milestone date that
# a particular work items is due.
workItemsDelta = {
    'feature one-pager approved': 0,
    'design spec': 0,
    'implementation': 0,
    'demo': 0,
    'ci tests': 14,
    'release notes': 0,
    'stakeholder signoff': 7,
    'documentation draft': 14,
    'documentation complete': 21}

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
    'Documentation Complete']

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

def getStatusColor(strings, itemName, milestone):
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
        # There was no date specified inline, use the date from 
        # the milestone plus the offset.
        targetDate = milestone.date_targeted + timedelta(days=workItemsDelta[itemName])
    else:
        try:
            targetDate = datetime.strptime(dateStr, "%d/%m/%Y")
        except Exception as e:
             print("Getting target date threw exception: %s" % e)

    return getDateStatus(targetDate, status)
        

def addFeature(spec, row_map, seriesName):
    if spec.milestone:
        milestone = spec.milestone
    else:
        print("Unable to find milestone for spec: %s (link: %s)" % (spec.title, spec.web_link))
        return

    html_row = []
    html_row.append(HTML.TableCell("<a href=\"%s\">%s</a>" % (spec.web_link, spec.title)))
    if spec.assignee:
        html_row.append(HTML.TableCell("<center>%s</center>" % spec.assignee.display_name))
    else:
        html_row.append(HTML.TableCell(""))


    html_row.append(HTML.TableCell("<center>%s</center>" % milestone.name))

    work_items = spec.workitems_text
    items = work_items.split("\n")

    #skip first header
    items = items[1:]
    i = 0
    for item in items:
        strings = item.lower().split(":")
        if len(strings) != 2:
            print("ERROR formatting feature: %s (link: %s)" % (spec.title, spec.web_link))
            return

        task, ok = correctTask(strings[0], i)
        if not ok:
            print("ERROR formatting feature: %s (link: %s)" % (spec.title, spec.web_link))
            return
        try:
            color = getStatusColor(strings, task, milestone)
        except Exception as e:
            print("Error reading status for task: %s, for %s" % (expectedWorkItems[i], spec.title))
            print("string was: %s" % strings[0])
            print("exception was: %s" % e)
            return

        html_row.append(HTML.TableCell("", bgcolor=color))
        i = i + 1

    features = row_map.get(milestone.name, [])
    features.append(html_row)
    row_map[milestone.name] = features

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

def writeSchedule(f, trunk):

    milestones = trunk.all_milestones
    releases = {}
    for ms in milestones:
        releases[ms.date_targeted] = ms.name

    # sort by target date
    keys = releases.keys()
    sorted_keys = sorted(keys)

    release_table = []
    for k in sorted_keys:
       release_table.append([k.strftime("%Y-%m-%d"), releases[k]])

    t = HTML.table(release_table, header_row=[HTML.TableCell("<b><center>Date</center</b>", bgcolor="DarkGray"), HTML.TableCell("<b><center>Milestone</center</b>", bgcolor="DarkGray")], 
        col_width=['200', '600'], col_align=['center', 'left'])
        
    f.write(t)
    f.write("<p>")


def writeSeriesFile(seriesName, series, trunk):
    filename = "juju-features-%s.html" % seriesName
    print("writing to filename: %s" % filename)
    f = open(filename, 'w')
    t = HTML.Table(header_row = makeMainHeader(), col_width=["300", "200", "100", "90", "90", "90", "90", "90", "90", "90", "90", "90"])

    # make an ordered map of releases so we can print the blueprints out
    # in order of target milestone.
    release_map = collections.OrderedDict()

    specs = series.all_specifications
    for spec in specs:
        addFeature(spec, release_map, seriesName)

    # Sort the release_map by milestone
    keys = release_map.keys()
    sorted_keys = natsorted(keys)
    sorted_map = collections.OrderedDict()
    for k in sorted_keys:
        sorted_map[k] = release_map[k]

    for rows in sorted_map.values():
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
    writeSchedule(f, trunk)
    f.write("<hr>")
    timeNow = datetime.now()
    f.write("<i>Last updated: %s</i>" % timeNow)

def main(args):
    parser = ArgumentParser("Generate red / green chart for release tracking")
    parser.add_argument('series')
    args = parser.parse_args()

    series = args.series

    try:
        lp = Launchpad.login_with("pypypy", "production", version="devel")
    except:
        print "** ERROR: Could not open LP "
        sys.exit(1)

    try:
        project = lp.projects["juju-core"]
    except KeyError:
        print "** ERROR: Project name does not exist: juju-core"
        sys.exit(1)

    # We need to find both the trunk and the specified series
    found = False
    lpSeries = project.series
    for ls in lpSeries:
        if ls.name == "trunk":
            trunk = ls
        if ls.name == series:
            repSeries = ls
            found = True


    if not found:
        print "** ERROR: Unable to find series: %s" % series
        sys.exit(1)

    writeSeriesFile(series, repSeries, trunk)
            


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
