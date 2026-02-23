import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


def strip_outer_quotes(value: str) -> str:
    s = value.rstrip("\r\n").strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s


def parse_wrapped_csv_line(raw: str):
    line = strip_outer_quotes(raw)
    cols = []
    field = []
    in_quotes = False
    i = 0

    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                field.append('"')
                i += 1
            else:
                in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            cols.append("".join(field))
            field = []
        else:
            field.append(ch)
        i += 1

    cols.append("".join(field))
    return cols


def load_wrapped_csv(path: Path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return [], []
    header = parse_wrapped_csv_line(lines[0])
    rows = [parse_wrapped_csv_line(line) for line in lines[1:] if line.strip()]
    return header, rows


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.sin(dlon / 2) ** 2 * math.cos(lat1) * math.cos(
        lat2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def normalize_name(name: str) -> str:
    value = name.strip()
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "،": " ",
        "/": " ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split())


def main():
    parser = argparse.ArgumentParser(description="Validate wrapped GTFS files.")
    parser.add_argument(
        "--db-path",
        default=str(Path(__file__).resolve().parents[1] / "Database"),
        help="Path to GTFS database folder",
    )
    parser.add_argument(
        "--max-name-spread-m",
        type=float,
        default=300.0,
        help="Max allowed spread for same normalized stop name",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    required = [
        "stops.csv",
        "routes.csv",
        "trips.csv",
        "stop_times.csv",
        "agency.csv",
        "calendar.csv",
        "shapes.csv",
    ]

    for filename in required:
        if not (db_path / filename).exists():
            raise SystemExit(f"Missing required file: {filename}")

    h_stops, stops_rows = load_wrapped_csv(db_path / "stops.csv")
    h_routes, routes_rows = load_wrapped_csv(db_path / "routes.csv")
    h_trips, trips_rows = load_wrapped_csv(db_path / "trips.csv")
    h_stop_times, stop_times_rows = load_wrapped_csv(db_path / "stop_times.csv")

    print("== GTFS Summary ==")
    print(f"stops: {len(stops_rows)} rows, {len(h_stops)} columns")
    print(f"routes: {len(routes_rows)} rows, {len(h_routes)} columns")
    print(f"trips: {len(trips_rows)} rows, {len(h_trips)} columns")
    print(f"stop_times: {len(stop_times_rows)} rows, {len(h_stop_times)} columns")

    stops = {row[0]: row for row in stops_rows if len(row) >= 4}
    routes = {row[0] for row in routes_rows if len(row) >= 1}
    trip_to_route = {row[2]: row[0] for row in trips_rows if len(row) >= 3}
    trip_ids = set(trip_to_route.keys())

    missing_stop_refs = {
        row[1] for row in stop_times_rows if len(row) >= 2 and row[1] not in stops
    }
    missing_trip_refs = {
        row[0] for row in stop_times_rows if len(row) >= 1 and row[0] not in trip_ids
    }
    missing_route_refs = {
        row[0] for row in trips_rows if len(row) >= 1 and row[0] not in routes
    }

    used_stop_ids = {row[1] for row in stop_times_rows if len(row) >= 2}
    orphan_stops = sorted(set(stops.keys()) - used_stop_ids)

    print("\n== Referential Integrity ==")
    print(f"missing stop refs in stop_times: {len(missing_stop_refs)}")
    print(f"missing trip refs in stop_times: {len(missing_trip_refs)}")
    print(f"missing route refs in trips: {len(missing_route_refs)}")
    print(f"orphan stops (not used in stop_times): {len(orphan_stops)}")
    if orphan_stops:
        for stop_id in orphan_stops[:20]:
            row = stops[stop_id]
            print(f"  - {stop_id}: {row[1]} ({row[2]}, {row[3]})")

    exact_duplicate_groups = defaultdict(list)
    for row in stops_rows:
        if len(row) >= 4:
            exact_duplicate_groups[(row[1], row[2], row[3])].append(row[0])
    exact_duplicates = [v for v in exact_duplicate_groups.values() if len(v) > 1]

    print("\n== Stop Duplicates ==")
    print(f"exact duplicate stop groups (name+coords): {len(exact_duplicates)}")

    by_normalized_name = defaultdict(list)
    for row in stops_rows:
        if len(row) >= 4:
            by_normalized_name[normalize_name(row[1])].append(row)

    suspicious_clusters = []
    for name, rows in by_normalized_name.items():
        if len(rows) < 2:
            continue
        max_spread = 0.0
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                try:
                    lat1, lon1 = float(rows[i][2]), float(rows[i][3])
                    lat2, lon2 = float(rows[j][2]), float(rows[j][3])
                except ValueError:
                    continue
                distance = haversine(lat1, lon1, lat2, lon2)
                max_spread = max(max_spread, distance)
        if max_spread > args.max_name_spread_m:
            suspicious_clusters.append((name, len(rows), max_spread))

    suspicious_clusters.sort(key=lambda item: item[2], reverse=True)
    print(
        f"suspicious same-name clusters (> {args.max_name_spread_m:.0f}m): {len(suspicious_clusters)}"
    )
    for name, count, spread in suspicious_clusters[:20]:
        print(f"  - {name}: variants={count}, spread={spread:.1f}m")

    print("\nValidation complete.")


if __name__ == "__main__":
    main()
