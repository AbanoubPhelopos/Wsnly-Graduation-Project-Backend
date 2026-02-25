with open("Database/stops.csv", "rb") as f:
    data = f.read(100)
with open("out.txt", "w") as f:
    f.write(repr(data))
