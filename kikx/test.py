from dev.cuteadb import adb

"""
OPPO CPH1989
    Device ID: 0
    State: device 
    SDK Version: 30
    Android Version: 11 
    Serial: localhost:40143
"""

device = adb.list_active_devices()[0]
print(device)


