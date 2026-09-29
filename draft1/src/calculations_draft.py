def topspeed(GPSLog, top_speed):
    if not GPSLog.readings:
        return top_speed

    last = GPSLog.readings[-1]["speed_kmh"]
    if last < top_speed:
        return top_speed
    return last


def accelation(GPSLog):
    if len(GPSLog.readings) < 2:
        return 0

    previous = GPSLog.readings[-2]
    current = GPSLog.readings[-1]

    speed_diff = (current["speed_kmh"] - previous["speed_kmh"]) / 3.6
    time_diff = (
        int(current["utc_time"][:2]) * 3600
        + int(current["utc_time"][2:4]) * 60
        + float(current["utc_time"][4:])
        - (
            int(previous["utc_time"][:2]) * 3600
            + int(previous["utc_time"][2:4]) * 60
            + float(previous["utc_time"][4:])
        )
    )

    if time_diff <= 0:
        return 0

    return speed_diff / time_diff


def maxtimediffrence(GPSLog, minspeed, maxspeed):
    best_time = -1
    start_index = -1

    if len(GPSLog.readings) < 2:
        return best_time

    for i in range(len(GPSLog.readings)):
        speed = GPSLog.readings[i]["speed_kmh"]

        if speed <= minspeed:
            start_index = i

        if start_index != -1 and speed >= maxspeed:
            start = GPSLog.readings[start_index]["utc_time"]
            finish = GPSLog.readings[i]["utc_time"]

            time_diff = (
                int(finish[:2]) * 3600
                + int(finish[2:4]) * 60
                + float(finish[4:])
                - (
                    int(start[:2]) * 3600
                    + int(start[2:4]) * 60
                    + float(start[4:])
                )
            )

            if time_diff < 0:
                time_diff += 24 * 3600

            if best_time == -1 or time_diff < best_time:
                best_time = time_diff

            start_index = -1

    return best_time


def maxgforce(GPSLog, max_g):
    acceleration = accelation(GPSLog) / 9.81
    if acceleration > max_g:
        max_g = acceleration
    return max_g


maxspeed = 0
maxg = 0
time_0_100 = -1
time_0_50 = -1
time_0_20 = -1
time_100_200 = -1
time_10_60 = -1


def calculate(gps_log):
    global maxspeed, maxg
    global time_0_100, time_0_50, time_0_20
    global time_100_200, time_10_60

    if not gps_log.readings:
        return

    maxspeed = topspeed(gps_log, maxspeed)
    maxg = maxgforce(gps_log, maxg)
    time_0_100 = maxtimediffrence(gps_log, 3, 100)
    time_0_50 = maxtimediffrence(gps_log, 3, 50)
    time_0_20 = maxtimediffrence(gps_log, 3, 20)
    time_100_200 = maxtimediffrence(gps_log, 100, 200)
    time_10_60 = maxtimediffrence(gps_log, 12, 60)
