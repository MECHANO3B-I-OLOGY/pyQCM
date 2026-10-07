import re
import struct
import numpy as np
import pandas as pd

from src.analyze import ordinal

'''
QSense .qsd layout (as reverse engineered from sample files)

An INI-style settings section comes first. Each recorded resonance has a
"[...\\Xtal_0_Settings\\Resonance_<k>_Settings]" entry with an "Overtone=<n>"
key and an "Include=<0|1>" key. The fundamental (Resonance_0) is not always
included, so the overtone number must come from the file, not from the
position of the data block.

After the settings, each resonance is stored as one block:

    02 08 00 00                     block tag
    u32 resonance index k           -> Resonance_<k>_Settings
    u32 n                           total samples stored in this block
    u32 seg_count                   number of contiguous recording segments
    seg_count * (u32 start, u32 len) placement of each segment on the
                                    shared sample grid (sum of len == n)
    then 3 arrays, each "0b 00 | u32 n | n * float64":
        time (days), frequency (Hz), dissipation (1e-6)

A resonance that was not included is stored as a block with n == 0 and
seg_count == 0. A block that briefly lost the resonance is stored with
seg_count > 1, and the samples in the gap are simply absent.
'''

BLOCK_TAG = b'\x02\x08\x00\x00'
ARRAY_TAG = b'\x0b\x00'
MAX_RESONANCES = 64
MAX_SEGMENTS = 1 << 16


def _u32(d, pointer):
    return struct.unpack_from('<I', d, pointer)[0]


def _read_overtone_map(d):
    """map resonance index -> overtone number using the first crystal's settings"""
    text = d.decode('latin-1')
    overtones = {}
    for section in re.finditer(r'Xtal_0_Settings\\Resonance_(\d+)_Settings\]([^\[]*)', text):
        match = re.search(r'\bOvertone=(\d+)', section.group(2))
        if match:
            overtones[int(section.group(1))] = int(match.group(1))
    return overtones


def _parse_block_header(d, pointer):
    """try to parse a resonance block header (after the block tag) at pointer

    Returns:
        tuple: (resonance index, n, segments, pointer to first array tag) or None if invalid
    """
    if pointer + 16 > len(d):
        return None
    idx, n, seg_count = struct.unpack_from('<III', d, pointer)
    if idx >= MAX_RESONANCES or seg_count > MAX_SEGMENTS:
        return None
    pointer += 12
    if n == 0:
        # excluded resonance: no segments and no arrays
        if seg_count != 0:
            return None
        return idx, 0, [], pointer
    if seg_count == 0 or pointer + 8 * seg_count + 6 > len(d):
        return None
    segs = np.frombuffer(d, dtype='<u4', count=2 * seg_count, offset=pointer).reshape(-1, 2).astype(np.int64)
    pointer += 8 * seg_count
    if segs[:, 1].sum() != n or d[pointer:pointer + 2] != ARRAY_TAG or _u32(d, pointer + 2) != n:
        return None
    return idx, n, [(int(s), int(l)) for s, l in segs], pointer


def _read_array(d, pointer, n):
    """read one '0b 00 | u32 n | n doubles' array, returns (values, pointer after array)"""
    if d[pointer:pointer + 2] != ARRAY_TAG or _u32(d, pointer + 2) != n:
        raise ValueError(f"Corrupt .qsd file: expected data array of length {n} at byte {pointer}")
    pointer += 6
    if pointer + n * 8 > len(d):
        raise ValueError(f"Corrupt .qsd file: data array at byte {pointer} runs past end of file")
    return np.frombuffer(d, dtype='<f8', count=n, offset=pointer), pointer + n * 8


def _find_first_block(d, start):
    """locate the first valid resonance block at or after start"""
    pointer = d.find(BLOCK_TAG, start)
    while pointer != -1:
        header = _parse_block_header(d, pointer + 4)
        if header is not None and header[1] > 0:
            return pointer
        pointer = d.find(BLOCK_TAG, pointer + 1)
    raise ValueError("Could not find any resonance data in .qsd file")


def read_qsd(filename):
    """read time, frequency, and dissipation of each recorded resonance of the first sensor

    Returns:
        tuple: (time, freq, dis, overtones)
            time, freq, dis: 2D arrays (one row per recorded resonance) on a shared sample grid,
                with NaN where a resonance has no sample (e.g. lost resonance)
            overtones: overtone number of each row
    """
    with open(filename, 'rb') as f:
        d = f.read()

    overtone_map = _read_overtone_map(d)
    settings_end = d.rindex(b'XtalDriveTimeFloat')
    pointer = _find_first_block(d, settings_end)

    blocks = []
    last_idx = -1
    while d[pointer:pointer + 4] == BLOCK_TAG:
        header = _parse_block_header(d, pointer + 4)
        # resonance indices only increase within one sensor, stop at the next sensor's data
        if header is None or header[0] <= last_idx:
            break
        idx, n, segs, pointer = header
        last_idx = idx
        if n == 0:
            continue
        tim, pointer = _read_array(d, pointer, n)
        fre, pointer = _read_array(d, pointer, n)
        dis, pointer = _read_array(d, pointer, n)
        blocks.append((idx, segs, tim, fre, dis))

    if not blocks:
        raise ValueError("No recorded resonances found in .qsd file")

    # place each segment on the shared sample grid so all overtones stay time aligned
    grid_len = max(s + l for _, segs, *_ in blocks for s, l in segs)
    time, freq, dis = (np.full((len(blocks), grid_len), np.nan) for _ in range(3))
    overtones = []
    for row, (idx, segs, tim, fre, di) in enumerate(blocks):
        overtones.append(overtone_map.get(idx, 2 * idx + 1))
        src = 0
        for start, length in segs:
            time[row, start:start + length] = tim[src:src + length]
            freq[row, start:start + length] = fre[src:src + length]
            dis[row, start:start + length] = di[src:src + length]
            src += length

    return time, freq, dis, overtones


def extract_sensor_data(time, freq, dis, overtones):
    df = pd.DataFrame()

    # each resonance is measured sequentially, use the first recorded timestamp of each sample
    first_valid = np.argmax(~np.isnan(time), axis=0)
    global_time = time[first_valid, np.arange(time.shape[1])]
    df["Time"] = (global_time - np.nanmin(global_time)) * 86400

    for i, overtone in enumerate(overtones):
        cur_overtone = 'fundamental' if overtone == 1 else ordinal(overtone)
        df[f"{cur_overtone}_freq"] = freq[i]
        df[f"{cur_overtone}_dis"] = dis[i]

    df = df.loc[(df >= 1e-8).all(axis=1)]
    return df
