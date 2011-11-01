#!/usr/bin/python3
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
"""Klassen zum Arbeiten mit Trac

@author: Markus Tacker <m@tacker.org>"""

import re
import urllib.request
from xml.dom.minidom import parse, parseString
from minidomutil import domGetText

def maskWikiPageNames(*strings):
    ret = []
    for string in strings:
        if string == None:
            continue
        if not re.match('^[a-z]', string):
            string = re.sub('([A-Z][a-z]+[A-Z][a-z]+)', "!\\1", str(string))
        ret.append(string)
    return ret[0] if len(ret) == 1 else tuple(ret)

class TracTicket(object):
    
    instance = {}
    dependencies = {}
    
    def factory(id, server):
        id = int(id)
        if id not in TracTicket.instance:
            TracTicket.instance[id] = __class__(id, server)
        return TracTicket.instance[id]
    
    def __init__(self, id, server):
        "Erzeugt ein neues Ticket-Object"
        self._id = int(id)
        self._server = server
        self._dependants = {}
        self._dependencies = {}
        self._attags = {}
        self.load()
        
    def load(self):
        "Lädt die Ticket-Daten via RPC"
        ticket = self._server.ticket.get(self._id)
        self._time_created = ticket[1]
        self._time_changed = ticket[2]
        self._attributes   = ticket[3]
        
        # Load dependencies
        rd = re.compile("(@depends (#[0-9]+,? ?)+)")
        rt = re.compile("#([0-9]+)")
        dmatch = rd.search(self.description)
        if dmatch:
            tmatch = rt.findall(dmatch.groups()[0])
            for ticket_id in tmatch:   
                ticket_id = int(ticket_id)             
                if ticket_id == self.id:
                    sys.stderr.write("Self reference in ticket #%d.\n" % ticket_id);
                    continue
                if ticket_id in TracTicket.dependencies and TracTicket.dependencies[ticket_id] == self.id:
                    raise Exception("Detected dependency recursion in tickets #%d and #%d" % (self.id, ticket_id))
                TracTicket.dependencies[self.id] = ticket_id 
                dticket = self.__class__.factory(ticket_id, self._server)
                dticket.addDependant(self)
                self.addDependency(dticket)      
        
    def getId(self):
        return self._id
    
    def getSummary(self):
        return self._attributes['summary']
    
    def getDescription(self):
        return self._attributes['description']
    
    def getDependencies(self):
        "Gibt die Liste mit Tickets zurück, von denen dieses Ticket abhängt"
        return self._dependencies.keys()
    
    def hasDependencies(self):
        return len(self._dependencies.keys()) > 0
    
    def addDependency(self, ticket):
        self._dependencies[ticket] = True

    def addDependant(self, ticket):
        self._dependants[ticket] = True
    
    def getDependants(self):
        "Gibt die Liste mit Tickets zurück, die von diesem Ticket abhängen"
        return self._dependants.keys()
    
    def getAtTag(self, tagname):
        "Gibt den Text hinter dem Tag mit dem Namen tagname zurück"
        if tagname not in self._attags:
            rs = re.compile('@%s (.+)' % tagname)
            match = rs.findall(self.description)
            self._attags[tagname] = match[0] if len(match) == 1 else match if match else None;
        return self._attags[tagname]
    
    def getStart(self):
        "Gibt das Start-Datum (@start) des Tickets zurück"
        return self.getAtTag('start')
        
    def getEnd(self):
        "Gibt das End-Datum (@end) des Tickets zurück"
        return self.getAtTag('end')
    
    def getOwner(self):
        "Gibt den Besitzer des Tickets zurück"
        return self._attributes['owner']
    
    def getCC(self):
        "Gibt die CC-Einträge des Tickets zurück"
        return self._attributes['cc']
    
    def getStatus(self):
        "Gibt den Status des Tickets zurück"
        return self._attributes['status']
    
    def getMilestone(self):
        "Gibt den Meilenstein des Tickets zurück"
        return self._attributes['milestone']
    
    def getKeywords(self):
        "Gibt die Keywords des Tickets zurück"
        return self._attributes['keywords']
    
    def __repr__(self):
        sum = self.summary 
        if self._attributes['status'] == "closed":
            sum = '~~' + sum + '~~'
        return "#%d (%s) %s" % (self.id, self._attributes['type'], sum)
        
    id = property(getId)
    summary = property(getSummary)
    description = property(getDescription)
    start = property(getStart)
    end = property(getEnd)
    owner = property(getOwner)
    cc = property(getCC)
    status = property(getStatus)
    milestone = property(getMilestone)
    keywords = property(getKeywords)
    
class TracTicketComments(object):
    "Lädt die Kommentare eines Tickets via RSS"
    
    def __init__(self, ticket, url, realm):
        m = re.match('(https?://)([^:]+):([^@]+)@(.+)', url)
        if m == None:
            raise Exception("Failed to match username and password from url")
        proto, username, password, path = m.groups()
        
        auth_handler = urllib.request.HTTPBasicAuthHandler()
        auth_handler.add_password(realm=realm,uri=proto + path,user=username,passwd=password)
        opener = urllib.request.build_opener(auth_handler)
        urllib.request.install_opener(opener)
        
        ticket_feed_xml = urllib.request.urlopen(proto + path + ("ticket/%d?format=rss" % ticket.id))
        
        dom = parseString(ticket_feed_xml.read())
        self._comments = []
        for item in dom.getElementsByTagName('item'):
            comment = {};
            for child in item.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    continue
                comment[child.nodeName] = domGetText(child)
            self._comments.append(comment)
        
    def getComments(self):
        return self._comments
        
