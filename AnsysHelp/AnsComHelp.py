import gtk
import gedit
from HTMLParser import HTMLParser
import urllib2 as url
import os.path
import glob
import pango
import gtkhtml2

# This HTML parser is to parse the command title, syntax and description
class htp(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.flag=""   # flag is used to identify where in the Ansys help file the parser is currently in 
        self.title=""  # once the title is identified, it is stored in this variable
        self.syntax="" # Place holder for syntax. Syntax is split in to different html tags. They are joined together to make complete syntax
        self.description=""
    def handle_starttag(self,tag,attrs):
        if tag=="div" or tag=="b":  # Check if identified tag is a div or bold
            attrs=dict(attrs)
            if len(attrs)>0:
                if attrs.get("class")=="refentrytitlehtml": #if the tag is div and class is as shown, then that means its inside the div which contains the data that has to be extracted
                    self.flag="title"
                elif attrs.get("class")=="refnamediv": # Similarly for syntax
                    self.flag="syntax"
                elif attrs.get("class")=="refpurpose": # And description
                    self.flag="description"
                else:
                    self.flag=""
    def handle_endtag(self,tag):
        if tag=="div" or tag=="b": # if the tag is closed, stop trying to read command items
            self.flag=""
    def handle_data(self,data): # With the right flags set, start interpreting the data
        if self.flag=="title":
            self.title=data.strip()
            self.flag=""
        elif self.flag=="syntax":
            self.syntax+=data.strip()
        elif self.flag=="description":
            self.description=data.strip()
    def output(self):
# if the output is read, return that to the calling function
        return [self.title,self.syntax,self.description]

# This HTML parser is used to parse the right item in the command syntax. Its a little more complicated than the previous one because of the complicated arragement of ansys help file
class htpd(HTMLParser):
    def __init__(self,itemnum):
        HTMLParser.__init__(self)
        self.flag=""    
        self.item=""
        self.itemcount=0
        self.itemnum=itemnum
        self.description=""

        self.ddcount=0 # This variable is used to check if the right dd tag is closed when the dd tags are nested
    def handle_starttag(self,tag,attrs):
        if tag=="div": 
            attrs=dict(attrs)
            if len(attrs)>0:
                if attrs.get("class")=="refsynopsisdiv" or attrs.get("class")=="refsect1":
# syntax items can be stored either in refsynopsisdiv or refsect1 class div
                    self.flag="varlist"
        elif tag=="dt":
            if self.flag=="varlist" and self.ddcount==0: #making sure the dt tag is inside the above div class and also its not inside a dd tag
                self.itemcount+=1
                if self.itemcount == self.itemnum-1:
                    self.flag="readitem"
        elif tag=="dd":
            self.ddcount+=1 # keeping track of number of dd tags opened right now. value of 0 means all dd tags are closed
            if self.flag=="readitem":
                self.flag="readdesc"
        else:
            if self.flag=="readdesc":
                self.description+="<"+tag+" " # to display the prper HTML inside the gtkhtml2 widget, all the tags has to be tracked
                for att, val in attrs:
                    self.description+=att + "='" + val + "' " # the attributes as well
                self.description+=">"
    def handle_endtag(self,tag):
        if self.flag=="readdesc":
            self.description+="</"+tag+"> " #Close the tag
        if tag=="dd":
            self.ddcount-=1 # reduce the ddcount by one denoting the closure of one dd tag
            if self.ddcount==0:
                self.flag="varlist"
    def handle_data(self,data):
        if self.flag=="readitem":
            self.item+=data.strip()
        elif self.flag=="readdesc":
            self.description+=data
    def output(self):
        return [self.item,self.description]

class AnsComHelp(gedit.Plugin): 
# The main class of gedit plugin
    def __init__(self):
        gedit.Plugin.__init__(self)

    def activate(self, window):
# Setting up the interface
        self.vpan = gtk.VPaned() # All items are contained inside a vertical paned container
        self.vbox = gtk.VBox(False,3) # Items related to the command title, syntax and description are inside a vbox
        self.vbox.set_border_width(3)
# GTK label for title of the command
        self.title = gtk.Label()
        fonttitle = pango.FontDescription('Lucida Sans Bold 15')
        self.title.modify_font(fonttitle)
        self.title.set_alignment(0,0.5) 

# GTK label for syntax of the command
        self.syntax = gtk.Label("Select any ANSYS command and press F2 to see a short help")
        fontsyntax = pango.FontDescription('Lucida Sans 12')
        self.syntax.modify_font(fontsyntax)
        self.syntax.set_use_markup(True)
        self.syntax.set_alignment(0,0.5)

# GTK label for description of the command
        self.description = gtk.Label()
        self.description.set_alignment(0,0.5)
        
# gtkhtml2 widget to show the html help of the command item
# This cannot be displayed inside a gtk label
        self.htmlView = gtkhtml2.View()
        self.htmlDoc = gtkhtml2.Document()
        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)
        self.htmlView.set_document(self.htmlDoc)

# Put all the command title,syntax items inside the vbox
        self.vbox.pack_start(self.title,False)
        self.vbox.pack_start(self.syntax,False)
        self.vbox.pack_start(self.description,False)
        self.vpan.add1(self.vbox)

# The htmlview item should be put inside a scroll window, otherwise overflowing data will be hidden
        self.scrollwin.add(self.htmlView)
        self.vpan.add2(self.scrollwin)

# Adding everything to the side panel, if you want it in the bottom panel, change side_panel to bottom_panel
        self.sidepanel = window.get_side_panel()
        self.sidepanel.add_item(self.vpan,"Ansys Help", gtk.STOCK_HELP)
        self.vpan.show_all()

# To check what the user is typing, the plugin has to listen to all keypress events happening inside the gedit window
        window.connect("key-press-event",self.keypress)

	

    def deactivate(self, window):
        #self._instances[window].deactivate()
        #del self._instances[window]
        self.sidepanel.remove_item(self.vpan)
	

    def update_ui(self, window):
        #self._instances[window].update_ui()
        pass

# place holder for the plugin configuration window
#    def is_configurable(self):
#        #return True
#        pass
#
#    def create_configure_dialog(self):
#        dialog = gtk.Dialog("Ansys Help Configuration")
#        checkb = gtk.CheckButton("Live help?")
#        dialog.action_area.add(checkb)
#        checkb.show() 
#        return dialog
#
         
    def keypress(self, window, event):
        if event.keyval in [44,65471,65472]:
            self.sidepanel.activate_item(self.vpan)
    	if event.keyval == 65471: # Pressing F2 will cause the plugin to display the help of a command in the active line
            doc = window.get_active_document()
            insertmark = doc.get_insert() # get the pointer where the cursor is lying
            insertiter = doc.get_iter_at_mark(insertmark) # get a gtkiter object the the cursor
            curline = insertiter.get_line() # get the line number of the cursor
            insertiter.set_line(curline) # move the gtkiter to start of the line. this will not change the cursor position
            enditer = insertiter.copy() # create a copy of gtkiter object
            enditer.forward_to_line_end() # move the new iter to end of the line
            stext = insertiter.get_text(enditer) # This will return the text in the current line
            search_text=stext.split(",") # split the current line with comma
            self.htmlDoc.open_stream("text/html")
            self.htmlDoc.write_stream("Press F3 to see Help for item")
            self.htmlDoc.close_stream()
            comhelp = self.PyAnsysHelp(search_text[0])
            self.title.set_text(comhelp[0])
            self.syntax.set_text(comhelp[1])
            self.description.set_text(comhelp[2])
        elif event.keyval == 65472:
            doc = window.get_active_document()
            insertmark = doc.get_insert()
            insertiter = doc.get_iter_at_mark(insertmark)
            enditer = insertiter.copy()
            curline = insertiter.get_line()
            insertiter.set_line(curline)
            stext = insertiter.get_text(enditer)
            search_text=stext.split(",")
            if search_text[0]!="":
                comhelp = self.PyAnsysHelpItem(search_text[0],len(search_text))
                self.htmlDoc.open_stream("text/html")
                self.htmlDoc.write_stream("<h2><b>" + comhelp[0] + "</h2></b>")
                self.htmlDoc.write_stream(comhelp[1])
                self.htmlDoc.close_stream()
        elif event.keyval == 44:
            doc = window.get_active_document()
            insertmark = doc.get_insert()
            insertiter = doc.get_iter_at_mark(insertmark)
            enditer = insertiter.copy()
            curline = insertiter.get_line()
            insertiter.set_line(curline)
            stext = insertiter.get_text(enditer)
            search_text=stext.split(",")
            if search_text[0]!="":
                comhelp = self.PyAnsysHelp(search_text[0])
                arglist = comhelp[1].split(",")
                for i in range(len(arglist)):
                    if i == len(search_text):
                        arglist[i]="<b>"+arglist[i]+"</b>"
                comhelp[1]=",".join(arglist)
                self.title.set_text(comhelp[0])
                self.syntax.set_markup(comhelp[1])
                self.description.set_text(comhelp[2])
                self.htmlDoc.open_stream("text/html")
                self.htmlDoc.write_stream("Press F3 to see Help for item")
                self.htmlDoc.close_stream()
            

    def PyAnsysHelp(self,command):
        command=command.strip().upper()
        if command[0]=="/" or command[0]=="*":
            command=command[1:]
        parser = htp()
        helplocprefix="/opt/ansys130/v130/commonfiles/help/en-us/help/ans_cmd/Hlp_C_"
        helplocsuffix=".html"
        helploc=helplocprefix+command+"*"+helplocsuffix
        helpfiles=sorted(glob.glob(helploc))
        if len(helpfiles)>0:
            mypage = url.urlopen("file://"+helpfiles[0])
            mytext=mypage.read()
            parser.feed(mytext)
            parser.close()
            return parser.output()
        else:
            return ["Does Not Exist","Help for " + command + " does not exist",""]
    def PyAnsysHelpItem(self,command,itemnum):
        command=command.strip().upper()
        if command[0]=="/" or command[0]=="*":
            command=command[1:]
        parser = htpd(itemnum)
        helplocprefix="/opt/ansys130/v130/commonfiles/help/en-us/help/ans_cmd/Hlp_C_"
        helplocsuffix=".html"
        helploc=helplocprefix+command+"*"+helplocsuffix
        helpfiles=sorted(glob.glob(helploc))
        if len(helpfiles)>0:
            mypage = url.urlopen("file://"+helpfiles[0])
            mytext=mypage.read()
            parser.feed(mytext)
            parser.close()
            return parser.output()
        else:
            return ["Command Not Found","The command " + command + " was not found in the help archive"]
