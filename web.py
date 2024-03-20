import os
import wifi

# if is connected to wifi
if not wifi.radio.ipv4_address:

    try: 
        have_net = False
        for network in wifi.radio.start_scanning_networks():
            print(network, network.ssid, network.channel, end="")
            if network.ssid == os.getenv("STELLA_WIFI_SSID"):
                print(" Found", network.ssid)
                have_net = True
                break
            else:
                have_net = False
                print("")
    except Exception as e:
        print("Error scanning for networks", e)
        have_net = False
    finally:
        wifi.radio.stop_scanning_networks() 

    if have_net:
        print("Connecting to", os.getenv("STELLA_WIFI_SSID"))
        wifi.radio.connect(os.getenv("STELLA_WIFI_SSID"), os.getenv("STELLA_WIFI_PASSWORD"))
        print("Connected as ip address", wifi.radio.ipv4_address)
    else:
        print("No network found")
else:
    print("Already connected as ip address", wifi.radio.ipv4_address)

import socketpool
import wifi
from adafruit_httpserver import Server, Request, JSONResponse, GET, POST, PUT, DELETE, ChunkedResponse, FileResponse, MIMETypes
import gc
from adafruit_ticks import ticks_ms, ticks_diff
import time

pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, debug=True)

@server.route("/api/mem", [GET], append_slash=True)
def api_mem(request: Request):
    mem = {'mem_alloc': gc.mem_alloc(),
        'mem_free': gc.mem_free(),
        'mem_total': gc.mem_alloc() + gc.mem_free()}
   
    # Get objects
    if request.method == GET:
        return JSONResponse(request, mem)
    

@server.route("/graph2.html", [GET], append_slash=True)
def graph2_html(request: Request):
    return FileResponse(request, "graph2.html", "/static")

@server.route("/graph2.js", [GET], append_slash=True)
def graph2_js(request: Request):
    return FileResponse(request, "graph2.js", "/static")
    
# iotawat emulation
@server.route("/status", [GET], append_slash=True)
def status(request: Request):
    ret = {"device":{"name":'BOX',"timediff":-8,"allowdst":False,"update":"MINOR"}}
    return JSONResponse(request, ret)

# saved graphs
@server.route("/graph/getallplus", [GET], append_slash=True)
def getallplus(request: Request):
    return JSONResponse(request, [])

@server.route("/query", [GET], append_slash=True)
def query(request):
    # query parameter 'show'
    show = request.query_params.get('show')
    format = request.query_params.get('format')
    if show and show == 'series':
        series = []
        for i, name in enumerate(server.history.columns):
            if name == 'timestamp': continue
            unit = server.column_units[i]
            series.append({'name':name, 'unit': unit})
        return JSONResponse(request, {'series': series} )
    # query?format=json&header=yes&resolution=high&missing=null&begin=d&end=s&select=[time.utc.unix,Input_1.Watts.d1]&group=auto
    elif format and format == 'json':
        # Get Time Range
        begin_t = parse_time_arg(request.query_params.get('begin'))
        end_t = parse_time_arg(request.query_params.get('end'))
        if begin_t == 0 or end_t == 0:
            begin_t = parse_time_arg("s-30m")
            end_t = parse_time_arg("s")

        # set range
        range = [begin_t, end_t]

        # Get Columns Requested
        print(request.query_params.get('select'))
        select = request.query_params.get('select')
        # remove first and last characters
        select = select[1:-1]
        # split string by comma
        list_of_inputs = select.split(',')
        selected_col_names = []
        selected_col_indices = []
        selected_col_units = []
        for c in list_of_inputs:
            c_name = c.split('.')[0]
            c_unit = c.split('.')[1]
            selected_col_names.append(c_name)
            selected_col_units.append(c_unit)

        # select the right interval to group by
        intervals = (5, 10, 15, 20, 30, 60, 120, 300, 600, 1200, 1800, 3600, 7200, 14400, 21600, 28800)
        rawInterval = (end_t - begin_t) / 800 # 2.2 seconds at 800 points. Also, 2.2 seconds at 400 points. Huh.
        interval = 86400
        for i in range(len(intervals)):
            if rawInterval <= intervals[i]:
                interval = intervals[i]
                break

        # Get Data
        data = []
        t = ticks_ms()
        # 2.1s retrieve data, 4.66 recieve all data in browser, with buffered output
        # 5s -> 20m 7 days: 20seconds
        num_rows = 0
        for time,count, a in server.history.arrays_by_time(begin_t, end_t, group_size=interval):
            time = int(time)
            row = [time] # convert seconds 2000 to 1970
            for i, name in enumerate(selected_col_names):
                if name == 'time': continue
                idx = server.history.C[name]              
                row.append(a[idx])
            data.append(row)
            num_rows += 1
        delta = ticks_diff(ticks_ms(), t) 
        print('items_grouped_cols Time = {:6.3f}ms'.format(delta))

        return JSONResponse(request, { "range": [begin_t, end_t], "group_size": interval, "num_processed":server.history.last_records_processed, "num_rows": num_rows, "labels": selected_col_names, "data": data} )
    
        # unbuffered output - takes 32-60 seconds, not good!!
        # def generate_response():
        #     yield '{"range":[' + str(begin_t +946_684_800) + ',' + str(end_t+946_684_800) + '],"labels":' + str(selected_col_names).replace("'",'"') + ',"data":['
        #     for row, is_last in app.fw.data_db.items_grouped_cols(begin_t,end_t,interval,selected_col_names):
        #         row[0] += 946_684_800
        #         if not is_last:
        #             yield str(row) + ','
        #         else:
        #             yield str(row)
        #     yield ']}'

        # return generate_response()
    
            
# convert time arg to seconds_since_2000
def parse_time_arg(arg):
    # localtime / gmtime
    _year=0 # includes the century (for example 2014).
    _month=1 #is 1-12
    _mday=2 #is 1-31
    _hour=3 #is 0-23
    _minute=4 #is 0-59
    _second=5 #is 0-59
    _weekday=6 #is 0-6 for Mon-Sun
    _yearday=7 #is 1-366

    # check for UNIX_time
    arg_len = len(arg)
    if arg_len == 10:
        # assume input is seconds since 1970, return since 1970
        return int(arg) #- 946_713_600
    elif arg_len == 13:
        # assume input is milliseconds since 1970, return since 1970
        return int(arg)/1000 #- 946_713_600
    
    # Check for relative time 
    # https://github.com/boblemaire/IoTaWatt/blob/90c12bb2887030c91372493bb3306ec12e3d5702/Docs/query.rst#relative-time
    global RTC
    tm = RTC.datetime
    tm = list(tm)     # copy a tuple into a list
    idx = 0
    # python switch on first character of arg
    if arg[idx] == 'y'  : tm[_month] = 0 ; tm[_mday] = 1 ; tm[_hour] = 0 ; tm[_minute] = 0 ; tm[_second] = 0
    elif arg[idx] == 'M':                  tm[_mday] = 1 ; tm[_hour] = 0 ; tm[_minute] = 0 ; tm[_second] = 0
    elif arg[idx] == 'd':                                  tm[_hour] = 0 ; tm[_minute] = 0 ; tm[_second] = 0
    elif arg[idx] == 'h':                                                  tm[_minute] = 0 ; tm[_second] = 0
    elif arg[idx] == 'm':                                                                    tm[_second] = 0
    elif arg[idx] == 's': pass
    elif arg[idx] == 'w':                  tm[_mday] -= tm[_weekday] ; tm[_hour] = 0 ; tm[_minute] = 0 ; tm[_second] = 0

    # modifiers
    idx = idx + 1
    while idx < len(arg):
        if arg[idx] != '+' and arg[idx] != '-': return 0
        mult, digits = strtol(arg[idx:])
        if mult == 0: return 0
        idx = idx + digits
        if idx >= len(arg): return 0
        if arg[idx] == 'y': tm[_year] += mult
        elif arg[idx] == 'M': tm[_month] += mult
        elif arg[idx] == 'w': tm[_mday] += 7 * mult
        elif arg[idx] == 'd': tm[_mday] += mult
        elif arg[idx] == 'h': tm[_hour] += mult
        elif arg[idx] == 'm': tm[_minute] += mult
        elif arg[idx] == 's': tm[_second] += mult - (mult % 5)
        else: return 0
        idx = idx + 1

    # convert to seconds since 2000
    return int(time.mktime(time.struct_time(tm)))

def strtol(s):
    #
    # Convert a string to a long integer.
    #
    # To do:  handle overflow
    #
    # s       string to convert
    # endptr  pointer to store terminating character
    # base    number base to use
    #   
    # returns long integer value, length of number
    # base 10 only
    #
    # skip leading white space
    while s[0] == ' ':
        s = s[1:]
    # check for sign
    sign = 1
    d = 0
    if s[0] == '-':
        sign = -1
        s = s[1:]
        d=d+1
    elif s[0] == '+':
        s = s[1:]
        d=d+1
    # check for base
    base = 10
    # if s[0:2] == '0x':
    #     base = 16
    #     s = s[2:]
    #     d=d+2
    # elif s[0] == '0':
    #     base = 8
    #     d=d+1
    # convert
    n = 0
    while True:
        c = s[0]
        if c >= '0' and c <= '9':
            n = n * base + ord(c) - ord('0')
        #elif c >= 'a' and c <= 'f':
        #    n = n * base + ord(c) - ord('a') + 10
        #elif c >= 'A' and c <= 'F':
        #    n = n * base + ord(c) - ord('A') + 10
        else:
            break
        s = s[1:]
        d=d+1
        if len(s) == 0:
            break
    return n * sign, d

if wifi.radio.ipv4_address:

    server.start(str(wifi.radio.ipv4_address),port=8001)

    pool_result = server.poll()

else:
    server = None

class WebServer:

    def __init__(self, history, rtc, column_units):
        global server, RTC
        if server is None:
            self = None
            return
        self.server = server
        self.server.column_units = column_units
        self.server.history = history
        RTC = rtc
        return 

    def start(self):
        pass

    def stop(self):
        return self.server.stop()

    def poll(self):
        return self.server.poll()
