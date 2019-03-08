from netmiko import ConnectHandler
import re
import sqlite3

def processData(ip, username, password, routing=True, version=True, vlan=True, cpu=True):
    # The main function that gets data from the network device
    # and inputs it into the database.
    conn = sqlite3.connect('networkDeviceStats.db')
    c = conn.cursor()
    deviceId = getDeviceId(username)
    if routing == True:
        routingTable = getRoutingTable(ip, username, password)
        c.execute("""INSERT INTO Routing_Table (DeviceID, Routing_Table) VALUES (?,?);""", (int(deviceId), str(routingTable)))
    if version == True:
        version = getIOSVersion(ip, username, password)
        c.execute("""INSERT INTO IOS_Version (DeviceID, IOS_Version) VALUES (?,?);""", (int(deviceId), str(version)))
    if vlan == True:
        vlanList = getVLANDatabase(ip, username, password)
        for key in vlanList:
            vlanNum = key
            for key in vlanList[vlanNum]:
                vlanName = vlanList[vlanNum]['Name']
                vlanStatus = vlanList[vlanNum]['Status']
                if 'Ports' in vlanList[vlanNum]:
                    vlanPorts = str(vlanList[vlanNum]['Ports'])
                else:
                    vlanPorts = "No Ports."                
                c.execute("""INSERT INTO VLAN_Config (VLAN_Number, VLAN_Name, Status, Ports, DeviceID) VALUES (?,?,?,?,?)""", (vlanNum, vlanName, vlanStatus, vlanPorts, deviceId))
    if cpu == True:
        percentage = getCPUUtilisation(ip, username, password)
        c.execute("""INSERT INTO CPU_Util (Percentage, DeviceID) VALUES (?,?)""", (percentage, deviceId))
    
    conn.commit()
    conn.close()

def getDeviceId(username):
    # Gets the device ID from the database by searching for the username and returns it as an integer.
    conn = sqlite3.connect('networkDeviceStats.db')
    c = conn.cursor()
    c.execute("SELECT DeviceID FROM devices WHERE Username = '{}'".format(username))
    deviceId = c.fetchone()
    return deviceId[0]     

def getRoutingTable(ip, username, password):
    # Gets the routing table from the network device and returns it as a string.
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }

    net_connect = ConnectHandler(**device)
    net_connect.find_prompt()
    net_connect.enable()
    routingTable = net_connect.send_command('show ip route')
    routingTableSplit = re.split('\n', routingTable, 8)
    net_connect.exit_enable_mode()
    return routingTableSplit[8]

def getIOSVersion(ip, username, password):
    # Gets the IOS Version from the network device and returns it as a string.
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }

    net_connect = ConnectHandler(**device)
    net_connect.find_prompt()
    net_connect.enable()
    version = net_connect.send_command('show version')
    net_connect.exit_enable_mode()
    versionSearch = re.findall('Version .*?,', version)
    versionNum = re.split(' |,', str(versionSearch[0]))
    return versionNum[1]

def getVLANDatabase(ip, username, password):
    # Gets the vlan database from the network device and returns it as a list.
    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': ip,
        'username': username,
        'password': password,
	'secret': 'cisco'
    }

    net_connect = ConnectHandler(**device)
    net_connect.find_prompt()
    net_connect.enable()
    vlanDb = net_connect.send_command('show vlan')
    net_connect.exit_enable_mode()

    splitVlan = vlanDb.split()
    currentVlan = ""
    vlanDict = {}
    vlanUiPattern = re.compile('-{3,}')
    vlanNumPattern = re.compile('[0-9]')
    vlanPortPattern = re.compile('Gig[0-9]+/[0-9]+|Fa[0-9]+/[0-9]+')
    vlanStatusPattern = ["suspended", "active", "act/lshut", "sus/lshut", "act/ishut", "sus/ishut", "act/unsup"]
    for i in range(8, len(splitVlan)):
        field = splitVlan[i]
        if vlanNumPattern.match(field) != None:
            vlanDict[splitVlan[i]] = {}
            currentVlan = splitVlan[i]
        elif splitVlan[i] in vlanStatusPattern:
            vlanDict[currentVlan]['Status'] = splitVlan[i].replace(',','')
        elif vlanPortPattern.match(splitVlan[i]) != None:
            if "Ports" in vlanDict[currentVlan]:
                vlanDict[currentVlan]['Ports'].append(splitVlan[i].replace(',',''))
            else:
                vlanDict[currentVlan]['Ports'] = [splitVlan[i]]
        elif i != 0 and splitVlan[i] == 'VLAN':
            return vlanDict
        elif vlanUiPattern.match(splitVlan[i]) != None:
            pass
        else:
            vlanDict[currentVlan]['Name'] = splitVlan[i]

def getCPUUtilisation(ip, username, password):
    # Gets the CPU utilisation over the past minute from the network device and returns it as an integer.
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }

    net_connect = ConnectHandler(**device)
    net_connect.find_prompt()
    net_connect.enable()
    processes = net_connect.send_command('show processes')
    net_connect.exit_enable_mode()

    utilisation = re.findall('one minute: .*?%', processes)
    print(utilisation)
    utilisationNum = re.split(' |%', utilisation[0])
    print(utilisationNum)
    return int(utilisationNum[2])
