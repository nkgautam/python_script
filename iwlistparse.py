#!/usr/bin/env python
#
# iwlistparse.py for Python 3.x
# Hugo Chargois - 17 jan. 2010 - v.0.1
# Parses the output of iwlist scan into a table
import subprocess
from collections import namedtuple

INTERFACE = 'wlan0'
CURRENTLY_DISCONNECTED_LABEL = '*'

# You can choose which columns to display here, and most importantly in what
# order. Of course, they must exist as keys in the dict rules.
COLUMNS = ['Name', 'Address', 'Quality', 'Signal', 'Channel', 'Encryption']

# iwlistparse function result
ParseResult = namedtuple(
    'ParseResult',
    ['currently_connected', 'headers', 'access_points', 'error'])


# You can add or change the functions to parse the properties of each AP (cell)
# below. They take one argument, the bunch of text describing one cell in
# iwlist scan and return a property of that cell.
def get_name(cell):
    return matching_line(cell, 'ESSID:')[1:-1]


def get_quality(cell):
    quality = matching_line(cell, 'Quality=').split()[0].split('/')
    return '{:3} %'.format(
        int(round(float(quality[0]) / float(quality[1]) * 100)))


def get_channel(cell):
    return matching_line(cell, 'Channel:')


def get_signal_level(cell):
    # Signal level is on same line as Quality data so a bit of ugly
    # hacking needed...
    return matching_line(cell, 'Quality=').split('Signal level=')[1]


def get_encryption(cell):
    enc = ""
    if matching_line(cell, 'Encryption key:') == 'off':
        enc = 'Open'
    else:
        for line in cell:
            matching = match(line, 'IE:')
            if matching is not None:
                wpa = match(matching, 'WPA Version ')
                if wpa is not None:
                    enc = 'WPA v.' + wpa
        if enc == '':
            enc = 'WEP'
    return enc


def get_address(cell):
    return matching_line(cell, 'Address: ')


# Here's a dictionary of rules that will be applied to the description of each
# cell. The key will be the name of the column in the table. The value is a
# function defined above.
RULES = {
    'Name': get_name,
    'Quality': get_quality,
    'Channel': get_channel,
    'Encryption': get_encryption,
    'Address': get_address,
    'Signal': get_signal_level
}


# Here you can choose the way of sorting the table. sortby should be a key of
# the dictionary rules.
def sort_cells(cells):
    sortby = 'Quality'
    reverse = True
    cells.sort(key=lambda el: el[sortby], reverse=reverse)


# Below here goes the boring stuff. You shouldn't have to edit anything below
# this point
def matching_line(lines, keyword):
    """Returns the first matching line in a list of lines. See match()"""
    for line in lines:
        matching = match(line, keyword)
        if matching is not None:
            return matching
    return None


def match(line, keyword):
    """If the first part of line (modulo blanks) matches keyword,
    returns the end of that line. Otherwise returns None"""
    length = len(keyword)
    if line[:length] == keyword:
        return line[length:]
    else:
        return None


def parse_cell(cell):
    """Applies the rules to the bunch of text describing a cell and returns the
    corresponding dictionary"""
    parsed_cell = {}
    for key, rule in RULES.items():
        parsed_cell.update({key: rule(cell)})
    return parsed_cell


def print_table(table):
    # Functional magic below :)
    widths = list(map(max, map(lambda l: map(len, l), zip(*table))))
    justified_table = []
    for line in table:
        justified_line = []
        for i, el in enumerate(line):
            justified_line.append(el.ljust(widths[i]+2))
        justified_table.append(justified_line)
    for line in justified_table:
        for el in line:
            print('{} '.format(el), end='')
        print()


def print_cells(cells, headers=True):
    table = []
    if headers is True:
        table = [COLUMNS]

    for cell in cells:
        cell_properties = []
        for column in COLUMNS:
            cell_properties.append(cell[column])
        table.append(cell_properties)

    print_table(table)


def popen_handler(args, stdout=subprocess.PIPE, universal_newlines=True):
    proc = subprocess.Popen(args=args,
                            stdout=stdout,
                            universal_newlines=universal_newlines)
    output, error = proc.communicate()

    return output.split('\n'), error


def iwlist_handler(interface):
    return popen_handler(['iwlist', interface, 'scan'])


def iwconfig_handler(interface):
    return popen_handler(['iwconfig', interface])


def iwlist_parse(lines):
    cells = [[]]
    parsed_cells = []

    for line in lines:
        cell_line = match(line, 'Cell ')
        if cell_line is not None:
            cells.append([])
            line = cell_line[-27:]
        cells[-1].append(line.strip())

    cells = cells[1:]

    for cell in cells:
        parsed_cells.append(parse_cell(cell))

    sort_cells(parsed_cells)

    return parsed_cells


def iwconfig_parse(lines):
    if isinstance(lines, list):
        line = str(lines[0]).strip()

        if line.count('ESSID:') > 0:
            indx = line.index('ESSID:') + 6
            currently_connected = line[indx:].replace('"', '')

            if not currently_connected == 'off/any':
                return currently_connected
    return CURRENTLY_DISCONNECTED_LABEL


def iwlistparse(interface=INTERFACE, switch='all', headers=True):
    currently_connected = CURRENTLY_DISCONNECTED_LABEL
    access_points = []
    error = None
    # Prepare currently connected
    if switch == 'connected':
        lines, error = iwconfig_handler(interface)
        currently_connected = iwconfig_parse(lines)

    # Prepare access points list
    if switch == 'all':
        lines, error = iwlist_handler(interface)
        access_points = iwlist_parse(lines)

    return ParseResult(currently_connected=currently_connected,
                       headers=headers,
                       access_points=access_points,
                       error=error)


def main(interface=INTERFACE):
    """Pretty prints the output of iwlist scan into a table"""
    print('Start variant #1: switch="all"')
    print('[100] here is output')
    parse_result = iwlistparse(switch='all', headers=True)
    print('[200] Parse Result: {}'.format(repr(parse_result)))
    print('[300] Table with headers')
    print_cells(parse_result.access_points, headers=parse_result.headers)
    print()
    print('[310] Table without headers')
    print_cells(parse_result.access_points, headers=False)
    print()
    print('Error: {}'.format(parse_result.error))
    print('-------------------------------------------------------------')
    print()

    print('Start variant #2: switch="connected"')
    print('[400] here is output')
    parse_result = iwlistparse(switch='connected', headers=False)
    print('[500] Parse Result: {}'.format(repr(parse_result)))
    print('[600] Connected to: {}'.format(parse_result.currently_connected))
    print()
    print('Error: {}'.format(parse_result.error))
    print('-------------------------------------------------------------')


if __name__ == '__main__':
    main()
