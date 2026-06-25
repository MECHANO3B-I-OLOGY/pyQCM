import struct
import numpy as np
from matplotlib import pyplot as plt # for demo only: remove otherwise
import pandas as pd

from src.analyze import ordinal

def read_qsd(filename):
    with open(filename, 'rb') as f:
        d = f.read()

    reslen=[]
    nmodes = d.rindex(bytes("XtalDriveTimeFloat".encode('ascii'))) # r = start from end

    pointer = nmodes + 30
    nsensors = d[pointer]
    ns = nsensors
    
    if nsensors != 1 and nsensors != 4:
        raise Exception("Invalid number of sensors, aborting")
    
    pointer += 4
    n = struct.unpack('<I', d[pointer:pointer+4])[0]
    pointer += 4     # skip length information
    pointer += (4 * nsensors)
    if d[pointer] != 0xee:
        raise Exception("Invalid value: != 0xee")
    pointer += 16
    newn = struct.unpack('<I', d[pointer:pointer+4])[0]
    if newn != n+1:
        # different file format inserts an extra 16-byte block between the 0xee
        # sentinel and the size-check field.  Try stepping over it.
        pointer += 16
        newn = struct.unpack('<I', d[pointer:pointer+4])[0]
        if newn != n+1:
            raise Exception("Invalid size repetition")
    pointer += 4     # skip length information
    if d[pointer] == 0x02:
        pointer += 8 # added to validate BSA dataset
    if d[pointer] != 0x01:
        raise Exception("Invalid value: != 0x01")
    pointer += 12
    if d[pointer] != 0x0b:
        raise Exception("Invalid value: != 0x0b")
    
    pointer += 6
    val = struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8])
    val = np.array(val)
    tim = (val - val[0])*86400;
    
    pointer += n*8-1+8*1+3
    n = struct.unpack('<I', d[pointer:pointer+4])[0]
    reslen.append(n)
    pointer += 4
    val = struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8])
    fre = np.array(val)
    
    pointer += n*8-1
    pointer += 7
    val = struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8])
    dis = np.array(val)
    
    pointer += n*8-1
    while True:
        pointer += 9
        n = struct.unpack('<I', d[pointer:pointer+4])[0]
        
        if n == 0:
            nsensors -= 1
            pointer += 40
            n = struct.unpack('<I', d[pointer:pointer+4])[0]
            
            if nsensors == 0:
                break
        
        reslen.append(n)
        pointer -= 2
        pointer += 3*8
        val = np.array(struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8]))
        timtmp = (val - val[0]) * 86400 
        if (len(timtmp)<max(np.shape((tim)))):
            timtmp=np.append(timtmp,0)
        if (len(timtmp)>max(np.shape((tim)))):
            tim=np.append(tim,0)
        tim=np.vstack([tim,timtmp])
        
        pointer += n*8-1
        pointer += 3
        n = struct.unpack('<I', d[pointer:pointer+4])[0]
        
        pointer += 4
        val = struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8])
        val = np.array(val)
        if (len(val)<max(np.shape((fre)))):
            val=np.append(val,0)
        fre=np.vstack([fre,val])        
        
        pointer += n*8-1
        pointer += 7
        val = struct.unpack('<{}d'.format(n), d[pointer:pointer+n*8])
        if (len(val)<max(np.shape((dis)))):
            val=np.append(val,0)
        dis=np.vstack([dis,val])        

        pointer += n*8-1
    return tim, fre, dis, reslen, ns

def extract_sensor_data(time,freq,dis,reslen,ns):
    """take the formatted raw qsd file and put it into a dataframe, into a csv for later use
    time, freq, dis are 2d arrs as follows:
    arr -> [ [overtone1 sensor1], [overtone2 sensor1], ... ,
    [overtone_n sensor1], [overtone1 sensor2], [overtone2 sensor2], ... , [overtone_n sensor_ns] ]

    Args:
        time (np.Array): formatted time values from raw .qsd
        freq (np.Array): formatted frequency values from raw .qsd
        dis (np.Array): formatted dissipation values from raw .qsd
        reslen (int): reslen is num of total entries (ns * n overtones)
        ns (int): num sensors

    Returns:
        _type_: _description_
    """    
    df = pd.DataFrame()
    reslen = len(reslen)
    n_overtones = int(reslen / ns)

    # ensure lengths are consistent (time and data may be offset by 1)
    if len(time[0]) < len(freq[0]) and len(time[0]) < len(dis[0]):
        global_time = np.insert(time[0], 0, 0)
    else:
        global_time = time[0]    
    df["Time"] = global_time

    # devices use either 1 or 4 sensors, use only 1 sensor
    for i in range(n_overtones):
        cur_overtone = 'fundamental' if i == 0 else ordinal(i * 2 + 1)
        df[f"{cur_overtone}_freq"] = freq[i]
        df[f"{cur_overtone}_dis"] = dis[i]

    # remove 0 entries
    df = df.loc[(df >= 1e-8).all(axis=1)]

    print(df.head)    
    return df

if __name__ == '__main__':
    [tim,fre,dis,reslen,ns]=read_qsd("raw_data/qsense_bsa/BSA.1mgml-1.280723.qsd")

    # for demo only: remove for a "useful" application
    plt.subplot(211)
    for k in range(0,min(np.shape(fre))):
        plt.plot(tim[k,:reslen[k]],fre[k,:reslen[k]]-fre[k][0])
    plt.ylabel('freq. variation (Hz)')
    plt.subplot(212)
    for k in range(0,min(np.shape(dis))):
        plt.plot(tim[k,:reslen[k]],dis[k,:reslen[k]]-dis[k][0])
    plt.xlabel('time (s)')
    plt.ylabel('dissipation (no unit)')
    plt.show()