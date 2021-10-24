import requests
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-a", "--pe_min", dest="pe_min", default=1,  help="Minimum P/E")
parser.add_option("-b", "--pe_max", dest="pe_max", default=15, help="Maximum P/E")
parser.add_option("-c", "--yield_min", dest="dividend_yield_min", default=5,    help="Minimum Direkte Rente")
parser.add_option("-d", "--yield_max", dest="dividend_yield_max", default=100,  help="Maximum Direkte Rente")
parser.add_option("-e", "--pawn_percentage_min", dest="instrument_pawn_percentage_min", default=70,    help="Minimum Belånings Grad")
parser.add_option("-f", "--pawn_percentage_max", dest="instrument_pawn_percentage_max", default=100,  help="Maximum Belånings Grad")
(options, args) = parser.parse_args()


cookies = {}
url = 'https://www.nordnet.dk/markedet'
r = requests.get(url)
cookies['NEXT'] = r.cookies['NEXT']
headers = {'client-id': 'NEXT'}

url = 'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?sort_order=desc&sort_attribute=dividend_yield&limit=100&offset=100'

counter = 1

def get_name_print(info):
    try:
        #return '{:50}'.format(info['instrument_info']['name'])'
        return info['instrument_info']['name']

    except:
        return None



def get_value(info, info_index, key, key_min, key_max):
    try:
        value = info[info_index][key]
        if value <= key_min:
            return None

        if value >= key_max:
            return None

        return value
        #return 'P/E:{:10}'.format(info['key_ratios_info']['pe'])

    except:
        return None


def get_ratios_value(info, key, key_min, key_max):
    return get_value(info, 'key_ratios_info', key, key_min, key_max)


def get_instrument_info_value(info, key, key_min, key_max):
    return get_value(info, 'instrument_info', key, key_min, key_max)


def print_info(keyInfo, counter):
    for info in keyInfo['results']:
        name = get_name_print(info)
        pe   = get_ratios_value(info, 'pe', options.pe_min, options.pe_max)
        dividend_yield = get_ratios_value(info, 'dividend_yield', options.dividend_yield_min, options.dividend_yield_max)
        instrument_pawn_percentage = get_instrument_info_value(info, 'instrument_pawn_percentage', options.instrument_pawn_percentage_min, options.instrument_pawn_percentage_max)

        if None in (pe, dividend_yield, instrument_pawn_percentage):
            continue
        if "Fund" not in name:
            print(f'{counter}:{name} - {pe} - {dividend_yield} - {instrument_pawn_percentage} ')
        counter += 1
    return counter


def loop_over_stocks(counter, exchange_country, country):
    offset = 0
    print(f"******* {country} *******")
    while 1:
        url = f'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3{exchange_country}&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset={offset}'

        r = requests.get(url, cookies=cookies, headers=headers)
        key_info = r.json()
        counter = print_info(key_info, counter)
        if offset > key_info['total_hits']:
           break
        offset = offset + 100
    return counter

counter = loop_over_stocks(counter, 'DDK', "Danmark")
counter = loop_over_stocks(counter, 'DSE', "Sverige")
#counter = loop_over_stocks(counter, 'DFI', "Finland")
#   counter = loop_over_stocks(counter, 'DNO', "Norge")
#counter = loop_over_stocks(counter, 'DDE', "Tyskland")
counter = loop_over_stocks(counter, 'DUS', "USA")
counter = loop_over_stocks(counter, 'DCA', "Canada")

