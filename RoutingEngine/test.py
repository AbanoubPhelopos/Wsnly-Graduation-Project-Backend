import csv, sys

def stripOuterQuotes(s):
    s = s.rstrip('\r\n \t').lstrip(' \t')
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s

def parseCSVLine(rawLine):
    line = stripOuterQuotes(rawLine)
    cols = []
    field = ""
    inQuotes = False
    
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"':
            if inQuotes and i + 1 < len(line) and line[i+1] == '"':
                field += '"'
                i += 1
            else:
                inQuotes = not inQuotes
        elif c == ',' and not inQuotes:
            cols.append(field)
            field = ""
        else:
            field += c
        i += 1
    cols.append(field)
    return cols

def main():
    try:
        with open('Database/stops.csv', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error opening file: {e}")
        return

    success = 0
    failed = 0
    for i in range(1, len(lines)):
        line = lines[i]
        cols = parseCSVLine(line)
        if len(cols) >= 4:
            try:
                lat = float(cols[2])
                lon = float(cols[3])
                success += 1
            except Exception as e:
                failed += 1
                if failed <= 5:
                    print(f"Failed to parse floats at line {i+1}: cols={cols}")
        else:
            failed += 1
            if failed <= 5:
                print(f"Too few cols at line {i+1}: {cols}")
    print(f"Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    main()
