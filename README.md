# Monitoring Extreme Cloud IQ with Nagios

Nagios check script for monitoring the Extreme Cloud IQ APs.
Written in Python and tested only with Python3.

### Dependencies

- requests

## Installation

1. `pip3 install requests`
2. `cd ~/ && git clone https://github.com/navaneethov/Extreme-Cloud-IQ-Nagios.git`
3. `cp ~/Extreme-Cloud-IQ-Nagios/check_extreme_cloud_iq.py /usr/local/nagios/libexec/`


## Capabilities

- Monitor AP device status
- Monitor Alert present in the web console
- Generate a permanent token

### AP device status

Generate CRITICAL alert if any of the device admin state is not ‘MANAGED’ or connected status is False (it will also list the device/s having issue).

Example:


```bash
./check_extreme_cloud_iq.py --mode device --token <token here>
OK: No problem detected, Total devices 61
```

You can also exclude the devices (RegEx supported, case insensitive)

Example:

```bash
./check_extreme_cloud_iq.py --mode device --token <token here> --exclude ^emea.*
# This will exclude all the device starting with 'emea'
```


### Alerts

Generate CRITICAL alert if any alert present in the system and show the alarms in extra info.

Example:

```bash
./check_extreme_cloud_iq.py --mode alarm --token <token here>
OK: No alerts found
````

## Token

Script can be used in case needed a new permanent token (must pass username and password for this)

Example:

```shell
./check_extreme_cloud_iq.py --mode alarm -u <user> -p <passwd> -t <current token>
<New token will print>
 ```
 
 ## How to use
 
 1. Generate a permanent token.
 2. Create a nagios command
 
 `$USER1$/check_extreme_cloud_iq.py --mode $ARG1$ --token $ARG2$ $ARG3$`
 
 3. By using this command create services for Device status and Alerts, pass the generated token in the 'arg2'.
 4. Apply config.
