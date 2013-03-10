import mmap
import struct
import yaml # Requires PyYAML


MEMMAPFILE = 'Local\\IRSDKMemMapFileName'

TELEM_HEADER_LEN = 144
TELEM_HEADER_SIZE = 28

# How far into a header the name sits, and it's max length
TELEM_NAME_OFFSET = 16
TELEM_NAME_MAX_LEN = 32

BUFFERS = (770160, 721008, 745584)

TYPEMAP = ['c', '?', 'i', 'I', 'f', 'd']

VALOFFSETS = {
    'SessionTime':0,
    'SessionNum':8,
    'SessionState':12,
    'SessionUniqueID':16,
    'SessionFlags':20,
    'SessionTimeRemain':24,
    'SessionLapsRemain':32,
    'RadioTransmitCarIdx':36,
    'DriverMarker':40,
    'IsReplayPlaying':41,
    'ReplayFrameNum':42,
    'ReplayFrameNumEnd':46,
    'CarIdxLap':50,
    'CarIdxLapDistPct':306,
    'CarIdxTrackSurface':562,
    'CarIdxOnPitRoad':818,
    'OnPitRoad':882,
    'CarIdxSteer':883,
    'CarIdxRPM':1139,
    'CarIdxGear':1395,
    'SteeringWheelAngle':1651,
    'Throttle':1655,
    'Brake':1659,
    'Clutch':1663,
    'Gear':1667,
    'RPM':1671,
    'Lap':1675,
    'LapDist':1679,
    'LapDistPct':1683,
    'RaceLaps':1687,
    'LapBestLap':1691,
    'LapBestLapTime':1695,
    'LapLastLapTime':1699,
    'LapCurrentLapTime':1703,
    'LapDeltaToBestLap':1707,
    'LapDeltaToBestLap_DD':1711,
    'LapDeltaToBestLap_OK':1715,
    'LapDeltaToOptimalLap':1716,
    'LapDeltaToOptimalLap_DD':1720,
    'LapDeltaToOptimalLap_OK':1724,
    'LapDeltaToSessionBestLap':1725,
    'LapDeltaToSessionBestLap_DD':1729,
    'LapDeltaToSessionBestLap_OK':1733,
    'LapDeltaToSessionOptimalLap':1734,
    'LapDeltaToSessionOptimalLap_DD':1738,
    'LapDeltaToSessionOptimalLap_OK':1742,
    'LongAccel':1743,
    'LatAccel':1747,
    'VertAccel':1751,
    'RollRate':1755,
    'PitchRate':1759,
    'YawRate':1763,
    'Speed':1767,
    'VelocityX':1771,
    'VelocityY':1775,
    'VelocityZ':1779,
    'Yaw':1783,
    'Pitch':1787,
    'Roll':1791,
    'PitRepairLeft':1795,
    'PitOptRepairLeft':1799,
    'CamCarIdx':1803,
    'CamCameraNumber':1807,
    'CamGroupNumber':1811,
    'CamCameraState':1815,
    'IsOnTrack':1819,
    'IsInGarage':1820,
    'SteeringWheelTorque':1821,
    'SteeringWheelPctTorque':1825,
    'ShiftIndicatorPct':1829,
    'ShiftPowerPct':1833,
    'ShiftGrindRPM':1837,
    'EngineWarnings':1841,
    'FuelLevel':1845,
    'FuelLevelPct':1849,
    'ReplayPlaySpeed':1853,
    'ReplayPlaySlowMotion':1857,
    'ReplaySessionTime':1858,
    'ReplaySessionNum':1866,
    'WaterTemp':1870,
    'WaterLevel':1874,
    'FuelPress':1878,
    'OilTemp':1882,
    'OilPress':1886,
    'OilLevel':1890,
    'Voltage':1894,
    'ManifoldPress':1898,
    'RRshockDefl':1902,
    'LRshockDefl':1906,
    'RFshockDefl':1910,
    'LFshockDefl':1914,
}


class API(object):

    def __init__(self):
        # Find max memory map size
        size = 500000
        while True:
            try:
                self.mmp = mmap.mmap(0, size, MEMMAPFILE)
                size += 1
            except:
                break

        # Set up the telemetry, working out the var types
        self.var_types = {}
        self.setup_telemetry()

        # Find the size of each slot in memory - pre-calc for speed later
        self.sizes = {}
        for key, t in self.var_types.items():
            self.sizes[key] = struct.calcsize(t)

    def telemetry(self, key):
        """ Return the data for a telemetry key.
        """
        offset = VALOFFSETS[key]
        for b in BUFFERS:
            self.mmp.seek(b + offset)
            data = self.mmp.read(self.sizes[key])
            if len(data.replace('\x00','')) != 0:
                return struct.unpack(self.var_types[key], data)[0]

    @property
    def yaml(self):
        """ Returns the YAML as a nested Python dict.
        """
        ymltxt = ''
        self.mmp.seek(0)
        headers = self.mmp.readline()
        while True:
            line = self.mmp.readline()
            if line.strip() == '...':
                break
            else:
                ymltxt += line
        return yaml.load(ymltxt, Loader=yaml.CLoader)

    def yaml_end(self):
        self.mmp.seek(0)
        offset = 0
        headers = self.mmp.readline()
        while True:
            line = self.mmp.readline()
            if line.strip() == '...':
                break
            else:
                offset += len(line)
        return offset + len(headers) + 4

    def setup_telemetry(self):
        # Find the start of the headers, starting from the end of the YAML
        self.mmp.seek(self.yaml_end())
        dat = '\x00'
        while dat.strip() == '\x00':
            dat = self.mmp.read(1)
        self.mmp.seek(self.mmp.tell() - 1)

        # Set up the type map based on the headers
        while True:
            pos = self.mmp.tell() + TELEM_NAME_OFFSET
            start = TELEM_NAME_OFFSET
            end = TELEM_NAME_OFFSET + TELEM_NAME_MAX_LEN
            header = self.mmp.read(TELEM_HEADER_LEN)
            name = header[start:end].replace('\x00','')
            if name == '':
                break
            var_type = TYPEMAP[int(struct.unpack('i', header[0:4])[0])]
            self.var_types[name] = var_type
        

if __name__ == '__main__':
    """ Simple test harness.
    """
    import time
    api = API()
    
    while True:
        print '{0} Gear, {1} m/s, {2} m/s/s'.format(api.telemetry('Gear'),
                                                    api.telemetry('Speed'),
                                                    api.telemetry('LatAccel'))
        time.sleep(1)