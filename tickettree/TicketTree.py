#!/usr/bin/python3
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
"""Script zum Erzeugen eines Ticket-Baums auf einer Wiki-Seite

@author: Markus Tacker <m@tacker.org>"""

import xmlrpc.client
import sys
import os.path
import re
import io
from Trac import TracTicket

class TreeTracTicket(TracTicket):

    def factory(id, server):
        id = int(id)
        if id not in TracTicket.instance:
            TracTicket.instance[id] = __class__(id, server)
        return TracTicket.instance[id]

    def __init__(self, id, server):
        "Erzeugt ein neues Ticket-Object"
        super().__init__(id, server)
        TicketTree.tickets.append(self)

class TicketTree(object):
    
    _components = [('Client', 'Client'), ('Server', 'Server'), ('Alle', None)]

    tickets = []
    
    def __init__(self, trac_url, wiki_page = None):
        self._trac_url = trac_url
        self._wiki_page = "TicketTree" if wiki_page == None else wiki_page
        self.loadTickets()
        
    def loadTickets(self):
        server = xmlrpc.client.ServerProxy("%slogin/xmlrpc" % trac_url)
        out = io.StringIO()
        # Load template
        query = "type!=feedback|workpackage&order=priority&status=new|assigned|reopened"
        out.write(open(os.path.dirname(sys.argv[0]) + os.sep + "TicketTree.wiki", encoding='utf-8').read() % query)
        
        for _ in self._components:
            title, component = _
            out.write("=== %s ===\n\n" % title)
            cquery = query
            if component is not None:
                cquery += "&component=%s" % component
            out.write("[query:%s Query]\n\n" % cquery) 
            ticket_list = server.ticket.query(cquery)
            TreeTracTicket.tickets = []
            TracTicket.instance = {}
            for ticket_id in ticket_list:
                TreeTracTicket.factory(ticket_id, server)
                
            # Build tree
            for ticket in TicketTree.tickets:
                if ticket.hasDependencies():
                    continue
                out.write(" * %s\n" % ticket)
                self.createTree(out, ticket.getDependants(), 1)
            out.write("\n")
                
        # Push wiki page
        try:
            server.wiki.putPage(self._wiki_page, out.getvalue(), {'comment': "Replaced from console."})
        except xmlrpc.client.Fault as e:
           if e.faultString != "'Page not modified' while executing 'wiki.putPage()'":
                raise e
        out.close() 
        
    def createTree(self, out, tickets, level):
        for ticket in tickets:
            out.write("  " * level)
            out.write(" * %s\n" % ticket)
            deps = ticket.getDependants()
            if len(deps) > 0:
                self.createTree(out, deps, level + 1)
        
if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        sys.stderr.write("Missing arguments.\n")
        sys.stderr.write("Usage: %s <trac url> [wiki page]>\n" % sys.argv[0])
        sys.exit(1)

    trac_url = sys.argv[1]
    if trac_url[-1] != "/":
        trac_url += "/"
    if len(sys.argv) == 3:
        wiki_page = sys.argv[2]
        if wiki_page[-1] == "/":
            wiki_pag
            e = wiki_page[0:-1]
        if wiki_page[0] == "/":
            wiki_page = wiki_page[1:]
    else:
        wiki_page = None
        
    TicketTree(trac_url, wiki_page)
