AI_FIXED = {
    "00": 18,  # SSCC
    "01": 14,  # GTIN
    "11": 6,   # MFG
    "17": 6    # EXP
}

AI_VARIABLE = ["10","21","30","37","92","240"]
ALL_AIS = ["00","01","10","11","17","21","30","37","92","240"]

def normalize_raw(raw):
    return raw.replace('\x1d','|').replace('\u001d','|').replace('(','').replace(')','')

def decode_gs1(raw):
    raw = normalize_raw(raw)
    i = 0
    data = {}

    while i < len(raw):
        # detect AI
        if raw[i:i+3] == "240":
            ai = "240"
            start = i + 3
        else:
            ai = raw[i:i+2]
            start = i + 2

        # FIXED
        if ai in AI_FIXED:
            ln = AI_FIXED[ai]
            data[ai] = raw[start:start+ln]
            i = start + ln

        # VARIABLE
        elif ai in AI_VARIABLE:
            end = len(raw)
            pipe = raw.find('|', start)
            if pipe != -1:
                end = pipe

            for nxt in ALL_AIS:
                p = raw.find(nxt, start)
                if p != -1 and p < end:
                    end = p

            data[ai] = raw[start:end]
            i = end

        else:
            i += 1

    return data

