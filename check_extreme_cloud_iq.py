##!/bin/python3

import requests, json, re
from datetime import datetime, timedelta
from argparse import ArgumentParser


class ExtreamCloudIQ():

    def __init__(self) -> None:
        
        self.base_uri = 'https://api.extremecloudiq.com'
        self.timeout = 20
        self.header = {
            'Content-type' : 'application/json',
            'Accept' : 'application/json'
        }

    def validate_response(self, res: requests.Response):

        data = res.json()
        if res.status_code in [200, 201, 202, 204]:
            return data
        elif data['error_code'] == 'AUTH_TOKEN_EXPIRED':
            raise TokenExpiredError('Auth token expired')
        else:
            raise ConnectionError(f'{res.status_code}, {data["error_code"]}, {data["error_message"]}')

    def login(self, user, passwd):

        url = f'{self.base_uri}/login'
        data = {
            'username' : user,
            'password' : passwd
        }

        res = requests.post(url, headers=self.header, data=json.dumps(data), timeout=self.timeout)

        data = self.validate_response(res)
        self.token = data['access_token']
        self.header['Authorization'] = f'Bearer {self.token}'

    def logout(self):

        url = f'{self.base_uri}/logout'
        res = requests.post(url=url, headers=self.header, timeout=self.timeout)
        self.validate_response(res)

    def token(self):

        url = f'{self.base_uri}/auth/apitoken'
        data = {
            "description" : "API Token for read devices and alarms.",
            "permissions" : ["device:r", "alert:r"]
        }
        res = requests.post(url, headers=self.header, data=json.dumps(data), timeout=self.timeout)

        #print(res.json())
        return self.validate_response(res)

    def fetch_page(self, url, params: dict, page=1) -> dict:

        params['page'] = page
        res = requests.get(url=url, headers=self.header, params=params, timeout=self.timeout)
        # print(json.dumps(res.json(), indent=2))
        return self.validate_response(res)

    def fetch_remaining(self, url, total_pages: int, params: dict):
            
        data = []
        for page in range(2, total_pages + 1):
            # print(f'------- Page {page} -------') # Test
            data_ = self.fetch_page(url=url, page=page, params=params)['data']
            #print(json.dumps(data_, indent=2))
            data += data_

        return data

    def paged_data(self, url, params: dict):

        res_body = self.fetch_page(url=url, params=params)
        total_pages = res_body['total_pages']
        data = res_body['data']

        if total_pages > 1:
            data += self.fetch_remaining(url=url, total_pages=total_pages, params=params)

        return data

    def device(self):

        url = f'{self.base_uri}/devices'
        params = {
                'views' : 'status,client',
                'fields' : 'hostname,ip_address',
                'limit' : 50,
                'sortField' : 'SN',
                # 'order' : 'ASC'
            }
        data = self.paged_data(url=url, params=params)

        print(json.dumps(data, indent=2))
        return data

    def alarms(self):

        url = f'{self.base_uri}/alerts'
        now = datetime.now()
        start = now - timedelta(days=15)
        params = {
            'limit' : 100,
            'startTime' : int(start.timestamp()),
            'endTime' : int(now.timestamp())
        }

        data = self.paged_data(url, params)
        #print(json.dumps(data, indent=2))
        return data

class TokenExpiredError(Exception):
    pass

class Nagios():

    def __init__(self) -> None:
        self.iq = ExtreamCloudIQ()
        self.args = self.get_args()
        self.iq.header['Authorization'] = 'Bearer ' + self.args.token

    def get_args(self):

        parser = ArgumentParser(description='This script is for monitoring Extream Cloud IQ via REST API for Nagios.')

        parser.add_argument('-u', '--user', required=False, help='Extream Cloud API Username')
        parser.add_argument('-p', '--password', required=False, help='Extreme Cloud user password')
        parser.add_argument('-t', '--token', required=True, help='Bearer token to access API')
        parser.add_argument('-m', '--mode', required=True, help="Check modes: device, alarm, generate-token")
        parser.add_argument('-e', '--exclude', help="Comma separated list of devices to exclude monitoring")

        args = parser.parse_args()
        return args
    
    def mode_device(self):
        
        devices = self.iq.device()

        # print(json.dumps(devices, indent=2))

        issues = []
        excluded = []
        for device in devices:
            if self.check_excluded(device['hostname']):
                excluded.append(device['hostname'])
                continue

            if device['device_admin_state'] != 'MANAGED' or device['connected'] != True:
                issues.append(f'{device["hostname"]} - Admin status: {device["device_admin_state"]}, Connected: {device["connected"]}')
        
        if len(excluded) > 0:
            ex = f'Excluded {len(excluded)}\nExcluded devices: {",".join(excluded)}'
        else: ex = ''


        if len(issues) > 0:
            code = 2
            info = f'CRITICAL: {len(issues)} problem/s detected\n' + '\n'.join(issues) + f'\n{ex}'
        else:
            code = 0
            info = f'OK: No problem detected, Total devices {len(devices)}, {ex}'

        return code, info

    def mode_alarm(self):
        
        alarms = self.iq.alarms()

        summary = []
        for alarm in alarms:
            summary.append(f"{alarm['source']['source_name']}, {alarm['summary']}, {alarm['tags']['location_names']}")

        if len(alarms) > 0:
            code = 2
            info = f'CRITICAL: Alert/s found ({len(alarms)}) \n' + '\n'.join(summary)
        else:
            code = 0
            info = 'OK: No alerts found'
            
        return code, info

    def alert(self, code, info):

        print(info)
        exit(code)

    def generate_token(self):

        if self.args.user == None or self.args.password == None:
            print("Specify the username and password to generate token")
            return {}

        self.iq.login(user=self.args.user, passwd=self.args.password)
        token = self.iq.token()
        
        self.iq.logout()

        print(token['access_token'])
        return token

    def check_excluded(self, device):

        excluded = []
        if self.args.exclude:
            excluded = self.args.exclude.split(',')

        for ex in excluded:
            if re.search(ex, device, re.IGNORECASE):
                return True
            
        return False

if __name__ == '__main__':

    try:
        nagios = Nagios()
        if nagios.args.mode == 'generate-token':
            nagios.generate_token()
            exit()
        elif nagios.args.mode == 'device':
            code, info = nagios.mode_device()
        elif nagios.args.mode == 'alarm':
            code, info = nagios.mode_alarm()
        else:
            code = 1
            info = "Invalid check mode, see -h to for help."

        nagios.alert(code, info)
    
    except TokenExpiredError as e:
        print(f'API Token expired, please renew: {e}')
        exit(2)
    except ConnectionError as e:
        print(f'Connection error, error {e}')
        exit(1)
    except requests.exceptions.ConnectTimeout as e:
        print(f'Connection timedout, error: {e}')
        exit(3)
    except Exception as e:
        print(f'Something went wrong, error: {e}')
        exit(1)

