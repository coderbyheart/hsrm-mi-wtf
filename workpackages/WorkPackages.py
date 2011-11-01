#!/usr/bin/python3
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
"""Script zum Pflegen einer Wiki-Seite mit WorkPackages in Trac

@author: Markus Tacker <m@tacker.org>"""

import xmlrpc.client
import sys
import os.path
import re
import io
import csv
import configparser
import locale
from Trac import TracTicket, TracTicketComments
from datetime import date

locale.setlocale(locale.LC_ALL, 'de_DE.utf8')

wptypes = ['Aktive', 'Ausstehende', 'Erledigte']
wpstati = {None: 'gruen', 'grün': 'gruen', 'rot': 'rot', 'gelb': 'gelb'}

def formatDate(dateStr):
    dateStr = dateStr.strip()
    try:
        year = dateStr[0:4]
        month = dateStr[5:7]
        day = dateStr[8:10]
        d = date(int(year), int(month), int(day))
    except ValueError:
        sys.stderr.write("Ungültiges Datum: %s-%s-%s\n" % (year, month, day))
        return "?"
    return d.strftime("%d. %B %Y")

if __name__ == "__main__":

    ini_file = os.path.realpath(os.path.dirname(sys.argv[0]) + os.sep + 'trac.ini')
    config = configparser.SafeConfigParser()
    config.add_section('trac')
    config.set('trac', 'url', '')
    if os.path.isfile(ini_file):
        config.read(ini_file)
        
    if config.get('trac', 'url') == '' and len(sys.argv) < 2:
        sys.stderr.write("Missing arguments.\n")
        sys.stderr.write("Usage: %s <trac url>\n" % sys.argv[0])
        sys.exit(1)
        
    if len(sys.argv) > 1:
        config.set('trac', 'url', sys.argv[1])
    
    short = True if len([arg for arg in sys.argv if arg == 'short']) == 1 else False
    long = False if short else True

    trac_url = config.get('trac', 'url')
    if trac_url[-1] != "/":
        trac_url += "/"
    
    server = xmlrpc.client.ServerProxy("%slogin/xmlrpc" % trac_url)
    
    out = io.StringIO()
    if long:
        out.write(open(os.path.dirname(sys.argv[0]) + os.sep + "WorkPackages.wiki", encoding='utf-8').read())
    
    # Lade DevTeam
    team = {}
    DevTeam = server.wiki.getPage('DevTeam')
    devre = re.compile('^ \* .+([a-z]{5}[0-9]{3})')
    for line in DevTeam.split("\n"):
        match = devre.search(line)
        if match:
            id = match.groups()[0]
            team[id] = re.sub('[^\w]', '', line[3:].replace(id, '').strip())
    
    # Liste alle Workpackages
    workpackages = {wptypes[0]: [], wptypes[1]: [], wptypes[2]: []}
    search = "type=workpackage&resolution!=invalid&order=summary"
    if short:
        search = search + "&keywords!~=WorkPackagesPLIgnore"
    for ticket_id in server.ticket.query(search):
        workpackage = TracTicket.factory(ticket_id, server)
        
        if workpackage.status in ['accepted', 'assigned', 'reopened']:
            workpackages[wptypes[0]].append(workpackage)
        elif workpackage.status == 'new':
            workpackages[wptypes[1]].append(workpackage)
        elif workpackage.status == 'closed':
            workpackages[wptypes[2]].append(workpackage)
            
    for type in wptypes:
        out.write("= %s !WorkPackages =\n" % type)
        for workpackage in sorted(workpackages[type], key=lambda wp: wp.start):
            if short:
                out.write("== %s ==\n" % (workpackage.summary))
            else:
                out.write("== [ticket:%d %s] ==\n" % (workpackage.id, workpackage.summary))
            status = workpackage.getAtTag('status')
            if status in wpstati:
                out.write("[[Image(source:/2011swtpro01/Project/Wochenberichte/ampel-%s-150.png, 25, left, margin-right=10)]]\n" % wpstati[status])
            out.write("Start: %s[[BR]]\n" % (formatDate(workpackage.start) if workpackage.start else "-"))
            out.write("Ende: %s[[BR]]\n" % (formatDate(workpackage.end) if workpackage.end else "-"))
            out.write("Team: %s[[BR]]\n" % ', '. join(["'''%s'''" % team[workpackage.owner]] + [team[cc.strip()] for cc in workpackage.cc.split(',') if cc.strip() in team]))
            if long:
                out.write("Keyword: [query:keywords~=workpackage-%03d workpackage-%03d]\n" % (workpackage.id, workpackage.id))
            out.write("[[BR]][[BR]]\n")
            
            # Beschreibung
            out.write("\n** Beschreibung **\n\n")
            for line in workpackage.description.split("\n"):
                skip = False
                for _ in ['@status', '@start', '@end', '@task', '@depends']:
                    if _ in line:
                        skip = True
                        continue
                if skip:
                    continue
                out.write(line + "\n")
            out.write("\n")
            
            # Tasks
            if not "WorkPackagesNoTask" in workpackage.keywords:
                tasksDef = workpackage.getAtTag('task')
                if tasksDef == None:
                    tasksDef = []
                if isinstance(tasksDef, str):
                    tasksDef = [tasksDef]
                tasks = {}
                for t in tasksDef:
                    t = t.split(" ")
                    tasks[t[0]] = ' '.join(t[1::])
                noTask = "//[WorkPackages/OhneTask Keine Rückmeldung.]//"
                out.write("\n** Aufgaben **\n\n")
                out.write("||**Person**||**Aufgabe**||\n")
                out.write("||%s||%s||\n" % (team[workpackage.owner], tasks[workpackage.owner] if workpackage.owner in tasks else noTask))
                ccs = workpackage.cc.strip()
                if len(ccs) > 0:
                    for cc in workpackage.cc.split(','):
                        cc = cc.strip()
                        try:
                            out.write("||%s||%s||\n" % (team[cc], tasks[cc] if cc in tasks else noTask))
                        except KeyError:
                            sys.stderr.write("Unbekannter Mitarbeiter %s im CC-Feld von Ticket #%d\n" % (cc, workpackage.id)) 
                out.write("\n")
            
            if long:
                out.write("\n**Tickets** (Neues Ticket: ")
                out.write("[[/newticket?keywords=workpackage-%03d&component=Client&milestone=%s&owner=rvowe001&cc=jhach001, kirrg001, lfroe001, aknob001|Client]]" % (workpackage.id, workpackage.milestone))
                out.write(" | ")
                out.write("[[/newticket?keywords=workpackage-%03d&component=Server&milestone=%s&owner=llieb001&cc=jstau001, sfran001, shess002, tster001|Server]]" % (workpackage.id, workpackage.milestone))
                out.write(")\n\n")
                out.write("**Features**\n\n")
                out.write("[[TicketQuery(keywords~=workpackage-%03d&order=priority&type=feature)]]\n" % workpackage.id)
                out.write("**Offene Tickets**\n\n")
                out.write("[[TicketQuery(keywords~=workpackage-%03d&order=priority&group=type&type=!feature&status=new|assigned|reopened)]]\n" % workpackage.id)
                out.write("**Erledigte Tickets**\n\n")
                out.write("[[TicketQuery(keywords~=workpackage-%03d&order=priority&group=type&type=!feature&status!=new|assigned|reopened)]]\n" % workpackage.id)
            
            ticketComments = TracTicketComments(workpackage, trac_url, 'trac account 2011swtpro01').getComments()
            hasProto = False
            if short:
                ticketComments = [comment for comment in ticketComments if comment['dc:creator'] == 'mtack001']    
            for comment in ticketComments:
                if 'description changed' in comment['title']:
                    continue
                if ' changed' in comment['title']:
                    continue
                if ' set' in comment['title']:
                    continue
                if 'owner' in comment['description']:
                    continue
                if '<strong>cc</strong>' in comment['description']:
                    continue
                if len(comment['description'].strip()) == 0:
                    continue
                if not hasProto:
                    out.write("**Besondere Vorkommnisse**\n\n")
                    hasProto = True
                if long:
                    out.write("//[%s] %s: // [[BR]]\n" % (comment['pubDate'], team[comment['dc:creator']]))
                out.write("{{{\n#!html\n%s\n}}}\n" % comment['description'])
            out.write("----\n")
    try:
        server.wiki.putPage('WorkPackages' if long else 'WorkPackages/Short', out.getvalue(), {'comment': 'Automatically updated by cron.'})

    except xmlrpc.client.Fault as e:
       if e.faultString != "'Page not modified' while executing 'wiki.putPage()'":
            raise e
