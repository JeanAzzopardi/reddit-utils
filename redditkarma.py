#!/usr/bin/env python

# Reddit karma trending tool
# Copywrite (c) 2009, Mason Larobina <mason.larobina@gmail.com>
# Copywrite (c) 2009, Ilyanep <http://reddit.com/user/ilyanep>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Attributions:
#   mr_dbr <http://reddit.com/user/mr_dbr> for his json code snippet.

'''
R E D D I T  K A R M A . P Y
============================

This script can be used to track, trend, plot, print a users or multiple reddit
users submission and comment karma.


Requires
========

  python 2.5 - 2.6
  simplejson
  gnuplot


Updating
========

Find the latest version of the script here:

  http://github.com/mason-larobina/reddit-utils/tree/master


Get trending
============

1. Tell the script which users you would like to follow with:
  
  redditkarma.py -k mason-l mr_dbr Ilyanep

2. Add this to an hourly/daily/monthly cron to build karma trends

  redditkarma.py -ak

3. After some trends have been built up print some plots:

  redditkarma.py -ap         # plot all users karma trends.
  redditkarma.py -p mason-l  # only plot mason-l's trend data.

4. See the full list of command line options and experiment:

  redditkarma.py -h

5. Contribute!


Issues
======

 - Changing the gnuplot output dimensions only changes the width at the 
   moment.


Wishlist/Todo
=============

 - Allow other graphing types (but what types?).
 - Command line option to perform some statistical analysis on a users
   trending data (most grown in shortest period, number of points, etc).
 - Code could do with some more comments explaining whats happening.
 - Gain a code contributor!

'''

import urllib
import time
import os
import sys
import re
from subprocess import check_call
from optparse import OptionParser

try:
    import json

except ImportError:
    import simplejson as json

# === Global configuration ====================================================

JSON_URL = "http://www.reddit.com/user/%s/about.json"

if 'XDG_DATA_HOME' in os.environ.keys() and os.environ['XDG_DATA_HOME']:
    DATA_DIR = os.path.join(os.environ['XDG_DATA_HOME'], 'reddit-utils/')

else:
    DATA_DIR = os.path.join(os.environ['HOME'], '.local/share/reddit-utils/')

if 'XDG_CACHE_HOME' in os.environ.keys() and os.environ['XDG_CACHE_HOME']:
    CACHE_DIR = os.path.join(os.environ['XDG_CACHE_HOME'], 'reddit-utils/')

else:
    CACHE_DIR = os.path.join(os.environ['HOME'], '.cache/reddit-utils/')

TREND_DIR = os.path.join(DATA_DIR, 'karma-trends/')

for path in [DATA_DIR, CACHE_DIR, TREND_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

PLOT_DIMENSIONS = "1600,900"
PLOT_OUTPUT = "karma-plot.png"
VERBOSE = False
TIME_FMT = "%F %R"
SUMMARY_FMT = "USERNAME(LINK_KARMA, COMMENT_KARMA)\n"
PLOT_ONLY_TOTAL = False
PLOT_FILE = os.path.join(CACHE_DIR, 'karma.p')

GNUPLOT_CONFIG = '''set xlabel "Date"
set ylabel "Karma"
set terminal %s size %r
set output "%s"
set title "%s"
set samples 3000
set xdata time
set format x "%%d-%%b-%%y"
set timefmt "%%s"
plot %s'''

# =============================================================================

_SCRIPTNAME = os.path.basename(sys.argv[0])

def echo(msg):
    '''Print messages to terminal if verbose is on.'''

    if VERBOSE:
        sys.stderr.write("%s: %s\n" % (_SCRIPTNAME, msg))


def get_karma(user):
    '''Saves and returns a users comment and submission karma.'''

    src = urllib.urlopen(JSON_URL % user).read()
    data = json.loads(src)['data']
    echo("retrieved data for %s: %r" % (user, data))
    link_karma, comment_karma = data['link_karma'], data['comment_karma']

    f = open(os.path.join(TREND_DIR, user), 'a')
    f.write('%d\t%d\t%d\n' % (int(time.time()), link_karma, comment_karma))
    f.close()

    return link_karma, comment_karma


def gnuplot_user(users):
    '''Plot a single user or multiple users comment karma submission karma
    and total karma using gnuplot.'''

    if len(users) == 1:
        title = "%s's karma on reddit.com" % users[0]

    else:
        title = "karma comparison (%s)" % ', '.join(users)

    plotfmt = "%r using %s title %r with linespoints"
    plots = [] 
    for user in users:
        plotdata = os.path.join(TREND_DIR, user)
        if not os.path.isfile(plotdata):
            raise Exception("No trending data found for user %r" % user)

        if not PLOT_ONLY_TOTAL:
            plots += [(plotdata, "1:3", "%s comment" % user),
              (plotdata, "1:2", "%s submission" % user)]
        
        plots += [(plotdata, "1:($2+$3)", "%s total" % user)]
            
    plot = ', '.join([plotfmt % t for t in plots])
    
    ext = os.path.splitext(PLOT_OUTPUT)[-1].strip('.').lower()
    plotconf = GNUPLOT_CONFIG % (ext, PLOT_DIMENSIONS,
      PLOT_OUTPUT, title, plot)   

    f = open(PLOT_FILE, 'w')
    f.write(plotconf)
    f.close()
    check_call(['gnuplot', PLOT_FILE])
   

def make_user_summary(user):
    '''Generates a summary string of the current user using the latest trend
    data.'''

    trend = os.path.join(TREND_DIR, user)
    if not os.path.exists(trend):
        echo("no trend data exists for user %r" % user)
        return False

    h = open(trend, 'r')
    (unixtime, link, comm) = h.readlines()[-1].strip().split("\t")
    h.close()
    d = {'LINK_KARMA': link, 'COMMENT_KARMA': comm, 'UNIXTIME': unixtime,
      'DATETIME': time.strftime(TIME_FMT, time.gmtime(int(unixtime))),
      'USERNAME': user}
    
    s = SUMMARY_FMT
    for key in d.keys():
        s = s.replace(key, d[key])

    return s


def get_trended_users():
    '''Return a list of all the users that have trend data in the trending
    directory.'''

    users = []
    for user in os.listdir(TREND_DIR):
        if user.startswith('.'):
            continue

        users.append(user)
    
    return users


def delete_user(user):
    '''Delete a users trend data.'''

    trend = os.path.join(TREND_DIR, user)
    if os.path.exists(trend):
        echo("deleting trend data for %r" % user)
        os.remove(trend)

    else:
        echo("unable to find trend data for user %r" % user)


if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option('-u', '--user', dest='user', action='store',
      help='reddit username.')
    
    parser.add_option('-p', '--plot', dest="plot", action='store_true',
      help="plot karma for user.")

    parser.add_option('-l', '--list', dest="list", action='store_true',
      help="list all trended users.")

    parser.add_option('-a', '--all', dest="all", action='store_true',
      help="include all previously trended users in operation.")
    
    parser.add_option('-x', '--dimensions', dest="dimensions", action="store",
      metavar="WIDTHxHEIGHT", help="specify plot dimensions")
    
    parser.add_option('-d', '--delete', dest='delete', action='store_true',
      help="delete listed users trending data.")
    
    parser.add_option('-o', '--output', dest="output", action="store",
      metavar="FILE", help="output plot to file")

    parser.add_option('-v', '--verbose', dest="verbose", action="store_true",
      help="print lots of extra information")
    
    parser.add_option('-k', '--fetch-karma', dest="fetch", 
      action="store_true", help="update karma trend data for user")

    parser.add_option('-s', '--summary', dest="summary", action="store_true",
      help="print karma summary for user on exit.")

    parser.add_option('-j', '--summary-format', dest='sformat', action="store",
      metavar='FORMAT', help='change the summary output format. '\
        'Example \"DATETIME USERNAME(LINK_KARMA, COMMENT_KARMA) UNIXTIME\"')
    
    parser.add_option('-t', '--summary-time-format', dest='tformat',
      action="store", metavar="FORMAT", help="refer to the date manpage.")

    parser.add_option('-y', '--only-total', dest='onlytotal',
      action="store_true", help="Only plot the total karma. Handy when "\
      "plotting multiple users at once.")

    (options, users) = parser.parse_args()
    
    if options.verbose:
        VERBOSE = True
        echo("setting verbose on.")

    if options.list:
        echo("searching in %r for saved karma trend data" % TREND_DIR)
        users = get_trended_users()
        echo("found %d users" % len(users))
        print " ".join(users)
        sys.exit(0)
    
    if not options.plot and not options.fetch and not options.summary \
      and not options.delete:
        parser.print_help()
        sys.exit(1)

    if options.user:
        echo("user %r" % user)
        users.append(options.user)

    if options.all:
        newusers = get_trended_users()
        echo("picked up %d users: %r" % (len(newusers), newusers))
        users += newusers

    if not len(users):
        parser.print_help()
        sys.exit(1)

    if options.delete:
        for user in users:
            delete_user(user)

        sys.exit(0)

    if options.plot:

        if options.onlytotal:
            echo("will only plot the total karma.")
            PLOT_ONLY_TOTAL = True

        if options.dimensions:
            if re.match("^\d+x\d+$", options.dimensions):
                PLOT_DIMENSIONS = ','.join(options.dimensions.split("x"))
                echo("using dimensions %s" % PLOT_DIMENSIONS)

            else:
                echo("invalid dimensions %r" % options.dimensions)
            
        if options.output:
            PLOT_OUTPUT = options.output
            echo("outputting plot to %r" % PLOT_OUTPUT)

        echo("generating plot")
        gnuplot_user(users)

    if options.fetch:
        for user in users:
            get_karma(user)
    
    if options.plot:
        echo("plotting user(s): %s" % ', '.join(users))
        gnuplot_user(users)
    
    if options.summary:
        if options.sformat:
            fmt = options.sformat
            for (s, g) in [('\\t','\t'), ('\\n', '\n')]:
                fmt = fmt.replace(s, g)

            SUMMARY_FMT = fmt
            echo("changed summary output format to %r" % SUMMARY_FMT)

        if options.tformat:
            SUMMARY_FMT = options.tformat
            echo("changed summary time format to %r" % SUMMARY_FMT)
        
        lastline = None
        for user in users:
            summary = make_user_summary(user)
            if summary:
                print summary,
                lastline = summary
        
        if summary and summary[-1] != "\n":
            print

