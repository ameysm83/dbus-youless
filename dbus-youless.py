from youless_api import YoulessAPI

# import normal packages
import platform 
import sys
import os
import sys
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject
import sys
import time

# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService

HOST_IP = "192.168.2.225"

class DbusYoulessP1Service(object):


    def __init__(self, paths, productname='Youless LS120', connection='Youless P1 HTTP JSOn service'):
        deviceinstance = 40
        customname = "Youless LS120"
        servicename = 'com.victronenergy.grid'
        productid = 45069

        self._api = YoulessAPI("192.168.2.225")
        self._api.initialize()

        self._dbusservice = VeDbusService("{}.http_{:02d}".format(servicename, deviceinstance))
        self._paths = paths

        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)
    
        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/ProductId', productid)
        self._dbusservice.add_path('/DeviceType', 345) # found on https://www.sascha-curth.de/projekte/005_Color_Control_GX.html#experiment - should be an ET340 Engerie Meter
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/CustomName', customname)
        self._dbusservice.add_path('/Latency', None)
        self._dbusservice.add_path('/FirmwareVersion', 0.2)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/Role', 'grid')
        self._dbusservice.add_path('/Serial', self._api.mac_address)
        self._dbusservice.add_path('/UpdateIndex', 0)
        
        # add path values to dbus
        for path, settings in self._paths.items():
          self._dbusservice.add_path(
            path, settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)
    
        # last update
        self._lastUpdate = 0
    
        # add _update function 'timer'
        gobject.timeout_add(1000, self._update) # pause 1000ms before the next request
 
    def _update(self):   
        try:
            self._api.update()

            #send data to DBus for 3pahse system
            self._dbusservice['/Ac/Power'] = self._api.current_power_usage.value
            self._dbusservice['/Ac/L1/Voltage'] = self._api.phase1.voltage.value
            self._dbusservice['/Ac/L2/Voltage'] = self._api.phase2.voltage.value
            self._dbusservice['/Ac/L3/Voltage'] = self._api.phase3.voltage.value
            self._dbusservice['/Ac/L1/Current'] = self._api.phase1.current.value
            self._dbusservice['/Ac/L2/Current'] = self._api.phase2.current.value
            self._dbusservice['/Ac/L3/Current'] = self._api.phase3.current.value
            self._dbusservice['/Ac/L1/Power'] = self._api.phase1.power.value
            self._dbusservice['/Ac/L2/Power'] = self._api.phase2.power.value
            self._dbusservice['/Ac/L3/Power'] = self._api.phase3.power.value
            self._dbusservice['/Ac/Energy/Forward'] = ((self._api.power_meter.low.value + self._api.power_meter.high.value)/1000)
            self._dbusservice['/Ac/Energy/Reverse'] = ((self._api.delivery_meter.low.value + self._api.delivery_meter.high.value)/1000)
            self._dbusservice['/UpdateIndex'] = (self._dbusservice['/UpdateIndex'] + 1 ) % 256

            #update lastupdate vars
            self._lastUpdate = time.time()

        except:    
            self._dbusservice['/Ac/L1/Power'] = 0                                       
            self._dbusservice['/Ac/L2/Power'] = 0                                       
            self._dbusservice['/Ac/L3/Power'] = 0
            self._dbusservice['/Ac/Power'] = 0
            self._dbusservice['/UpdateIndex'] = (self._dbusservice['/UpdateIndex'] + 1 ) % 256        
        
        # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
        return True

def main():
 
    try:
    
        from dbus.mainloop.glib import DBusGMainLoop
        # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
        DBusGMainLoop(set_as_default=True)
        
        #formatting 
        _kwh = lambda p, v: (str(round(v, 2)) + ' kWh')
        _a = lambda p, v: (str(round(v, 1)) + ' A')
        _w = lambda p, v: (str(round(v, 1)) + ' W')
        _v = lambda p, v: (str(round(v, 1)) + ' V')   
        
        #start our main-service
        
        pvac_output = DbusYoulessP1Service(
            paths={
                '/Ac/Energy/Forward': {'initial': 0, 'textformat': _kwh}, # energy bought from the grid
                '/Ac/Energy/Reverse': {'initial': 0, 'textformat': _kwh}, # energy sold to the grid
                '/Ac/Power': {'initial': 0, 'textformat': _w},
                
                '/Ac/Current': {'initial': 0, 'textformat': _a},
                '/Ac/Voltage': {'initial': 0, 'textformat': _v},
                
                '/Ac/L1/Voltage': {'initial': 0, 'textformat': _v},
                '/Ac/L2/Voltage': {'initial': 0, 'textformat': _v},
                '/Ac/L3/Voltage': {'initial': 0, 'textformat': _v},
                '/Ac/L1/Current': {'initial': 0, 'textformat': _a},
                '/Ac/L2/Current': {'initial': 0, 'textformat': _a},
                '/Ac/L3/Current': {'initial': 0, 'textformat': _a},
                '/Ac/L1/Power': {'initial': 0, 'textformat': _w},
                '/Ac/L2/Power': {'initial': 0, 'textformat': _w},
                '/Ac/L3/Power': {'initial': 0, 'textformat': _w},
                })
        mainloop = gobject.MainLoop()
        mainloop.run()            
    except:
        print('Error')
        
if __name__ == "__main__":
    main()
