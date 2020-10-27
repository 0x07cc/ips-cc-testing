#!/usr/bin/env python3
# ips-cc Testing Entrypoint. Run it in a Docker container.
import subprocess
import os


lightBlue = '\033[1;34m'
lightCyan = '\033[1;36m'
lightGreen = '\033[1;32m'
red = '\033[0;31m'
noColor = '\033[0m'

# Function that returns the command output if successful,
# otherwise it returns a string containing the return code.
def runCommand(cmdList):
    process = subprocess.run(cmdList, stdout=subprocess.PIPE, timeout=5)
    if process.returncode == 0:
        return process.stdout.decode().rstrip("\n")
    else:
        cmdString = " ".join(cmdList)
        return f"Error executing '{cmdString}' Code: {process.returncode}"


print(f"{lightBlue}IPS Testing Environment Entrypoint")
print(f"{noColor}")

# Root privileges
if os.geteuid() != 0:
    print(f"{red}Script not started as root. Aborting.")
    print(f"This script is meant to be executed in a container!{noColor}")
    exit(-1)

longHash = runCommand(['git', '-C', '/root/ips-cc/', 'rev-parse', 'HEAD'])
shrtHash = runCommand(['git', '-C', '/root/ips-cc/', 'rev-parse', '--short', 'HEAD'])
print(f"Current git hash: {lightBlue}{longHash}{noColor}")
print(f"Short hash: {lightBlue}{shrtHash}{noColor}")

print("0: Run testing script\n1: Update IPS via GitHub\n2: Bash")
print("3: Edit GitHub Token\n4: Exit")
inputStr = input("[4]> ")
if inputStr == '0':
    os.system("/usr/bin/env python3 /root/test.py")
elif inputStr == '1':
    r = runCommand(['git', '-C', '/root/ips-cc/', 'pull', '-v', '--ff-only'])
    print(r)
elif inputStr == '2':
    os.system("bash")
elif inputStr == '3':
    # Edit token line in /root/test.py file
    tokenStr = input("New token: ")
    if tokenStr != "":
        inputFile = open("/root/test.py", 'r')
        inputList = inputFile.readlines()
        inputFile.close()
        for line in inputList:
            if "githubToken =" in line:
                lineNum = inputList.index(line)
                inputList[lineNum] = f'githubToken = "{tokenStr}"\n'
                outputFile = open("/root/test.py", 'w')
                outputFile.writelines(inputList)
                outputFile.close()
                print(f"New token added: {tokenStr}")

print("Leaving the container.")
