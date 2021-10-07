import sqlite3


con = sqlite3.connect("CPP_Data.sqlite")
con.execute('''CREATE TABLE  Interface_Calculate(Fetch_datetime,Device_Name ,Total_Port ,Total_Access ,Total_Access_Connected ,Total_Access_free ,Total_Uplink ,Total_Uplink_Connected ,Total_Uplink_free
    ,Total_spd_1000_Connected ,Total_spd_1000_free,Total_spd_10G_Connected,Total_spd_10G_free ,Total_spd_100G_Connected ,Total_spd_100G_free ,Total_spd_40G_Connected
    ,Total_spd_40G_free,Port_Speed_1000,Port_Speed_100G  ,Port_Speed_10G ,Port_Speed_40G ,Total_Connected  ,Free_Port)''')
con.execute('''CREATE TABLE  Interface_Details(Port,Name,Status, Vlan, Speed, Duplex,Type, Device_Name ,Port_Availability ,Port_Category ,Port_Speed)''')
con.close()

Location_name