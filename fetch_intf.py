
import textfsm
import paramiko, xlsxwriter
import time
import datetime
import pathlib
import pandas as pd
from pandas import ExcelWriter

import base64

from key import user_pwd
username = user_pwd()[0]
password = user_pwd()[1]
password = base64.b64decode(password)
password = password.decode("utf-8")



ts = time.time()
current_timestamp = datetime.datetime.fromtimestamp(ts).strftime('%A-%d-%b-%Y %H-%M-%S')
current_time = datetime.datetime.fromtimestamp(ts).strftime('%A-%d-%b-%Y')


error_log_file_name = "Error_DC" + "_" + current_time + ".txt"
err_file_path = pathlib.Path(error_log_file_name)
err_file = open(error_log_file_name, 'w')


def precheck_fsm(cmd):

    lst = []

    input_file = open("show_inventory.txt", encoding='utf-8')
    raw_text_data = input_file.read()

    input_file.close()
    if cmd == 'sh int status | in Eth':
        template = open("sh_int_status.textfsm.txt")
    else:
        template = open("sh_int_desc.textfsm.txt")

    re_table = textfsm.TextFSM(template)
    fsm_results = re_table.ParseText(raw_text_data)
    print(fsm_results)

    for row in fsm_results:

        lst.append(row)
        if cmd == 'sh int status | in Eth':
            df = pd.DataFrame(lst, columns=['Port', 'Name' , 'Status' , 'Vlan' , 'Duplex', 'Speed', 'Type'])
        else:
            df = pd.DataFrame(lst, columns=['Interface', 'Status' , 'Protocol' , 'Description'])


    return df

def dcmetro_desc(dc_devices):
    w = ExcelWriter('DC_Metro_desc.xlsx')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cmd = "sh int status | in Eth"


    df = pd.DataFrame([])
    for lines in dc_devices['Device Name']:

        print(lines)

        device_name = lines

        device_iniial = ['rotv','rrmetro','voiceivr','rpe']

        if any(s in device_name for s in device_iniial):
            cmd = 'sh int desc'
        else:
            cmd = 'sh int status | in Eth'

        print(cmd)
        try:
            ssh.connect(lines, username=username, password=password)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:

                output_file = "show_inventory.txt"
                f = open(output_file, 'a+')
                f.truncate(0)
                output = stdout.readlines()
                print(output)


                if cmd == 'sh int status | in Eth':

                    for out in output:
                        f.write(out)

                    f.close()
                    interface_rem = precheck_fsm(cmd)

                    col_name = ['Port', 'Name' , 'Status' , 'Vlan' , 'Duplex', 'Speed', 'Type','Device Name']
                    interface_rem_list = interface_rem.values.tolist()
                    interface_list = []
                    for i in interface_rem_list:
                        i.append(lines)

                        interface_list.append(i)

                    df = df.append(pd.DataFrame(interface_list, columns=col_name), ignore_index=True)
                elif cmd == 'sh int desc':

                    count = 0
                    pay_attention = False
                    for out_line in output:
                        if pay_attention:
                            if count == 0:
                                count = count + 1
                                continue
                            else:
                                out = out_line
                                f.write(out)

                        else:
                            if 'Interface' in out_line:

                                pay_attention = True
                                out = out_line
                                f.write(out)

                    f.close()
                    interface_rem = precheck_fsm(cmd)
                    col_name = ['Interface', 'Status' , 'Protocol' , 'Description', 'Device Name']
                    interface_rem_list = interface_rem.values.tolist()
                    interface_list = []
                    for i in interface_rem_list:
                        i.append(lines)

                        interface_list.append(i)

                    df = df.append(pd.DataFrame(interface_list, columns=col_name), ignore_index=True)

            else:
                err_file.write("\n")
                err_file.write(
                    "Device - " + str(lines) + " Error - Unable to execute the command" + " timestamp : " + str(
                        current_time) + "\n")
                ssh.close()

            ssh.close()

        except Exception as e:
            err_file.write("\n")
            print("Exception Occured in " + str(lines) + str(e))
            err_file.write("Device - " + str(lines) + " Exception - " + str(e) + "\n")
            ssh.close()

    df.to_excel(w)
    w.save()

    return df







