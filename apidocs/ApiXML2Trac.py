#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
'''Konvertiert die Schnittstellendefinition (XML) in eine Trac-Wiki-Seite

@author Markus Tacker <m@tacker.org>'''

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

class BaseType(object):
    'Basisklasse für alle Typen'
    todo = False

class SimpleType(BaseType):
    'Definiert einene einfachen Datentypen'
    def __repr__(self):
        return 'SimpleType(%s)' % self.identifier

class IntegerType(SimpleType):
    'Definiert einen Integer'
    identifier = 'Integer'

class StringType(SimpleType):
    'Definiert einen String'
    identifier = 'String'

class BooleanType(SimpleType):
    'Definiert einen Boolean'
    identifier = 'Boolean'

class FloatType(SimpleType):
    'Definiert einen Float'
    identifier = 'Float'

class DateTimeType(StringType):
    'Definiert ein Datum'
    identifier = 'DateTime'

class BinaryType(SimpleType):
    'Definiert Binärdaten'
    identifier = 'binary'
    
class DictionaryType(SimpleType):
    'Definiert Dictionaries'
    identifier = 'Dictionary'

class ObjectType(SimpleType):
    'Definiert Objekte'
    identifier = 'Object'
    
class EnumTypeException(Exception):
    'Exception für die Klasse EnumType'
    
class EnumType(BaseType):
    'Definiert Enums'
    def __init__(self, identifier):
        self.identifier = identifier
        self.values = {}
        
    def addValue(self, key, description):
        if key in self.values:
            raise EnumTypeException("Value %s already defined" % key)
        self.values[key] = description

class ComplexType(BaseType):
    'Definiert einen komplexten Typen'
    def __init__(self, type, identifier):
        if type not in ('Object', 'Dictionary'):
            raise ComplexTypeException('A complex type must be either Object or Dictionary')
        self.isobject = type == 'Object'
        self.identifier = identifier

    def __repr__(self):
        return 'ComplexType(%s)' % self.identifier
    
    @property
    def properties(self):
        return self._properties
    
    @properties.setter
    def properties(self, props):
        if len(props) == 0:
            raise ComplexTypeException('Properties must not be empty')
        self._properties = props

class ComplexTypeException(Exception):
    'Exception für die Klasse Property'

class Property(object):
    'Definiert eine Property'
    
    islist = False
    isoptional = False
    isproperty = False
    example = '-'
    
    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return 'Property(%s)' % self.identifier
    
class ActionGroup(object):
    'Definiert eine Gruppe von Actions, was einem Namespace entspricht'
    todo = False
    def __init__(self, identifier):
        self.identifier = identifier
        
class Action(object):
    'Definiert eine Action'
    todo = False
    def __init__(self, identifier, group):
        self.identifier = identifier
        self.group = group
        
class SchnittstellenXMLException(Exception):
    'Exception für SchnittstellenXML'

class SchnittstellenXML(object):
    'Repräsentiert die Schnittstellendefinition, die in einer XML-Datei abgelegt ist.'

    def __init__(self, xmlfile):
        self.dom = parse(xmlfile)
        
        # Erzeugt ein Dictionary mit Typedefinitionen
        self.types = {}
        for item in self.dom.getElementsByTagName('simpletype'):
            self.createSimpleType(item)
            
        for item in self.dom.getElementsByTagName('enum'):
            self.createEnumType(item)

        for item in self.dom.getElementsByTagName('complextype'):
            self.createComplexType(item)

    def createSimpleType(self, item):
        'Erzeugt aus einem XML Element einen einfachen Datentypen'
        t = item.getAttribute('name')
        if t == 'String':
            type = StringType()
        elif t == 'Float':
            type = FloatType()
        elif t == 'Integer':
            type = IntegerType()
        elif t == 'DateTime':
            type = DateTimeType()
        elif t == 'Boolean':
            type = BooleanType()
        elif t == 'binary':
            type = BinaryType()
        else:
            raise SchnittstellenXMLException('Unknown type: %s' % t)
        if type.identifier in self.types:
            raise SchnittstellenXMLException('Already defined: %s' % type.identifier)
        self.types[type.identifier] = type
        type.description = domGetText(item.getElementsByTagName('description')[0])
        type.example = domGetText(item.getElementsByTagName('example')[0])
        todo = item.getElementsByTagName('todo')
        if len(todo) > 0:
            type.todo = domGetText(todo[0])
            
    def createEnumType(self, item):
        'Erzeugt aus einem XML Element einen Enum'
        type = EnumType(item.getAttribute('name'))
        if type.identifier in self.types:
            raise SchnittstellenXMLException('Already defined: %s' % type.identifier)
        self.types[type.identifier] = type
        type.description = domGetText(item.getElementsByTagName('description')[0])
        type.example = domGetText(item.getElementsByTagName('example')[0])
        todo = item.getElementsByTagName('todo')
        if len(todo) > 0:
            type.todo = domGetText(todo[0])
        items = item.getElementsByTagName('items')[0]
        for item in items.getElementsByTagName('item'):
            type.addValue(item.getAttribute('value'), domGetText(item.getElementsByTagName('description')[0]))

    def createComplexType(self, item):
        'Erzeugt aus einem XML Element einen komplexten Datentypen'
        type = ComplexType(item.getAttribute('type'), item.getAttribute('name'))
        if type.identifier in self.types:
            raise SchnittstellenXMLException('Already defined: %s' % type.identifier)
        self.types[type.identifier] = type
        type.description = domGetText(item.getElementsByTagName('description')[0])
        todo = item.getElementsByTagName('todo')
        if len(todo) > 0:
            type.todo = domGetText(todo[0])
        type.properties = self.getProperties(item)

    def getProperties(self, item):
        'Erzeugt aus einem XML Element ein Dictionary mit Properties'
        props = {}
        for p in item.getElementsByTagName('property'):
            prop = self.getProperty(p)
            if prop.identifier in props:
                raise SchnittstellenXMLException("Property already defined: %s\n%s" % (prop.identifier, item.toxml()))
            props[prop.identifier] = prop
        return props

    def getProperty(self, item):
        'Erzeugt aus einem XML Element eine Property'
        property = Property(item.getAttribute('name'))
        property.type = self.types[item.getAttribute('type')]
        property.description = item.getAttribute('description')
        multiple = item.getAttribute('multiple')
        if multiple == "true":
            property.islist = True
        optional = item.getAttribute('optional')
        if optional == "true":
            property.isoptional = True
        example = item.getElementsByTagName('example')
        if len(example) > 0:
            property.example = domGetText(example[0])
        else:
            # Standardbeispiel des Basis-Typen nehmen
            if not isinstance(property.type, ComplexType):
                property.example = property.type.example
        todo = item.getElementsByTagName('todo')
        if len(todo) > 0:
            property.todo = domGetText(todo[0])
        return property
    
    def getGroupedActions(self):
        'Erzeugt ein Dictionary mit den gruppierten Actions'
        self._groupedActions = {}
        for ag in self.dom.getElementsByTagName('group'):
            actionGroup = ActionGroup(ag.getAttribute('name'))
            actionGroup.description = domGetText(ag.getElementsByTagName('description')[0])
            todo = ag.getElementsByTagName('todo')
            if len(todo) > 0:
                actionGroup.todo = domGetText(todo[0])
            actionGroup.actions = self.getActions(actionGroup, ag)
            if actionGroup.identifier in self._groupedActions:
                raise SchnittstellenXMLException("Action group already defined: %s\n%s" % (actionGroup.identifier, item.toxml()))
            self._groupedActions[actionGroup.identifier] = actionGroup
        return self._groupedActions
    
    def getActions(self, group, item):
        'Erzeugt ein Dictionary mit den Actions, die in item definiert sind'
        actions = {}
        for actionItem in item.getElementsByTagName('action'):
            action = Action(actionItem.getAttribute('name'), group)
            action.description = domGetText(actionItem.getElementsByTagName('description')[0])
            action.inServer = actionItem.getAttribute("inServer") == "true"
            action.inClient = actionItem.getAttribute("inClient") == "true"
            action.messageType = actionItem.getAttribute("messageType")
            todo = actionItem.getElementsByTagName('todo')
            if len(todo) > 0:
                action.todo = domGetText(todo[0])
            if action.identifier in actions:
                raise SchnittstellenXMLException("Action already defined: %s\n%s" % (action.identifier, item.toxml()))
            actions[action.identifier] = action
            action.request = self.getProperties(actionItem.getElementsByTagName('request')[0])
            action.response = self.getProperties(actionItem.getElementsByTagName('response')[0])
            notification = actionItem.getElementsByTagName('notification')
            if notification:
                action.notification = self.getProperties(notification[0])
            else:
                action.notification = None
        return actions
    
def writeProperties(properties, out):
        out.write("||**Name**||**Typ**||**Beschreibung**||**Beispiel**||\n")
        for p in sorted(properties):
            prop = properties[p]
            out.write("||%s{{{%s}}}||[#%s %s]%s||%s||{{{%s}}}||\n" % ("(optional) " if prop.isoptional else "", maskWikiPageNames(prop.identifier), prop.type.identifier, prop.type.identifier, maskWikiPageNames('[]' if prop.islist else ''), maskWikiPageNames(prop.description), maskWikiPageNames(prop.example)))

if __name__ == '__main__':
    import io
    import sys
    import os
    import xmlrpc.client
    import configparser
    
    ini_file = os.path.realpath(os.path.dirname(sys.argv[0]) + os.sep + 'trac.ini')
    config = configparser.SafeConfigParser()
    config.add_section('trac')
    config.set('trac', 'url', '')
    if os.path.isfile(ini_file):
        config.read(ini_file)

    if config.get('trac', 'url') == '' and len(sys.argv) < 2:
        sys.stderr.write("Missing arguments.\n")
        sys.stderr.write("Usage: %s <trac url> [xml file]\n" % sys.argv[0])
        sys.exit(1)
    
    if len(sys.argv) > 1:
        config.set('trac', 'url', sys.argv[1])
    
    s = SchnittstellenXML(sys.argv[2] if len(sys.argv) > 2 else os.path.realpath(os.path.dirname(sys.argv[0]) + os.sep + '../Schnittstellen/schnittstellen.xml'))
    
    groups = s.getGroupedActions()
    out = io.StringIO()
    
    out.write("[[PageOutline()]]\n")
    
    # Erzeuge Übersicht der Typen
    out.write("= Datentypen =\n")
    out.write("Diese Datentypen werden von den Methoden der API zum Datenaustausch verwendet.\n")
    out.write("== Einfache Datentypen ==\n")
    for st in s.types:
        type = s.types[st]
        if not isinstance(type, SimpleType):
            continue
        out.write("=== %s ===\n%s\n\nBeispiel: {{{%s}}}\n" % maskWikiPageNames(type.identifier, type.description, type.example))
        if type.todo:
            out.write("\n||[[Image(source:2011swtpro01/Project/Material/Icons/woo/warning_32.png)]]||%s||\n\n" % type.todo)
    out.write("----\n\n")
    
    out.write("== Enums ==\n")
    for et in s.types:
        type = s.types[et]
        if not isinstance(type, EnumType):
            continue
        out.write("=== %s ===\n%s\n\nBeispiel: {{{%s}}}\n" % maskWikiPageNames(type.identifier, type.description, type.example))
        if type.todo:
            out.write("\n||[[Image(source:2011swtpro01/Project/Material/Icons/woo/warning_32.png)]]||%s||\n\n" % type.todo)
        out.write("\n**Werte**\n\n")
        out.write("||**Übertragener Wert**||**Beschreibung**||\n")
        for value in type.values:
            out.write("||{{{%s}}}||%s||\n" % (value, type.values[value]))
    out.write("----\n\n")
    
    for ct in sorted(s.types):
        type = s.types[ct]
        if not isinstance(type, ComplexType):
            continue
        out.write("== %s ==\n" % maskWikiPageNames(type.identifier))
        if type.todo:
            out.write("\n||[[Image(source:2011swtpro01/Project/Material/Icons/woo/warning_32.png)]]||%s||\n\n" % type.todo)
        out.write("(//%s//) %s\n" % ('Object' if type.isobject else 'Dictionary', maskWikiPageNames(type.description)))
        out.write("\n**%s**\n\n" % ('Attribute' if type.isobject else 'Schlüssel'))
        writeProperties(type.properties, out)
        out.write("----\n\n")

    # Erzeuge eine Liste der Schnittstellen
    out.write("= API =\n")
    out.write("Nachfolgend findet sich die Liste der Methoden.\n\n")
    out.write("⚑ Eine schwarze Fahne vor einem Schnittstellennamen bedeutet, dass dieses Schnittstelle serverseitig implementiert wurde.\n\n")
    out.write("⚐ Eine weiße Fahne vor einem Schnittstellennamen bedeutet, dass dieses Schnittstelle clientseitig implementiert wurde. Siehe #316.\n")
    
    for ag in sorted(groups):
        group = groups[ag]
        out.write("== %s ==\n%s\n" % maskWikiPageNames(group.identifier, group.description))
        if group.todo:
            out.write("||[[Image(source:2011swtpro01/Project/Material/Icons/woo/warning_32.png)]]||%s||\n" % group.todo)
        for a in sorted(group.actions):
            action = group.actions[a]
            out.write("=== %s%s%s.%s() ===\n%s\n" % maskWikiPageNames("⚑ " if action.inServer else "", "⚐ " if action.inClient else "", group.identifier, action.identifier, action.description))
            if action.todo:
                out.write("||[[Image(source:2011swtpro01/Project/Material/Icons/woo/warning_32.png)]]||%s||\n" % action.todo)
            if action.messageType:
                out.write("\n\nMessage-Type: {{{%s}}}\n\n" % action.messageType)
            out.write("\n** Request **\n")
            writeProperties(action.request, out)
            # Standard-Anwtort ist vom Typ Response, überschreibe mit Porperties der Antwort
            out.write("\n** Response **\n")
            response = s.types['Response']
            writeProperties(dict(response.properties, **action.response), out)
            if action.notification:
                out.write("\n** Notification **\n")
                writeProperties(action.notification, out)
            out.write("\n** Tickets **\n")    
            out.write("[[TicketQuery(component=Schnittstellen&summary~=%s.%s())]]\n" % maskWikiPageNames(group.identifier, action.identifier))
    
    # Upload        
    trac_url = config.get('trac', 'url')
    if trac_url[-1] != "/":
        trac_url += "/"
    
    server = xmlrpc.client.ServerProxy("%slogin/xmlrpc" % trac_url)
    try:
        server.wiki.putPage('SchnittStellen', out.getvalue(), {'comment': 'Automatically updated by cron.'})
    except xmlrpc.client.Fault as e:
       if e.faultString != "'Page not modified' while executing 'wiki.putPage()'":
            raise e
