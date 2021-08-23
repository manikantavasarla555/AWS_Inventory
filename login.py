#!/usr/bin/python3
import time
import wexpect  # pip install wexpect

from inputs import *


def login(userid, role, account):
    print("logging into cloud-tool")
    print(f"user:{userid} - role:{role} - account:{account} Logging in...")
    cmd = f'cloud-tool --region us-east-1 login -u "{userid}" -r "{role}" -a "{account}"'
    print(cmd)
    child = wexpect.spawn(cmd)
    child.expect('MGMT Password: ')
    child.sendline(passwd)

    print(child.before, end='')
    print(f"user:{userid} - role:{role} - account:{account} - Login successful !!")


def main():
    for account_details in accounts:
        # login into the account - assume role to get the keys
        login(user, account_details['role'], account_details['account'])

    time.sleep(30)
    print("Login successful - Inventory Script execution can be started !!")


if __name__ == "__main__":
    print("Login script started...")
    main()
    print("Login script completed !!")
