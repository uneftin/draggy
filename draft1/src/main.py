def is_valid_gprmc(gps_line):
    fields = gps_line.strip().split("*")[0].split(",")
    if len(fields) != 13:
        return False
    (message_type, utc_time, status, latitude_raw, latitude_direction,
     longitude_raw, longitude_direction, speed_knots, course_degrees,
     date, _, _, _) = fields
    if message_type not in ("$GPRMC", "$GNRMC"):
        return False
    if status != "A":
        return False
    if latitude_direction not in ("N", "S") or longitude_direction not in ("E", "W"):
        return False
    if len(utc_time) < 6 or len(date) != 6:
        return False
    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
        float(speed_knots)
        float(course_degrees)
    except ValueError:
        return False
    if not (0 <= latitude <= 9060):
        return False
    if not (0 <= longitude <= 18060):
        return False
    return True


def parse_gprmc(gps_line):
    fields = gps_line.split("*")[0].split(",")
    message_type = fields[0]
    utc_time = fields[1]
    status = fields[2]
    latitude_raw = fields[3]
    latitude_direction = fields[4]
    longitude_raw = fields[5]
    longitude_direction = fields[6]
    speed_knots = float(fields[7])
    course_degrees = float(fields[8])
    date = fields[9]
    speed_kmh = round(speed_knots * 1.852, 3)

    return {
        "message_type": message_type,
        "utc_time": utc_time,
        "status": status,
        "latitude_raw": latitude_raw,
        "latitude_direction": latitude_direction,
        "longitude_raw": longitude_raw,
        "longitude_direction": longitude_direction,
        "speed_kmh": speed_kmh,
        "course_degrees": course_degrees,
        "date": date,
    }



def process(gps_line):
    if not is_valid_gprmc(gps_line):
        print("Invalid GPS data, skipping.")
        return None
    data = parse_gprmc(gps_line)
    return data


class GPSLog:
    # מחזיק את כל המדידות הנכונות שנקלטו

    def __init__(self):
        self.readings = []

    def add(self, gps_line):
        if not is_valid_gprmc(gps_line):
            return False
        self.readings.append(parse_gprmc(gps_line))
        return True


def calculate(GPSLog):
    if not GPSLog.readings:
        return
    # Perform calculations on the readings


def main():
    gps_log = GPSLog()
    while True:
        gps_line = input("Enter a GPRMC line: ")
        if gps_line.lower() == "quit":
            break
        if gps_log.add(gps_line):
            print("Valid GPS data added.")
        else:
            print("Invalid GPS data, not added.")




if __name__ == "__main__":
    main()
