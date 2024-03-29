import requests
from optparse import OptionParser
import json


parser = OptionParser()
parser.add_option("-a", "--pe_min", dest="pe_min", default=1,  help="Minimum P/E")
parser.add_option("-b", "--pe_max", dest="pe_max", default=10, help="Maximum P/E")
parser.add_option("-c", "--yield_min", dest="dividend_yield_min", default=1,    help="Minimum Direkte Rente")
parser.add_option("-d", "--yield_max", dest="dividend_yield_max", default=100,  help="Maximum Direkte Rente")
parser.add_option("-e", "--pawn_percentage_min", dest="instrument_pawn_percentage_min", default=65,    help="Minimum Belånings Grad")
parser.add_option("-f", "--pawn_percentage_max", dest="instrument_pawn_percentage_max", default=101,  help="Maximum Belånings Grad")
parser.add_option("-x", "--exclude", dest="exclude_stocks", default=None,  help="JSON file with List of stock to exclude ")
(options, args) = parser.parse_args()


options.exclude_stocks = "exclude_list.json"
exclude_list = []
if options.exclude_stocks is not None:
    f = open(options.exclude_stocks)
    exclude_list = json.load(f)


class Nordnet_screener():
    def get_stocks_info(self, exchange_country):
        url = f'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3{exchange_country}&sort_order=desc&sort_attribute=dividend_yield&limit=1&offset={0}'
        r = requests.get(url, cookies=cookies, headers=headers)
        number_of_stocks = r.json()['total_hits']
        list_of_stocks = r.json()["results"]

        number_of_stock_to_be_downloaded = 100
        offset = 1
        while offset < number_of_stocks:
            url = f'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3{exchange_country}&sort_order=desc&sort_attribute=dividend_yield&limit={number_of_stock_to_be_downloaded}&offset={offset}'
            r = requests.get(url, cookies=cookies, headers=headers)
            list_of_stocks += r.json()["results"]
            offset = offset + number_of_stock_to_be_downloaded

        return list_of_stocks


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


def print_info(keyInfo, counter):
    for info in keyInfo['results']:
        symbol = info['instrument_info']['symbol']
        name = get_name_print(info)

        if name in exclude_list["all_stocks"][0]["my_stocks"]:
            continue

        if name in exclude_list["all_stocks"][1]["exclude_stocks"]:
            continue

        pe   = get_ratios_value(info, 'pe', options.pe_min, options.pe_max)
        dividend_yield = get_ratios_value(info, 'dividend_yield', options.dividend_yield_min, options.dividend_yield_max)
        instrument_pawn_percentage = get_instrument_info_value(info, 'instrument_pawn_percentage', options.instrument_pawn_percentage_min, options.instrument_pawn_percentage_max)


        if None in (pe, dividend_yield, instrument_pawn_percentage):
            continue
        if "Fund" not in name:
            print("%-4d %-35s - %-10f - %-15f - %-5d" % (counter, name, pe, dividend_yield, instrument_pawn_percentage))
            counter += 1
    return counter


def loop_over_stocks(counter, exchange_country, country):
    offset = 0
    print("")
    print("*" * 100)
    print(f"* {country}" + " " * (100 - len(country) - 3) + "*")
    print("*" * 100)
    print("%-4s %-35s - %-10s - %-15s - %-5s" % ("#", "Firma", "P/E", "Rente", "Belåning"))
    print("-" * 100)
    while 1:
        url = f'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3{exchange_country}&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset={offset}'

        r = requests.get(url, cookies=cookies, headers=headers)
        key_info = r.json()
        counter = print_info(key_info, counter)
        if offset > key_info['total_hits']:
           break
        offset = offset + 100
    return counter


def get_instrument_info_value(info, key, key_min, key_max):
    return get_value(info, 'instrument_info', key, key_min, key_max)


screener = Nordnet_screener()
# screener.get_stocks_info('DDK')

counter = loop_over_stocks(counter, 'DDK', "Danmark")
counter = loop_over_stocks(counter, 'DSE', "Sverige")
counter = loop_over_stocks(counter, 'DFI', "Finland")
#counter = loop_over_stocks(counter, 'DNO', "Norge")
#counter = loop_over_stocks(counter, 'DDE', "Tyskland")
counter = loop_over_stocks(counter, 'DUS', "USA")
counter = loop_over_stocks(counter, 'DCA', "Canada")

