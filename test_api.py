import requests
import sys

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
r = requests.get('https://www.nordnet.dk/markedet', headers={'User-Agent': ua})
cookies = {c.name: c.value for c in r.cookies}
sys.stderr.write('Cookies: ' + str(cookies) + '\n')
sys.stderr.write('Status1: ' + str(r.status_code) + '\n')

headers = {'client-id': 'NEXT'}

url = 'https://www.nordnet.dk/api/2/instrument_search/query/stocklist?apply_filters=exchange_country%3ADDK&sort_order=desc&sort_attribute=dividend_yield&limit=1&offset=0'
r2 = requests.get(url, cookies=cookies, headers=headers)
sys.stderr.write('Status2: ' + str(r2.status_code) + '\n')
sys.stderr.write('Response: ' + r2.text[:500] + '\n')
sys.stderr.flush()
