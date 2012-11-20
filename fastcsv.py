"""
Quickly parse a CSV file

How it works
============

First, all rows have to be written in sort order of the searchable keys.

Then, when writing the file, we pad the end of a row (before the ``\r\n``) with extra spaces if necessary so that a row always starts two characters after a block boundary.

This enables the reader to seek to a block boundary in the knowledge that a row starts two characters afterwards. We want the two characters to ensure that it really is the end of a line just before, and not the middle of a quoted value.

New rows are appended to the end of the file so you have to choose your sort keys such that it makes sense for new rows to always have the largest sort value.

The block size must be large enough to hold at least the header row and one data row.

Potential Drawbacks
===================

* Random insertion of new rows are not allowed, as they would be very slow, requiring the re-writing of the whole CSV file after them.
* Row updates can only be preformed if the row contains less than or eqaul the length of encoded data it did to start with.
* Row deletes do not free up space unless the very last row is deleted.

Coping Strategies
=================

Never delete rows, just have a column that takes a status code of "ACTIVE" or "DELTED". When you want to update a row, just write it to the end of the file, set the old row to DELTED and keep a pointer somewhere else to say where the new file is.


Todo
====

* Implement update, delete, insert

"""
import os
from collections import OrderedDict

def debug(msg):
    return
    print '[DEBUG]   %s'%(msg,)

def warn(msg):
    print '[WARNING] %s'%(msg,)

# State types
ROW_START=    0
PRE_PADDING=  1
END_PADDING=  2
IN_QUOTED=    3
FIRST_QUOTE_OR_END_QUOTED=  4
END_VALUE=    5
IN_UNQUOTED=  6
END_UNQUOTED= 7
COMMA=        8
NON_VALUE_CR= 9

## Column types
#SAFE = 4
#QUOTE_SAFE = 3
#ASCII = 2
#UNICODE = 1
#col_types = UNICODE, ASCII, QUOTE_SAFE, SAFE

def parse_filename(path):
    filename = path.replace('\\', '/').split('/')[-1]
    if not filename:
        raise Exception("%r does not represent a file"%(path,))
    parts = filename.split('.')
    if not parts[-1].lower() == 'csv':
        raise Exception("%r does not have a .csv extension")
    if not len(parts) == 3:
        raise Exception("%r does not have a block size in the file extension eg 'data.16.csv'")
    try:
        bits = int(parts[1])
    except:
        raise Exception("%r block size is not an integer")
    size = 2**bits
    return size, parts[0], parts[1], parts[2]

def repad(path, tmp, size):
    """
    Repad the file with the new blocksize, renaming it if neccessary
    """

    #size = parse_filename(path)
    pos = [0]
    block = [0]
    fp = open(tmp, 'wb')
    def row_callback(row, end_pos):
        new_row = ''
        for value in row:
            new_row += '"'+value.replace('"','""')+'",'
        new_row += '\r\n'
        if pos[0]+len(new_row) > size:
            fp.write(' '*(size-pos[0]))
            block[0] += 1
            pos[0] = 0
        else:
            fp.write(new_row)
            pos[0] += len(new_row)
        return True
    #def value_callback(value):
    #    pass #print "Value: %r" % (value,)
    #print lex('page/data.csv', 0, row_callback, value_callback, rows=10)
    #step('Completed Python, my version ...', type='test')
    count, r =  lex(test_csv, 0, row_callback,  rows=None)
    fp.close()

def find_row(filename, key):
    """\
    Our naive algorithm (which turns out to be very fast) is to:

    * Parse the first two rows in the file

    Check the number of headers matches the number of values in each of the rows we have managed to parse.
    If the value is in one of the already parsed rows, our job is done.

    * Parse the last block in the file
    * The last block tells us if the file is correctly padded

    If the rows aren't at a block boundary we re-pad the file and repeat try again.

    Check the number of headers matches the number of values in each of the rows we have managed to parse.
    If the value is in one of the already parsed rows, our job is done.

    If the value we are looking for is greater than the last block or less than the first, we return None
    
    Now we need to iterate:

        We choose the block in the middle of the blocks we've already found and read the first row.
        Check the number of headers matches the number of values in each of the rows we have managed to parse.
        If the value we are looking for is in the first row our job is done.
        Otherwise we iterate using this block as the new lower bound if the value is higher than the value of the middle block and using it as the upper bound if the value is lower.
        If the number of blocks between the lower and upper bound is 5 or less, we just parse them all to find the value.
        If the value is not found we return None.
    """
    first_block = 1
    for value in key:
        if not isinstance(value, unicode):
            raise Exception('Key contains non-unicode values: %r'%(key,))
    header_end_pos, header_rows = lex(filename, rows=1)
    if not len(header_rows)>0:
        raise Exception('No header in CSV')
    headers = header_rows[0]
    if len(headers) < len(key):
        raise Exception('Key being asked for is longer than the number of columns')
    end_pos, rows = lex(filename, pos=header_end_pos+1, rows=1)
    if not len(rows)>0:
        # No rows in the CSV file
        raise KeyError('No rows for key %r'%(key, ))
    if len(rows[0]) != len(headers):
        debug('The number of columns in the first row does not match the number of headers')
    first_block_row_key = [value.decode('utf8') for value in rows[0][:len(key)]]
    debug("First block key: %r"%(first_block_row_key,))
    if key == first_block_row_key:
        return return_rows_from(filename, key, end_pos+1, [[value.decode('utf8') for value in rows[0]]])
    block_size, a, b, c = parse_filename(filename)
    last_block = calculate_last_block(filename, block_size)
    if last_block <= first_block:
        return iterate_until_finding(filename, key, header_end_pos+1)
    end_pos, rows = lex(filename, pos=last_block*block_size, rows=1)
    if len(rows[0]) != len(headers):
        debug('The number of columns in the last block\'s first row does not match the number of headers')
    last_block_row_key = [value.decode('utf8') for value in rows[0][:len(key)]]
    debug("Last block key: %r"%(last_block_row_key,))
    if key == last_block_row_key:
        return return_rows_from(filename, key, end_pos+1, [[value.decode('utf8') for value in rows[0]]])
    # If it is in the last block:
    if key > last_block_row_key:
        result = return_rows_from(filename, key, end_pos+1)
        if not result:
            raise KeyError('No rows for key %r'%(key, ))
        return result
    # At this point we have the headers, first row key and last row key, and the key is between the two
    while True:
        debug("Looping between %s and %s"%(first_block, last_block))
        if last_block - first_block <= 1:
            # Just search the blocks
            debug("Searching the blocks directly")
            return iterate_until_finding(filename, key, first_block*block_size, (last_block+1)*block_size)
        else:
            next_block = int((last_block + first_block)/2)
            debug("Next block is %s"%(next_block))
            end_pos, rows = lex(filename, pos=next_block*block_size, rows=1)
            next_block_row_key = [value.decode('utf8') for value in rows[0][:len(key)]]
            if key == next_block_row_key:
                return return_rows_from(filename, key, end_pos, [value.decode('utf8') for value in rows[0]])
            elif key > next_block_row_key:
                first_block = next_block
            else:
                last_block = next_block
    return rows[0], header_length

def iterate_until_finding(filename, key, start_pos, max_pos=None):
    rows = []
    def row_callback(row, end_pos):
        if max_pos is not None and end_pos > max_pos:
            debug("Reached %s, past the maximum of %s"%(end_pos, max_pos))
            return False
        pyrow = [x.decode('utf8') for x in row]
        if pyrow[:len(key)] == key:
            rows.append(pyrow)
            debug("Found a row")
            return True
        elif rows:
            # We've stopped finding our key
            debug("Finished finding key")
            return False
        # Not one we want yet, keep looking
        return True
    lex(filename, start_pos, row_callback, rows=None)
    if not rows:
        raise KeyError('No rows for key %r'%(key, ))
    return rows

def return_rows_from(filename, key, pos, start_rows=None):
    if start_rows:
        rows = start_rows[:]
    else:
        rows = []
    def row_callback(row, end_pos):
        new_row = [x.decode('utf8') for x in row[:len(key)]]
        if new_row != key:
            return False
        else:
            rows.append(new_row+[x.decode('utf8') for x in row[len(key):]])
            return True
    lex(filename, pos, row_callback, rows=None)
    return rows


def update_row(filename, query, updates):
    """
    Here we find the row, measure its encoded length and ensure the updates don't make it longer. If they don't we write the new row over the top of the old one.
    """
    pass

def new_row(filename, row):
    """
    We read the last block of the file and check the new row comes after the last row in the file. If the new row fits in the current last block, we append the new row, otherwise we append padding and then the new row to start a new block.
    """
    pass

def delete_row(filename, row):
    """
    We find the row and overwrite it with spaces unless it is the last row, in which case the file is truncated.
    """
    pass

def headers_from_csv(filename):
    """
    Return the parsed headers and file offset of the end of the headers
    """
    header_length, rows = lex(filename)
    if not rows:
        raise Exception('No header in CSV')
    return rows[0], header_length

def calculate_last_block(filename, block_size):
    size = os.stat(filename).st_size
    if size/block_size < 1:
        return 0
    # Remove the remainder
    last = int(size/block_size)
    return last

try:
    raise Exception('Use pure Python')
    from ctypes import *

    make_callback_value = CFUNCTYPE(None, c_char_p)
    make_callback_row = CFUNCTYPE(None)
    # gcc -Wall -c -fPIC fastcsv.c -o fastcsv.o
    # gcc -shared -Wl,-soname,libfastcsv.so.0 -o libfastcsv.so.0.0.1 fastcsv.o
    fastcsv = cdll.LoadLibrary(os.path.join(os.path.abspath(os.path.dirname(__file__)), "libfastcsv.so.0.0.1"))
    def lex(filename, pos=0, row_callback=None, value_callback=None, rows=1, cols=None):
        rowsi = []
        rowi = []
        if value_callback:
            def callback_value_wrapper(value):
                #print 1,
                if value:
                    rowi.append(value)
                else:
                    rowi.append("")
                value_callback(rowi[-1])
                return None
        else:
            def callback_value_wrapper(value):
                #print 2,
                if value:
                    rowi.append(value)
                else:
                    rowi.append("")
                return None
        callback_value = make_callback_value(callback_value_wrapper)
        if row_callback:
            def callback_row_wrapper():
                #print 3,
                length = 0
                for item in rowi:
                    length += len(item)
                result = row_callback(rowi, pos+length)
                rowsi.append(rowi[:])
                while rowi:
                    rowi.pop()
                return result
        else:
            def callback_row_wrapper():
                #print 4,
                length = 0
                for item in rowi:
                    length += len(item)
                rowsi.append(rowi[:])
                while rowi:
                    rowi.pop()
                return True
        callback_row = make_callback_row(callback_row_wrapper)
        if rows is None:
            rows = -1
        end = fastcsv.lex(filename, pos, rows, callback_value, callback_row)
        #print end, rowsi
        return end, rowsi
except:
    def lex(filename, pos=0, row_callback=None, value_callback=None, rows=1, cols=None):
        """\
        Open a file at the specified position and start parsing the rows, calling
        ``value_calback()`` every time a value is found and ``row_callback()``
        every time a row is completed.
        """
        with open(filename, "rb") as fp:
            row_data = []
            fp.seek(pos)
            row_callback_count = 0
            state = ROW_START
            value = ''
            row = []
            final = pos
            keep_going = True
            while True:
                chars = fp.read(4096)
                if not chars:
                    if row:
                        if value_callback:
                            value_callback(value)
                        row.append(value)
                        if row_callback:
                            keep_going = row_callback(row, final-1)
                            if keep_going not in [True, False]:
                                raise Exception("Row callback failed to return True or False")
                        else:
                            row_data.append(row)
                    return final-1, row_data
                for char in chars: 
                    final+=1
                    if state == IN_QUOTED:
                        if char == '"':
                            state = FIRST_QUOTE_OR_END_QUOTED
                        else:
                            value += char
                    elif state == IN_UNQUOTED:
                        if char == '"':
                            warn('Found a %r character in an unquoted value at %s, assuming a quote was missed from the front of the value and continuing'%(char, final-1,))
                            state = FIRST_QUOTE_OR_END_QUOTED
                        elif char  == ',':
                            state = COMMA
                            row.append(value)
                            if value_callback:
                                value_callback(value)
                            value = ''
                        elif char in [' ']:
                            warn('Found a %r character in an unquoted value at %s, assuming the quoting was accidentally forgotten and continuing, expecting to a quote was missed from the front of the value and continuing'%(char, final-1,))
                            state = FIRST_QUOTE_OR_END_QUOTED
                        else:
                            value += char 
                    elif state == ROW_START:
                        if char == '\n':
                            # XXX raise Exception(r'Expected \r\n at position %s, not \n'%(final-1,))
                            warn(r'Expected \r\n at position %s, not \n'%(final-1,))
                        elif char == '\r':
                            state = NON_VALUE_CR
                        elif char == ',':
                            if value_callback:
                                value_callback(value)
                            value = ''
                            state == COMMA
                        elif char == '"':
                            state = IN_QUOTED
                        elif char == ' ':
                            state = PRE_PADDING
                        else:
                            state = IN_UNQUOTED
                            value += char
                    elif state == PRE_PADDING:
                        if char == ' ':
                            continue
                            # XXX Depending on the implementation, might want to add this:
                            # value += char
                        elif char == '\r':
                            state = NON_VALUE_CR
                        elif char == ',':
                            warn('We found a %r at the end of a row at %s, assuming that it was supposed to be \'\\r\\n\' and continuing'%(char, final-1,))
    
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            value = ''
                            state = COMMA
                        elif char == '\n':
                            warn('We found a %r at the end of a row at %s, assuming that it was supposed to be \'\\r\\n\' and continuing'%(char, final-1,))
    
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            if row_callback:
                                keep_going = row_callback(row, final-1)
                                if keep_going not in [True, False]:
                                    raise Exception("Row callback failed to return True or False")
                            else:
                                row_data.append(row)
                            row_callback_count += 1
                            if not keep_going or (rows != None and row_callback_count >= rows): 
                                return final-1, row_data
                            row = []
                            value = ''
                            state = ROW_START
                        elif char == '"':
                            state = IN_QUOTED
                        else:
                            state = IN_UNQUOTED
                            value += char
                    elif state == FIRST_QUOTE_OR_END_QUOTED:
                        if char == '"':
                            value += char
                            state = IN_QUOTED
                        elif char == ' ':
                            state = END_PADDING
                        elif char == '\r':
                            state = NON_VALUE_CR
                        elif char == '\n':
                            warn('We found a %r at the end of a row at %s, assuming that it was supposed to be \'\\r\\n\' and continuing'%(char, final-1,))
    
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            if row_callback:
                                keep_going = row_callback(row, final-1)
                                if keep_going not in [True, False]:
                                    raise Exception("Row callback failed to return True or False")
                            else:
                                row_data.append(row)
                            row_callback_count += 1
                            if not keep_going or (rows != None and row_callback_count >= rows):
                                return final-1, row_data
                            row = []
                            value = ''
                            state = ROW_START
                        elif char == ',':
                            state = COMMA
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            value = ''
                        else:
                            raise Exception('Expected a second %r character at %s or a comma or space, not %r'%('"', final-1, char))
                    elif state == END_PADDING:
                        if char == ' ':
                            continue
                        elif char == ',':
                            state = COMMA
                        elif char == '\r':
                            state = NON_VALUE_CR
                        elif char == '\n':
                            warn('We found a \'\\n\' at the end of a row at %s, assuming that it was supposed to be \'\\r\\n\' and continuing'%(ifnal-1,))
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            if row_callback:
                                keep_going = row_callback(row, final-1)
                                if keep_going not in [True, False]:
                                    raise Exception("Row callback failed to return True or False")
                            else:
                                row_data.append(row)
                            row_callback_count += 1
                            if not keep_going or (rows != None and row_callback_count >= rows): 
                                return final-1, row_data
                            row = []
                            value = ''
                            state = ROW_START
                        else:
                            raise Exception('Expected a comma, space or newline after the padding at %s, not a %r'%(final-1, char))
                    elif state == COMMA:
                        if char == '\n':
                            warn('We found a \'\\n\' at the end of a row at %s, assuming that it was supposed to be \'\\r\\n\' and continuing'%(final-1,))
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            if row_callback:
                                keep_going = row_callback(row, final-1)
                                if keep_going not in [True, False]:
                                    raise Exception("Row callback failed to return True or False")
                            else:
                                row_data.append(row)
                            row_callback_count += 1
                            if not keep_going or (rows != None and row_callback_count >= rows): 
                                return final-1, row_data
                            row = []
                            value = ''
                            state = ROW_START
                        elif char == '\r':
                            state = NON_VALUE_CR
                        elif char == ' ':
                            state = PRE_PADDING
                        elif char == '"':
                            state = IN_QUOTED
                        elif char == ',':
                            if value_callback:
                                value_callback('')
                            row.append('')
                        else:
                            state = IN_UNQUOTED
                            value += char
                    elif state == NON_VALUE_CR:
                        if char != '\n':
                            raise Exception('Expected \'\\r\\n\' at position %s, not \'\r%s\''%(final0, char))
                        else:
                            if value_callback:
                                value_callback(value)
                            row.append(value)
                            if row_callback:
                                keep_going = row_callback(row, final-1)
                                if keep_going not in [True, False]:
                                    raise Exception("Row callback failed to return True or False")
                            else:
                                row_data.append(row)
                            row_callback_count += 1
                            if not keep_going or (rows != None and row_callback_count >= rows):
                                return final-1, row_data
                            row = []
                            value = ''
                            state = ROW_START


if __name__ == '__main__':

    test_csv = '/home/james/fastcsv/orig/5/data.gov.uk/data.32.csv'
    #repad(
    #    '/home/james/fastcsv/orig/5/data.gov.uk/data.32.csv', 
    #    '/home/james/fastcsv/orig/5/data.gov.uk/data.22.csv', 
    #    2**22
    #)
    print find_row('/home/james/fastcsv/orig/5/data.gov.uk/data.22.csv', [u"518d566f-1b8d-4be4-996d-8ad984be980d"])



    #header, length = headers_from_csv(test_csv)
    #print header, length
    ##print header.keys()
    ##import sys
    ##sys.exit(0)

    #number = 400

    #import csv 
    ##step('Starting Python version ...', type='test')
    #rows = []
    #with open(test_csv, 'rb') as fp:
    #    reader = csv.reader(fp, delimiter=',', quotechar='"', skipinitialspace=True)
    #    counter = 0
    #    for row in reader:
    #        rows.append(row)
    #        counter += 1
    #        if counter == number:
    #            break

    #rows1 = []
    #def row_callback(row, end_pos):
    #    rows1.append(row)
    #    return True
    ##def value_callback(value):
    ##    pass #print "Value: %r" % (value,)
    ##print lex('page/data.csv', 0, row_callback, value_callback, rows=10)
    ##step('Completed Python, my version ...', type='test')
    #count, r =  lex(test_csv, 0, row_callback,  rows=number)
    ##step('Done', type='test')
    #print len(rows1[1]), len(rows[1])
    ##step('Done', type='test')
    #for i in range(len(rows)):
    #    if i > len(rows)-1:
    #        import pdb; pdb.set_trace()
    #    elif i > len(rows1)-1:
    #        import pdb; pdb.set_trace()
    #    elif rows[i] != rows1[i]:
    #        import pdb; pdb.set_trace()
    #assert rows1 == rows
