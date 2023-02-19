import shared

if 1:
    shared.options.instrument_pawn_percentage_min = 0
    shared.options.instrument_pawn_percentage_max = 60
    shared.options.pe_min = 1
    shared.options.pe_max = 15
    shared.options.dividend_yield_min = 1
    shared.options.dividend_yield_max = 100
else:
    shared.options.instrument_pawn_percentage_min = 75
    shared.options.instrument_pawn_percentage_max = 100
    shared.options.pe_min = 1
    shared.options.pe_max = 15
    shared.options.dividend_yield_min = 5
    shared.options.dividend_yield_max = 100

counter = 1
def print_info(keyInfo, counter):
    for stock_info in keyInfo['results']:
        symbol = stock_info['instrument_info']['symbol']
        name = screener.get_name(stock_info)

        exclude_list = screener.get_stocks_list()
        exclude_these_stocks = exclude_list["all_stocks"][0]["my_stocks"] + exclude_list["all_stocks"][1]["exclude_stocks"]
        if name in exclude_these_stocks:
            continue

        if 'yield_1y' not in stock_info['historical_returns_info']:
            continue

        if stock_info['historical_returns_info']['yield_1y'] > -50:
            continue

        pe = screener.get_pe(stock_info)

        dividend_yield = screener.get_ratios_value(stock_info, 'dividend_yield')
        instrument_pawn_percentage = get_instrument_info_value(stock_info, 'instrument_pawn_percentage', shared.options.instrument_pawn_percentage_min, shared.options.instrument_pawn_percentage_max)

        if dividend_yield is None:
            pass
            #dividend_yield = shared.options.dividend_yield_min

        if None in (pe, dividend_yield, instrument_pawn_percentage):
            continue

        if pe < shared.options.pe_min or pe > shared.options.pe_max:
            continue
        if instrument_pawn_percentage < shared.options.instrument_pawn_percentage_min or instrument_pawn_percentage > shared.options.instrument_pawn_percentage_max:
            continue

        if dividend_yield < shared.options.dividend_yield_min or dividend_yield > shared.options.dividend_yield_max:
            continue

        if "Fund" not in name:
            print("%-4d %-35s - %-10f - %-15f - %-5d" % (counter, name, pe, dividend_yield, instrument_pawn_percentage))
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
    return screener.get_value(info, 'instrument_info', key)

screener = shared.Nordnet_screener()

counter = loop_over_stocks(counter, 'DDK', "Danmark")
counter = loop_over_stocks(counter, 'DSE', "Sverige")
counter = loop_over_stocks(counter, 'DFI', "Finland")
#counter = loop_over_stocks(counter, 'DNO', "Norge")
#counter = loop_over_stocks(counter, 'DDE', "Tyskland")
counter = loop_over_stocks(counter, 'DUS', "USA")
counter = loop_over_stocks(counter, 'DCA', "Canada")

