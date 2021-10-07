
from fetch_intf import dcmetro_desc
import pandas as pd
import numpy as np
import os,json
import re
from flask import Flask, request, render_template, jsonify
import pandas as pd
import requests
from datetime import datetime
import sqlite3
from pandas.io.json import json_normalize
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger


app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

dc_devices = pd.read_excel('data/Nexus_devices.xlsx')


def interface_details(check_type, device_list):
    url = 'http://127.0.0.8:5204/api/interface_details'
    # url = 'http://10.253.1.8:5000/api/hyg_upgrade_single'

    device_json = device_list.to_json(orient='records')

    params = {'devices': device_json, 'check_type': check_type}
    r = requests.post(url=url, json=params)
    result = r.json()['result']
    jdata = json.loads(result)

    df = json_normalize(jdata)

    return df


#******************fetch the interface data*****************

def interface_calculate_db():

    df = interface_details('dcmetro_desc',dc_devices)

    # df.groupby(['Device Name', 'Status']).agg({'Status': 'count'})
    # borderleaf
    df = df[~df['Device Name'].str.contains('borderleaf', case=False)]
    # df = df.join(df['Port'].str.split('/', 1, expand=True))
    # df.rename(columns={1: 'split1', 2: 'split2', 3: 'split3'}, inplace=True)
    # df['split1'] = df['split1'].astype(float)
    # df = df[df['split1'].between(0, 49)]
    df.loc[df['Status'].str.contains('connected'), 'Port_Availability'] = 'Occupied'
    df.loc[df['Status'].str.contains('disabled'), 'Port_Availability'] = 'Free'
    # df.loc[df['split1'].between(0, 49),'Port_Category'] = 'Access'
    df.loc[~df['Name'].str.contains('UPLINK', case=False), 'Port_Category'] = 'Access'
    df.loc[df['Name'].str.contains('UPLINK', case=False), 'Port_Category'] = 'Uplink'
    # df.loc[df['split1'] >= 49,'Port_Category'] = 'Uplink'
    # df['Port_Speed'] = df['Speed'].apply(lambda x: '--' if x == 'auto' else x)

    bw_interface = {'SFP-H25GB-SR': ['25G'], '10Gbase-SR': ['10G'], '1000base-SX': ['1000'], '1000base-T': ['1000'],
                    'QSFP-100G40G-BIDI': ['100G'], 'QSFP-40G-SR-BD': ['40G'], '10/25Gbase-CSR': ['25G'],
                    'QSFP-40G-SR4': ['40G'], '10g': ['10G']}

    def find_BW(x):
        for key, value in bw_interface.items():

            if key in x.Type:
                bw_value = value[0]
                break
            else:
                bw_value = 'NA'

            if bw_value != 'NA':
                break
        return bw_value

    df['Port_Speed'] = df.apply(lambda x: find_BW(x) if x.Speed == 'auto' else x.Speed, axis=1)
    #df.to_excel('Detail_Desc.xlsx')

    #*************load the data into the database*********************

    con = sqlite3.connect('CPP_Data.sqlite')
    cur = con.cursor()

    sql_delete_query = "DELETE from Interface_Details"
    cur.execute(sql_delete_query)
    con.commit()

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d %H:%M:%S")
    current_time = now.strftime("%H:%M:%S")

    for i, row in df.iterrows():


        Port = row['Port']
        Name = row['Name']
        Status = row['Status']
        Vlan = row['Vlan']
        Speed = row['Speed']
        Duplex = row['Duplex']
        Type = row['Type']
        Device_Name = row['Device Name']
        Port_Availability = row['Port_Availability']
        Port_Category = row['Port_Category']
        Port_Speed=  row['Port_Speed']

        cur.execute(
            '''INSERT into Interface_Details (Port,Name,Status, Vlan, Speed, Duplex,Type, Device_Name ,Port_Availability ,Port_Category ,Port_Speed ) values (?,?,?,?,?,?,?,?,?,?,?)''',
            (Port,Name,Status, Vlan, Speed, Duplex,Type, Device_Name ,Port_Availability ,Port_Category, Port_Speed ))

        con.commit()
    con.close()


@app.route('/', methods=['GET', 'POST'])
def index():

    con = sqlite3.connect('CPP_Data.sqlite')
    cur = con.cursor()
    cur.execute('SELECT * FROM Interface_Details')
    check = cur.fetchall()

    if len(check) == 0:
        interface_calculate_db()
        df = pd.read_sql_query('Select * from Interface_Details;', con)

    else:
        df = pd.read_sql_query('Select * from Interface_Details;', con)

    print("**********************Logical calculation starts**********")

    # devices with interface
    status_total = df.groupby('Device_Name')['Status'].count().reset_index()
    # status_total = df.groupby('Device Name').agg({'Status': ['count']})
    status_total.rename(columns={'Status': 'Total Port'}, inplace=True)

    # devices with status connected
    status_connected = df['Status'].str.contains('connected').groupby(df['Device_Name']).sum().reset_index()
    status_connected.rename(columns={'Status': 'Total Connected'}, inplace=True)

    # device interface port category access
    status_access = df['Port_Category'].str.contains('Access').groupby(df['Device_Name']).sum().reset_index()
    status_access.rename(columns={'Port_Category': 'Total Access'}, inplace=True)

    df_access = df[(df['Port_Category'].str.contains('Access'))]
    status_connected_access = df_access['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    status_connected_access.rename(columns={'Status': 'Total Access Connected'}, inplace=True)

    status_free_access = df_access['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    status_free_access.rename(columns={'Status': 'Total Access free'}, inplace=True)

    status_uplink = df['Port_Category'].str.contains('Uplink').groupby(df['Device_Name']).sum().reset_index()
    status_uplink.rename(columns={'Port_Category': 'Total Uplink'}, inplace=True)

    df_uplink = df[(df['Port_Category'].str.contains('Uplink'))]
    status_connected_uplink = df_uplink['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    status_connected_uplink.rename(columns={'Status': 'Total Uplink Connected'}, inplace=True)

    status_free_uplink = df_uplink['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    status_free_uplink.rename(columns={'Status': 'Total Uplink free'}, inplace=True)

    speed_1000 = df['Port_Speed'].str.contains('1000').groupby(df['Device_Name']).sum().reset_index()
    speed_1000.rename(columns={'Port_Speed': 'Port_Speed_1000'}, inplace=True)

    df_speed_1000 = df[(df['Port_Speed'].str.contains('1000', na=False))]
    speed_1000_connected = df_speed_1000['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    speed_1000_connected.rename(columns={'Status': 'Total_spd_1000_Connected'}, inplace=True)

    speed_1000_free = df_speed_1000['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    speed_1000_free.rename(columns={'Status': 'Total_spd_1000_free'}, inplace=True)

    speed_10G = df['Port_Speed'].str.contains('10G').groupby(df['Device_Name']).sum().reset_index()
    speed_10G.rename(columns={'Port_Speed': 'Port_Speed_10G'}, inplace=True)

    df_speed_10G = df[(df['Port_Speed'].str.contains('10G', na=False))]
    speed_10G_connected = df_speed_10G['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    speed_10G_connected.rename(columns={'Status': 'Total_spd_10G_Connected'}, inplace=True)

    speed_10G_free = df_speed_10G['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    speed_10G_free.rename(columns={'Status': 'Total_spd_10G_free'}, inplace=True)

    speed_100G = df['Port_Speed'].str.contains('100G').groupby(df['Device_Name']).sum().reset_index()
    speed_100G.rename(columns={'Port_Speed': 'Port_Speed_100G'}, inplace=True)

    df_speed_100G = df[(df['Port_Speed'].str.contains('100G', na=False))]
    speed_100G_connected = df_speed_100G['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    speed_100G_connected.rename(columns={'Status': 'Total_spd_100G_Connected'}, inplace=True)

    speed_100G_free = df_speed_100G['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    speed_100G_free.rename(columns={'Status': 'Total_spd_100G_free'}, inplace=True)

    speed_40G = df['Port_Speed'].str.contains('40G').groupby(df['Device_Name']).sum().reset_index()
    speed_40G.rename(columns={'Port_Speed': 'Port_Speed_40G'}, inplace=True)

    df_speed_40G = df[(df['Port_Speed'].str.contains('40G', na=False))]
    speed_40G_connected = df_speed_40G['Status'].str.contains('connected').groupby(
        df['Device_Name']).sum().reset_index()
    speed_40G_connected.rename(columns={'Status': 'Total_spd_40G_Connected'}, inplace=True)

    speed_40G_free = df_speed_40G['Status'].str.contains('disabled').groupby(df['Device_Name']).sum().reset_index()
    speed_40G_free.rename(columns={'Status': 'Total_spd_40G_free'}, inplace=True)

    dfs = [df.set_index(['Device_Name']) for df in [status_total, status_access,
                                                    status_connected_access, status_free_access,
                                                    status_connected_uplink,
                                                    status_free_uplink, speed_1000_connected,
                                                    speed_1000_free, speed_10G_connected, speed_10G_free,
                                                    speed_100G_connected, speed_100G_free,
                                                    speed_40G_connected, speed_40G_free,
                                                    status_uplink, speed_1000, speed_100G, speed_10G, speed_40G,
                                                    status_connected]]
    total_port = pd.concat(dfs, axis=1).reset_index()
    total_port['Free Port'] = total_port['Total Port'] - total_port['Total Connected']

    #total_port.to_excel('Port_detail.xlsx')

    # *************load the data into the database*********************

    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d %H:%M:%S")
    current_time = now.strftime("%H:%M:%S")

    for i, row in total_port.iterrows():
        Device_Name = row['Device_Name']
        Total_Port = row['Total Port']
        Total_Access = row['Total Access']
        Total_Access_Connected = row['Total Access Connected']
        Total_Access_free = row['Total Access free']
        Total_Uplink = row['Total Uplink']
        Total_Uplink_Connected = row['Total Uplink Connected']
        Total_Uplink_free = row['Total Uplink free']
        Total_spd_1000_Connected = row['Total_spd_1000_Connected']
        Total_spd_1000_free = row['Total_spd_1000_free']
        Total_spd_10G_Connected = row['Total_spd_10G_Connected']
        Total_spd_10G_free = row['Total_spd_10G_free']
        Total_spd_100G_Connected = row['Total_spd_100G_Connected']
        Total_spd_100G_free = row['Total_spd_100G_free']
        Total_spd_40G_Connected = row['Total_spd_40G_Connected']
        Total_spd_40G_free = row['Total_spd_40G_free']
        Port_Speed_1000 = row['Port_Speed_1000']
        Port_Speed_100G = row['Port_Speed_100G']
        Port_Speed_10G = row['Port_Speed_10G']
        Port_Speed_40G = row['Port_Speed_40G']
        Total_Connected = row['Total Connected']
        Free_Port = row['Free Port']

        cur.execute(
            '''INSERT into Interface_Calculate (Fetch_datetime,Device_Name ,Total_Port ,Total_Access ,Total_Access_Connected ,Total_Access_free ,Total_Uplink ,
            Total_Uplink_Connected ,Total_Uplink_free
        ,Total_spd_1000_Connected ,Total_spd_1000_free,Total_spd_10G_Connected,Total_spd_10G_free ,Total_spd_100G_Connected ,Total_spd_100G_free ,Total_spd_40G_Connected
        ,Total_spd_40G_free,Port_Speed_1000,Port_Speed_100G  ,Port_Speed_10G ,Port_Speed_40G ,Total_Connected  ,Free_Port ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (current_date, Device_Name, Total_Port, Total_Access, Total_Access_Connected, Total_Access_free,
             Total_Uplink, Total_Uplink_Connected, Total_Uplink_free
             , Total_spd_1000_Connected, Total_spd_1000_free, Total_spd_10G_Connected, Total_spd_10G_free,
             Total_spd_100G_Connected, Total_spd_100G_free, Total_spd_40G_Connected
             , Total_spd_40G_free, Port_Speed_1000, Port_Speed_100G, Port_Speed_10G, Port_Speed_40G, Total_Connected,
             Free_Port))

        con.commit()
    con.close()

    return 'True'

sched = BackgroundScheduler(daemon=True)
#sched.add_job(interface_calculate_db, 'interval', minutes=15)
trigger = OrTrigger([CronTrigger(day_of_week='sat', hour=9)])
sched.add_job(interface_calculate_db, trigger)
sched.start()

@app.route('/api/port_data', methods=['GET'])
def port_data():

    con = sqlite3.connect('CPP_Data.sqlite')
    data = pd.read_sql_query('Select * from Interface_Calculate;', con)
    data = data.to_json(orient='records')
    con.close()
    return data

@app.route('/api/interface', methods=['GET'])
def interface():

    con = sqlite3.connect('CPP_Data.sqlite')
    device_name = request.args.get("device_name")
    print(device_name)

    data = pd.read_sql_query('Select * from Interface_Details;', con)
    data = data[data['Device_Name'].str.contains(device_name)]
    data = data.to_json(orient='records')
    con.close()
    return data


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port='5203')