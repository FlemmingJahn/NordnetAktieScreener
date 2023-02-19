import shared

counter = 1

def return_zero_if_none(value):
    if value is None:
        return 0
    return value

def print_info(keyInfo, counter):
    for stock_info in keyInfo['results']:
        symbol = stock_info['instrument_info']['symbol']
        name = screener.get_name(stock_info)

        exclude_list = screener.get_stocks_list()
        my_stocks = exclude_list["all_stocks"][0]["my_stocks"]
        if name not in my_stocks:
            continue

        pe              = screener.get_pe(stock_info)
        dividend_yield  = screener.get_dividend_yield(stock_info)
        pawn_percentage = screener.get_pawn_percentage(stock_info)

        sell = False
        if shared.options.pe_min < pe < shared.options.pe_max:
            sell = True
        elif shared.options.dividend_yield_min < dividend_yield < shared.options.dividend_yield_max:
            sell = True
        elif shared.options.instrument_pawn_percentage_min < pawn_percentage < shared.options.instrument_pawn_percentage_max:
            sell = True

        if sell:
            print("%-4d %-35s - %-10f - %-15f - %-5d" % (counter, name, pe, dividend_yield, pawn_percentage))
            counter += 1

    return counter


def loop_over_stocks(counter, exchange_country, country):
    offset = 0
    screener.print_header(country)
    while 1:
        r = screener.get_nordnet_stock_info(exchange_country, offset)
        key_info = r.json()
        counter = print_info(key_info, counter)
        if offset > key_info['total_hits']:
           break
        offset = offset + 100
    return counter


def get_instrument_info_value(info, key, key_min, key_max):
    return screener.get_value(info, 'instrument_info', key, key_min, key_max)

screener = shared.Nordnet_screener()

counter = loop_over_stocks(counter, 'DDK', "Danmark")
counter = loop_over_stocks(counter, 'DSE', "Sverige")
#counter = loop_over_stocks(counter, 'DFI', "Finland")
#counter = loop_over_stocks(counter, 'DNO', "Norge")
#counter = loop_over_stocks(counter, 'DDE', "Tyskland")
counter = loop_over_stocks(counter, 'DUS', "USA")
counter = loop_over_stocks(counter, 'DCA', "Canada")

