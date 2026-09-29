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
        float(utc_time)  # מוודא ששעת ה-GPS היא מספר לפני שהיא מגיעה לחישובים
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


def topspeed(GPSLog, top_speed):  # מקבלת את המדידות ואת שיא המהירות הנוכחי
    if not GPSLog.readings:  # בודקת שקיימות מדידות ברשימה
        return top_speed  # מחזירה את השיא הקיים כשאין מדידה חדשה
    last = GPSLog.readings[-1]["speed_kmh"]  # לוקחת את המהירות מהמדידה האחרונה
    if last < top_speed:  # בודקת אם המהירות האחרונה נמוכה מהשיא
        return top_speed  # משאירה את השיא הקודם
    return last  # מחזירה את המהירות האחרונה בתור השיא החדש


def accelation(GPSLog):  # מחשבת תאוצה בין שתי המדידות האחרונות
    if len(GPSLog.readings) < 2:  # בודקת שיש לפחות שתי מדידות
        return 0  # אי אפשר לחשב תאוצה ממדידה אחת
    previous = GPSLog.readings[-2]  # שומרת את המדידה הקודמת
    current = GPSLog.readings[-1]  # שומרת את המדידה החדשה
    speed_diff = (current["speed_kmh"] - previous["speed_kmh"]) / 3.6  # ממירה את הפרש המהירות למטר לשנייה
    time_diff = (  # מתחילה לחשב את הפרש הזמן בשניות
        int(current["utc_time"][:2]) * 3600  # ממירה את השעות של המדידה החדשה לשניות
        + int(current["utc_time"][2:4]) * 60  # ממירה את הדקות של המדידה החדשה לשניות
        + float(current["utc_time"][4:])  # מוסיפה שניות ושברירי שנייה של המדידה החדשה
        - (  # מתחילה להפחית את זמן המדידה הקודמת
            int(previous["utc_time"][:2]) * 3600  # ממירה את השעות הקודמות לשניות
            + int(previous["utc_time"][2:4]) * 60  # ממירה את הדקות הקודמות לשניות
            + float(previous["utc_time"][4:])  # מוסיפה שניות ושברירי שנייה קודמים
        )  # מסיימת את חישוב זמן המדידה הקודמת
    )  # מסיימת את חישוב הפרש הזמן
    if time_diff < 0:  # בודקת אם שתי המדידות נמצאות משני צדי חצות UTC
        time_diff += 24 * 3600  # מוסיפה יממה כדי לקבל הפרש זמן חיובי
    if time_diff <= 0:  # מונעת חלוקה באפס או בזמן שלילי
        return 0  # מחזירה אפס כשהפרש הזמן אינו תקין
    return speed_diff / time_diff  # מחזירה תאוצה במטר לשנייה בריבוע


def maxtimediffrence(GPSLog, minspeed, maxspeed):  # מוצאת את הזמן הטוב ביותר בין שתי מהירויות
    best_time = -1  # מציינת שעדיין לא נמצאה תוצאה
    start_index = -1  # מציינת שעדיין לא נמצאה מדידת התחלה
    if len(GPSLog.readings) < 2:  # בודקת שיש מספיק מדידות לחישוב זמן
        return best_time  # מחזירה מינוס אחת כשאין מספיק מידע
    for i in range(len(GPSLog.readings)):  # עוברת על כל המדידות שנאספו
        speed = GPSLog.readings[i]["speed_kmh"]  # לוקחת את המהירות במדידה הנוכחית
        if speed <= minspeed:  # בודקת אם זו יכולה להיות נקודת ההתחלה
            start_index = i  # שומרת את מיקום מדידת ההתחלה האחרונה
        if start_index != -1 and speed >= maxspeed:  # בודקת אם הרכב הגיע למהירות הסיום
            start = GPSLog.readings[start_index]["utc_time"]  # לוקחת את זמן ההתחלה
            finish = GPSLog.readings[i]["utc_time"]  # לוקחת את זמן הסיום
            time_diff = (  # מתחילה לחשב את הזמן שעבר
                int(finish[:2]) * 3600  # ממירה את שעת הסיום לשניות
                + int(finish[2:4]) * 60  # ממירה את דקות הסיום לשניות
                + float(finish[4:])  # מוסיפה שניות ושברירי שנייה של הסיום
                - (  # מתחילה להפחית את זמן ההתחלה
                    int(start[:2]) * 3600  # ממירה את שעת ההתחלה לשניות
                    + int(start[2:4]) * 60  # ממירה את דקות ההתחלה לשניות
                    + float(start[4:])  # מוסיפה שניות ושברירי שנייה של ההתחלה
                )  # מסיימת את חישוב זמן ההתחלה
            )  # מסיימת את חישוב הפרש הזמן
            if time_diff < 0:  # בודקת אם המדידה חצתה את חצות UTC
                time_diff += 24 * 3600  # מוסיפה יממה כדי לקבל הפרש חיובי
            if best_time == -1 or time_diff < best_time:  # בודקת אם זו התוצאה הראשונה או הטובה ביותר
                best_time = time_diff  # שומרת את הזמן הטוב ביותר
            start_index = -1  # מסיימת את הריצה ומחכה להתחלה חדשה
    return best_time  # מחזירה את הזמן הטוב ביותר שנמצא


def maxgforce(GPSLog, max_g):  # מעדכנת את כוח ה-G החיובי הגבוה ביותר
    acceleration = accelation(GPSLog) / 9.81  # ממירה את התאוצה ליחידות G
    if acceleration > max_g:  # בודקת אם התאוצה החדשה גבוהה מהשיא
        max_g = acceleration  # שומרת את שיא ה-G החדש
    return max_g  # מחזירה את שיא ה-G הנוכחי


maxspeed = 0  # שומר את המהירות הגבוהה ביותר
maxg = 0  # שומר את כוח ה-G החיובי הגבוה ביותר
time_0_100 = -1  # שומר את הזמן הטוב ביותר מ-3 עד 100 קמ"ש
time_0_50 = -1  # שומר את הזמן הטוב ביותר מ-3 עד 50 קמ"ש
time_0_20 = -1  # שומר את הזמן הטוב ביותר מ-3 עד 20 קמ"ש
time_100_200 = -1  # שומר את הזמן הטוב ביותר מ-100 עד 200 קמ"ש
time_10_60 = -1  # שומר את הזמן הטוב ביותר מ-12 עד 60 קמ"ש


def calculate(gps_log):  # מעדכנת את כל תוצאות הביצועים אחרי מדידה תקינה
    global maxspeed, maxg  # מאפשרת לעדכן את משתני השיא הכלליים
    global time_0_100, time_0_50, time_0_20  # מאפשרת לעדכן את זמני ההאצה הראשונים
    global time_100_200, time_10_60  # מאפשרת לעדכן את זמני ההאצה הנוספים
    if not gps_log.readings:  # בודקת שהתקבלה לפחות מדידה אחת
        return  # מפסיקה אם אין נתונים לחישוב
    maxspeed = topspeed(gps_log, maxspeed)  # מעדכנת את שיא המהירות
    maxg = maxgforce(gps_log, maxg)  # מעדכנת את שיא כוח ה-G
    time_0_100 = maxtimediffrence(gps_log, 3, 100)  # מעדכנת את זמן 0 עד 100
    time_0_50 = maxtimediffrence(gps_log, 3, 50)  # מעדכנת את זמן 0 עד 50
    time_0_20 = maxtimediffrence(gps_log, 3, 20)  # מעדכנת את זמן 0 עד 20
    time_100_200 = maxtimediffrence(gps_log, 100, 200)  # מעדכנת את זמן 100 עד 200
    time_10_60 = maxtimediffrence(gps_log, 12, 60)  # מעדכנת את זמן 10 עד 60

def main():
    gps_log = GPSLog()
    while True:
        gps_line = input("Enter a GPRMC line: ")
        if gps_line.lower() == "quit":
            break
        if gps_log.add(gps_line):
            calculate(gps_log)  # מריצה את החישובים מיד אחרי שכל הבדיקות עברו והמדידה נוספה
            print("Valid GPS data added.")
        else:
            print("Invalid GPS data, not added.")




if __name__ == "__main__":
    main()
