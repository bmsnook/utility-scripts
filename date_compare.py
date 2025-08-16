import datetime
import dateutil.relativedelta as relativedelta

dt_string_formats = {
    r"%Y-%m-%d %H:%M:%S.%f%z",
    r"%Y-%m-%dT%H:%M:%S.%f%z",
    r"%Y-%m-%d %H:%M:%S.%f%Z",
    r"%Y-%m-%dT%H:%M:%S.%f%Z",
    r"%Y-%m-%d %H:%M:%S.%f",
    r"%Y-%m-%dT%H:%M:%S.%f",
    r"%Y-%m-%d %H:%M:%S%z",
    r"%Y-%m-%dT%H:%M:%S%z",
    r"%Y-%m-%d %H:%M:%S%Z",
    r"%Y-%m-%dT%H:%M:%S%Z",
    r"%a %b %d %H:%M:%S %Y %z",
    r"%a %b %d %H:%M:%S %Z %Y",
    r"%Y-%m-%d %H:%M:%S",
    r"%Y-%m-%d %H:%M",
    r"%Y-%m-%d"
}

def read_date_string_to_dtz(dt_string):
    # print(f"INFO: Attempting to convert string \"{dt_string}\"")
    for each_format in dt_string_formats:
        # print(f"DEBUG: testing format: \"{each_format}\"")
        try:
            dt_object = datetime.datetime.strptime(dt_string, each_format)
        except:
            pass
        else:
            return(dt_object.astimezone())
    return(False)

def datetime_1_month_ago():
    dt_now  = datetime.datetime.now().astimezone()
    dt_then = dt_now - relativedelta.relativedelta(months=1)
    return dt_then

def datetime_6_months_ago():
    dt_now  = datetime.datetime.now().astimezone()
    dt_then = dt_now - relativedelta.relativedelta(months=6)
    return dt_then

def datetime_x_months_ago(num_months=3):
    dt_now  = datetime.datetime.now().astimezone()
    dt_then = dt_now - relativedelta.relativedelta(months=num_months)
    return dt_then

def date_more_than_one_month_ago(dt_string):
    dt_target = read_date_string_to_dtz(dt_string)
    if dt_target < datetime_1_month_ago():
        return True
    else:
        return False

def date_more_than_six_months_ago(dt_string):
    dt_target = read_date_string_to_dtz(dt_string)
    if dt_target < datetime_6_months_ago():
        return True
    else:
        return False

def date_more_than_x_months_ago(dt_string, num_months=3):
    dt_target = read_date_string_to_dtz(dt_string)
    if dt_target < datetime_x_months_ago(num_months):
        return True
    else:
        return False
