import json
rows=[
 ("overview","Overview and Shared Parts",[("Home.dc.html",1440,1300,"Dashboard"),("Sidebar.dc.html",248,1700,"Shared Sidebar"),("Tabs.dc.html",960,64,"Shared Section Tabs")]),
 ("aircraft","Aircraft Management",[("Fleet.dc.html",1440,1160,"Aircraft, All Aircraft"),("Reviews.dc.html",1440,1360,"Aircraft, Airworthiness Reviews"),("Aircraft.dc.html",1440,1900,"Aircraft Record, G-ABCD")]),
 ("safety","Safety Management",[("Main.dc.html",1440,1700,"Hazard Log, Light"),("Dark.dc.html",1440,1700,"Hazard Log, Dark"),("Reports.dc.html",1440,1200,"Safety Reports"),("SafetyReport.dc.html",1440,1500,"Report a Safety Issue"),("Audit.dc.html",1440,1500,"Compliance Monitoring"),("Actions.dc.html",1440,1300,"Actions")]),
 ("planning","Planning",[("WorkPackages.dc.html",1440,2100,"Work Packages"),("Plan.dc.html",1440,1760,"Manhours and Capacity, Manhour Plan"),("Load.dc.html",1440,1760,"Manhours and Capacity, Load and Capacity"),("Roster.dc.html",1440,1360,"Manhours and Capacity, Staff Roster")]),
 ("tools","Tools and Equipment",[("Tools.dc.html",1440,1560,"Control Register"),("Tool.dc.html",1440,1900,"Tool Record, Torque Wrench 0142"),("Providers.dc.html",1440,1460,"Service Providers"),("AltTool.dc.html",1440,1960,"Alternative Tooling"),("ToolNeed.dc.html",1440,1460,"Tooling Need Evaluations")]),
 ("people","People",[("Staff.dc.html",1440,1660,"Staff and Training"),("Recency.dc.html",1440,2060,"Recency"),("Logbook.dc.html",1440,1960,"Engineer Logbooks"),("Training.dc.html",1440,2160,"On the Job Training"),("Competence.dc.html",1440,1560,"Competency Assessments"),("Assessment.dc.html",1440,2400,"Competency Assessment Form")]),
 ("settings","Settings and Help",[("Settings.dc.html",1440,1700,"Settings, Organisation"),("PlanSettings.dc.html",1440,1360,"Settings, Planning"),("Guide.dc.html",1440,1900,"Help, Assessor Guide")]),
]
boards={};order=[];notes={};y=260
for nid,title,items in rows:
  x=0;h=0
  for f,w,hh,t in items:
    b={"x":x,"y":y,"w":w,"h":hh,"title":t}
    if w==1440: b.update({"expand":"fill","is_interactive":True})
    boards[f]=b;order.append(f);x+=w+80;h=max(h,hh)
  notes[nid]={"x":0,"y":y-260,"text":title,"kind":"title1","maxW":x-80}
  y+=h+120+260
c={"v":3,"createdOnFiles":{"v":1,"at":"2026-11-17T23:40:00Z"},"title":"Airworthiness+ Web App","launch":{"view":"canvas"},"pages":[],"boards":boards,"order":order,"notes":notes,"designSystems":[]}
json.dump(c,open('/home/claude/overhaul/project/canvas.json','w'),separators=(',',':'))
print(len(boards))
