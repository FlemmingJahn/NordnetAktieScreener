from optparse import OptionParser
import json
import requests

parser = OptionParser()
parser.add_option("-a", "--pe_min", dest="pe_min", default=5,  help="Minimum P/E")
parser.add_option("-b", "--pe_max", dest="pe_max", default=15, help="Maximum P/E")
parser.add_option("-c", "--yield_min", dest="dividend_yield_min", default=5,    help="Minimum Direkte Rente")
parser.add_option("-d", "--yield_max", dest="dividend_yield_max", default=100,  help="Maximum Direkte Rente")
parser.add_option("-e", "--pawn_percentage_min", dest="instrument_pawn_percentage_min", default=75,    help="Minimum Belånings Grad")
parser.add_option("-f", "--pawn_percentage_max", dest="instrument_pawn_percentage_max", default=100,  help="Maximum Belånings Grad")
parser.add_option("-x", "--exclude", dest="stocks_list", default="exclude_list.json",  help="JSON file with List of stocks")
(options, args) = parser.parse_args()

class Nordnet_screener():
    def read_stocks_list_file(self):
        self.stocks_list = []
        if options.stocks_list is not None:
            f = open(options.stocks_list, encoding='utf-8')
            self.stocks_list = json.load(f)

    def setup_nordnet_access(self):
        url = 'https://www.nordnet.dk/markedet'
        r = requests.get(url)

        self.cookies = {}
        self.cookies['NEXT'] = r.cookies['NEXT']
        self.headers = {'client-id': 'NEXT'}

    def __init__(self):
        self.read_stocks_list_file()
        self.setup_nordnet_access()

    def get_stocks_list(self):
        return self.stocks_list

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

    def get_nordnet_stock_info(self, exchange_country, offset):
        url = f'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3{exchange_country}&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset={offset}'
        return requests.get(url, cookies=self.cookies, headers=self.headers)


    def print_header(self, country):
        print("")
        print("*" * 100)
        print(f"* {country}" + " " * (100 - len(country) - 3) + "*")
        print("*" * 100)
        print("%-4s %-35s - %-10s - %-15s - %-5s" % ("#", "Firma", "P/E", "Rente", "Belåning"))
        print("-" * 100)

    def get_ratios_value(self, info, key):
        return self.get_value(info, 'key_ratios_info', key)

    def get_instrument_value(self, info, key):
        """
          Gets a value for a key within the 'instrument_info' keys
             :param info: The stock information from Nordnet
             :return: Returns the value found. If not found 0 is returned
             """
        return self.get_value(info, 'instrument_info', key)

    def get_dividend_yield(self, stock_info):
        """
        Gets the dividend_yield value for a stock
        :param stock_info: The stock information from Nordnet
        :return: Returns the value found. If not found 0 is returned
        """
        return self.get_ratios_value(stock_info, 'dividend_yield')

    def get_pe(self, stock_info):
        """
        Gets the P/E value for a stock
        :param stock_info: The stock information from Nordnet
        :return: Returns the value found. If not found 0 is returned
        """
        return self.get_ratios_value(stock_info, 'pe')

    def get_pawn_percentage(self, stock_info):
        """
        Gets the pawn persentage value for a stock
        :param stock_info: The stock information from Nordnet
        :return: Returns the value found. If not found 0 is returned
        """
        return self.get_instrument_value(stock_info, 'instrument_pawn_percentage')

    def get_value(self, stock_info, info_index, key):
        """
        Gets the value for specific parameter

        :param stock_info: The stock information from Nordnet
        :param key: The key for information to get value for. E.g. "pe"
        :return: Returns the value found. If not found 0 is returned
        """
        try:
            value = stock_info[info_index][key]
            return value
        except:
            return 0

    def get_name(self, stock_info):
        """
        Returns the name for a stock
        :param stock_info: The stock information from Nordnet
        :return: Returns the name found. If not found None is returned

        """
        try:
            return stock_info['instrument_info']['name']

        except:
            return None