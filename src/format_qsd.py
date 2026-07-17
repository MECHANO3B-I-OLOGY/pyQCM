import struct
import numpy as np
import pandas as pd

from src.analyze import ordinal

def _safe_unpack_doubles(d, pointer, n):
    """Unpack up to n little-endian doubles starting at pointer.

    Some files have a channel whose recording was
    cut short, so the array on disk is shorter than the length declared
    elsewhere in the file. Rather than crashing with a struct.error, read
    as many doubles as are actually available and pad the remainder with
    zeros -- consistent with how mismatched overtone lengths are already
    handled elsewhere in this parser.
    """
    available_bytes = max(0, len(d) - pointer)
    available_n = available_bytes // 8
    read_n = min(n, available_n)
    val = np.array(struct.unpack('<{}d'.format(read_n), d[pointer:pointer + read_n * 8]))
    if read_n < n:
        val = np.append(val, np.zeros(n - read_n))
    return val

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
    if newn == n:
        # newest file format has no padding element at all: the repeated
        # size field matches n exactly, with no extra 16-byte block and no
        # "+1" sample to skip later.
        no_pad = True
    elif newn != n+1:
        # older intermediate format inserts an extra 16-byte block between
        # the 0xee sentinel and the size-check field. Try stepping over it.
        pointer += 16
        newn = struct.unpack('<I', d[pointer:pointer+4])[0]
        if newn != n+1:
            raise Exception("Invalid size repetition")
        no_pad = False
    else:
        no_pad = False

    pointer += 4     # skip length information
    if d[pointer] == 0x02:
        pointer += 8 # added to validate BSA dataset
    if d[pointer] != 0x01:
        raise Exception("Invalid value: != 0x01")
    pointer += 12
    if d[pointer] != 0x0b:
        raise Exception("Invalid value: != 0x0b")

    pointer += 6
    val = _safe_unpack_doubles(d, pointer, n)
    tim = (val - val[0])*86400;
    
    pointer += n*8-1+3 if no_pad else n*8-1+8*1+3
    n = struct.unpack('<I', d[pointer:pointer+4])[0]
    reslen.append(n)
    pointer += 4
    fre = _safe_unpack_doubles(d, pointer, n)
    
    pointer += n*8-1
    pointer += 7
    dis = _safe_unpack_doubles(d, pointer, n)
    
    pointer += n*8-1
    while True:
        pointer += 9
        if pointer + 4 > len(d):
            break  # ran out of file before the next block header
        n = struct.unpack('<I', d[pointer:pointer+4])[0]
        
        if n == 0:
            nsensors -= 1
            pointer += 40
            if pointer + 4 > len(d):
                break
            n = struct.unpack('<I', d[pointer:pointer+4])[0]
            
            if nsensors == 0:
                break
        
        reslen.append(n)
        pointer -= 2
        pointer += 3*8
        val = _safe_unpack_doubles(d, pointer, n)
        timtmp = (val - val[0]) * 86400 
        if (len(timtmp)<max(np.shape((tim)))):
            timtmp=np.append(timtmp,0)
        if (len(timtmp)>max(np.shape((tim)))):
            tim=np.append(tim,0)
        tim=np.vstack([tim,timtmp])
        
        pointer += n*8-1
        pointer += 3
        if pointer + 4 > len(d):
            break
        n = struct.unpack('<I', d[pointer:pointer+4])[0]
        
        pointer += 4
        val = _safe_unpack_doubles(d, pointer, n)
        if (len(val)<max(np.shape((fre)))):
            val=np.append(val,0)
        fre=np.vstack([fre,val])        
        
        pointer += n*8-1
        pointer += 7
        val = _safe_unpack_doubles(d, pointer, n)
        if (len(val)<max(np.shape((dis)))):
            val=np.append(val,0)
        dis=np.vstack([dis,val])        

        pointer += n*8-1
    return tim, fre, dis, reslen, ns

def extract_sensor_data(time,freq,dis,reslen,ns):
    df = pd.DataFrame()
    reslen = len(reslen)
    n_overtones = int(reslen / ns)

    # a file with only a single overtone never gets stacked into a 2D
    # array by read_qsd, so normalize to 2D here for consistent indexing
    time = np.atleast_2d(time)
    freq = np.atleast_2d(freq)
    dis = np.atleast_2d(dis)

    if len(time[0]) < len(freq[0]) and len(time[0]) < len(dis[0]):
        global_time = np.insert(time[0], 0, 0)
    else:
        global_time = time[0]    
    df["Time"] = global_time

    for i in range(n_overtones):
        cur_overtone = 'fundamental' if i == 0 else ordinal(i * 2 + 1)
        df[f"{cur_overtone}_freq"] = freq[i]
        df[f"{cur_overtone}_dis"] = dis[i]

    df = df.loc[(df >= 1e-8).all(axis=1)]
    return df