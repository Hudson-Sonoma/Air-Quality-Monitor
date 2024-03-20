# his.py 

import os, struct
import struct
from ulab import numpy as np
from adafruit_ticks import ticks_ms, ticks_diff
from collections import OrderedDict
import gc
import time

def timed_function(f, *args, **kwargs):
    def new_func(*args, **kwargs):
        t = ticks_ms()
        result = f(*args, **kwargs)
        delta = ticks_diff(ticks_ms(),t)
        try:
            fname = f.__name__
        except AttributeError:  # generally not present in CircuitPython builds, unless enabled.
            fname = f.__class__.__name__
        print('Function {} Time = {:6.3f}ms'.format(fname,delta))
        return result
    return new_func

# History class
# Copyright (C) 2023 Salvatore Sanfilippo <antirez@gmail.com>
# All Rights Reserved
#
# This code is released under the BSD 2 clause license.
# See the LICENSE file for more information
# This class implements an append only history file. In order to
# avoid any seek, and in general to demand too much to the very
# rudimental filesystem of the ESP32, we use two files, and always
# append to one of them, up 'histlen+1' entries are reached.
#
# Files are created inside the specified folder, and are called
# hist1 and hist2. We append to only one of the two. Our records
# are fixed length, so just from the file length we can know how
# many items each file contains, and we can seek at fixed offsets
# in order to read specific items.
#
# This is how the append algorithm works:
#
# To select where to append among hist1 and hist2:
# * If no file exists, we append to hist1.
# * If only a single file exists, we use it if it has less than histlen+1
#   entries.
# * If only a single file exists, but it reached histlen+1 len (or more), we
#   append to the other file (creating it).
# * If two files exist, we pick the shortest one, that is the only one
#   that didn't yet reach histlen+1 entries. In case of corruptions or
#   bugs, and we found both files having the same length, we use the
#   first file. In case the histlen changed and now even the shortest file is
#   larger than histlen+1, we still select the shortest file among the two,
#   and append there.
#
# To append to the selected file:
# * When we append a new entry to the selected file, if appending to it
#   will make it reach histlen+1 or more (can happen if histlen changed)
#   entires, we delete the other file, then append.
#
# To read entries from the history files:
# * If there is only one file, it contains the latest N entries.
# * If there are two files, the longer contains the oldest N
#   messages and the shortest contains additional M newest messages. So
#   the algorithm knows to have a total history of M+N and will seek
#   in one or the other file according to the requested index. Entries
#   indexes, to retrieve the history, are specified as indexes from the
#   newest to the oldest entry. So an index of 0 means the newest entry
#   stored, 1 is the previous one, and so forth.
#
# This way we are sure that at least 'histlen' entries are always stored
# on disk, just using two operations: append only writes and file deletion.
class History:
    def __init__(self, folder, histlen=100, recordsize=25, padding=b'\0', columns=[]):
        try:
            os.mkdir(folder)
        except:
            pass
        self.files = [folder+"/hist1",folder+"/hist2"]
        self.histlen = histlen
        self.recordsize = recordsize
        self.padding = padding
        # everything stored as a float - 4 bytes
        assert self.recordsize >= len(columns) * 4
        self.columns = columns
        self.C  = OrderedDict()
        for i, d in enumerate(self.columns): 
            self.C[d] = i
        self.last_records_processed = 0

    def build_array(self, **kwargs):
        a = np.zeros(len(self.columns), dtype=np.float)
        for colname, v in kwargs.items():
            col_idx = self.C[colname]
            a[col_idx] = v
        return a
    
    def append_array(self, **kwargs):
        time = kwargs.pop('timestamp', None)
        a = self.build_array(**kwargs)
        return self.append(time, a.tobytes())

    # Return number of records len of first and second file.
    # Non existing files are reported as 0 len.
    def get_file_size(self,file_id):
        try:
            flen = int(os.stat(self.files[file_id])[6] / (self.recordsize+8))
        except:
            flen = 0
        return flen

    # Return the ID (0 or 1) of the file we should append new entries to.
    # See algorithm in the top comment of this class.
    def select_file(self):
        len0 = self.get_file_size(0)
        len1 = self.get_file_size(1)

        # Files are the same length. Happens when no file exists (both zero)
        # or in case of corrutpions / bugs if they are non zero. Use the
        # first file.
        if len0 == len1:
            try:
                os.unlink(self.files[1])
            except:
                pass
            return 0

        # Only a single file exists. We use it if it is still within size
        # limits.
        if len0 == 0 or len1 == 0:
            file = 0 if len0 else 1
            file_len = max(len0,len1)

            if file_len <= self.histlen:  # was <= +1
                return file
            else:
                # if we reached histlen, switch file.
                return (file+1)%2

        # Both files exist, select the smaller one.
        return 0 if len0 < len1 else 1

    def append(self, time, data):
        if (len(data) > self.recordsize):
            print("[history] Data to append is larger than record size");
            return False

        file_id = self.select_file()
        file_name = self.files[file_id]
        print("b",end="")
        # Delete the other file if we are appending the last
        # entry in the current file.
        if self.get_file_size(file_id) >= (self.histlen):
            try:
                os.unlink(self.files[(file_id+1)%2])
            except:
                pass

        # The only record header we have is 8 bytes of length + time
        # information. Our records are fixed size, so the remaning
        # space is just padding.
        padding_bytes = self.padding * (self.recordsize - len(data))
        record = struct.pack("<LL",len(data),time) + data + padding_bytes
        print("c",end="")
        f = open(file_name,'ab')
        print("d",end="")
        f.write(record)
        print("e",end="")
        f.close()
        print("f",end="")
        #print("time: {}, file_id: {}, filesize: {}".format(time, file_id, self.get_file_size(file_id)))
        return True

    # Total number of records in our history
    def get_num_records(self):
        return self.get_file_size(0)+self.get_file_size(1)
    
    # Return 
    def get_records_from_time(self, time, count=1):
        end_time = self.get_records(0,1)[0]['time']
        start = (end_time-time)//self.period + 1
        print("end_time %d, num: %d" % (end_time, start))
        records = self.get_records(0, start)
        for i in range(len(records)):
            if records[i]['time'] > time:
                break
        i = i - 1
        end = min(i+count, len(records))
        print("effective index: %d, count: %d" % (len(records) - end, end-i))
        return records[i:end]
    
    # Return count, index
    def get_index_from_time(self, time, count=1):
        end_time = self.get_records(0,1)[0]['time']
        start = (end_time-time)//self.period + 1
        records = self.get_records(0, start)
        for i in range(len(records)):
            if records[i]['time'] > time:
                break
        i = i - 1
        end = min(i+count, len(records))
        count = end - i
        index = len(records) - end
        return index, count

    # Return stored entries, starting at 'index' and for 'count' total
    # items (or less, if there are less entries stored than the ones
    # requested). An index of 0 means the last entry stored (so the newest)
    # 1 is the penultimate record stored and so forth. The method returns
    # an array of items.
    def get_records(self, index_from_end, count=1):
        if count == 0: return []
        # Order files according to length. We need to read from the
        # bigger file and proceed to the smaller file (if there is one)
        # and if the records count requires so.
        lens = self.get_file_size(0), self.get_file_size(1)
        if lens[0] > lens[1]:
            files = [0,1]
        else:
            files = [1,0]
            lens = lens[1],lens[0]

        total_records = lens[0] + lens[1]

        if total_records == 0: return []

        # Normalize index according to actual history len
        if index_from_end >= total_records: 
            index_from_end = total_records-1

        # Turn the index under an offset in the whole history len,
        # so that 0 would be the oldest entry stored, and so forth:
        # it makes more sense to work with offsets here, but for the API
        # it makes more sense to reason in terms of "last N items".
        last = total_records - index_from_end - 1
        first = last - count + 1
        first = max(first,0)


        def record_index_to_file_and_offset(idx,len0,len1):
            if idx < len0:
                return (0,idx)
            else:
                return (1,idx-len0)

        last_file = None
        f = None
        result = []
        #print("count_available: %d" % count_available)
        #print("lens[0], lens[1]=%d,%d" % (lens[0],lens[1]))
        for r in range(first,last+1):
            file_no,offset = record_index_to_file_and_offset(r,lens[0],lens[1])
            #print(r)
            if file_no != last_file:
                if f:
                    f.close()
                if lens[file_no] == 0: 
                    break
                #print("Opening file %d" % file_no)
                #print("file: %s" % self.files[files[file_no]])
                f = open(self.files[files[file_no]],'rb')
                f.seek(offset*(8+self.recordsize),0)
                last_file = file_no
            rlen,time = struct.unpack("<LL",f.read(8))  # 4 for time.
            data = f.read(self.recordsize)[0:rlen]
            result.append({
                'time':time, 'data':data 
                })

        return result


        # Load results from one or both files.
        # result = []
        # for i in range(2):
        #     #print("From file %d: count:%d seek:%d" % (files[i],subcount[i],seek[i]))
        #     if subcount[i] == 0: continue
        #     f = open(self.files[files[i]],'rb')
        #     #print("Seeking to {}, {}".format(seek[i],seek[i]*(4+self.recordsize)))
        #     f.seek(seek[i]*(4+self.recordsize))
        #     for c in range(subcount[i]):
        #         rlen = struct.unpack("<L",f.read(4))[0]
        #         #print("Reading %d bytes" % rlen)
        #         data = f.read(self.recordsize)[0:rlen]
        #         #print("Data: %s" % data)
        #         result.append(data)
        #     f.close()
        # return result


    # Return stored entries, starting at 'index' and for 'count' total
    # items (or less, if there are less entries stored than the ones
    # requested). An index of 0 means the last entry stored (so the newest)
    # 1 is the penultimate record stored and so forth. The method returns
    # an array of items.
    def get_records_iter(self, index_from_end, count=1):
        if count == 0: return []
        # Order files according to length. We need to read from the
        # bigger file and proceed to the smaller file (if there is one)
        # and if the records count requires so.
        lens = self.get_file_size(0), self.get_file_size(1)
        if lens[0] > lens[1]:
            files = [0,1]
        else:
            files = [1,0]
            lens = lens[1],lens[0]
        total_records = lens[0] + lens[1]
        #print("lens: %d %d" % (lens[0],lens[1]))
        if total_records == 0: return []

        # Normalize index according to actual history len
        if index_from_end >= total_records: 
            index_from_end = total_records-1

        # Turn the index under an offset in the whole history len,
        # so that 0 would be the oldest entry stored, and so forth:
        # it makes more sense to work with offsets here, but for the API
        # it makes more sense to reason in terms of "last N items".
        last = total_records - index_from_end
        first = last - count
        first = max(first,0)
        #print("range(%d, %d)" % (first,last))

        # if in first file only
        if first < lens[0] and last <= lens[0]:
            # if in first file only
            file = 0
            index = first
            end = last
            query_plan = [[files[0], index, end]]
        elif first >= lens[0]:
            # in last file only
            file = 1
            index = first - lens[0]
            end = last - lens[0]
            query_plan = [[files[1], index, end]]
        else:
            # in both files
            file0 = 0
            index0 = first
            end0 = lens[0]
            file1 = 1
            index1 = 0
            end1 = last - lens[0]
            query_plan = [[files[0], index0, end0], [files[1], index1, end1]]

        #print(query_plan)
        recordsize = self.recordsize
        for file, location, end in query_plan:
            f = open(self.files[file],'rb')
            f.seek(location*(8+recordsize),0)
            while location < end:
                rlen,time = struct.unpack("<LL",f.read(8))  # 4 for time.
                #print("file %d, location %d, time %d" % (file,location,time))
                data = f.read(recordsize)[0:rlen]
                yield time,data
                location += 1
            f.close()

    def open_record_random_access(self):
        # Order files according to length. We need to read from the
        # bigger file and proceed to the smaller file (if there is one)
        # and if the records count requires so.
        lens = self.get_file_size(0), self.get_file_size(1)
        if lens[0] > lens[1]:
            files = [0,1]
        else:
            files = [1,0]
            lens = lens[1],lens[0]
        total_records = lens[0] + lens[1]
        #print("lens: %d %d" % (lens[0],lens[1]))
        if total_records == 0: return []

        self.RA_files = []
        self.RA_lens = lens
        if lens[0] > 0:
            self.RA_files.append(open(self.files[files[0]],'rb'))
        else:
            self.RA_files.append(None)
        if lens[1] > 0:
            self.RA_files.append(open(self.files[files[1]],'rb'))
        else:  
            self.RA_files.append(None)
        self.RA_prepared = True

    def get_records_random_access(self, index_from_end):
        if not self.RA_prepared == True:
            raise "prepare_record_random_access() must be called first"
        
        # Normalize index according to actual history len
        if index_from_end >= self.RA_lens[0] + self.RA_lens[1]:
            index_from_end = self.RA_lens[0] + self.RA_lens[1] - 1

        # Turn the index under an offset in the whole history len,
        # so that 0 would be the oldest entry stored, and so forth:
        # it makes more sense to work with offsets here, but for the API
        # it makes more sense to reason in terms of "last N items".
        index = self.RA_lens[0] + self.RA_lens[1] - index_from_end - 1

        if index < self.RA_lens[0]:
            # if in first file only
            file = 0
            index = index
        elif index >= self.RA_lens[0]:
            # in last file only
            file = 1
            index = index - self.RA_lens[0]
            
        f = self.RA_files[file]
        f.seek(index*(8+self.recordsize),0)
        rlen,time = struct.unpack("<LL",f.read(8))  # 4 for time.
        try:
            data = f.read(self.recordsize)[0:rlen]  # OverflowError: overflow converting long int to machine word (from binary_search_records_fast)
        except OverflowError as e:
            print(f"OverflowError: {e} - recordsize:{self.recordsize}, file: {file}, self.RA_lens:{self.RA_lens}, index: {index}, rlen: {rlen}, time: {time}")
            raise e

        return time,data
    
    def close_random_access(self):
        for f in self.RA_files:
            if f:
                f.close()
        self.RA_prepared = False


    @timed_function
    def binary_search_records_slow(self, seek_time):
        left = 0                           # offset of first record
        right = self.get_num_records() - 1 # offset of last record
        last = right

        while left <= right:
            mid = (left + right) // 2
            idx_from_end = last - mid

            mid_rec_time, _ = list(self.get_records_iter(idx_from_end,1))[0]

            if mid_rec_time == seek_time:
                return idx_from_end, True  # exact match, found
            elif mid_rec_time < seek_time:
                left = mid + 1
            else:
                right = mid - 1

        return idx_from_end, False # closest record, but not found

    @timed_function
    def binary_search_records_fast(self, seek_time, start_search=0):
        left = start_search                # offset of first record
        right = self.get_num_records() - 1 # offset of last record
        last = right

        #self.open_record_random_access()
        while left <= right:
            mid = (left + right) // 2
            idx_from_end = last - mid

            mid_rec_time, _ = self.get_records_random_access(idx_from_end)

            if mid_rec_time == seek_time:
                return idx_from_end, mid_rec_time, True  # exact match, found
            elif mid_rec_time < seek_time:
                left = mid + 1
            else:
                right = mid - 1

        #self.close_random_access()
        return idx_from_end, mid_rec_time, False # closest record, but not found

    # # return records up to but not including the last one.
    # def items_by_time(self,first,last):
    #     self.open_record_random_access()
    #     idx_first, f_time, f_exact = self.binary_search_records_fast(first) # finds closest record, even if out of range
    #     print("search: %s idx_first: %d, f_time: %d" % (first, idx_first, f_time))
    #     idx_last, l_time, l_exact = self.binary_search_records_fast(last, start_search=idx_first)   # finds closest record, even if out of range
    #     self.close_random_access()

    #     # print ftime and ltime
    #     print("f_time: %d, l_time: %d" % (f_time, l_time))
    #     if last > l_time:
    #         yield from self.get_records_iter(idx_last, idx_first - idx_last + 1)  # gives [first, last] - returns last record
    #     else:
    #         yield from self.get_records_iter(idx_last + 1, idx_first - idx_last + 1)  # does not return last record, gives [first, last>

    def items_by_time(self,first,last):
        self.open_record_random_access()
        idx_first, f_time, f_exact = self.binary_search_records_fast(first) # say 1 back
        idx_last, l_time, l_exact = self.binary_search_records_fast(last)   # say 0 back
        self.close_random_access()

        yield from self.get_records_iter(index_from_end=idx_last, count=(idx_first - idx_last + 1)) # return time, data, is_last

    def arrays_by_time(self,first,last, group_size=1):
        self.open_record_random_access()
        idx_first, f_time, f_exact = self.binary_search_records_fast(first) # say 1 back
        idx_last, l_time, l_exact = self.binary_search_records_fast(last)   # say 0 back
        self.close_random_access()

        try:
            first_time = time.localtime(first)
            last_time = time.localtime(last)
        except:
            first_time = last_time = None
        print(f"search: [{first}, {last}] [{first_time}, {last_time}]")
        yield from self.get_arrays_iter(index_from_end=idx_last, count=(idx_first - idx_last + 1), group_size=group_size) # return time, data, is_last


    # Return stored entries, starting at 'index' and for 'count' total
    # items (or less, if there are less entries stored than the ones
    # requested). An index of 0 means the last entry stored (so the newest)
    # 1 is the penultimate record stored and so forth. The method returns
    # an array of items.
    def get_arrays_iter(self, index_from_end, count, group_size=1):
        if count == 0: return []
        # Order files according to length. We need to read from the
        # bigger file and proceed to the smaller file (if there is one)
        # and if the records count requires so.
        lens = self.get_file_size(0), self.get_file_size(1)
        if lens[0] > lens[1]:
            files = [0,1]
        else:
            files = [1,0]
            lens = lens[1],lens[0]
        total_records = lens[0] + lens[1]
        #print("lens: %d %d" % (lens[0],lens[1]))
        if total_records == 0: return []

        # Normalize index according to actual history len
        if index_from_end >= total_records: 
            index_from_end = total_records-1

        # Turn the index under an offset in the whole history len,
        # so that 0 would be the oldest entry stored, and so forth:
        # it makes more sense to work with offsets here, but for the API
        # it makes more sense to reason in terms of "last N items".
        last = total_records - index_from_end
        first = last - count
        first = max(first,0)
        #print("range(%d, %d)" % (first,last))

        # if in first file only
        if first < lens[0] and last <= lens[0]:
            # if in first file only
            file = 0
            index = first
            end = last
            query_plan = [[files[0], index, end]]
        elif first >= lens[0]:
            # in last file only
            file = 1
            index = first - lens[0]
            end = last - lens[0]
            query_plan = [[files[1], index, end]]
        else:
            # in both files
            file0 = 0
            index0 = first
            end0 = lens[0]
            file1 = 1
            index1 = 0
            end1 = last - lens[0]
            query_plan = [[files[0], index0, end0], [files[1], index1, end1]]

        #print(query_plan)
        recordsize = self.recordsize
        # for file, location, end in query_plan:
        #     f = open(self.files[file],'rb')
        #     f.seek(location*(8+recordsize))
        #     while location < end:
        #         rlen,time = struct.unpack("<LL",f.read(8))  # 4 for time.
        #         #print("file %d, location %d, time %d" % (file,location,time))
        #         data = f.read(recordsize)[0:rlen]
        #         yield time,data
        #         location += 1
        #     f.close()

        if gc.mem_free() > 1_000_000:
            batch_size = 100   # with PSRAM
        else:
            batch_size = 10    # no PSRAM
        rec_size = recordsize+8
        buf = bytearray(rec_size*batch_size)
        record_count = 0
        last_time32 = None
        group_count = 0
        last_group = -1
        result = np.zeros(34,dtype=np.float)
        yield_count = 0
        for file, location, end in query_plan:
            f = open(self.files[file],'rb')
            f.seek(location*(8+recordsize),0)
            while location < end:
                bufsize = min(batch_size, end-location)
                n=f.readinto(buf, rec_size*bufsize)
                if n == 0: 
                    break
                for j in range(0,n//rec_size):
                    rlen32, time32 = struct.unpack_from("<LL",buf,j*rec_size)
                    #print(f"time: {time32}")
                    a = np.frombuffer(buf[j*rec_size+8:(j+1)*rec_size], dtype=np.float)  # 34: buf[j*rec_size+8:j*rec_size+8+4*34]
                    cur_group = (time32//group_size) * group_size  # 2100  2100,   2100 2101
                    if cur_group == last_group:
                        # add up current group
                        group_count += 1
                        result += a
                        max_time = max(max_time, time32)
                        #print(f"{time32}, {cur_group}, {last_group}, {a}")
                    else:
                        if record_count>0:
                            result /= group_count
                            #print(f"I yielding: {max_time}, {group_count}, {result}")
                            yield_count += 1
                            yield [max_time, group_count, result]  # use (last_group+cur_group)/2 to have the time exactly split the interval.

                        last_group = cur_group
                        group_count = 1
                        result = a
                        max_time = time32
                        #print(f"{time32}, {cur_group}, {last_group}, {a}")
                    last_time32 = time32
                    record_count += 1
                location += batch_size

        if group_count > 0:
            # results for last bit
            result /= group_count
            #print(f"I yielding: {max_time}, {group_count}, {result}")
            yield_count += 1
            yield [max_time, group_count, result]

        self.last_records_processed = record_count
        print(f"processed {record_count} records") 
        print(f"yielded {yield_count} records")


    # Remove all the history
    def reset(self):
        try:
            os.unlink(self.files[0])
            os.unlink(self.files[1])
        except:
            pass

# Only useful in order to test the history API
def test_history(reset=False):
    h = History("/sd/test_history",histlen=5,recordsize=20)
    if reset:
        h.reset()
    t = 100
    h.append(0, b'idx0')   # 0  - 0
    h.append(1, b'idx1') # 1  - 1
    h.append(2,b'idx2') # 2  - 2
    h.append(3,b'idx3') # 3  - 3
    h.append(4,b'idx4')# 4  - 4
    h.append(5,b'idx5')# 5  - 5
    h.append(106,b'idx6')# 6  - 0
    h.append(107,b'idx7')# 7  - 1
    print("Current records: %d" % h.get_num_records())
    print("records(0,1)")
    records = list(h.get_records_iter(0,1)) # Cross file fetch
    print(records)
    print("records(0,2)")
    records = list(h.get_records_iter(0,2))
    print(records)
    print("records(0,1)")
    records = list(h.get_records_iter(0,3))
    print(records)
    print("records(1,1)")
    records = list(h.get_records_iter(4,4))
    print(records)
    print("binary search")
    return h
    # records = h.get_records_from_time(114,3)
    # print(records)
    # index, count = h.get_index_from_time(114,3)
    # print("Index: %d Count: %d" % (index,count))
    # records = h.get_records(index,count)
    # print(records)
    # records = h.get_records_from_time(104,4)
    # print(records)
    # index, count = h.get_index_from_time(104,4)
    # print("Index: %d Count: %d" % (index,count))
    # records = h.get_records(index,count)
    # print(records)

    # print("Adding 100 entries individual call...")
    # for i in range(100):
    #     h.append(i,bytes("entry %d" % i,'utf-8'))
    # print("Current records: %d" % h.get_num_records())
    # records = h.get_records(1,2)
    # print(records)

    # h2 = History("test_history2",histlen=5_000,recordsize=20, period_s=2)
    # print("add 8_000 blank rows")
    # h2.append_empty_records(1000,5,8_000)
    # print("Done")


# from ulab import numpy as np
# import mount_sd
# from his import History, timed_function

# make a list of "C1" to "C34"
#  
# columns = ["C%d" % i for i in range(1,35)]

@timed_function
def test_his_idx(back, count, group_size, columns):
    h = History("/sd/d3_5m_256",histlen=60/5*60*24*30,recordsize=256-8,columns=columns)
    for i,data in enumerate(h.get_arrays_iter(back, count, group_size=group_size)):
        print(data)
    print(f"returned {i} records")

# test_his_idx(0, 36, 1, columns)

@timed_function
def test_his_time(first,last, group_size, columns):
    h = History("/sd/d3_5m_256",histlen=60/5*60*24*30,recordsize=256-8,columns=columns)
    for i,data in enumerate(h.arrays_by_time(first, last, group_size=group_size)):
        print(data)
        pass
    print(f"returned {i} records")

#test_his_time(1709416500, 1709416800,10,columns)

# 1709402733, 1709489133 5s 1095 / 48
# 1709316341, 1709489141 5m 1/1
# test_his_time(1709316341, 1709489141,10,columns)

class HistoryFiles:

    def __init__(self,columns):
        self.history5s = History("/sd/d3_5s_256", histlen=60/5*60*24*30,recordsize=256-8, columns=columns) 
        self.history5m = History("/sd/d3_5m_256", histlen=3600/300*24*365*5,recordsize=256-8, columns=columns)
        self.columns = columns
        self.C = self.history5s.C
        self.last_5m_group = None
        self.last_records_processed = 0

    def append_array(self, **kwargs):
        time = kwargs.pop('timestamp', None)
        a = self.history5s.build_array(**kwargs)
        print("a",end="")
        self.history5s.append(time, a.tobytes())
        self.current_5m_group = time // 300  # should be 300
        # on first run:
        if not self.last_5m_group:
            self.last_5m_group = self.current_5m_group
        # on group change:
        if self.current_5m_group != self.last_5m_group:
            time, count, a = next(self.history5s.arrays_by_time(self.last_5m_group*300, self.current_5m_group*300, group_size=300))
            print(f"appended data_5m time: {time}, count: {count}, data: {a}")
            self.history5m.append(time, a.tobytes())
            self.last_5m_group = self.current_5m_group

    def arrays_by_time(self,first,last, group_size=1):
        if group_size < 300:
            print(f"searching 5s {first} {last} {group_size}")   
            yield from self.history5s.arrays_by_time(first, last, group_size=group_size)  # group_size is in seconds
            self.last_records_processed = self.history5s.last_records_processed
        else:
            print(f"searching 5m {first} {last} {group_size}")
            yield from self.history5m.arrays_by_time(first, last, group_size=group_size)  # group_size is in seconds
            self.last_records_processed = self.history5m.last_records_processed


# >>> test_his_time(20_000,60_000,100)  @34vars returned.
# processed 40001 records
# returned 400 records
# Function test_his_time Time = 18857.445ms
# >>> test_his_time(20_000,60_000,100)  @64 vars returned. 19687.070ms
#
# test_his_time(10_000,10_000+3600,10) @34vars returned. print: 4524.871ms. no_print 1893.341ms
    
    

